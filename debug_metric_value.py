#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для извлечения конкретного значения метрики из .dat файла.
Используется для отладки и сравнения данных между сырыми логами, CSV и VictoriaMetrics.
"""

import sys
import struct
import re
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'Data2csv'))

from Data2csv.METRIC_DICT import METRIC_NAME_DICT
from Data2csv.RESOURCE_DICT import RESOURCE_NAME_DICT


def construct_data_header(result):
    """Построить заголовок данных из .dat файла."""
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


def find_metric_value(dat_file: Path, target_resource_id: str, target_metric_id: str, 
                      target_element: str, target_time_str: str):
    """
    Найти конкретное значение метрики в .dat файле.
    
    Args:
        dat_file: Путь к .dat файлу
        target_resource_id: ID ресурса (например, "212" для FC Port)
        target_metric_id: ID метрики (например, "1183")
        target_element: Имя элемента (например, "CTE0.A.IOM0.P0")
        target_time_str: Целевое время в формате "YYYY-MM-DD HH:MM:SS"
    """
    print("=" * 80)
    print("🔍 ПОИСК ЗНАЧЕНИЯ МЕТРИКИ В СЫРОМ .DAT ФАЙЛЕ")
    print("=" * 80)
    print(f"📁 Файл: {dat_file.name}")
    print(f"📊 Ресурс: {RESOURCE_NAME_DICT.get(target_resource_id, target_resource_id)} (ID: {target_resource_id})")
    print(f"📈 Метрика: {METRIC_NAME_DICT.get(target_metric_id, target_metric_id)} (ID: {target_metric_id})")
    print(f"🎯 Элемент: {target_element}")
    print(f"⏰ Целевое время: {target_time_str}")
    print("=" * 80)
    
    target_time = datetime.strptime(target_time_str, "%Y-%m-%d %H:%M:%S")
    
    with open(dat_file, "rb") as fin:
        # Читаем заголовок файла
        bit_correct = fin.read(32)
        bit_msg_version = fin.read(4)
        bit_equip_sn = fin.read(256).decode('utf-8').strip('\x00')
        bit_equip_name = fin.read(41).decode('utf-8').strip('\x00')
        bit_equip_data_length = fin.read(4)

        print(f"\n📋 Заголовок файла:")
        print(f"   Serial Number: {bit_equip_sn}")
        print(f"   Equipment Name: {bit_equip_name}")

        process_finish_flag = False

        bit_map_type = fin.read(4)
        bit_map_length, = struct.unpack("<l", fin.read(4))
        bit_map_value = fin.read(bit_map_length - 8)

        if len(bit_map_value) < bit_map_length - 8:
            print("❌ Ошибка чтения заголовка данных")
            return

        while not process_finish_flag:
            result = re.match(
                '{(.*),"Map":{(.*)}}', bit_map_value.decode('utf-8')
            )
            data_header = construct_data_header(result)
            list_data_type, size_collect_once = construct_data_type(data_header)

            times_collect = int(
                (int(data_header['EndTime']) - int(data_header['StartTime'])) /
                int(data_header['Archive'])
            )
            
            archive_interval = int(data_header['Archive'])
            start_time = datetime.fromtimestamp(int(data_header['StartTime']))
            end_time = datetime.fromtimestamp(int(data_header['EndTime']))
            
            print(f"\n📅 Временной блок:")
            print(f"   Начало: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Конец:  {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Интервал сбора: {archive_interval}s")
            print(f"   Количество точек: {times_collect}")

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
            next_time = start_time
            time_list = []
            for i in range(len(list_data_type[0][3])):
                time_list.append(next_time)
                next_time += timedelta(seconds=archive_interval)

            # Ищем нужную метрику
            found_values = []
            for data_type in list_data_type:
                resource_id = str(data_type[0])
                metric_id = str(data_type[1])
                element = data_type[2]
                
                if (resource_id == target_resource_id and 
                    metric_id == target_metric_id and 
                    element == target_element):
                    
                    print(f"\n✅ Найдена метрика!")
                    print(f"   Ресурс: {resource_id} ({RESOURCE_NAME_DICT.get(resource_id)})")
                    print(f"   Метрика: {metric_id} ({METRIC_NAME_DICT.get(metric_id)})")
                    print(f"   Элемент: {element}")
                    print(f"\n📊 Значения в этом блоке:")
                    
                    for idx, (ts, val) in enumerate(zip(time_list, data_type[3])):
                        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
                        time_diff = abs((ts - target_time).total_seconds())
                        
                        marker = ""
                        if time_diff < archive_interval:
                            marker = " ⭐ ЦЕЛЕВОЕ ВРЕМЯ"
                            found_values.append({
                                'time': ts_str,
                                'value': val,
                                'time_diff': time_diff
                            })
                        
                        print(f"   [{idx:3d}] {ts_str} | Значение: {val:>6}{marker}")
                    
                    break

            # Очищаем данные
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
                        break
            else:
                process_finish_flag = True
    
    if found_values:
        print("\n" + "=" * 80)
        print("🎯 РЕЗУЛЬТАТ")
        print("=" * 80)
        closest = min(found_values, key=lambda x: x['time_diff'])
        print(f"Найдено ближайшее значение:")
        print(f"   Время: {closest['time']}")
        print(f"   Значение: {closest['value']}")
        print(f"   Разница с целевым временем: {closest['time_diff']:.0f}s")
        print("=" * 80)
    else:
        print("\n❌ Метрика не найдена в файле")


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python3 debug_metric_value.py <dat_file> <resource_id> <metric_id> <element> <target_time>")
        print("Example: python3 debug_metric_value.py file.dat 212 1183 'CTE0.A.IOM0.P0' '2025-10-20 00:01:00'")
        sys.exit(1)
    
    dat_file = Path(sys.argv[1])
    resource_id = sys.argv[2]
    metric_id = sys.argv[3]
    element = sys.argv[4]
    target_time = sys.argv[5]
    
    find_metric_value(dat_file, resource_id, metric_id, element, target_time)

