#!/usr/bin/env python3
"""
perf_zip2csv_wide.py - Extract and parse Huawei storage performance archives (WIDE FORMAT)

Outputs data in wide format compatible with perfmonkey format:
- One row per timestamp with metrics as columns
- CSV format with comma delimiter
- Specific headers for each resource type

Usage:
    python perf_zip2csv_wide.py <archive_or_dir> -o <out_dir> [--workers N] [--verbose]
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
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from multiprocessing import Manager, cpu_count

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

# Resource configuration
RESOURCE_CONFIG = {
    '207': {  # Controller
        'filename': 'cpu_output.csv',
        'prefix': 'CPUPERF',
        'meta_fields': ['Serial', 'Slot', 'Type'],
        'metrics': [
            '93',   # Read cache hit ratio (%)
            '95',   # Write cache hit ratio (%)
            '333',  # Cache water (%)
            '5',    # Max. bandwidth (MB/s)
            '19',   # Queue length
            '21',   # Block bandwidth (MB/s)
            '22',   # Total IOPS (IO/s)
            '23',   # Read bandwidth (MB/s)
            '24',   # Avg. read I/O size (KB)
            '25',   # Read IOPS (IO/s)
            '26',   # Write bandwidth (MB/s)
            '27',   # Avg. write I/O size (KB)
            '28',   # Write IOPS (IO/s)
            '1182', # Read I/O granularity distribution: [0K,4K) (%)
            '33',   # Read I/O granularity distribution: [4K,8K) (%)
            '34',   # Read I/O granularity distribution: [8K,16K) (%)
            '35',   # Read I/O granularity distribution: [16K,32K) (%)
            '36',   # Read I/O granularity distribution: [32K,64K) (%)
            '37',   # Read I/O granularity distribution: [64K,128K) (%)
            '1183', # Read I/O granularity distribution: [128K,+∞) (%)
            '1184', # Write I/O granularity distribution: [0K,4K) (%)
            '44',   # Write I/O granularity distribution: [4K,8K) (%)
            '45',   # Write I/O granularity distribution: [8K,16K) (%)
            '46',   # Write I/O granularity distribution: [16K,32K) (%)
            '47',   # Write I/O granularity distribution: [32K,64K) (%)
            '48',   # Write I/O granularity distribution: [64K,128K) (%)
            '1185', # Write I/O granularity distribution: [128K,+∞) (%)
            '265',  # Ratio of read I/Os to total I/Os (%)
            '370',  # Avg. I/O Response Time (us)
            '384',  # Avg. Read I/O Response Time (us)
            '385',  # Avg. Write I/O Response Time (us)
            '68',   # Avg. CPU usage (%)
            '1299', # KV CPU Usage (%)
            '1075', # Disk Max. Usage (%)
        ]
    },
    '10': {  # Disk (RAID Group)
        'filename': 'disk_output.csv',
        'prefix': 'RGPERF',
        'meta_fields': ['Serial', 'MpCnt', 'Rg', 'PgCnt', 'LdCnt', 'Alias'],
        'metrics': [
            '5',    # Max. bandwidth (MB/s)
            '18',   # Usage (%)
            '19',   # Queue length
            '21',   # Block bandwidth (MB/s)
            '22',   # Total IOPS (IO/s)
            '23',   # Read bandwidth (MB/s)
            '24',   # Avg. read I/O size (KB)
            '25',   # Read IOPS (IO/s)
            '26',   # Write bandwidth (MB/s)
            '27',   # Avg. write I/O size (KB)
            '28',   # Write IOPS (IO/s)
            '1182', # Read I/O granularity distribution: [0K,4K) (%)
            '33',   # Read I/O granularity distribution: [4K,8K) (%)
            '34',   # Read I/O granularity distribution: [8K,16K) (%)
            '35',   # Read I/O granularity distribution: [16K,32K) (%)
            '36',   # Read I/O granularity distribution: [32K,64K) (%)
            '37',   # Read I/O granularity distribution: [64K,128K) (%)
            '1183', # Read I/O granularity distribution: [128K,+∞) (%)
            '1184', # Write I/O granularity distribution: [0K,4K) (%)
            '44',   # Write I/O granularity distribution: [4K,8K) (%)
            '45',   # Write I/O granularity distribution: [8K,16K) (%)
            '46',   # Write I/O granularity distribution: [16K,32K) (%)
            '47',   # Write I/O granularity distribution: [32K,64K) (%)
            '48',   # Write I/O granularity distribution: [64K,128K) (%)
            '1185', # Write I/O granularity distribution: [128K,+∞) (%)
            '265',  # Ratio of read I/Os to total I/Os (%)
            '370',  # Avg. I/O Response Time (us)
            '384',  # Avg. Read I/O Response Time (us)
            '385',  # Avg. Write I/O Response Time (us)
        ]
    },
    '11': {  # LUN
        'filename': 'lun_output.csv',
        'prefix': 'LDEVPERF',
        'meta_fields': ['Serial', 'DefMp', 'DaCnt', 'Rg', 'Ld', 'Alias'],
        'metrics': [
            '5',    # Max. bandwidth (MB/s)
            '19',   # Queue length
            '21',   # Block bandwidth (MB/s)
            '22',   # Total IOPS (IO/s)
            '23',   # Read bandwidth (MB/s)
            '24',   # Avg. read I/O size (KB)
            '25',   # Read IOPS (IO/s)
            '26',   # Write bandwidth (MB/s)
            '27',   # Avg. write I/O size (KB)
            '28',   # Write IOPS (IO/s)
            '1182', # Read I/O granularity distribution: [0K,4K) (%)
            '33',   # Read I/O granularity distribution: [4K,8K) (%)
            '34',   # Read I/O granularity distribution: [8K,16K) (%)
            '35',   # Read I/O granularity distribution: [16K,32K) (%)
            '36',   # Read I/O granularity distribution: [32K,64K) (%)
            '37',   # Read I/O granularity distribution: [64K,128K) (%)
            '1183', # Read I/O granularity distribution: [128K,+∞) (%)
            '1184', # Write I/O granularity distribution: [0K,4K) (%)
            '44',   # Write I/O granularity distribution: [4K,8K) (%)
            '45',   # Write I/O granularity distribution: [8K,16K) (%)
            '46',   # Write I/O granularity distribution: [16K,32K) (%)
            '47',   # Write I/O granularity distribution: [32K,64K) (%)
            '48',   # Write I/O granularity distribution: [64K,128K) (%)
            '1185', # Write I/O granularity distribution: [128K,+∞) (%)
            '265',  # Ratio of read I/Os to total I/Os (%)
            '370',  # Avg. I/O Response Time (us)
            '384',  # Avg. Read I/O Response Time (us)
            '385',  # Avg. Write I/O Response Time (us)
            '93',   # Read cache hit ratio (%)
            '95',   # Write cache hit ratio (%)
        ]
    },
    '21': {  # Host
        'filename': 'host_output.csv',
        'prefix': 'HAPERF',
        'meta_fields': ['Serial', 'DefMp', 'DaCnt', 'RgCnt', 'PgCnt', 'Alias'],
        'metrics': [
            '5',    # Max. bandwidth (MB/s)
            '19',   # Queue length
            '21',   # Block bandwidth (MB/s)
            '22',   # Total IOPS (IO/s)
            '23',   # Read bandwidth (MB/s)
            '24',   # Avg. read I/O size (KB)
            '25',   # Read IOPS (IO/s)
            '26',   # Write bandwidth (MB/s)
            '27',   # Avg. write I/O size (KB)
            '28',   # Write IOPS (IO/s)
            '1182', # Read I/O granularity distribution: [0K,4K) (%)
            '33',   # Read I/O granularity distribution: [4K,8K) (%)
            '34',   # Read I/O granularity distribution: [8K,16K) (%)
            '35',   # Read I/O granularity distribution: [16K,32K) (%)
            '36',   # Read I/O granularity distribution: [32K,64K) (%)
            '37',   # Read I/O granularity distribution: [64K,128K) (%)
            '1183', # Read I/O granularity distribution: [128K,+∞) (%)
            '1184', # Write I/O granularity distribution: [0K,4K) (%)
            '44',   # Write I/O granularity distribution: [4K,8K) (%)
            '45',   # Write I/O granularity distribution: [8K,16K) (%)
            '46',   # Write I/O granularity distribution: [16K,32K) (%)
            '47',   # Write I/O granularity distribution: [32K,64K) (%)
            '48',   # Write I/O granularity distribution: [64K,128K) (%)
            '1185', # Write I/O granularity distribution: [128K,+∞) (%)
            '265',  # Ratio of read I/Os to total I/Os (%)
            '370',  # Avg. I/O Response Time (us)
            '384',  # Avg. Read I/O Response Time (us)
            '385',  # Avg. Write I/O Response Time (us)
        ]
    },
    '212': {  # FC Port
        'filename': 'fcp_output.csv',
        'prefix': 'PORTPERF',
        'meta_fields': ['Serial', 'Slot', 'Port', 'Mode', 'Alias'],
        'metrics': [
            '5',    # Max. bandwidth (MB/s)
            '18',   # Usage (%)
            '19',   # Queue length
            '21',   # Block bandwidth (MB/s)
            '22',   # Total IOPS (IO/s)
            '23',   # Read bandwidth (MB/s)
            '24',   # Avg. read I/O size (KB)
            '25',   # Read IOPS (IO/s)
            '26',   # Write bandwidth (MB/s)
            '27',   # Avg. write I/O size (KB)
            '28',   # Write IOPS (IO/s)
            '1182', # Read I/O granularity distribution: [0K,4K) (%)
            '33',   # Read I/O granularity distribution: [4K,8K) (%)
            '34',   # Read I/O granularity distribution: [8K,16K) (%)
            '35',   # Read I/O granularity distribution: [16K,32K) (%)
            '36',   # Read I/O granularity distribution: [32K,64K) (%)
            '37',   # Read I/O granularity distribution: [64K,128K) (%)
            '1183', # Read I/O granularity distribution: [128K,+∞) (%)
            '1184', # Write I/O granularity distribution: [0K,4K) (%)
            '44',   # Write I/O granularity distribution: [4K,8K) (%)
            '45',   # Write I/O granularity distribution: [8K,16K) (%)
            '46',   # Write I/O granularity distribution: [16K,32K) (%)
            '47',   # Write I/O granularity distribution: [32K,64K) (%)
            '48',   # Write I/O granularity distribution: [64K,128K) (%)
            '1185', # Write I/O granularity distribution: [128K,+∞) (%)
            '265',  # Ratio of read I/Os to total I/Os (%)
            '370',  # Avg. I/O Response Time (us)
            '384',  # Avg. Read I/O Response Time (us)
            '385',  # Avg. Write I/O Response Time (us)
            '812',  # Transmitting Bandwidth for Replication (KB/s)
            '813',  # Receiving Bandwidth for Replication (KB/s)
            '1140', # Avg. Write I/O Link Transmission Latency (us)
            '1139', # Avg. Read I/O Link Transmission Latency (us)
        ]
    },
    '216': {  # Storage Pool
        'filename': 'pool_output.csv',
        'prefix': 'POOLPERF',
        'meta_fields': ['Serial', 'Mode', 'Alias', 'State', 'Alias2'],
        'metrics': [
            '1090', # Data Reduction Ratio
            '1091', # Deduplication Ratio
            '1092', # Compression Ratio
            '1093', # Overall Space Saving Ratio
            '1094', # Thin LUN Space Saving Rate (%)
            '808',  # Average usage of member disks (%)
            '19',   # Queue length
            '21',   # Block bandwidth (MB/s)
            '22',   # Total IOPS (IO/s)
            '23',   # Read bandwidth (MB/s)
            '24',   # Avg. read I/O size (KB)
            '25',   # Read IOPS (IO/s)
            '26',   # Write bandwidth (MB/s)
            '27',   # Avg. write I/O size (KB)
            '28',   # Write IOPS (IO/s)
            '1182', # Read I/O granularity distribution: [0K,4K) (%)
            '33',   # Read I/O granularity distribution: [4K,8K) (%)
            '34',   # Read I/O granularity distribution: [8K,16K) (%)
            '35',   # Read I/O granularity distribution: [16K,32K) (%)
            '36',   # Read I/O granularity distribution: [32K,64K) (%)
            '37',   # Read I/O granularity distribution: [64K,128K) (%)
            '1183', # Read I/O granularity distribution: [128K,+∞) (%)
            '1184', # Write I/O granularity distribution: [0K,4K) (%)
            '44',   # Write I/O granularity distribution: [4K,8K) (%)
            '45',   # Write I/O granularity distribution: [8K,16K) (%)
            '46',   # Write I/O granularity distribution: [16K,32K) (%)
            '47',   # Write I/O granularity distribution: [32K,64K) (%)
            '48',   # Write I/O granularity distribution: [64K,128K) (%)
            '1185', # Write I/O granularity distribution: [128K,+∞) (%)
            '258',  # Back-end read requests per second
            '259',  # Back-end write requests per second
            '261',  # Back-end read traffic (MB/s)
            '262',  # Back-end write traffic (MB/s)
            '265',  # Ratio of read I/Os to total I/Os (%)
            '271',  # BackEnd Read Response Time (us)
            '272',  # BackEnd Write Response Time (us)
            '370',  # Avg. I/O Response Time (us)
            '384',  # Avg. Read I/O Response Time (us)
            '385',  # Avg. Write I/O Response Time (us)
        ]
    }
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


def extract_serial_from_filename(filename: str) -> str:
    """Extract serial number from filename."""
    # Try pattern like: PerfData_OceanStorDorado5000V6_SN_2102355TJUFSQ4100015_SP0_...
    match = re.search(r'_SN_([0-9A-Z]+)_', filename)
    if match:
        return match.group(1)
    return '111111'  # Default


def parse_element_metadata(element: str, resource_id: str) -> dict:
    """
    Parse element name to extract metadata fields.
    
    Examples:
    - Controller: "CTE0-A" -> Slot="0A", Type="CPU"
    - Disk: "CTE0.1" -> Rg="CTE0.1"
    - LUN: "prd.zvirt.01" -> Ld="prd.zvirt.01"
    - Host: "dc1_zvirtprod02" -> Alias="dc1_zvirtprod02"
    - FC Port: "CTE0.A.IOM0.P0" -> Port="CTE0.A.IOM0.P0"
    - Pool: "StoragePool001" -> Alias="StoragePool001"
    """
    metadata = {}
    
    if resource_id == '207':  # Controller
        # Extract Slot from element like "CTE0-A" or "CTE0-B"
        metadata['Slot'] = element.replace('CTE', '').replace('-', '')
        metadata['Type'] = "'CPU'"
    elif resource_id == '10':  # Disk (RG)
        metadata['MpCnt'] = "'1'"
        metadata['Rg'] = element
        metadata['PgCnt'] = "'1'"
        metadata['LdCnt'] = "'1'"
        metadata['Alias'] = "'-'"
    elif resource_id == '11':  # LUN
        metadata['DefMp'] = "'?'"
        metadata['DaCnt'] = "'1'"
        metadata['Rg'] = "'01-01'"
        metadata['Ld'] = element
        metadata['Alias'] = "'-'"
    elif resource_id == '21':  # Host
        metadata['DefMp'] = "'1'"
        metadata['DaCnt'] = "'1'"
        metadata['RgCnt'] = "'1'"
        metadata['PgCnt'] = "'1'"
        metadata['Alias'] = element
    elif resource_id == '212':  # FC Port
        metadata['Slot'] = "'1'"
        metadata['Port'] = element
        metadata['Mode'] = "'Tgt'"
        metadata['Alias'] = "'---'"
    elif resource_id == '216':  # Storage Pool
        metadata['Mode'] = "'AOU'"
        metadata['Alias'] = element
        metadata['State'] = "'POLN'"
        metadata['Alias2'] = element
    
    return metadata


def process_perf_file_to_wide_format(file_path: Path, serial_number: str) -> Dict[str, dict]:
    """
    Парсинг бинарного файла и возврат данных в wide format.
    
    Returns:
        Dict {
            resource_id: {
                element_name: {
                    timestamp: {metric_id: value, ...}
                }
            }
        }
    """
    result = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    
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

                # Организуем данные по ресурсам/элементам/timestamp/метрикам
                for data_type in list_data_type:
                    resource_id = str(data_type[0])
                    metric_id = str(data_type[1])
                    element = data_type[2]
                    
                    # Пропускаем неизвестные ресурсы
                    if resource_id not in RESOURCE_CONFIG:
                        continue
                    
                    # Сохраняем только нужные метрики
                    if metric_id not in RESOURCE_CONFIG[resource_id]['metrics']:
                        continue
                    
                    for index, point_value in enumerate(data_type[3]):
                        try:
                            timestamp = time_list[index]
                            result[resource_id][element][timestamp][metric_id] = point_value
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


def format_timestamp(dt: datetime) -> str:
    """Format timestamp as MM/DD/YY HH:MM:SS"""
    return dt.strftime('%m/%d/%y %H:%M:%S')


def write_wide_format_csv(data: dict, serial_number: str, output_dir: Path, file_locks: dict):
    """
    Write data in wide format to CSV files.
    
    data: {
        resource_id: {
            element_name: {
                timestamp: {metric_id: value, ...}
            }
        }
    }
    """
    stats = {}
    
    for resource_id, elements_data in data.items():
        if resource_id not in RESOURCE_CONFIG:
            continue
        
        config = RESOURCE_CONFIG[resource_id]
        output_file = output_dir / config['filename']
        lock = file_locks[resource_id]
        
        # Собираем все строки для этого ресурса
        rows = []
        row_num = 1
        
        for element, timestamps_data in sorted(elements_data.items()):
            for timestamp, metrics in sorted(timestamps_data.items()):
                # Формируем строку
                row_parts = [config['prefix'], str(row_num)]
                
                # Даты
                time_str = format_timestamp(timestamp)
                row_parts.extend([time_str, time_str])
                
                # Serial
                row_parts.append(serial_number)
                
                # Metadata
                metadata = parse_element_metadata(element, resource_id)
                for field in config['meta_fields']:
                    if field == 'Serial':
                        continue
                    row_parts.append(metadata.get(field, "'-'"))
                
                # Метрики в порядке из конфига
                for metric_id in config['metrics']:
                    value = metrics.get(metric_id, '0')
                    row_parts.append(value)
                
                rows.append(','.join(row_parts) + '\n')
                row_num += 1
        
        # Записываем в файл с блокировкой
        if rows:
            with lock:
                with open(output_file, 'a', encoding='utf-8') as f:
                    f.writelines(rows)
            
            stats[resource_id] = len(rows)
    
    return stats


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
    """Worker для обработки одного .tgz файла."""
    tgz_file, output_dir, file_locks = args
    
    try:
        # Extract serial from filename
        serial_number = extract_serial_from_filename(tgz_file.name)
        
        # Decompress
        decompressed_file = decompress_tgz(tgz_file)
        if not decompressed_file:
            return {'success': False, 'stats': {}}
        
        # Process to wide format
        wide_data = process_perf_file_to_wide_format(decompressed_file, serial_number)
        
        # Cleanup decompressed file
        if decompressed_file.exists():
            decompressed_file.unlink()
            if decompressed_file.parent.exists():
                try:
                    decompressed_file.parent.rmdir()
                except:
                    pass
        
        if wide_data is None:
            return {'success': False, 'stats': {}}
        
        # Write to CSV files
        stats = write_wide_format_csv(wide_data, serial_number, output_dir, file_locks)
        
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


def create_csv_headers(output_dir: Path):
    """Create CSV headers for all resource types."""
    for resource_id, config in RESOURCE_CONFIG.items():
        output_file = output_dir / config['filename']
        
        # Build header
        header_parts = [config['prefix'], '#', 'BgnDateTime', 'EndDateTime']
        
        # Add all meta fields including Serial
        for field in config['meta_fields']:
            header_parts.append(field)
        
        # Add metric names
        for metric_id in config['metrics']:
            metric_name = METRIC_NAME_DICT.get(metric_id, f"UNKNOWN_METRIC_{metric_id}")
            # Replace commas inside brackets to underscores (for CSV compatibility)
            # [0K,4K) -> [0K_4K), [128K,+∞) -> [128K_+8)
            metric_name = (metric_name
                .replace('[0K,4K)', '[0K_4K)')
                .replace('[4K,8K)', '[4K_8K)')
                .replace('[8K,16K)', '[8K_16K)')
                .replace('[16K,32K)', '[16K_32K)')
                .replace('[32K,64K)', '[32K_64K)')
                .replace('[64K,128K)', '[64K_128K)')
                .replace('[128K,256K)', '[128K_256K)')
                .replace('[256K,512K)', '[256K_512K)')
                .replace('[512K,+∞)', '[512K_+8)')
                .replace('[128K,+∞)', '[128K_+8)')
                .replace(',+∞)', '_+8)')
            )
            header_parts.append(metric_name)
        
        header = ','.join(header_parts) + '\n'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(header)


def process_archive(archive_path: str, output_dir: str, workers: int = None, verbose: bool = False):
    """Основная функция обработки."""
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
    
    logger.info("Creating CSV headers...")
    create_csv_headers(output_dir)
    
    # Создаём locks для thread-safe записи
    manager = Manager()
    file_locks = {res_id: manager.Lock() for res_id in RESOURCE_CONFIG.keys()}
    
    # Параллельная обработка
    logger.info(f"Processing {len(tgz_files)} files with {workers} workers...")
    
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
    total_stats = {res_id: 0 for res_id in RESOURCE_CONFIG.keys()}
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
        config = RESOURCE_CONFIG.get(resource_id, {})
        filename = config.get('filename', f"resource_{resource_id}_output.csv")
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
        description='Extract and parse Huawei storage performance archives (WIDE FORMAT)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s archive.zip -o output/
  %(prog)s /path/to/tgz_dir -o output/ --workers 30
  %(prog)s archive.zip -o output/ --verbose

Features:
  - Wide format output (one row per timestamp with metrics as columns)
  - Compatible with perfmonkey format
  - ProcessPoolExecutor for true multicore parallelism
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

