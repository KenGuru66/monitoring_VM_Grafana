#!/usr/bin/env python3
"""
Проверка метрик в VictoriaMetrics - сравнение с CSV референсом
"""
import sys
import requests
import json
from collections import defaultdict

def sanitize_metric_name(name: str) -> str:
    """Преобразует название метрики в формат Prometheus."""
    result = name.replace("(%)", "percent").replace(" (%)", "_percent")
    result = result.replace("(", "").replace(")", "")
    result = result.replace("(MB/s)", "mb_s").replace("(KB/s)", "kb_s").replace("(KB)", "kb")
    result = result.replace("(IO/s)", "io_s").replace("(us)", "us").replace("(ms)", "ms")
    result = result.replace("(Bps)", "bps")
    result = result.replace("/", "_").replace("-", "_").replace(".", "").replace(",", "")
    result = result.replace(":", "").replace("[", "").replace("]", "")
    result = result.replace("+∞", "inf").replace("+", "plus").replace("∞", "inf")
    result = "_".join(result.lower().split())
    while "__" in result:
        result = result.replace("__", "_")
    return "huawei_" + result.strip("_")

def get_vm_metrics(vm_url, time_range=None):
    """Получить все метрики из VictoriaMetrics"""
    try:
        params = {}
        if time_range:
            params = {
                'start': str(time_range[0]),
                'end': str(time_range[1])
            }
        response = requests.get(f"{vm_url}/api/v1/label/__name__/values", params=params, timeout=10)
        response.raise_for_status()
        return set(response.json().get('data', []))
    except Exception as e:
        print(f"Error getting metrics from VM: {e}")
        return set()

def get_vm_resources(vm_url, time_range=None):
    """Получить все значения лейбла Resource из VictoriaMetrics"""
    try:
        params = {}
        if time_range:
            params = {
                'start': str(time_range[0]),
                'end': str(time_range[1])
            }
        response = requests.get(f"{vm_url}/api/v1/label/Resource/values", params=params, timeout=10)
        response.raise_for_status()
        return set(response.json().get('data', []))
    except Exception as e:
        print(f"Error getting resources from VM: {e}")
        return set()

def get_metric_count(vm_url, metric_name=None):
    """Получить количество точек данных в VM"""
    try:
        if metric_name:
            query = f'count({metric_name}{{SN="2102355THQFSQ2100014"}})'
        else:
            query = 'count({SN="2102355THQFSQ2100014"})'
        
        response = requests.get(
            f"{vm_url}/api/v1/query",
            params={'query': query},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get('data', {}).get('result'):
            return int(float(data['data']['result'][0]['value'][1]))
        return 0
    except Exception as e:
        print(f"Error getting metric count: {e}")
        return 0

def load_csv_reference(csv_file):
    """Загрузить референсные данные из CSV"""
    resources = set()
    metrics = set()
    total_lines = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        for line in f:
            total_lines += 1
            parts = line.strip().split(';')
            if len(parts) >= 6:
                resources.add(parts[0])
                metrics.add(parts[1])
    
    # Преобразуем метрики в формат Prometheus
    sanitized_metrics = {sanitize_metric_name(m) for m in metrics}
    
    return resources, metrics, sanitized_metrics, total_lines

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 check_vm_metrics.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    vm_url = "http://localhost:8428"
    
    print("="*80)
    print("🔍 CHECKING VICTORIAMETRICS METRICS")
    print("="*80)
    print()
    
    # Загружаем референсные данные
    print("📄 Loading CSV reference...")
    csv_resources, csv_metrics_orig, csv_metrics_sanitized, csv_total = load_csv_reference(csv_file)
    print(f"   CSV Resources: {len(csv_resources)}")
    print(f"   CSV Metrics: {len(csv_metrics_orig)}")
    print(f"   CSV Total lines: {csv_total:,}")
    print()
    
    # Временной диапазон для данных (13 октября 2025)
    time_range = (1760310000000, 1760400000000)  # 13 октября весь день
    
    # Получаем данные из VM
    print("📊 Querying VictoriaMetrics...")
    vm_metrics = get_vm_metrics(vm_url, time_range)
    vm_resources = get_vm_resources(vm_url, time_range)
    
    # Фильтруем только метрики huawei
    vm_huawei_metrics = {m for m in vm_metrics if m.startswith('huawei_')}
    
    print(f"   VM Metrics (huawei_*): {len(vm_huawei_metrics)}")
    print(f"   VM Resources: {len(vm_resources)}")
    print()
    
    # Проверяем ресурсы
    print("="*80)
    print("🔍 CHECKING RESOURCES")
    print("="*80)
    
    missing_resources = csv_resources - vm_resources
    extra_resources = vm_resources - csv_resources
    
    if not missing_resources:
        print("✅ All CSV resources found in VictoriaMetrics!")
    else:
        print(f"❌ Missing {len(missing_resources)} resources:")
        for r in sorted(missing_resources):
            print(f"   - {r}")
    
    if extra_resources:
        print(f"ℹ️  Found {len(extra_resources)} extra resources in VM:")
        for r in sorted(extra_resources):
            print(f"   + {r}")
    
    print()
    
    # Проверяем метрики
    print("="*80)
    print("🔍 CHECKING METRICS")
    print("="*80)
    
    missing_metrics = csv_metrics_sanitized - vm_huawei_metrics
    extra_metrics = vm_huawei_metrics - csv_metrics_sanitized
    
    if not missing_metrics:
        print("✅ All CSV metrics found in VictoriaMetrics!")
    else:
        print(f"❌ Missing {len(missing_metrics)} metrics:")
        for m in sorted(list(missing_metrics)[:20]):  # Показываем только первые 20
            print(f"   - {m}")
        if len(missing_metrics) > 20:
            print(f"   ... and {len(missing_metrics) - 20} more")
    
    if extra_metrics:
        print(f"ℹ️  Found {len(extra_metrics)} extra metrics in VM:")
        for m in sorted(list(extra_metrics)[:10]):
            print(f"   + {m}")
        if len(extra_metrics) > 10:
            print(f"   ... and {len(extra_metrics) - 10} more")
    
    print()
    
    # Проверяем количество данных
    print("="*80)
    print("🔍 CHECKING DATA POINT COUNT")
    print("="*80)
    
    print("⏳ Counting data points in VM (this may take a moment)...")
    vm_count = get_metric_count(vm_url)
    
    print(f"   CSV data points: {csv_total:,}")
    print(f"   VM data points:  {vm_count:,}")
    
    if vm_count == csv_total:
        print(f"✅ Perfect match! All {csv_total:,} data points are in VictoriaMetrics!")
    elif vm_count > 0:
        diff = abs(vm_count - csv_total)
        percentage = (diff / csv_total) * 100 if csv_total > 0 else 0
        print(f"⚠️  Difference: {diff:,} data points ({percentage:.2f}%)")
    else:
        print("❌ Could not count data points in VM")
    
    print()
    print("="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"Resources: {len(csv_resources & vm_resources)}/{len(csv_resources)} matched")
    print(f"Metrics: {len(csv_metrics_sanitized & vm_huawei_metrics)}/{len(csv_metrics_sanitized)} matched")
    print(f"Data points: {vm_count:,}/{csv_total:,}")
    print()
    
    # Возвращаем код завершения
    if missing_resources or missing_metrics or vm_count != csv_total:
        sys.exit(1)
    else:
        print("✅ ALL CHECKS PASSED!")
        sys.exit(0)

if __name__ == "__main__":
    main()

