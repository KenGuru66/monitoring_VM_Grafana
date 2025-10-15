#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматического обновления словарей METRIC_DICT.py и RESOURCE_DICT.py
на основе найденных UNKNOWN ID в CSV файлах
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


def extract_unknown_from_csv(csv_file):
    """
    Извлекает все UNKNOWN ID из CSV файла
    
    Returns:
        (set of unknown_resources, set of unknown_metrics)
    """
    unknown_resources = set()
    unknown_metrics = set()
    
    print(f"📖 Анализирую файл: {csv_file}")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            parts = line.strip().split(';')
            if len(parts) == 6:
                resource_name = parts[0]
                metric_name = parts[1]
                
                # Проверяем ресурсы
                if resource_name.startswith("UNKNOWN_RESOURCE_"):
                    resource_id = resource_name.replace("UNKNOWN_RESOURCE_", "")
                    unknown_resources.add(resource_id)
                
                # Проверяем метрики
                if metric_name.startswith("UNKNOWN_METRIC_"):
                    metric_id = metric_name.replace("UNKNOWN_METRIC_", "")
                    unknown_metrics.add(metric_id)
            
            if line_num % 100000 == 0:
                print(f"  Обработано {line_num:,} строк...")
    
    return unknown_resources, unknown_metrics


def extract_unknown_from_directory(directory):
    """
    Извлекает все UNKNOWN ID из всех CSV файлов в директории
    """
    all_unknown_resources = set()
    all_unknown_metrics = set()
    
    directory = Path(directory)
    csv_files = list(directory.glob("*.csv"))
    
    if not csv_files:
        print(f"⚠️  В директории {directory} не найдено CSV файлов")
        return all_unknown_resources, all_unknown_metrics
    
    print(f"\n🔍 Найдено {len(csv_files)} CSV файлов")
    print("=" * 80)
    
    for csv_file in csv_files:
        unknown_res, unknown_met = extract_unknown_from_csv(csv_file)
        all_unknown_resources.update(unknown_res)
        all_unknown_metrics.update(unknown_met)
    
    return all_unknown_resources, all_unknown_metrics


