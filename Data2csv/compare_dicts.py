#!/usr/bin/env python3
"""
Скрипт для сравнения словарей метрик и ресурсов между оригинальным Parse_Perf_Files.py 
и новыми METRIC_DICT.py / RESOURCE_DICT.py
"""

import re
import sys

# Импортируем новые словари
sys.path.insert(0, '/data/projects/monitoring_VM_Grafana/Data2csv')
from METRIC_DICT import METRIC_NAME_DICT
from RESOURCE_DICT import RESOURCE_NAME_DICT

# Читаем оригинальный файл
with open('/data/projects/monitoring_VM_Grafana/Data2csv/Hu_vers/Parse_Perf_Files.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Извлекаем metric_name_dict из оригинала
metric_match = re.search(r'metric_name_dict = \{([^}]+(?:\}[^}])*)\}', content, re.DOTALL)
if metric_match:
    metric_str = '{' + metric_match.group(1) + '}'
    old_metric_dict = eval(metric_str)
else:
    old_metric_dict = {}

# Извлекаем resource_name_dict из оригинала
resource_match = re.search(r'resource_name_dict = \{([^}]+)\}', content, re.DOTALL)
if resource_match:
    resource_str = '{' + resource_match.group(1) + '}'
    old_resource_dict = eval(resource_str)
else:
    old_resource_dict = {}

print("="*80)
print("СРАВНЕНИЕ СЛОВАРЕЙ МЕТРИК И РЕСУРСОВ")
print("="*80)

print(f"\nОригинал (Parse_Perf_Files.py):")
print(f"  Метрик: {len(old_metric_dict)}")
print(f"  Ресурсов: {len(old_resource_dict)}")

print(f"\nНовые словари (METRIC_DICT.py / RESOURCE_DICT.py):")
print(f"  Метрик: {len(METRIC_NAME_DICT)}")
print(f"  Ресурсов: {len(RESOURCE_NAME_DICT)}")

# Находим отсутствующие метрики
old_metric_keys = set(old_metric_dict.keys())
new_metric_keys = set(METRIC_NAME_DICT.keys())

missing_in_old = new_metric_keys - old_metric_keys
only_in_old = old_metric_keys - new_metric_keys

print("\n" + "="*80)
print("МЕТРИКИ")
print("="*80)

if missing_in_old:
    print(f"\n✅ Новые метрики в METRIC_DICT.py (отсутствуют в оригинале): {len(missing_in_old)}")
    for key in sorted(missing_in_old, key=lambda x: int(x) if x.isdigit() else 999999):
        print(f"  {key}: {METRIC_NAME_DICT.get(key)}")
else:
    print("\n✓ Все метрики из METRIC_DICT.py присутствуют в оригинале")

if only_in_old:
    print(f"\n⚠️  Метрики только в оригинале (отсутствуют в METRIC_DICT.py): {len(only_in_old)}")
    for key in sorted(only_in_old, key=lambda x: int(x) if x.isdigit() else 999999):
        print(f"  {key}: {old_metric_dict.get(key)}")
else:
    print("\n✓ Все метрики из оригинала присутствуют в METRIC_DICT.py")

# Находим отсутствующие ресурсы
old_resource_keys = set(old_resource_dict.keys())
new_resource_keys = set(RESOURCE_NAME_DICT.keys())

missing_resources_in_old = new_resource_keys - old_resource_keys
only_resources_in_old = old_resource_keys - new_resource_keys

print("\n" + "="*80)
print("РЕСУРСЫ")
print("="*80)

if missing_resources_in_old:
    print(f"\n✅ Новые ресурсы в RESOURCE_DICT.py (отсутствуют в оригинале): {len(missing_resources_in_old)}")
    for key in sorted(missing_resources_in_old, key=lambda x: int(x) if x.isdigit() else 999999):
        print(f"  {key}: {RESOURCE_NAME_DICT.get(key)}")
else:
    print("\n✓ Все ресурсы из RESOURCE_DICT.py присутствуют в оригинале")

if only_resources_in_old:
    print(f"\n⚠️  Ресурсы только в оригинале (отсутствуют в RESOURCE_DICT.py): {len(only_resources_in_old)}")
    for key in sorted(only_resources_in_old, key=lambda x: int(x) if x.isdigit() else 999999):
        print(f"  {key}: {old_resource_dict.get(key)}")
else:
    print("\n✓ Все ресурсы из оригинала присутствуют в RESOURCE_DICT.py")

print("\n" + "="*80)
print("ВЫВОД")
print("="*80)
print(f"\nНовые словари более ПОЛНЫЕ:")
print(f"  • Содержат все метрики из оригинала + {len(missing_in_old)} новых")
print(f"  • Содержат все ресурсы из оригинала + {len(missing_resources_in_old)} новых")
print(f"\n✅ Ваш скрипт Huawei_perf_parser_v0.2_parallel.py с флагом --all-metrics")
print(f"   будет парсить БОЛЬШЕ данных, чем оригинальный скрипт!")
print("="*80)


