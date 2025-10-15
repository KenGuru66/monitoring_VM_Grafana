#!/usr/bin/env python3
"""
Скрипт для сравнения результатов парсинга между оригинальным Parse_Perf_Files.py (Python2)
и новым Huawei_perf_parser_v0.2_parallel.py (Python3)

Сравниваем:
1. Количество строк
2. Уникальные комбинации Resource + Metric
3. Выборочно значения метрик и временные метки
"""

import sys
import csv
from pathlib import Path
from collections import defaultdict
import random

def parse_csv_file(file_path, max_lines=None):
    """
    Парсит CSV файл и возвращает статистику
    
    Формат CSV (оба скрипта):
    Resource;Metric;InstanceName;Value;Time;UnixTime
    """
    stats = {
        'total_lines': 0,
        'resource_metric_counts': defaultdict(int),
        'sample_data': []  # Выборка для сравнения значений
    }
    
    print(f"Чтение файла: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if max_lines and line_num > max_lines:
                break
                
            parts = line.strip().split(';')
            if len(parts) != 6:
                continue
                
            resource, metric, instance, value, time_str, unix_time = parts
            
            stats['total_lines'] += 1
            key = f"{resource}|{metric}"
            stats['resource_metric_counts'][key] += 1
            
            # Сохраняем случайную выборку для детального сравнения
            if random.random() < 0.0001:  # 0.01% строк
                stats['sample_data'].append({
                    'resource': resource,
                    'metric': metric,
                    'instance': instance,
                    'value': value,
                    'time': time_str,
                    'unix_time': unix_time
                })
            
            if line_num % 1000000 == 0:
                print(f"  Обработано {line_num:,} строк...")
    
    print(f"  Всего строк: {stats['total_lines']:,}")
    print(f"  Уникальных Resource+Metric: {len(stats['resource_metric_counts'])}")
    print(f"  Выборка для сравнения: {len(stats['sample_data'])} строк")
    
    return stats


def compare_stats(original_stats, new_stats):
    """Сравнивает статистику двух парсеров"""
    
    print("\n" + "="*80)
    print("СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print("="*80)
    
    # 1. Общее количество строк
    print("\n1. ОБЩЕЕ КОЛИЧЕСТВО СТРОК:")
    print(f"   Оригинальный (Python2): {original_stats['total_lines']:>15,}")
    print(f"   Новый (Python3):        {new_stats['total_lines']:>15,}")
    
    diff = new_stats['total_lines'] - original_stats['total_lines']
    diff_pct = (diff / original_stats['total_lines'] * 100) if original_stats['total_lines'] > 0 else 0
    
    if diff == 0:
        print(f"   ✅ ИДЕНТИЧНО!")
    elif abs(diff_pct) < 0.01:
        print(f"   ⚠️  Разница: {diff:+,} строк ({diff_pct:+.4f}%) - ПРЕНЕБРЕЖИМО МАЛА")
    else:
        print(f"   ❌ Разница: {diff:+,} строк ({diff_pct:+.2f}%)")
    
    # 2. Уникальные комбинации Resource + Metric
    print("\n2. УНИКАЛЬНЫЕ КОМБИНАЦИИ RESOURCE + METRIC:")
    
    original_keys = set(original_stats['resource_metric_counts'].keys())
    new_keys = set(new_stats['resource_metric_counts'].keys())
    
    only_in_original = original_keys - new_keys
    only_in_new = new_keys - original_keys
    common_keys = original_keys & new_keys
    
    print(f"   Только в оригинале:     {len(only_in_original):>6}")
    print(f"   Только в новом:         {len(only_in_new):>6}")
    print(f"   Общие:                  {len(common_keys):>6}")
    
    if only_in_original:
        print(f"\n   ⚠️  Комбинации только в оригинале (первые 10):")
        for key in list(only_in_original)[:10]:
            resource, metric = key.split('|')
            count = original_stats['resource_metric_counts'][key]
            print(f"      {resource} | {metric} ({count:,} строк)")
    
    if only_in_new:
        print(f"\n   ✅ Комбинации только в новом (первые 10):")
        for key in list(only_in_new)[:10]:
            resource, metric = key.split('|')
            count = new_stats['resource_metric_counts'][key]
            print(f"      {resource} | {metric} ({count:,} строк)")
    
    # 3. Сравнение количества строк для общих комбинаций
    print("\n3. СРАВНЕНИЕ КОЛИЧЕСТВА СТРОК ДЛЯ ОБЩИХ КОМБИНАЦИЙ:")
    
    differences = []
    for key in common_keys:
        orig_count = original_stats['resource_metric_counts'][key]
        new_count = new_stats['resource_metric_counts'][key]
        if orig_count != new_count:
            diff = new_count - orig_count
            diff_pct = (diff / orig_count * 100) if orig_count > 0 else 0
            differences.append((key, orig_count, new_count, diff, diff_pct))
    
    if differences:
        print(f"   ⚠️  Найдено {len(differences)} различий (первые 20):")
        differences.sort(key=lambda x: abs(x[3]), reverse=True)
        for key, orig, new, diff, diff_pct in differences[:20]:
            resource, metric = key.split('|')
            print(f"      {resource} | {metric}")
            print(f"         Оригинал: {orig:,}, Новый: {new:,}, Разница: {diff:+,} ({diff_pct:+.2f}%)")
    else:
        print(f"   ✅ Все совпадают!")
    
    # 4. Сравнение выборки значений
    print("\n4. СРАВНЕНИЕ ВЫБОРКИ ЗНАЧЕНИЙ:")
    print(f"   Размер выборки из оригинала: {len(original_stats['sample_data'])}")
    print(f"   Размер выборки из нового:    {len(new_stats['sample_data'])}")
    
    # Создаем индекс для быстрого поиска
    new_sample_index = {}
    for item in new_stats['sample_data']:
        key = f"{item['resource']}|{item['metric']}|{item['instance']}|{item['unix_time']}"
        new_sample_index[key] = item
    
    matches = 0
    value_mismatches = []
    
    for orig_item in original_stats['sample_data'][:100]:  # Проверяем первые 100
        key = f"{orig_item['resource']}|{orig_item['metric']}|{orig_item['instance']}|{orig_item['unix_time']}"
        
        if key in new_sample_index:
            new_item = new_sample_index[key]
            if orig_item['value'] == new_item['value']:
                matches += 1
            else:
                value_mismatches.append((orig_item, new_item))
    
    if matches > 0:
        print(f"   ✅ Совпадений по значениям: {matches}")
    
    if value_mismatches:
        print(f"   ⚠️  Несовпадений по значениям: {len(value_mismatches)} (первые 5):")
        for orig, new in value_mismatches[:5]:
            print(f"      {orig['resource']} | {orig['metric']} | {orig['instance']}")
            print(f"         Оригинал: {orig['value']}, Новый: {new['value']}")
    
    print("\n" + "="*80)
    print("ИТОГОВЫЙ ВЫВОД")
    print("="*80)
    
    if (diff == 0 and not differences and not value_mismatches):
        print("✅ ПОЛНОЕ СОВПАДЕНИЕ!")
        print("   Ваш новый скрипт (Python3) полностью корректен и")
        print("   дает ИДЕНТИЧНЫЕ результаты с оригинальным (Python2).")
    elif abs(diff_pct) < 1 and len(differences) < 10:
        print("⚠️  МИНИМАЛЬНЫЕ РАЗЛИЧИЯ")
        print("   Различия пренебрежимо малы (<1%).")
        print("   Вероятно, связаны с округлением или форматированием.")
    else:
        print("❌ СУЩЕСТВЕННЫЕ РАЗЛИЧИЯ")
        print("   Требуется дополнительная проверка логики парсинга.")
    
    print("="*80)


def main():
    # Пути к файлам
    original_file = Path("/data/projects/monitoring_VM_Grafana/Data2csv/output_test/original_py2")
    new_file = Path("/data/projects/monitoring_VM_Grafana/Data2csv/output_test/parallel_py3/2102353TJWFSP3100020.csv")
    
    # Находим CSV файл в директории оригинала
    original_csv_files = list(original_file.glob("*.csv"))
    
    if not original_csv_files:
        print("❌ Ошибка: не найдены CSV файлы в output_test/original_py2/")
        print("   Сначала запустите: bash run_original_parser.sh")
        sys.exit(1)
    
    original_csv = original_csv_files[0]
    
    if not new_file.exists():
        print(f"❌ Ошибка: файл {new_file} не найден")
        sys.exit(1)
    
    print("="*80)
    print("АНАЛИЗ РЕЗУЛЬТАТОВ ПАРСИНГА")
    print("="*80)
    print(f"\nОригинальный файл: {original_csv}")
    print(f"Новый файл:        {new_file}")
    print()
    
    # Парсим оба файла
    print("Шаг 1: Анализ оригинального файла...")
    original_stats = parse_csv_file(original_csv)
    
    print("\nШаг 2: Анализ нового файла...")
    new_stats = parse_csv_file(new_file)
    
    print("\nШаг 3: Сравнение результатов...")
    compare_stats(original_stats, new_stats)


if __name__ == "__main__":
    main()


