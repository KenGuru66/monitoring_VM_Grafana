#!/usr/bin/env python3
"""
Анализ корреляции OPS ↔ Response Times для определения метрик NFSv3
"""

import csv
from collections import defaultdict
import sys

if len(sys.argv) < 2:
    print("Usage: python3 analyze_nfsv3_correlation.py <csv_file>")
    print("\nExample:")
    print("  python3 analyze_nfsv3_correlation.py temp/2102355TLFFSQ4100003.csv")
    sys.exit(1)

csv_file = sys.argv[1]

print(f"Анализируем файл: {csv_file}")
print()

# Словарь: timestamp → {metric: value}
ops_data = defaultdict(lambda: defaultdict(float))
rt_data = defaultdict(lambda: defaultdict(float))

# Читаем CSV
line_count = 0
with open(csv_file, 'r') as f:
    reader = csv.reader(f, delimiter=';')
    for row in reader:
        line_count += 1
        if len(row) >= 6:
            resource = row[0]
            metric = row[1]
            element = row[2]
            value = float(row[3])
            timestamp = row[4]
            
            if resource == "Controller NFSV3" and element == "0A":
                if "OPS(Number/s)" in metric:
                    ops_data[timestamp][metric] += value
                elif "Response Time(us)" in metric:
                    rt_data[timestamp][metric] = max(rt_data[timestamp][metric], value)

print(f"✅ Прочитано {line_count:,} строк")
print(f"✅ Найдено {len(ops_data)} временных меток с OPS данными")
print(f"✅ Найдено {len(rt_data)} временных меток с Response Time данными")

# Анализ: найти моменты с высоким Response Time
print("\n" + "=" * 100)
print("АНАЛИЗ КОРРЕЛЯЦИИ OPS ↔ RESPONSE TIMES")
print("=" * 100)

# Для каждой Response Time метрики
rt_metrics = [
    "CREATE", "REMOVE", "LOOKUP", "GETATTR", "ACCESS", "MKDIR", 
    "READDIR", "READDIRPLUS", "READLINK", "SYMLINK", "RENAME", 
    "LINK", "FSSTAT", "FSINFO", "PATHCONF"
]

results = []

for proc in rt_metrics:
    rt_metric = f"NFS V3 {proc} Response Time(us)"
    
    # Найти максимальный Response Time
    max_rt = 0
    max_ts = None
    
    for ts, metrics in rt_data.items():
        if rt_metric in metrics and metrics[rt_metric] > max_rt:
            max_rt = metrics[rt_metric]
            max_ts = ts
    
    if max_rt > 0 and max_ts:
        # Находим OPS метрики с наибольшими значениями
        ops_at_time = sorted(ops_data[max_ts].items(), key=lambda x: x[1], reverse=True)
        
        # Ищем метрики с значением > 100 (значимые OPS)
        significant_ops = [(m, v) for m, v in ops_at_time if v > 100]
        
        if significant_ops:
            results.append({
                'procedure': proc,
                'max_rt': max_rt,
                'timestamp': max_ts,
                'ops_metrics': significant_ops[:5]  # топ-5
            })

# Выводим результаты
for result in results:
    print(f"\n{'=' * 100}")
    print(f"📊 Процедура: {result['procedure']}")
    print(f"{'=' * 100}")
    print(f"⏰ Максимальный Response Time: {result['max_rt']:.1f} us в {result['timestamp']}")
    print(f"\n📈 OPS метрики в этот момент (>100):")
    
    for metric, value in result['ops_metrics']:
        m = metric.replace("NFS V3 ", "").replace(" OPS(Number/s)", "")
        # Выделяем топ-1
        marker = " ⭐ ВЕРОЯТНО это " + result['procedure'] + " OPS!" if value == result['ops_metrics'][0][1] else ""
        print(f"  {m:25s}: {value:10.1f}{marker}")

print("\n" + "=" * 100)
print("📋 ИТОГОВАЯ ТАБЛИЦА ПРЕДПОЛОЖЕНИЙ")
print("=" * 100)
print()
print(f"{'Процедура':<20} | {'Max RT (us)':<12} | {'Вероятная OPS метрика':<30}")
print("-" * 100)

for result in results:
    if result['ops_metrics']:
        top_metric = result['ops_metrics'][0][0]
        top_metric_short = top_metric.replace("NFS V3 ", "").replace(" OPS(Number/s)", "")
        print(f"{result['procedure']:<20} | {result['max_rt']:>10.1f}   | {top_metric_short:<30}")

print("\n" + "=" * 100)
print("💡 РЕКОМЕНДАЦИИ")
print("=" * 100)
print("""
1. Проверить предположения с графиками утилиты
2. Для каждой процедуры проверить в нескольких точках времени
3. Обновить METRIC_DICT.py с подтверждёнными значениями
4. Перепарсить архив и повторить проверку
""")


