#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Metric Mapping - Генератор полного соответствия метрик

Создаёт mapping между:
- Metric ID (из логов/.dat файлов)
- Название из METRIC_DICT.py
- Имя в VictoriaMetrics (после sanitize + huawei_ prefix)
- Коэффициент конверсии (если есть)
- Присутствие в VictoriaMetrics

Использование:
    python3 generate_metric_mapping.py                    # Генерация CSV + JSON
    python3 generate_metric_mapping.py --vm-url http://localhost:8428
    python3 generate_metric_mapping.py --no-vm-check      # Без проверки VM
    python3 generate_metric_mapping.py --days 180         # Период проверки VM

Выходные файлы:
    - metric_mapping.csv
    - metric_mapping.json
"""

import sys
import os
import json
import csv
import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta

# Импорт словарей из текущей директории
# Скрипт находится в monitoring/parsers/dictionaries/
sys.path.insert(0, str(Path(__file__).parent))

from METRIC_DICT import METRIC_NAME_DICT
from METRIC_CONVERSION import METRIC_CONVERSION

# Опционально: requests для запросов к VictoriaMetrics
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def sanitize_metric_name(name: str) -> str:
    """
    Преобразует название метрики в формат Prometheus/VictoriaMetrics.
    Точная копия функции из streaming_pipeline.py для 100% совместимости.
    """
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


def get_vm_metrics(vm_url: str, days: int = 120) -> set:
    """
    Получить список всех метрик из VictoriaMetrics за указанный период.
    
    Args:
        vm_url: URL VictoriaMetrics (например, http://localhost:8428)
        days: Количество дней для запроса (исторические данные)
    
    Returns:
        set: Множество имён метрик в VM
    """
    if not REQUESTS_AVAILABLE:
        print("⚠️  requests не установлен, проверка VM пропущена")
        return set()
    
    # Вычисляем временной диапазон
    end_time = int(time.time())
    start_time = int((datetime.now() - timedelta(days=days)).timestamp())
    
    url = f"{vm_url}/api/v1/label/__name__/values?start={start_time}&end={end_time}"
    
    try:
        print(f"📡 Запрос к VictoriaMetrics: {vm_url}")
        print(f"   Период: последние {days} дней")
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if data.get("status") == "success":
            metrics = set(data.get("data", []))
            # Фильтруем только huawei_* метрики
            huawei_metrics = {m for m in metrics if m.startswith("huawei_")}
            print(f"✅ Получено {len(huawei_metrics)} huawei_* метрик из VM")
            return huawei_metrics
        else:
            print(f"⚠️  VM вернул неуспешный статус: {data}")
            return set()
            
    except requests.RequestException as e:
        print(f"⚠️  Ошибка запроса к VM: {e}")
        return set()


def generate_mapping(check_vm: bool = True, vm_url: str = "http://localhost:8428", days: int = 120) -> list:
    """
    Генерирует полный mapping метрик.
    
    Args:
        check_vm: Проверять ли наличие в VictoriaMetrics
        vm_url: URL VictoriaMetrics
        days: Период для проверки VM
    
    Returns:
        list: Список словарей с mapping информацией
    """
    print("="*80)
    print("🔄 GENERATING METRIC MAPPING")
    print("="*80)
    
    # Получаем метрики из VM если нужно
    vm_metrics = set()
    if check_vm:
        vm_metrics = get_vm_metrics(vm_url, days)
    
    # Генерируем mapping
    mapping = []
    
    for metric_id, metric_name in sorted(METRIC_NAME_DICT.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999999):
        # Генерируем VM имя
        sanitized = sanitize_metric_name(metric_name)
        vm_name = f"huawei_{sanitized}"
        
        # Проверяем конверсию
        conversion = ""
        if metric_id in METRIC_CONVERSION:
            factor = METRIC_CONVERSION[metric_id]
            if factor == 1024:
                conversion = "÷1024 (KB→MB)"
            elif factor == 1000:
                conversion = "÷1000 (us→ms)"
            elif factor == 1/1024:
                conversion = "×1024 (→KB)"
            else:
                conversion = f"÷{factor}"
        
        # Проверяем наличие в VM
        in_vm = "yes" if vm_name in vm_metrics else "no" if check_vm else "-"
        
        mapping.append({
            "metric_id": metric_id,
            "metric_dict_name": metric_name,
            "vm_name": vm_name,
            "conversion": conversion,
            "in_vm": in_vm
        })
    
    return mapping


def save_csv(mapping: list, output_path: Path):
    """Сохранить mapping в CSV файл."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["metric_id", "metric_dict_name", "vm_name", "conversion", "in_vm"])
        writer.writeheader()
        writer.writerows(mapping)
    print(f"📄 CSV сохранён: {output_path}")


def save_json(mapping: list, output_path: Path):
    """Сохранить mapping в JSON файл."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"📄 JSON сохранён: {output_path}")


def print_stats(mapping: list):
    """Вывести статистику по mapping."""
    total = len(mapping)
    with_conversion = sum(1 for m in mapping if m["conversion"])
    in_vm = sum(1 for m in mapping if m["in_vm"] == "yes")
    not_in_vm = sum(1 for m in mapping if m["in_vm"] == "no")
    
    print("")
    print("="*80)
    print("📊 СТАТИСТИКА")
    print("="*80)
    print(f"   Всего метрик в METRIC_DICT:     {total}")
    print(f"   С конверсией единиц:            {with_conversion}")
    if in_vm > 0 or not_in_vm > 0:
        print(f"   Присутствуют в VictoriaMetrics: {in_vm}")
        print(f"   Отсутствуют в VictoriaMetrics:  {not_in_vm}")
        print(f"   Покрытие VM:                    {in_vm/total*100:.1f}%")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description="Генератор mapping метрик: ID → METRIC_DICT → VictoriaMetrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python3 generate_metric_mapping.py                     # Полный mapping с проверкой VM
  python3 generate_metric_mapping.py --no-vm-check       # Без запроса к VM (быстрее)
  python3 generate_metric_mapping.py --days 180          # Проверка за 180 дней
  python3 generate_metric_mapping.py --vm-url http://10.5.10.163:8428

Выходные файлы создаются в той же директории:
  - metric_mapping.csv  (для Excel)
  - metric_mapping.json (для программ)
        """
    )
    
    parser.add_argument('--vm-url', type=str, default='http://localhost:8428',
                        help='URL VictoriaMetrics (default: http://localhost:8428)')
    parser.add_argument('--no-vm-check', action='store_true',
                        help='Не проверять наличие метрик в VictoriaMetrics')
    parser.add_argument('--days', type=int, default=120,
                        help='Период для проверки VM в днях (default: 120)')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Директория для выходных файлов (default: рядом со скриптом)')
    
    args = parser.parse_args()
    
    # Определяем директорию для выходных файлов
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).parent
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Генерируем mapping
    check_vm = not args.no_vm_check
    mapping = generate_mapping(check_vm=check_vm, vm_url=args.vm_url, days=args.days)
    
    # Сохраняем в файлы
    csv_path = output_dir / "metric_mapping.csv"
    json_path = output_dir / "metric_mapping.json"
    
    save_csv(mapping, csv_path)
    save_json(mapping, json_path)
    
    # Статистика
    print_stats(mapping)
    
    print("")
    print("✅ Готово!")
    print(f"   CSV:  {csv_path}")
    print(f"   JSON: {json_path}")


if __name__ == "__main__":
    main()

