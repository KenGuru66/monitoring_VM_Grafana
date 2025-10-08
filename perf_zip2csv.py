#!/usr/bin/env python3
"""
perf_zip2csv.py - Extract and parse Huawei storage performance archives

Основан на Huawei_perf_parser_v0.2_parallel.py, но с выводом отдельных CSV по ресурсам.

Usage:
    python perf_zip2csv.py <archive_or_dir> -o <out_dir> [--workers N] [--verbose]
"""

import argparse
import logging
import os
import re
import struct
import sys
import tarfile
import time
import zipfile
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict
from multiprocessing import Manager, Lock, cpu_count

from tqdm import tqdm

# Add Data2csv to path
sys.path.insert(0, str(Path(__file__).parent / 'Data2csv'))

from Data2csv.METRIC_DICT import METRIC_NAME_DICT
from Data2csv.RESOURCE_DICT import RESOURCE_NAME_DICT

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Resource type to output filename mapping
RESOURCE_TO_FILENAME = {
    '207': 'cpu_output.csv',      # Controller/CPU
    '10': 'disk_output.csv',       # Disk
    '11': 'lun_output.csv',        # LUN
    '21': 'host_output.csv',       # Host
    '212': 'fcp_output.csv',       # FC Port
    '216': 'pool_output.csv',      # Storage Pool
}


def construct_data_header(result):
    """Построить заголовок данных."""
    data_header = {}
    if result:
        result = result.groups()
        map_header = result[0]
        map_content = result[1]

        list_map_header = map_header.split(",")
        for each_key in list_map_header:
            list_key_value = each_key.split(":")
            map_key = list_key_value[0].replace('"', '')
            map_value = list_key_value[1].replace('"', '')
            data_header[map_key] = map_value.strip()

        data_header['Map'] = []
        result = re.findall(
            '"([0-9]+)":{"IDs":\\[(("[0-9a-zA-Z]+",?)+)\\],'
            '"Names":\\[(("[.0-9A-Za-z$ \\[\\]\\(\\):_-]*",?)+)\\],'
            '"DataTypes":\\[(([0-9]+,?)+)\\]}',
            map_content
        )
        if result:
            for each_result in result:
                object_type = {}
                object_type['ObjectTypes'] = each_result[0]
                object_type['IDs'] = each_result[1].replace('"', '').split(',')
                object_type['Names'] = each_result[3].replace('"', '').split(',')
                object_type['DataTypes'] = each_result[5].replace('"', '').split(',')
                data_header['Map'].append(object_type)
    return data_header


def construct_data_type(data_header):
    """Построить структуру типов данных."""
    list_data_type = []
    size_collect_once = 0
    if 'Map' in data_header:
        for resource_type in data_header['Map']:
            size_collect_once += (
                len(resource_type['IDs']) *
                len(resource_type['DataTypes']) * 4
            )
            for index_ids, _ in enumerate(resource_type['IDs']):
                for index_data_type in resource_type['DataTypes']:
                    list_index = [
                        resource_type['ObjectTypes'],
                        index_data_type,
                        resource_type['Names'][index_ids], []
                    ]
                    list_data_type.append(list_index)

    return list_data_type, size_collect_once