def read_dict_file(dict_file):
    """
    Читает файл словаря и извлекает существующие ID
    
    Returns:
        dict: {id: name}
    """
    current_dict = {}
    
    with open(dict_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Извлекаем все пары "ID": "Name"
    pattern = r'"(\d+)":\s*"([^"]*)"'
    matches = re.findall(pattern, content)
    
    for match in matches:
        id_str, name = match
        current_dict[id_str] = name
    
    return current_dict


def update_dict_file(dict_file, dict_name, new_entries):
    """
    Добавляет новые записи в файл словаря
    
    Args:
        dict_file: путь к файлу словаря
        dict_name: имя переменной словаря (METRIC_NAME_DICT или RESOURCE_NAME_DICT)
        new_entries: dict {id: name} - новые записи для добавления
    """
    if not new_entries:
        return
    
    # Читаем текущий файл
    with open(dict_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Находим последнюю строку со значением (перед закрывающей })
    insert_index = -1
    for i in range(len(lines) - 1, -1, -1):
        if re.search(r'"\d+"\s*:\s*"[^"]*"', lines[i]):
            insert_index = i
            break
    
    if insert_index == -1:
        print(f"⚠️  Не могу найти место для вставки в {dict_file}")
        return
    
    # Убираем запятую в конце, если её нет
    if not lines[insert_index].rstrip().endswith(','):
        lines[insert_index] = lines[insert_index].rstrip() + ',\n'
    
    # Готовим новые строки
    new_lines = []
    for id_str in sorted(new_entries.keys(), key=lambda x: int(x)):
        name = new_entries[id_str]
        new_lines.append(f'    "{id_str}": "{name}",  # AUTO-ADDED\n')
    
    # Вставляем новые строки
    lines = lines[:insert_index + 1] + new_lines + lines[insert_index + 1:]
    
    # Записываем обратно
    with open(dict_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"✅ Добавлено {len(new_entries)} записей в {dict_file}")


def main(csv_directory=None, auto_confirm=False):
    """
    Основная функция
    
    Args:
        csv_directory: путь к директории с CSV файлами
        auto_confirm: если True, не запрашивает подтверждение
    """
    print("=" * 80)
    print("АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ СЛОВАРЕЙ")
    print("=" * 80)
    print()
    
    # Определяем директорию с CSV
    if csv_directory is None:
        # Ищем последние CSV файлы в output_test
        possible_dirs = [
            "output_test/improved_new",
            "output_test/final_new",
            "output_test/parallel_6000v6_v2",
            "output",
        ]
        
        for dir_path in possible_dirs:
            if Path(dir_path).exists() and list(Path(dir_path).glob("*.csv")):
                csv_directory = dir_path
                print(f"📂 Используем директорию: {csv_directory}")
                break
        
        if csv_directory is None:
            print("❌ Не найдена директория с CSV файлами")
            print("   Укажите путь: python3 update_dictionaries.py <path_to_csv_dir>")
            return 1
    
    # Извлекаем UNKNOWN ID
    unknown_resources, unknown_metrics = extract_unknown_from_directory(csv_directory)
    
    print()
    print("=" * 80)
    print("РЕЗУЛЬТАТЫ АНАЛИЗА")
    print("=" * 80)
    print()
    
    if not unknown_resources and not unknown_metrics:
        print("✅ Неизвестных ID не найдено!")
        print("   Все ID присутствуют в словарях")
        return 0
    
    if unknown_resources:
        print(f"📋 Найдено неизвестных ресурсов: {len(unknown_resources)}")
        for res_id in sorted(unknown_resources, key=lambda x: int(x)):
            print(f"  - ID {res_id}")
        print()
    
    if unknown_metrics:
        print(f"📋 Найдено неизвестных метрик: {len(unknown_metrics)}")
        for met_id in sorted(unknown_metrics, key=lambda x: int(x)):
            print(f"  - ID {met_id}")
        print()
    
    # Читаем текущие словари
    print("📖 Читаю текущие словари...")
    current_resources = read_dict_file("RESOURCE_DICT.py")
    current_metrics = read_dict_file("METRIC_DICT.py")
    
    print(f"  Текущих ресурсов: {len(current_resources)}")
    print(f"  Текущих метрик: {len(current_metrics)}")
    print()
    
    # Определяем, что нужно добавить
    resources_to_add = {}
    for res_id in unknown_resources:
        if res_id not in current_resources:
            resources_to_add[res_id] = f"UNKNOWN_RESOURCE_{res_id}"
    
    metrics_to_add = {}
    for met_id in unknown_metrics:
        if met_id not in current_metrics:
            metrics_to_add[met_id] = f"UNKNOWN_METRIC_{met_id}"
    
    if not resources_to_add and not metrics_to_add:
        print("✅ Все неизвестные ID уже есть в словарях!")
        return 0
    
    # Спрашиваем подтверждение
    print("=" * 80)
    print("ПЛАНИРУЕМЫЕ ИЗМЕНЕНИЯ")
    print("=" * 80)
    print()
    
    if resources_to_add:
        print(f"📝 Будет добавлено в RESOURCE_DICT.py: {len(resources_to_add)} записей")
        for res_id in sorted(resources_to_add.keys(), key=lambda x: int(x)):
            print(f'    "{res_id}": "{resources_to_add[res_id]}"')
        print()
    
    if metrics_to_add:
        print(f"📝 Будет добавлено в METRIC_DICT.py: {len(metrics_to_add)} записей")
        for met_id in sorted(metrics_to_add.keys(), key=lambda x: int(x)):
            print(f'    "{met_id}": "{metrics_to_add[met_id]}"')
        print()
    
    # Подтверждение
    if auto_confirm:
        print("🤖 Режим авто-подтверждения: применяю изменения...")
        response = 'y'
    else:
        response = input("Применить изменения? [y/N]: ").strip().lower()
        
        if response not in ['y', 'yes', 'д', 'да']:
            print("\n❌ Отменено пользователем")
            return 0
    
    print()
    print("=" * 80)
    print("ОБНОВЛЕНИЕ СЛОВАРЕЙ")
    print("=" * 80)
    print()
    
    # Обновляем файлы
    if resources_to_add:
        update_dict_file("RESOURCE_DICT.py", "RESOURCE_NAME_DICT", resources_to_add)
    
    if metrics_to_add:
        update_dict_file("METRIC_DICT.py", "METRIC_NAME_DICT", metrics_to_add)
    
    print()
    print("=" * 80)
    print("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО!")
    print("=" * 80)
    print()
    print("📊 Итого:")
    print(f"  Ресурсов было: {len(current_resources)}")
    print(f"  Ресурсов стало: {len(current_resources) + len(resources_to_add)}")
    print(f"  Добавлено: {len(resources_to_add)}")
    print()
    print(f"  Метрик было: {len(current_metrics)}")
    print(f"  Метрик стало: {len(current_metrics) + len(metrics_to_add)}")
    print(f"  Добавлено: {len(metrics_to_add)}")
    print()
    print("💡 Рекомендация:")
    print("   1. Проверьте обновленные словари")
    print("   2. Перезапустите парсер на тех же данных")
    print("   3. Убедитесь, что UNKNOWN ID больше нет")
    print()
    
    return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Автоматическое обновление словарей METRIC_DICT.py и RESOURCE_DICT.py'
    )
    parser.add_argument(
        'csv_directory',
        nargs='?',
        help='Путь к директории с CSV файлами (необязательно, будет автоопределена)'
    )
    parser.add_argument(
        '--auto', '-y',
        action='store_true',
        help='Автоматически применить изменения без подтверждения'
    )
    
    args = parser.parse_args()
    
    sys.exit(main(args.csv_directory, auto_confirm=args.auto))

