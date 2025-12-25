#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Реэкспорт unknown метрик в правильные имена.

Экспортирует данные huawei_unknown_metric_* из VictoriaMetrics,
переименовывает согласно METRIC_DICT и импортирует обратно.

Использование:
    python3 reexport_unknown_metrics.py                    # Dry-run (только показать)
    python3 reexport_unknown_metrics.py --execute          # Выполнить реэкспорт
    python3 reexport_unknown_metrics.py --execute --delete # + удалить старые
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path

# Импорт словарей
sys.path.insert(0, str(Path(__file__).parent / "dictionaries"))
from METRIC_DICT import METRIC_NAME_DICT

# Функция sanitize из streaming_pipeline
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
    return result.strip("_")


# Паттерн для unknown метрик (streaming_pipeline создаёт их автоматически)
UNKNOWN_METRIC_PREFIX = "huawei_unknown_metric_"


def discover_unknown_metrics() -> dict:
    """
    Автоматически находит все huawei_unknown_metric_* в VictoriaMetrics
    и проверяет, есть ли их ID в словаре METRIC_DICT.
    
    Returns:
        dict: {metric_id: old_metric_name} для метрик, которые можно реэкспортировать
    """
    import re
    
    # Получаем все имена метрик из VM за последние 120 дней
    cmd = f'''curl -s "{vm_url}/api/v1/label/__name__/values?start=$(date -d '120 days ago' +%s)&end=$(date +%s)" | jq -r '.data[]' '''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"⚠️  Ошибка получения списка метрик из VM")
        return {}
    
    unknown_metrics = {}
    
    for line in result.stdout.strip().split('\n'):
        if line.startswith(UNKNOWN_METRIC_PREFIX):
            # Извлекаем ID из имени: huawei_unknown_metric_1212 → 1212
            metric_id = line.replace(UNKNOWN_METRIC_PREFIX, "")
            
            # Проверяем, есть ли этот ID в словаре
            if metric_id in METRIC_NAME_DICT:
                unknown_metrics[metric_id] = line
    
    return unknown_metrics

DEFAULT_VM_URL = "http://localhost:8428"
vm_url = DEFAULT_VM_URL


def get_new_metric_name(metric_id: str) -> str:
    """Получить новое имя метрики из словаря."""
    if metric_id not in METRIC_NAME_DICT:
        return None
    return "huawei_" + sanitize_metric_name(METRIC_NAME_DICT[metric_id])


def export_metric(old_name: str) -> str:
    """Экспортировать метрику из VM."""
    cmd = f'curl -s "{vm_url}/api/v1/export?match[]={old_name}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout


def import_metric(data: str) -> bool:
    """Импортировать данные в VM."""
    cmd = f'curl -s -X POST "{vm_url}/api/v1/import" --data-binary @-'
    result = subprocess.run(cmd, shell=True, input=data, capture_output=True, text=True)
    return result.returncode == 0


def delete_metric(metric_name: str) -> bool:
    """Удалить метрику из VM."""
    cmd = f'curl -s -X POST "{vm_url}/api/v1/admin/tsdb/delete_series?match[]={metric_name}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0


def count_series(metric_name: str) -> int:
    """Подсчитать количество time series для метрики."""
    cmd = f'curl -s "{vm_url}/api/v1/export?match[]={metric_name}" | wc -l'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return int(result.stdout.strip())
    except:
        return 0


def main():
    global vm_url
    
    parser = argparse.ArgumentParser(description="Реэкспорт unknown метрик в правильные имена")
    parser.add_argument('--execute', action='store_true', help='Выполнить реэкспорт (без флага - dry-run)')
    parser.add_argument('--delete', action='store_true', help='Удалить старые метрики после успешного импорта')
    parser.add_argument('--vm-url', default=DEFAULT_VM_URL, help=f'URL VictoriaMetrics (default: {DEFAULT_VM_URL})')
    args = parser.parse_args()
    
    vm_url = args.vm_url
    
    print("=" * 80)
    print("🔄 REEXPORT UNKNOWN METRICS")
    print("=" * 80)
    
    if not args.execute:
        print("⚠️  DRY-RUN MODE - никакие изменения не будут сделаны")
        print("   Добавьте --execute для выполнения")
        print()
    
    # Автоматически находим unknown метрики в VM, которые теперь есть в словаре
    print("🔍 Поиск huawei_unknown_metric_* в VictoriaMetrics...")
    unknown_metrics = discover_unknown_metrics()
    
    if not unknown_metrics:
        print("✅ Нет unknown метрик для реэкспорта!")
        print("   Все метрики уже имеют правильные имена, или ID не найдены в METRIC_DICT.")
        return
    
    print(f"   Найдено {len(unknown_metrics)} unknown метрик с ID в словаре")
    print()
    
    # Генерируем маппинг
    mapping = []
    for metric_id, old_name in unknown_metrics.items():
        new_name = get_new_metric_name(metric_id)
        if new_name:
            series_count = count_series(old_name)
            mapping.append({
                'id': metric_id,
                'old_name': old_name,
                'new_name': new_name,
                'series': series_count
            })
    
    print(f"📊 Найдено {len(mapping)} метрик для реэкспорта:")
    print()
    
    total_series = 0
    for m in mapping:
        total_series += m['series']
        print(f"  {m['old_name']}")
        print(f"    → {m['new_name']}")
        print(f"    📈 {m['series']} time series")
        print()
    
    print(f"📈 Всего: {total_series} time series")
    print()
    
    if not args.execute:
        print("=" * 80)
        print("✅ DRY-RUN завершён. Для выполнения добавьте --execute")
        return
    
    # Выполняем реэкспорт
    print("=" * 80)
    print("🚀 ВЫПОЛНЕНИЕ РЕЭКСПОРТА")
    print("=" * 80)
    
    success_count = 0
    failed = []
    
    for m in mapping:
        print(f"\n📤 Обработка {m['old_name']}...")
        
        # Экспорт
        data = export_metric(m['old_name'])
        if not data:
            print(f"   ❌ Не удалось экспортировать")
            failed.append(m['old_name'])
            continue
        
        # Замена имени
        new_data = data.replace(m['old_name'], m['new_name'])
        
        # Импорт
        if import_metric(new_data):
            print(f"   ✅ Импортировано как {m['new_name']}")
            success_count += 1
            
            # Удаление старой метрики если запрошено
            if args.delete:
                if delete_metric(m['old_name']):
                    print(f"   🗑️  Удалена старая метрика {m['old_name']}")
                else:
                    print(f"   ⚠️  Не удалось удалить {m['old_name']}")
        else:
            print(f"   ❌ Ошибка импорта")
            failed.append(m['old_name'])
    
    print()
    print("=" * 80)
    print("📊 РЕЗУЛЬТАТЫ")
    print("=" * 80)
    print(f"   ✅ Успешно: {success_count}/{len(mapping)}")
    if failed:
        print(f"   ❌ Ошибки: {len(failed)}")
        for f in failed:
            print(f"      - {f}")
    
    if args.delete and success_count == len(mapping):
        print()
        print("🗑️  Все старые метрики удалены")
    elif not args.delete and success_count > 0:
        print()
        print("💡 Для удаления старых метрик запустите с флагом --delete")


if __name__ == "__main__":
    main()