def process_perf_file_to_memory(file_path: Path) -> Dict[str, list]:
    """
    Парсинг бинарного файла и возврат CSV строк по ресурсам.
    Накапливаем ВСЕ строки в памяти (как в оригинальном скрипте).
    
    Returns:
        Dict {resource_id: [csv_line1, csv_line2, ...]}
    """
    result = {res_id: [] for res_id in RESOURCE_TO_FILENAME.keys()}
    
    try:
        with open(file_path, "rb") as fin:
            bit_correct = fin.read(32)
            bit_msg_version = fin.read(4)
            bit_equip_sn = fin.read(256).decode('utf-8')
            bit_equip_name = fin.read(41).decode('utf-8')
            bit_equip_data_length = fin.read(4)

            process_finish_flag = False

            bit_map_type = fin.read(4)
            bit_map_length, = struct.unpack("<l", fin.read(4))
            bit_map_value = fin.read(bit_map_length - 8)
            
            if len(bit_map_value) < bit_map_length - 8:
                logger.error(f"Read Data Header Failed for {file_path}")
                return None

            while not process_finish_flag:
                result_re = re.match(
                    '{(.*),"Map":{(.*)}}', bit_map_value.decode('utf-8')
                )
                data_header = construct_data_header(result_re)
                list_data_type, size_collect_once = construct_data_type(data_header)

                times_collect = int(
                    (int(data_header['EndTime']) - int(data_header['StartTime'])) /
                    int(data_header['Archive'])
                )

                # Читаем данные блоками
                for i in range(times_collect):
                    buffer_read = fin.read(size_collect_once)
                    if len(buffer_read) < size_collect_once:
                        process_finish_flag = True
                        break
                    
                    for index_in_buffer in range(0, size_collect_once, 4):
                        bytes_read_4 = buffer_read[index_in_buffer: index_in_buffer + 4]
                        bytes_read_int, = struct.unpack("<l", bytes_read_4)
                        list_data_type[int(index_in_buffer / 4)][3].append(str(bytes_read_int))

                # Генерируем timestamps
                start_time = datetime.fromtimestamp(int(data_header['StartTime']))
                next_time = start_time
                time_list = []
                for i, _ in enumerate(list_data_type[0][3]):
                    time_list.append(next_time)
                    next_time += timedelta(seconds=int(data_header['Archive']))

                # STREAMING запись в файлы
                for data_type in list_data_type:
                    resource_id = str(data_type[0])
                    metric_id = str(data_type[1])
                    element = data_type[2]
                    
                    # Пропускаем если нет файла для этого ресурса
                    if resource_id not in RESOURCE_TO_FILENAME:
                        continue
                    
                    resource_name = RESOURCE_NAME_DICT.get(resource_id, f"UNKNOWN_RESOURCE_{resource_id}")
                    metric_name = METRIC_NAME_DICT.get(metric_id, f"UNKNOWN_METRIC_{metric_id}")
                    
                    # Накапливаем строки (как в оригинальном скрипте)
                    str_to_csv = f'{resource_name};{metric_name};{element};'
                    for index, point_value in enumerate(data_type[3]):
                        try:
                            time_string = time_list[index].strftime("%Y-%m-%dT%H:%M:%SZ")
                            time_unix = time.mktime(time_list[index].timetuple())
                            result[resource_id].append(
                                f'{str_to_csv}{point_value};{time_string};{time_unix}\n'
                            )
                        except (ValueError, IndexError):
                            continue

                # Очищаем память
                for data_type in list_data_type:
                    data_type[3].clear()

                bit_map_type = fin.read(4)
                if bit_map_type == b'':
                    process_finish_flag = True
                elif bit_map_type == b'\x00\x00\x00\x00':
                    bit_map_length, = struct.unpack("<l", fin.read(4))
                    if bit_map_length < 8:
                        process_finish_flag = True
                    else:
                        bit_map_value = fin.read(bit_map_length - 8)
                        if len(bit_map_value) < bit_map_length - 8:
                            return None
                else:
                    process_finish_flag = True
                    
    except Exception as exc_info:
        logger.error(f"Error processing {file_path}: {exc_info}")
        return None
    
    return result


def decompress_tgz(file_tgz: Path) -> Path:
    """Распаковать .tgz файл."""
    tar = tarfile.open(file_tgz)
    names = tar.getnames()
    temp_file_path = Path("temp") / f"temp_{os.getpid()}_{time.time()}"
    temp_file_path.mkdir(parents=True, exist_ok=True)
    
    if len(names) == 1:
        tar.extract(names[0], temp_file_path)
        return temp_file_path / names[0]
    
    logger.error(f"perf file content error: {file_tgz}")
    return None


def process_single_tgz_worker(args):
    """
    Worker для обработки одного .tgz файла.
    ТОЧНАЯ КОПИЯ логики из Huawei_perf_parser_v0.2_parallel.py
    """
    tgz_file, output_dir, file_locks = args
    
    try:
        # Decompress
        decompressed_file = decompress_tgz(tgz_file)
        if not decompressed_file:
            return {'success': False, 'stats': {}}
        
        # Process to memory (накапливаем ВСЕ строки)
        csv_lines_by_resource = process_perf_file_to_memory(decompressed_file)
        
        # Cleanup decompressed file
        if decompressed_file.exists():
            decompressed_file.unlink()
            if decompressed_file.parent.exists():
                try:
                    decompressed_file.parent.rmdir()
                except:
                    pass
        
        if csv_lines_by_resource is None:
            return {'success': False, 'stats': {}}
        
        # Write to files ONCE per resource
        stats = {}
        for resource_id, csv_lines in csv_lines_by_resource.items():
            if not csv_lines:
                continue
            
            output_file = output_dir / RESOURCE_TO_FILENAME[resource_id]
            lock = file_locks[resource_id]
            
            lines_count = len(csv_lines)
            with lock:
                with open(output_file, 'a', encoding="utf-8") as fout:
                    fout.writelines(csv_lines)
            
            stats[resource_id] = lines_count
            # Clear memory
            del csv_lines
        
        return {'success': True, 'stats': stats}
        
    except Exception as e:
        logger.error(f"Error in worker for {tgz_file}: {e}")
        return {'success': False, 'stats': {}}


