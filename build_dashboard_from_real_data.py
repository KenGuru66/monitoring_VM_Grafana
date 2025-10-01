#!/usr/bin/env python3
"""
Скрипт для построения дашборда Grafana на основе реальных данных.

Шаги:
1. Запускает парсер со ВСЕМИ метриками и ресурсами
2. Анализирует CSV и извлекает уникальные комбинации Resource-Metric
3. Создает маппинг RESOURCE_TO_METRICS на основе реальных данных
4. Генерирует дашборд Grafana
"""

import subprocess
import sys
import os
import csv
import json
from collections import defaultdict
from pathlib import Path

# Импортируем словари
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Data2csv'))
from METRIC_DICT import METRIC_NAME_DICT
from RESOURCE_DICT import RESOURCE_NAME_DICT

def step1_parse_with_all_metrics(input_zip: str, output_dir: str = "Data2csv/output"):
    """Шаг 1: Парсинг со ВСЕМИ метриками и ресурсами"""
    print("="*80)
    print("📊 ШАГ 1: Парсинг данных со ВСЕМИ метриками и ресурсами")
    print("="*80)
    
    # Получаем все ID метрик и ресурсов
    all_metrics = list(METRIC_NAME_DICT.keys())
    all_resources = list(RESOURCE_NAME_DICT.keys())
    
    print(f"   Всего метрик: {len(all_metrics)}")
    print(f"   Всего ресурсов: {len(all_resources)}")
    print()
    
    # Очищаем output директорию
    output_path = Path(output_dir)
    if output_path.exists():
        for csv_file in output_path.glob("*.csv"):
            csv_file.unlink()
            print(f"   ✅ Удален старый CSV: {csv_file.name}")
    else:
        output_path.mkdir(parents=True)
    
    print()
    print("   → Запуск парсера...")
    
    # Формируем команду
    cmd = [
        "python3",
        "Data2csv/Huawei_perf_parser_v0.2_parallel.py",
        "-i", input_zip,
        "-o", output_dir
    ]
    
    # Добавляем каждый ресурс отдельно
    for resource_id in all_resources:
        cmd.extend(["-r", resource_id])
    
    # Добавляем каждую метрику отдельно
    for metric_id in all_metrics:
        cmd.extend(["-m", metric_id])
    
    # Запускаем парсер
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ Ошибка парсинга:")
        print(result.stderr)
        sys.exit(1)
    
    print("   ✅ Парсинг завершен!")
    print()
    
    # Находим созданный CSV файл
    csv_files = list(output_path.glob("*.csv"))
    if not csv_files:
        print("   ❌ CSV файлы не найдены!")
        sys.exit(1)
    
    csv_file = csv_files[0]
    print(f"   📁 CSV файл: {csv_file}")
    print(f"   📊 Размер: {csv_file.stat().st_size / (1024**2):.2f} MB")
    print()
    
    return str(csv_file)

