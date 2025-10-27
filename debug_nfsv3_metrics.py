#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для диагностики NFSv3 метрик в сырых .dat файлах.
Проверяет наличие данных для всех 33 NFSv3 метрик.
"""

import struct
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# NFSv3 метрики из METRIC_DICT.py
NFSV3_OPS_METRICS = {
    "1099": "NFS V3 NULL OPS(Number/s)",
    "1100": "NFS V3 CREATE OPS(Number/s)",
    "1101": "NFS V3 REMOVE OPS(Number/s)",
    "1102": "NFS V3 LOOKUP OPS(Number/s)",
    "1103": "NFS V3 ACCESS OPS(Number/s)",
    "1104": "NFS V3 READLINK OPS(Number/s)",
    "1105": "NFS V3 READ OPS(Number/s)",
    "1106": "NFS V3 WRITE OPS(Number/s)",
    "1107": "NFS V3 CREATE OPS(Number/s)",  # дубликат?
    "1108": "NFS V3 MKDIR OPS(Number/s)",
    "1109": "NFS V3 SYMLINK OPS(Number/s)",
    "1110": "NFS V3 MKNOD OPS(Number/s)",
    "1111": "NFS V3 RMDIR OPS(Number/s)",
    "1112": "NFS V3 RENAME OPS(Number/s)",
    "1113": "NFS V3 LINK OPS(Number/s)",
    "1114": "NFS V3 GETATTR OPS(Number/s)",
    "1115": "NFS V3 READDIR OPS(Number/s)",
    "1116": "NFS V3 READDIRPLUS OPS(Number/s)",
    "1117": "NFS V3 FSSTAT OPS(Number/s)",
    "1118": "NFS V3 FSINFO OPS(Number/s)",
    "1119": "NFS V3 PATHCONF OPS(Number/s)",
    "1120": "NFS V3 COMMIT OPS(Number/s)",
}

NFSV3_RT_METRICS = {
    "1121": "NFS V3 LOOKUP Response Time(us)",
    "1122": "NFS V3 PATHCONF Response Time(us)",
    "1123": "NFS V3 READDIR Response Time(us)",
    "1124": "NFS V3 GETATTR Response Time(us)",
    "1125": "NFS V3 SETATTR Response Time(us)",
    "1126": "NFS V3 MKDIR Response Time(us)",
    "1127": "NFS V3 RMDIR Response Time(us)",
    "1128": "NFS V3 READDIR Response Time(us)",  # дубликат?
    "1129": "NFS V3 ACCESS Response Time(us)",
    "1130": "NFS V3 READDIRPLUS Response Time(us)",
    "1131": "NFS V3 OPEN Response Time(us)",
}

ALL_NFSV3_METRICS = {**NFSV3_OPS_METRICS, **NFSV3_RT_METRICS}

RESOURCE_ID_NFSV3 = "1000"  # Controller NFSV3


def parse_dat_file(file_path: Path):
    """
    Парсит .dat файл и возвращает статистику по NFSv3 метрикам.
    """
    print(f"\n{'='*80}")
    print(f"🔍 АНАЛИЗ ФАЙЛА: {file_path.name}")
    print(f"{'='*80}\n")
    
    with open(file_path, 'rb') as f:
        # Читаем заголовок файла
        bit_correct = f.read(32)
        bit_msg_version = struct.unpack('<I', f.read(4))[0]
        bit_equip_sn = f.read(256).decode('utf-8', errors='ignore').strip('\x00')
        bit_equip_name = f.read(41).decode('utf-8', errors='ignore').strip('\x00')
        bit_equip_data_length = struct.unpack('<I', f.read(4))[0]
        
        print(f"📋 Заголовок файла:")
        print(f"   Serial Number: {bit_equip_sn}")
        print(f"   Equipment Name: {bit_equip_name}")
        print(f"   Data Length: {bit_equip_data_length:,} bytes")
        
        # Статистика по метрикам
        nfsv3_stats = defaultdict(lambda: {
            'count': 0,
            'non_zero_count': 0,
            'min_value': float('inf'),
            'max_value': float('-inf'),
            'sum_value': 0,
            'elements': set()
        })
        
        found_nfsv3_resource = False
        total_time_blocks = 0
        
        # Читаем временные блоки
        while f.tell() < len(bit_correct) + 4 + 256 + 41 + 4 + bit_equip_data_length:
            try:
                bit_map_type = struct.unpack('<I', f.read(4))[0]
                bit_map_length = struct.unpack('<I', f.read(4))[0]
                bit_map_value = f.read(bit_map_length).decode('utf-8', errors='ignore')
                
                # Парсим JSON карту
                try:
                    map_data = json.loads(bit_map_value)
                except json.JSONDecodeError:
                    continue
                
                total_time_blocks += 1
                start_time = datetime.fromtimestamp(int(map_data.get('StartTime', 0)))
                end_time = datetime.fromtimestamp(int(map_data.get('EndTime', 0)))
                archive_interval = int(map_data.get('Archive', 60))
                
                if total_time_blocks == 1:
                    print(f"\n📅 Первый временной блок:")
                    print(f"   Начало: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Конец:  {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Интервал: {archive_interval}s")
                
                # Проверяем наличие NFSv3 ресурса
                resource_map = map_data.get('Map', {})
                if RESOURCE_ID_NFSV3 in resource_map:
                    found_nfsv3_resource = True
                    nfsv3_data = resource_map[RESOURCE_ID_NFSV3]
                    element_ids = nfsv3_data.get('IDs', [])
                    element_names = nfsv3_data.get('Names', [])
                    metric_ids = nfsv3_data.get('DataTypes', [])
                    
                    if total_time_blocks == 1:
                        print(f"\n✅ Найден NFSv3 ресурс (ID: {RESOURCE_ID_NFSV3}):")
                        print(f"   Элементы: {element_names}")
                        print(f"   Метрики (IDs): {metric_ids}")
                    
                    # Вычисляем количество точек данных
                    time_diff = int(map_data.get('EndTime', 0)) - int(map_data.get('StartTime', 0))
                    num_points = max(1, time_diff // archive_interval)
                    
                    # Читаем бинарные данные
                    num_elements = len(element_ids)
                    num_metrics = len(metric_ids)
                    
                    for elem_idx, elem_name in enumerate(element_names):
                        for metric_idx, metric_id in enumerate(metric_ids):
                            if metric_id in ALL_NFSV3_METRICS:
                                for point_idx in range(num_points):
                                    # Вычисляем позицию в бинарных данных
                                    offset = (point_idx * num_elements * num_metrics + 
                                             elem_idx * num_metrics + 
                                             metric_idx) * 4
                                    
                                    value_bytes = f.read(4)
                                    if len(value_bytes) < 4:
                                        break
                                    
                                    value = struct.unpack('<i', value_bytes)[0]
                                    
                                    # Обновляем статистику
                                    stats = nfsv3_stats[metric_id]
                                    stats['count'] += 1
                                    stats['elements'].add(elem_name)
                                    
                                    if value != 0:
                                        stats['non_zero_count'] += 1
                                        stats['min_value'] = min(stats['min_value'], value)
                                        stats['max_value'] = max(stats['max_value'], value)
                                        stats['sum_value'] += value
                            else:
                                # Пропускаем не-NFSv3 метрики
                                f.read(4 * num_points)
                
            except struct.error:
                break
            except Exception as e:
                print(f"⚠️ Ошибка при чтении блока: {e}")
                break
        
        print(f"\n📊 Всего обработано временных блоков: {total_time_blocks}")
        
        if not found_nfsv3_resource:
            print(f"\n❌ NFSv3 ресурс (ID: {RESOURCE_ID_NFSV3}) НЕ НАЙДЕН в файле!")
            return None
        
        return nfsv3_stats


def print_statistics(stats):
    """
    Выводит статистику по NFSv3 метрикам.
    """
    print(f"\n{'='*80}")
    print(f"📈 СТАТИСТИКА NFSv3 МЕТРИК")
    print(f"{'='*80}\n")
    
    # Разделяем на OPS и RT метрики
    ops_metrics = {k: v for k, v in stats.items() if k in NFSV3_OPS_METRICS}
    rt_metrics = {k: v for k, v in stats.items() if k in NFSV3_RT_METRICS}
    
    print(f"📊 OPS МЕТРИКИ (Operations Per Second):")
    print(f"{'─'*80}")
    print(f"{'Metric ID':<12} {'Название':<40} {'Записей':<10} {'Ненулевых':<12} {'Max':<15}")
    print(f"{'─'*80}")
    
    for metric_id in sorted(NFSV3_OPS_METRICS.keys()):
        metric_name = NFSV3_OPS_METRICS[metric_id]
        if metric_id in ops_metrics:
            s = ops_metrics[metric_id]
            status = "✅" if s['non_zero_count'] > 0 else "⚠️"
            max_val = f"{s['max_value']:,}" if s['max_value'] != float('-inf') else "N/A"
            print(f"{status} {metric_id:<10} {metric_name:<40} {s['count']:<10} {s['non_zero_count']:<12} {max_val:<15}")
        else:
            print(f"❌ {metric_id:<10} {metric_name:<40} {'НЕ НАЙДЕНА':<10}")
    
    print(f"\n⏱️  RESPONSE TIME МЕТРИКИ (Microseconds):")
    print(f"{'─'*80}")
    print(f"{'Metric ID':<12} {'Название':<40} {'Записей':<10} {'Ненулевых':<12} {'Max':<15}")
    print(f"{'─'*80}")
    
    for metric_id in sorted(NFSV3_RT_METRICS.keys()):
        metric_name = NFSV3_RT_METRICS[metric_id]
        if metric_id in rt_metrics:
            s = rt_metrics[metric_id]
            status = "✅" if s['non_zero_count'] > 0 else "⚠️"
            max_val = f"{s['max_value']:,}" if s['max_value'] != float('-inf') else "N/A"
            print(f"{status} {metric_id:<10} {metric_name:<40} {s['count']:<10} {s['non_zero_count']:<12} {max_val:<15}")
        else:
            print(f"❌ {metric_id:<10} {metric_name:<40} {'НЕ НАЙДЕНА':<10}")
    
    # Подсчёт проблемных метрик
    total_metrics = len(ALL_NFSV3_METRICS)
    found_metrics = len(stats)
    metrics_with_data = sum(1 for s in stats.values() if s['non_zero_count'] > 0)
    metrics_zero_only = found_metrics - metrics_with_data
    missing_metrics = total_metrics - found_metrics
    
    print(f"\n{'='*80}")
    print(f"📊 ИТОГОВАЯ СТАТИСТИКА:")
    print(f"{'='*80}")
    print(f"   Всего NFSv3 метрик: {total_metrics}")
    print(f"   ✅ Найдено с данными: {metrics_with_data}")
    print(f"   ⚠️  Найдено, но только нули: {metrics_zero_only}")
    print(f"   ❌ Не найдено в файле: {missing_metrics}")
    print(f"{'='*80}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 debug_nfsv3_metrics.py <path_to_dat_file>")
        sys.exit(1)
    
    dat_file = Path(sys.argv[1])
    if not dat_file.exists():
        print(f"❌ Файл не найден: {dat_file}")
        sys.exit(1)
    
    stats = parse_dat_file(dat_file)
    if stats:
        print_statistics(stats)


if __name__ == "__main__":
    main()