def decompress_zip(zip_path: Path, extract_to: Path = None):
    """Распаковать ZIP архив."""
    if extract_to is None:
        extract_to = Path("temp_zip_extract")
    
    if extract_to.exists():
        shutil.rmtree(extract_to)
    extract_to.mkdir(parents=True)
    
    logger.info(f"Extracting zip archive {zip_path} to {extract_to}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    logger.info(f"Successfully extracted zip archive to {extract_to}")
    return extract_to


def process_archive(archive_path: str, output_dir: str, workers: int = None, verbose: bool = False):
    """
    Основная функция обработки с STREAMING записью.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
    
    archive_path = Path(archive_path)
    output_dir = Path(output_dir)
    
    # Определяем workers
    if workers is None:
        workers = max(1, cpu_count() - 2)
    
    logger.info("="*80)
    logger.info(f"Processing: {archive_path}")
    logger.info(f"Output dir: {output_dir}")
    logger.info(f"Workers: {workers}")
    logger.info("="*80)
    
    # Распаковка ZIP если нужно
    temp_extract_dir = None
    if archive_path.is_file() and archive_path.suffix.lower() == '.zip':
        temp_extract_dir = decompress_zip(archive_path)
        search_path = temp_extract_dir
    elif archive_path.is_dir():
        search_path = archive_path
    else:
        logger.error(f"{archive_path} is not a valid path or zip file!")
        return
    
    # Находим .tgz файлы
    tgz_files = list(search_path.rglob("*.tgz"))
    if not tgz_files:
        logger.error("No .tgz files found!")
        if temp_extract_dir and temp_extract_dir.exists():
            shutil.rmtree(temp_extract_dir)
        return
    
    logger.info(f"Found {len(tgz_files)} .tgz files")
    
    # Инициализируем CSV файлы
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Initializing CSV files...")
    header = "Resource;Metric;Element;Value;Time;UnixTime\n"
    
    for resource_id, filename in RESOURCE_TO_FILENAME.items():
        output_file = output_dir / filename
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(header)
    
    # Создаём locks для thread-safe записи
    manager = Manager()
    file_locks = {res_id: manager.Lock() for res_id in RESOURCE_TO_FILENAME.keys()}
    
    # Параллельная обработка
    logger.info(f"Processing {len(tgz_files)} files with {workers} workers...")
    logger.info("Streaming directly to CSV files (minimal memory usage)...")
    
    all_stats = []
    process_args = [(tgz, output_dir, file_locks) for tgz in tgz_files]
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_single_tgz_worker, arg): arg[0] for arg in process_args}
        
        with tqdm(total=len(futures), desc="Processing", unit="file") as pbar:
            for future in as_completed(futures):
                try:
                    result = future.result()
                    all_stats.append(result)
                except Exception as e:
                    logger.error(f"Failed to process: {e}")
                finally:
                    pbar.update(1)
    
    # Подсчёт статистики
    total_stats = {res_id: 0 for res_id in RESOURCE_TO_FILENAME.keys()}
    for result_dict in all_stats:
        if result_dict.get('success', False):
            for resource_id, count in result_dict.get('stats', {}).items():
                total_stats[resource_id] += count
    
    elapsed = time.time() - start_time
    
    # Выводим статистику
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total_rows = 0
    for resource_id, row_count in sorted(total_stats.items()):
        filename = RESOURCE_TO_FILENAME.get(resource_id, f"resource_{resource_id}_output.csv")
        resource_name = RESOURCE_NAME_DICT.get(resource_id, f"UNKNOWN_{resource_id}")
        print(f"{filename:<30} {row_count:>15,} rows  ({resource_name})")
        total_rows += row_count
    
    print("="*80)
    print(f"{'TOTAL':<30} {total_rows:>15,} rows")
    print(f"{'TIME':<30} {elapsed:>15.1f} seconds ({elapsed/60:.1f} min)")
    print(f"{'THROUGHPUT':<30} {total_rows/elapsed:>15,.0f} rows/sec")
    print("="*80)
    
    logger.info(f"✓ Complete! Output: {output_dir}")
    
    # Cleanup
    if temp_extract_dir and temp_extract_dir.exists():
        logger.info(f"Cleaning up {temp_extract_dir}")
        shutil.rmtree(temp_extract_dir)
    
    temp_path = Path("temp")
    if temp_path.exists():
        for item in temp_path.iterdir():
            if item.is_dir() and item.name.startswith("temp_"):
                try:
                    shutil.rmtree(item)
                except:
                    pass


def main():
    parser = argparse.ArgumentParser(
        description='Extract and parse Huawei storage performance archives',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s archive.zip -o output/
  %(prog)s /path/to/tgz_dir -o output/ --workers 30
  %(prog)s archive.zip -o output/ --verbose

Features:
  - ProcessPoolExecutor for true multicore parallelism
  - Streaming write - minimal memory usage
  - Based on proven Huawei_perf_parser_v0.2_parallel.py logic
        """
    )
    
    parser.add_argument(
        'archive',
        help='Path to .zip archive or directory containing .tgz files'
    )
    
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output directory for CSV files'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: CPU_COUNT - 2)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    try:
        process_archive(
            archive_path=args.archive,
            output_dir=args.output,
            workers=args.workers,
            verbose=args.verbose
        )
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == '__main__':
    main()
