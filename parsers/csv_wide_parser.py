""" script for parsing Huawei performance data - PARALLEL VERSION
    Parallelized for multi-core processing
"""

import inspect
import logging
import sys
from pathlib import Path

# Импорт словарей из parsers/dictionaries/
# Поддержка запуска как модуля и напрямую
try:
    from parsers.dictionaries import METRIC_NAME_DICT, RESOURCE_NAME_DICT, METRIC_CONVERSION
except ImportError:
    # Запуск напрямую из директории parsers
    sys.path.insert(0, str(Path(__file__).parent))
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from dictionaries import METRIC_NAME_DICT, RESOURCE_NAME_DICT, METRIC_CONVERSION


import re
import os
import struct
from datetime import datetime
from datetime import timedelta
import tarfile
import time
import zipfile
import shutil
from multiprocessing import Pool, cpu_count, Manager
from functools import partial
import io

import click
import pandas as pd
import tqdm

# Try to import psutil for smart worker detection
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

LOGDIR = 'log'
LOGFILE = 'process_perf_files.log'
LOGFILE_REPEAT = 'process_perf_files_repeat.log'
if not (Path() / LOGDIR).is_dir():
    (Path() / LOGDIR).mkdir()
logging.root.handlers = []
logging.basicConfig(
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    # handlers=[],
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
log_repeat = logging.getLogger("repeat")

log_format = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")
log_handler = logging.FileHandler(f"{LOGDIR}/{LOGFILE}", mode="a", encoding="utf-8")
log_repeat_handler = logging.FileHandler(f"{LOGDIR}/{LOGFILE_REPEAT}", mode="a", encoding="utf-8")

log_handler.setFormatter(log_format)
log_repeat_handler.setFormatter(log_format)

logger.handlers.clear()
logger.addHandler(log_handler)
log_repeat.handlers.clear()
log_repeat.addHandler(log_repeat_handler)

# Try to import influxdb (optional dependency)
try:
    from influxdb import DataFrameClient
    INFLUXDB_AVAILABLE = True
except ImportError:
    INFLUXDB_AVAILABLE = False
    logger.warning("influxdb module not available, --to_db option will not work")

# default parse such objects:
DEFAULT_RESOURCES = [
    "207", #"Controller"
    "212", #"FC Port"
    "225", #"FC Replication Link"
    "216",  #Storage Pool
    "266", #"Disk Domain"
    "10", #Disk
    "11", #LUN
    "21" # "Host"
]

DEFAULT_METRICS = [
    "18", #Usage
    "22", # "Total IOPS (IO/s)"
    "25", #"Read IOPS (IO/s)"
    "28", #"Write IOPS (IO/s)"
    "23", #"Read bandwidth (MB/s)"
    "26", #"Write bandwidth (MB/s)"
    "1079", #"SCSI IOPS(IO/s)"
    "1073", #"ISCSI IOPS(IO/s)"
    "627", #"NFS operation count per second"
    "1074", #"CIFS operation count per second"
    "240", #"Average queue depth"
    "1158", #"WRITE SAME Command Bandwidth (MB/s)"
    "1154", #"Unmap Command Bandwidth (MB/s)"
    "1162", #"Full Copy Read Request Bandwidth (MB/s)"
    "1166", #"Full Copy Write Request Bandwidth (MB/s)"
    "1170", #"ODX Read Request Bandwidth (MB/s)"
    "1174", #"ODX Write Request Bandwidth (MB/s)
    "1332", #"Post-Process Deduplication Read Bandwidth(MB/s)",#NEW
    "1333", #"Post-Process Deduplication Write Bandwidth(MB/s)",#NEW
    "1334", #"Post-Process Deduplication Fingerprint Read Bandwidth(MB/s)",#NEW
    "1335", #"Post-Process Deduplication Fingerprint Write Bandwidth(MB/s)",#NEW
    "1337", #"Post-Process Deduplication and Reduction Read Bandwidth(MB/s)",#NEW
    "1338", #"Post-Process Deduplication and Reduction Write Bandwidth(MB/s)",#NEW
    "1633", #"Avg. Corrected CPU usage (%)",#NEW
    "260", #"Back-End traffic (MB/s)",
    "261", #"Back-end read traffic (MB/s)",
    "262", #"Back-end write traffic (MB/s)",
    "1298", #"Back-End Partition CPU Usage (%)",#NEW
    "1297", #"Front-End Partition CPU Usage (%)",#NEW
    "68", #Avg. CPU usage (%)
    "1299", #KV CPU Usage (%)
    "1182", #"Read I/O Granularity Distribution: [0K,4K)(%)",#NEW
    "33", #"Read I/O granularity distribution: [4K,8K) (%)",
    "34", #"Read I/O granularity distribution: [8K,16K) (%)",
    "35", #"Read I/O granularity distribution: [16K,32K) (%)",
    "36", #"Read I/O granularity distribution: [32K,64K) (%)",
    "37", #"Read I/O granularity distribution: [64K,128K) (%)",
    "1183", #"Read I/O Granularity Distribution: [128K,+∞)(%)",#NEW
    "1184", #"Write I/O Granularity Distribution: [0K,4K)(%)",#NEW
    "44", #"Write I/O granularity distribution: [4K,8K) (%)",
    "45", #"Write I/O granularity distribution: [8K,16K) (%)",
    "46", #"Write I/O granularity distribution: [16K,32K) (%)",
    "47", #"Write I/O granularity distribution: [32K,64K) (%)",
    "48", #"Write I/O granularity distribution: [64K,128K) (%)",
    "1185", #"Write I/O Granularity Distribution: [128K,+∞)(%)",#NEW
    "1188", #"VAAI Bandwidth (MB/s)",#NEW
    "93", #"Read cache hit ratio (%)"
    "95", #"Write cache hit ratio (%)"
    "333", #"Cache water (%)"
    "384", #"Avg. Read I/O Response Time(us)",
    "385", #"Avg. Write I/O Response Time(us)",
    "24", #"Avg. read I/O size (KB)",
    "27", #"Avg. write I/O size (KB)"
    "228", #Avg. I/O size (KB)
    "369", #"Service Time(us)"
    "808", #Avg. Member Disk Usage (%)
    "812", #Transmitting Bandwidth for replication(KB/s) 
    "813", #Receiving Bandwidth for replication(KB/s) 
    "1075" #"Disk Max. Usage(%)"
]


# -----------------------------------------------------------------------------
def construct_data_header(result):
    """ construct data header
        {
            'EndTime': '1664312940', 'StartTime': '1664312040', 'Archive': '60',
            'CtrlID': '1129',
            'Map': [{
                'ObjectTypes': '10',
                'IDs': ['134234114', '134234112', ...],
                'Names': ['DAE010.2', 'DAE010.0', ...],
                'DataTypes': ['5', '18', ...]
            }]
        }
    """
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


# -----------------------------------------------------------------------------
def construct_data_type(data_header):
    """ construct data type
        ['10', '5', 'DAE010.2', []]
    """
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


# -----------------------------------------------------------------------------
def process_perf_file_to_memory(file_path, resources, metrics, to_db=False):
    """ read binary perf file and return CSV lines as a list
    """
    csv_lines = []
    
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
                logger.error("Read Data Header Failed for %s", file_path)
                return None

            while not process_finish_flag:
                result = re.match(
                    '{(.*),"Map":{(.*)}}', bit_map_value.decode('utf-8')
                )
                data_header = construct_data_header(result)
                list_data_type, size_collect_once = construct_data_type(data_header)

                times_collcet = int(
                    (int(data_header['EndTime'])-int(data_header['StartTime']))/
                    int(data_header['Archive'])
                )

                for i in range(times_collcet):
                    buffer_read = fin.read(size_collect_once)
                    if len(buffer_read) < size_collect_once:
                        process_finish_flag = True
                        break
                    for index_in_buffer in range(0, size_collect_once, 4):
                        bytes_read_4 = buffer_read[index_in_buffer: index_in_buffer + 4]
                        bytes_read_int, = struct.unpack("<l", bytes_read_4)
                        list_data_type[int(index_in_buffer / 4)][3].append(str(bytes_read_int))

                start_time = datetime.fromtimestamp(int(data_header['StartTime']))
                next_time = start_time
                time_list = []
                for i, _ in enumerate(list_data_type[0][3]):
                    time_list.append(next_time)
                    next_time += timedelta(seconds=int(data_header['Archive']))

                # Собираем статистику по неизвестным ID (для логирования)
                unknown_resources = set()
                unknown_metrics = set()
                
                for i, data_type in enumerate(list_data_type):
                    resource_id = str(data_type[0])
                    metric_id = str(data_type[1])
                    
                    if not is_resource_and_datatype_needed(
                        resource_id=data_type[0], metric_id=data_type[1],
                        resources=resources, metrics=metrics, allow_unknown=True
                    ):
                        continue

                    # Проверяем, известны ли ID
                    resource_name = RESOURCE_NAME_DICT.get(resource_id, f"UNKNOWN_RESOURCE_{resource_id}")
                    metric_name = METRIC_NAME_DICT.get(metric_id, f"UNKNOWN_METRIC_{metric_id}")
                    
                    # Собираем ТОЛЬКО те ID, которых НЕТ в словарях (для логирования)
                    # Если ID уже добавлен в словарь (даже с именем UNKNOWN_XXX), warning не нужен
                    if resource_id not in RESOURCE_NAME_DICT:
                        unknown_resources.add(resource_id)
                    if metric_id not in METRIC_NAME_DICT:
                        unknown_metrics.add(metric_id)
                    
                    str_to_csv = ""
                    str_to_csv += resource_name + ';'
                    str_to_csv += metric_name + ';'
                    str_to_csv += data_type[2] + ';'
                    for index, point_value in enumerate(data_type[3]):
                        time_string = time_list[index].strftime("%Y-%m-%dT%H:%M:%SZ")
                        time_qqq = time.mktime(time_list[index].timetuple())
                        
                        # Применяем конверсию единиц измерения если нужно
                        # Для метрик, где сырые данные в других единицах (KB/s→MB/s, us→ms)
                        value = float(point_value)
                        if metric_id in METRIC_CONVERSION:
                            value = value / METRIC_CONVERSION[metric_id]
                        
                        csv_lines.append(
                            f'{str_to_csv}{value};{time_string};{time_qqq}\n'
                        )
                
                # Логируем неизвестные ID если они есть
                if unknown_resources:
                    logger.warning(f"Found {len(unknown_resources)} unknown resource IDs in {file_path}: {sorted(unknown_resources)}")
                if unknown_metrics:
                    logger.warning(f"Found {len(unknown_metrics)} unknown metric IDs in {file_path}: {sorted(unknown_metrics)}")

                bit_map_type = fin.read(4)
                if bit_map_type == '':
                    process_finish_flag = True
                elif bit_map_type == '\x00\x00\x00\x00':
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
        
    return csv_lines


# -----------------------------------------------------------------------------
def process_single_tgz_file(args):
    """
    Process a single .tgz file and write directly to CSV file.
    Memory optimized - streams data to disk instead of accumulating in memory.
    """
    file_path, resources, metrics, to_db, output_file = args
    
    try:
        # Decompress
        decompressed_file_path = decompress_tgz(file_path)
        if not decompressed_file_path:
            return {
                'file': file_path,
                'lines_count': 0,
                'success': False
            }
            
        # Process to memory
        csv_lines = process_perf_file_to_memory(
            file_path=decompressed_file_path,
            resources=resources,
            metrics=metrics,
            to_db=to_db,
        )
        
        # Cleanup decompressed file
        if decompressed_file_path.exists():
            decompressed_file_path.unlink()
        
        if csv_lines is None:
            return {
                'file': file_path,
                'lines_count': 0,
                'success': False
            }
        
        # Write to file immediately and release memory
        lines_count = len(csv_lines)
        with open(output_file, 'a', encoding="utf-8") as fout:
            fout.writelines(csv_lines)
        
        # Clear memory
        del csv_lines
        
        return {
            'file': file_path,
            'lines_count': lines_count,
            'success': True
        }
    except Exception as e:
        logger.error(f"Error in process_single_tgz_file for {file_path}: {e}")
        return {
            'file': file_path,
            'lines_count': 0,
            'success': False
        }


# -----------------------------------------------------------------------------
# filter the resource and metrics
def is_resource_and_datatype_needed(resource_id, metric_id, resources, metrics, allow_unknown=True):
    """
    Проверяет, нужны ли данные ресурса и метрики.
    
    Args:
        allow_unknown: Если True, пропускает неизвестные ID (которых нет в словарях).
                      Они будут записаны как UNKNOWN_RESOURCE_X / UNKNOWN_METRIC_Y
    """
    resource_str = str(resource_id)
    metric_str = str(metric_id)
    
    # Проверяем, запрошены ли эти ID
    resource_requested = resource_str in resources
    metric_requested = metric_str in metrics
    
    # Если allow_unknown=True, принимаем ВСЕ ID (даже неизвестные)
    if allow_unknown:
        return resource_requested and metric_requested
    
    # Иначе проверяем наличие в словарях
    resource_known = resource_str in RESOURCE_NAME_DICT
    metric_known = metric_str in METRIC_NAME_DICT
    
    return resource_requested and metric_requested and resource_known and metric_known

# -----------------------------------------------------------------------------
#decompress zip archive
def decompress_zip(zip_path, extract_to=None):
    """
    Извлекает zip архив во временную директорию
    Возвращает путь к директории с извлеченными файлами
    """
    if extract_to is None:
        extract_to = Path("temp_zip_extract")
    else:
        extract_to = Path(extract_to)
    
    if extract_to.exists():
        shutil.rmtree(extract_to)
    extract_to.mkdir(parents=True)
    
    logger.info(f"Extracting zip archive {zip_path} to {extract_to}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    logger.info(f"Successfully extracted zip archive to {extract_to}")
    return extract_to

# -----------------------------------------------------------------------------
#decompress file
def decompress_tgz(file_tgz):
    tar = tarfile.open(file_tgz)
    names = tar.getnames()
    temp_file_path = Path("temp") / f"temp_{os.getpid()}_{time.time()}"
    if not temp_file_path.is_dir():
        temp_file_path.mkdir(parents=True)
    if len(names) == 1:
        tar.extract(names[0], temp_file_path)
        return temp_file_path / names[0]
    logger.error("perf file content error, perf file: %s", file_tgz)
    return ""

# -----------------------------------------------------------------------------
def split_files_by_sn(files, prefix=None):
    """
    Группирует файлы по серийному номеру (SN) оборудования.
    
    Args:
        files: Список файлов для обработки
        prefix: Опциональный префикс для фильтрации файлов (например, "PerfData_OceanStorDorado5500V6")
    
    Returns:
        Словарь {serial_number: [список файлов]}
    """
    sn_to_perf_file_list = {}
    for file in files:
        # Логируем имя файла для отладки
        logger.info(f"Processing file: {file.name}")
        
        # Если указан префикс, проверяем, что имя файла начинается с этого префикса
        if prefix and not file.name.startswith(prefix):
            logger.info(f"File {file.name} does not match prefix {prefix}, skipping")
            continue

        # Регулярное выражение для поиска серийного номера и SP
        # Формат: PerfData_MODEL_SN_SERIALNUMBER_SP0_...
        file_sn_matches = re.findall(re.compile(r"_SN_([0-9A-Z]+)_SP\d+"), file.name)
        
        if not file_sn_matches:
            # Если совпадения не найдены, выводим предупреждение и пропускаем файл
            logger.warning(f"Could not extract serial number from file name: {file.name}")
            continue
        
        file_sn = file_sn_matches[0]
        if file_sn not in sn_to_perf_file_list:
            sn_to_perf_file_list[file_sn] = []
        sn_to_perf_file_list[file_sn].append(file)
    
    return sn_to_perf_file_list
# -----------------------------------------------------------------------------
def get_model_from_perf_file_name(file):
    return re.findall(re.compile(r"PerfData_(.+?)_SN"), file.name)[0]

# -----------------------------------------------------------------------------
def find_first_invalid_resource(resources):
    for r in resources:
        if r not in RESOURCE_NAME_DICT:
            return r
    return None

# -----------------------------------------------------------------------------
def find_first_invalid_metric(metrics):
    for m in metrics:
        if m not in METRIC_NAME_DICT:
            return m
    return None


# -----------------------------------------------------------------------------
def rename_metric(metric, add_prefix=True):
    if add_prefix:
        res = "hu_"
    else:
        res = ""
    return (
        res + metric.lower().replace(" ", "_")
        .replace("io/s", "iops")
        .replace("i/os", "io")
        .replace("/", "p")
        .replace("(", "").replace(")", "")
        .replace("[", "").replace("]", "")
        .replace(".", "").replace(",", "")
        .replace(":", "")
        .replace("%", "pct")
    )


# -----------------------------------------------------------------------------
def determine_optimal_workers_for_parsing(num_workers=None):
    """
    Определяет оптимальное количество worker процессов для парсинга.
    
    Учитывает:
    - Количество CPU ядер
    - Доступную память
    - Текущую загрузку системы
    """
    if num_workers is not None and num_workers > 0:
        return num_workers
    
    cpu_cores = cpu_count()
    
    # Базовое количество workers
    if cpu_cores <= 4:
        base_workers = max(1, cpu_cores - 1)
    elif cpu_cores <= 8:
        base_workers = cpu_cores - 1
    elif cpu_cores <= 16:
        # Для 16 ядер используем 12-14 workers (оставляем 2 ядра системе)
        base_workers = cpu_cores - 2
    elif cpu_cores <= 32:
        # Для больших систем - оставляем больше запаса
        base_workers = min(20, cpu_cores - 4)
    else:
        base_workers = 20  # Максимум 20 workers для парсинга
    
    # Если psutil доступен, учитываем память и загрузку
    if PSUTIL_AVAILABLE:
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024**3)
        
        # Оценка: ~500MB на worker для парсинга (с учетом декомпрессии)
        memory_per_worker_gb = 0.5
        max_workers_by_memory = int(available_gb / memory_per_worker_gb)
        
        # Учитываем загрузку CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent > 70:
            base_workers = max(1, int(base_workers * 0.7))
        elif cpu_percent > 50:
            base_workers = max(1, int(base_workers * 0.85))
        
        # Финальное значение с учетом памяти
        final_workers = min(base_workers, max_workers_by_memory)
    else:
        final_workers = base_workers
    
    return max(1, final_workers)

# -----------------------------------------------------------------------------
def process_perf_file_tgz_dir(input_path, output_path, is_delete_after_parse, resources, metrics, to_db=False, prefix=None, num_workers=None):
    logger.info("%s: start processing  %s", inspect.stack()[0][3], input_path)
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    # Определяем количество worker процессов
    optimal_workers = determine_optimal_workers_for_parsing(num_workers)
    
    if PSUTIL_AVAILABLE:
        mem = psutil.virtual_memory()
        cpu_cores = cpu_count()
        logger.info(f"System resources: {cpu_cores} CPU cores, {mem.total / (1024**3):.1f} GB RAM ({mem.available / (1024**3):.1f} GB available)")
        logger.info(f"CPU load: {psutil.cpu_percent(interval=0.1):.1f}%")
    else:
        logger.info(f"System resources: {cpu_count()} CPU cores (psutil not available)")
    
    if num_workers is not None:
        logger.info(f"Using {optimal_workers} worker processes (requested: {num_workers})")
    else:
        logger.info(f"Using {optimal_workers} worker processes (auto-detected)")
    
    num_workers = optimal_workers
    
    # Проверяем, является ли входной путь zip файлом
    temp_extract_dir = None
    original_input_path = input_path
    
    if input_path.is_file() and input_path.suffix.lower() == '.zip':
        logger.info("Input is a zip archive, extracting...")
        temp_extract_dir = decompress_zip(input_path)
        input_path = temp_extract_dir
        logger.info(f"Working with extracted directory: {input_path}")
    elif not input_path.is_dir():
        logger.error("%s is not a valid path or zip file!", input_path)
        return

    # Рекурсивный поиск всех .tgz файлов
    files = list(input_path.rglob("*.tgz"))
    if len(files) == 0:
        logger.warning("There are no perf files yet in %s", input_path)
        if temp_extract_dir and temp_extract_dir.exists():
            logger.info(f"Cleaning up temporary directory {temp_extract_dir}")
            shutil.rmtree(temp_extract_dir)
        return

    logger.info(f"Found {len(files)} .tgz files")
    
    sn_to_perf_file_list = split_files_by_sn(files, prefix=prefix)

    for serial, sn_files in sn_to_perf_file_list.items():
        logger.info("Processing array %s with %d files", serial, len(sn_files))
        sn_files.sort()

        output_csv_file_name = f'{serial}.csv'
        output_csv_file_path = output_path / output_csv_file_name

        logger.info(f"Writing to CSV: {output_csv_file_path}")
        
        try:
            # Prepare arguments for parallel processing
            # Each worker writes directly to the output file
            process_args = [(f, resources, metrics, to_db, output_csv_file_path) for f in sn_files]
            
            # Process files in parallel
            with Pool(processes=num_workers) as pool:
                # Use imap_unordered for better performance and progress tracking
                results = list(tqdm.tqdm(
                    pool.imap_unordered(process_single_tgz_file, process_args),
                    total=len(sn_files),
                    desc=f"Processing {serial}"
                ))
            
            # Log results
            total_lines = 0
            for result in results:
                if result['success']:
                    total_lines += result['lines_count']
                    logger.info(f"Successfully processed {result['file'].name} ({result['lines_count']:,} lines)")
                else:
                    logger.error(f"Failed to process {result['file'].name}")
            
            # Cleanup source files if needed
            if not temp_extract_dir:
                for file_info in results:
                    file = file_info['file']
                    if is_delete_after_parse:
                        if file.exists():
                            file.unlink()
                    else:
                        parsed_files_path = original_input_path / "parsed_files"
                        if not parsed_files_path.is_dir():
                            parsed_files_path.mkdir()
                        if file.exists():
                            file.replace(parsed_files_path / file.name)
                    
            logger.info(f"Finished writing to {output_csv_file_path}")
        except Exception as e:
            logger.error(f"Error writing to {output_csv_file_path}: {str(e)}")
    
    # Очистка временной директории после обработки zip архива
    if temp_extract_dir and temp_extract_dir.exists():
        logger.info(f"Cleaning up temporary directory {temp_extract_dir}")
        shutil.rmtree(temp_extract_dir)
        
    # Cleanup temp directories
    temp_path = Path("temp")
    if temp_path.exists():
        for item in temp_path.iterdir():
            if item.is_dir() and item.name.startswith("temp_"):
                try:
                    shutil.rmtree(item)
                except:
                    pass

# -----------------------------------------------------------------------------
def check_resource_existance(resources):
    """ Resource existence
    """
    first_invalid_resource = find_first_invalid_resource(resources)
    if first_invalid_resource:
        logger.error("invalid resource type:%s", find_first_invalid_resource)
        return False
    return True

# -----------------------------------------------------------------------------
def check_metric_existance(metrics):
    """ Metric existence
    """
    first_invalid_metric = find_first_invalid_metric(metrics)
    if first_invalid_metric:
        logger.error("invalid metric type: %s", first_invalid_metric)
        return False
    return True

# -----------------------------------------------------------------------------
def make_dirs(log_path, output_path):
    """ make output folders is not exists
    """
    if not log_path.is_dir():
        log_path.mkdir(parents=True)
    if not output_path.is_dir():
        output_path.mkdir(parents=True)


# -----------------------------------------------------------------------------
@click.command()
@click.option("-i", "--input_path", type=click.Path(exists=True), required=True, help='Path to directory with .tgz files or a .zip archive')
@click.option("-o", "--output_path", type=click.Path(), required=True, help='Path to output directory for CSV files')
@click.option("-l", "--log_path", type=click.Path(), default='log', help='Path to log directory')
@click.option("-d", "--is_delete_after_parse", is_flag=True, default=False, help='Delete source files after parsing')
@click.option("-r", "--resources", multiple=True, default=DEFAULT_RESOURCES, help='Resource types to collect (comma-separated)')
@click.option("-m", "--metrics", multiple=True, default=DEFAULT_METRICS, help='Metric types to collect (comma-separated)')
@click.option("-p", "--prefix", type=click.STRING, required=False, default=None, help='Optional: Filter files by name prefix (e.g., "PerfData_OceanStorDorado5500V6"). If not specified, all .tgz files in the archive will be processed.')
@click.option("-e", "--ext", type=click.STRING, default="tgz", help='File extension to search for')
@click.option("--to_db", is_flag=True, show_default=True, required=False, default=False, help='Send data to InfluxDB')
@click.option("-w", "--num_workers", type=int, default=None, help='Number of parallel workers (default: CPU count - 1)')
@click.option("--all-metrics", is_flag=True, default=False, help='Parse ALL metrics and resources from METRIC_DICT and RESOURCE_DICT (instead of DEFAULT lists)')
def huawei_collect(
    input_path, output_path, log_path, is_delete_after_parse, resources,
    metrics, prefix, ext, to_db, num_workers, all_metrics
):
    """ process collected data - PARALLEL VERSION
    """
    logger.info("%s: Start", inspect.stack()[0][3])
    logger.info(f"Available CPU cores: {cpu_count()}")
    
    # Если установлен флаг --all-metrics, используем ВСЕ метрики и ресурсы из словарей
    if all_metrics:
        resources = tuple(RESOURCE_NAME_DICT.keys())
        metrics = tuple(METRIC_NAME_DICT.keys())
        logger.info(f"🔥 ALL-METRICS MODE: Parsing ALL resources ({len(resources)}) and ALL metrics ({len(metrics)})")
    else:
        logger.info(f"📊 DEFAULT MODE: Parsing {len(resources)} resources and {len(metrics)} metrics")
    
    make_dirs(Path(log_path), Path(output_path))
    process_perf_file_tgz_dir(
        input_path=input_path,
        output_path=output_path,
        is_delete_after_parse=is_delete_after_parse,
        resources=resources,
        metrics=metrics,
        prefix=prefix,
        to_db=to_db,
        num_workers=num_workers,
    )
    logger.info("%s: done", inspect.stack()[0][3])

    logger.info("Process End!")


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    huawei_collect()

