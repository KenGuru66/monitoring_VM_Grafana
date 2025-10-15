#!/usr/bin/env python3
"""
Анализ CSV файла: извлечение уникальных ресурсов и метрик
"""
import sys
import csv
from collections import Counter

def analyze_csv(csv_file):
    """Анализирует CSV файл и возвращает уникальные ресурсы и метрики"""
    resources = set()
    metrics = set()
    total_lines = 0
    
    print(f"Analyzing {csv_file}...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        for line in f:
            total_lines += 1
            parts = line.strip().split(';')
            if len(parts) >= 6:
                resource = parts[0]
                metric = parts[1]
                resources.add(resource)
                metrics.add(metric)
            
            if total_lines % 100000 == 0:
                print(f"  Processed {total_lines:,} lines... (Resources: {len(resources)}, Metrics: {len(metrics)})")
    
    print(f"\n✅ Analysis complete!")
    print(f"   Total lines: {total_lines:,}")
    print(f"   Unique resources: {len(resources)}")
    print(f"   Unique metrics: {len(metrics)}")
    
    return resources, metrics, total_lines

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_csv.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    resources, metrics, total = analyze_csv(csv_file)
    
    print("\n" + "="*80)
    print("RESOURCES:")
    print("="*80)
    for r in sorted(resources):
        print(f"  - {r}")
    
    print("\n" + "="*80)
    print("METRICS:")
    print("="*80)
    for m in sorted(metrics):
        print(f"  - {m}")
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    print(f"Total data points: {total:,}")
    print(f"Unique resources: {len(resources)}")
    print(f"Unique metrics: {len(metrics)}")