def step2_extract_unique_combinations(csv_file: str):
    """Шаг 2: Извлечение уникальных комбинаций Resource-Metric"""
    print("="*80)
    print("📋 ШАГ 2: Извлечение уникальных комбинаций Resource-Metric")
    print("="*80)
    
    # Словарь: Resource ID → set(Metric Names)
    resource_metrics = defaultdict(set)
    
    # Счетчики
    total_rows = 0
    processed_rows = 0
    
    print("   → Чтение CSV файла...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        # Определяем разделитель
        first_line = f.readline()
        f.seek(0)
        
        if '\t' in first_line:
            delimiter = '\t'
        elif ';' in first_line:
            delimiter = ';'
        else:
            delimiter = ','
        
        reader = csv.reader(f, delimiter=delimiter)
        
        for row in reader:
            total_rows += 1
            
            if len(row) < 3:
                continue
            
            resource_id = row[0].strip()
            metric_name = row[1].strip()
            
            if resource_id and metric_name:
                resource_metrics[resource_id].add(metric_name)
                processed_rows += 1
            
            # Прогресс каждые 100k строк
            if total_rows % 100000 == 0:
                print(f"   ... обработано {total_rows:,} строк")
    
    print()
    print(f"   ✅ Обработано строк: {total_rows:,}")
    print(f"   ✅ Уникальных комбинаций: {processed_rows:,}")
    print(f"   ✅ Найдено ресурсов: {len(resource_metrics)}")
    print()
    
    # Выводим статистику по каждому ресурсу
    print("   📊 Статистика по ресурсам:")
    print()
    
    for resource_id in sorted(resource_metrics.keys()):
        resource_name = RESOURCE_NAME_DICT.get(resource_id, f"Unknown ({resource_id})")
        metric_count = len(resource_metrics[resource_id])
        print(f"      • {resource_name:30s} (ID: {resource_id:5s}) - {metric_count:3d} метрик")
    
    print()
    
    return resource_metrics

def step3_create_metric_mapping(resource_metrics: dict):
    """Шаг 3: Создание маппинга метрик"""
    print("="*80)
    print("🗺️  ШАГ 3: Создание маппинга Resource → Metrics")
    print("="*80)
    
    # Обратный маппинг: Metric Name → Metric ID
    metric_name_to_id = {}
    for metric_id, metric_name in METRIC_NAME_DICT.items():
        metric_name_to_id[metric_name] = metric_id
    
    # Создаем маппинг: Resource ID → [Metric IDs]
    resource_to_metric_ids = {}
    
    for resource_id, metric_names in resource_metrics.items():
        metric_ids = []
        
        for metric_name in sorted(metric_names):
            # Находим ID метрики
            metric_id = metric_name_to_id.get(metric_name)
            if metric_id:
                metric_ids.append(metric_id)
            else:
                print(f"   ⚠️  Метрика '{metric_name}' не найдена в METRIC_NAME_DICT")
        
        if metric_ids:
            resource_to_metric_ids[resource_id] = metric_ids
    
    print(f"   ✅ Создан маппинг для {len(resource_to_metric_ids)} ресурсов")
    print()
    
    return resource_to_metric_ids

def step4_save_mapping(resource_to_metric_ids: dict, output_file: str = "resource_metric_mapping_real.py"):
    """Шаг 4: Сохранение маппинга в файл"""
    print("="*80)
    print("💾 ШАГ 4: Сохранение маппинга в файл")
    print("="*80)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('"""\n')
        f.write('Маппинг ресурсов и метрик на основе РЕАЛЬНЫХ данных.\n')
        f.write('Автоматически сгенерирован из CSV файла.\n')
        f.write('"""\n\n')
        
        f.write('# Маппинг ID ресурсов → названия\n')
        f.write('RESOURCE_MAPPING = {\n')
        for resource_id in sorted(resource_to_metric_ids.keys()):
            # Используем resource_id как есть, если он совпадает с названием
            resource_name = RESOURCE_NAME_DICT.get(resource_id, resource_id)
            f.write(f'    "{resource_id}": "{resource_name}",\n')
        f.write('}\n\n')
        
        f.write('# Маппинг ID метрик → названия\n')
        f.write('METRIC_MAPPING = {\n')
        
        # Собираем все уникальные метрики
        all_metric_ids = set()
        for metric_ids in resource_to_metric_ids.values():
            all_metric_ids.update(metric_ids)
        
        for metric_id in sorted(all_metric_ids):
            metric_name = METRIC_NAME_DICT.get(metric_id, f"Unknown_{metric_id}")
            # Экранируем кавычки в названии метрики
            metric_name = metric_name.replace('"', '\\"')
            f.write(f'    "{metric_id}": "{metric_name}",\n')
        f.write('}\n\n')
        
        f.write('# Маппинг: Ресурс → Список применимых метрик (НА ОСНОВЕ РЕАЛЬНЫХ ДАННЫХ)\n')
        f.write('RESOURCE_TO_METRICS = {\n')
        for resource_id in sorted(resource_to_metric_ids.keys()):
            metric_ids = resource_to_metric_ids[resource_id]
            f.write(f'    "{resource_id}": [  # {RESOURCE_NAME_DICT.get(resource_id, "Unknown")}\n')
            
            # Группируем по 10 метрик в строку
            for i in range(0, len(metric_ids), 10):
                chunk = metric_ids[i:i+10]
                metric_list = ', '.join(f'"{m}"' for m in chunk)
                f.write(f'        {metric_list},\n')
            
            f.write('    ],\n')
        f.write('}\n\n')
        
        f.write('# Список ресурсов по умолчанию\n')
        f.write('DEFAULT_RESOURCES = [\n')
        for resource_id in sorted(resource_to_metric_ids.keys()):
            f.write(f'    "{resource_id}",  # {RESOURCE_NAME_DICT.get(resource_id, "Unknown")}\n')
        f.write(']\n')
    
    print(f"   ✅ Маппинг сохранен: {output_file}")
    print()
    
    # Выводим статистику
    total_metrics = sum(len(ids) for ids in resource_to_metric_ids.values())
    print(f"   📊 Статистика:")
    print(f"      • Ресурсов: {len(resource_to_metric_ids)}")
    print(f"      • Уникальных метрик: {len(all_metric_ids)}")
    print(f"      • Всего комбинаций: {total_metrics}")
    print()

def step5_generate_dashboard():
    """Шаг 5: Генерация дашборда"""
    print("="*80)
    print("📈 ШАГ 5: Генерация дашборда Grafana")
    print("="*80)
    
    print("   → Запуск генератора дашборда...")
    
    # Запускаем генератор дашборда
    cmd = ["python3", "generate_dashboard_real.py"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ Ошибка генерации:")
        print(result.stderr)
        sys.exit(1)
    
    print(result.stdout)
    print()

def main():
    """Главная функция"""
    print()
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║                                                                ║")
    print("║   📊 ПОСТРОЕНИЕ ДАШБОРДА НА ОСНОВЕ РЕАЛЬНЫХ ДАННЫХ            ║")
    print("║                                                                ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    
    # Проверяем наличие входного файла
    input_zip = "Data2csv/logs/Storage_History_Performance_Files (1).zip"
    
    if not Path(input_zip).exists():
        print(f"❌ Файл не найден: {input_zip}")
        print()
        print("Укажите путь к ZIP архиву:")
        input_zip = input("> ").strip()
        
        if not Path(input_zip).exists():
            print(f"❌ Файл не найден: {input_zip}")
            sys.exit(1)
    
    print(f"📁 Входной файл: {input_zip}")
    print()
    
    # Выполняем все шаги
    csv_file = step1_parse_with_all_metrics(input_zip)
    resource_metrics = step2_extract_unique_combinations(csv_file)
    resource_to_metric_ids = step3_create_metric_mapping(resource_metrics)
    step4_save_mapping(resource_to_metric_ids)
    step5_generate_dashboard()
    
    # Итог
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║                                                                ║")
    print("║            ✅ ВСЕ ШАГИ ВЫПОЛНЕНЫ УСПЕШНО!                      ║")
    print("║                                                                ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    print("📝 Созданные файлы:")
    print("   • resource_metric_mapping_real.py - Маппинг на основе реальных данных")
    print("   • grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json")
    print()
    print("🚀 Следующие шаги:")
    print("   1. Импортируйте CSV в VictoriaMetrics:")
    print("      python3 csv2vm_parallel.py", csv_file)
    print()
    print("   2. Откройте Grafana: http://localhost:3000")
    print("   3. Найдите дашборд: 'Huawei OceanStor - Real Data'")
    print()

if __name__ == "__main__":
    main()

