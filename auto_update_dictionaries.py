#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматическое обновление словарей METRIC_DICT и RESOURCE_DICT.
Сканирует логи парсинга на unknown IDs и добавляет их в словари с метаданными.
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def extract_unknown_ids_from_logs(log_file: Path):
    """
    Извлекает unknown resource и metric IDs из логов парсинга.
    
    Returns:
        tuple: (set of unknown resource IDs, set of unknown metric IDs)
    """
    unknown_resources = set()
    unknown_metrics = set()
    
    if not log_file.exists():
        print(f"⚠️  Лог файл не найден: {log_file}")
        return unknown_resources, unknown_metrics
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Ищем строки с unknown resource IDs
            match = re.search(r'unknown resource IDs.*?: \[(.*?)\]', line)
            if match:
                ids_str = match.group(1).replace("'", "").replace('"', '')
                ids = [x.strip() for x in ids_str.split(',') if x.strip()]
                unknown_resources.update(ids)
            
            # Ищем строки с unknown metric IDs
            match = re.search(r'unknown metric IDs.*?: \[(.*?)\]', line)
            if match:
                ids_str = match.group(1).replace("'", "").replace('"', '')
                ids = [x.strip() for x in ids_str.split(',') if x.strip()]
                unknown_metrics.update(ids)
    
    return unknown_resources, unknown_metrics


def read_existing_dict(dict_file: Path):
    """Читает существующий словарь и возвращает множество известных IDs."""
    existing_ids = set()
    
    if not dict_file.exists():
        return existing_ids
    
    with open(dict_file, 'r', encoding='utf-8') as f:
        content = f.read()
        # Ищем все ID в формате "1234":
        matches = re.findall(r'"(\d+)":', content)
        existing_ids.update(matches)
    
    return existing_ids


def generate_resource_dict_entry(resource_id: str, date_added: str) -> str:
    """
    Генерирует новую запись для RESOURCE_DICT.
    
    Args:
        resource_id: ID ресурса
        date_added: Дата добавления
    
    Returns:
        str: Строка для добавления в словарь
    """
    return f'    "{resource_id}": "UNKNOWN_RESOURCE_{resource_id}",  # ⚠️ Автоматически добавлено {date_added}, требует уточнения'


def generate_metric_dict_entry(metric_id: str, date_added: str) -> str:
    """
    Генерирует новую запись для METRIC_DICT.
    
    Args:
        metric_id: ID метрики
        date_added: Дата добавления
    
    Returns:
        str: Строка для добавления в словарь
    """
    return f'    "{metric_id}": "UNKNOWN_METRIC_{metric_id}",  # ⚠️ Автоматически добавлено {date_added}, требует уточнения'


def update_resource_dict(new_resources: set, dict_file: Path, date_added: str) -> int:
    """
    Обновляет RESOURCE_DICT новыми ресурсами.
    
    Returns:
        int: Количество добавленных записей
    """
    if not new_resources:
        return 0
    
    # Читаем существующий файл
    with open(dict_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Находим позицию для вставки (перед закрывающей скобкой)
    insert_pos = -1
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == '}':
            insert_pos = i
            break
    
    if insert_pos == -1:
        print(f"❌ Не могу найти закрывающую скобку в {dict_file}")
        return 0
    
    # Создаем секцию для новых ресурсов
    new_section = []
    new_section.append("\n")
    new_section.append(f"    # ============================================================================\n")
    new_section.append(f"    # АВТОМАТИЧЕСКИ ДОБАВЛЕННЫЕ РЕСУРСЫ - {date_added}\n")
    new_section.append(f"    # ============================================================================\n")
    new_section.append(f"    # ⚠️ ВНИМАНИЕ: Эти ресурсы были найдены в логах парсинга, но не были\n")
    new_section.append(f"    # определены в словаре. Требуется вручную уточнить названия!\n")
    new_section.append("\n")
    
    for resource_id in sorted(new_resources, key=int):
        new_section.append(f"{generate_resource_dict_entry(resource_id, date_added)}\n")
    
    # Вставляем новую секцию
    lines[insert_pos:insert_pos] = new_section
    
    # Записываем обратно
    with open(dict_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return len(new_resources)


def update_metric_dict(new_metrics: set, dict_file: Path, date_added: str) -> int:
    """
    Обновляет METRIC_DICT новыми метриками.
    
    Returns:
        int: Количество добавленных записей
    """
    if not new_metrics:
        return 0
    
    # Читаем существующий файл
    with open(dict_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Находим позицию для вставки (перед закрывающей скобкой)
    insert_pos = -1
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == '}':
            insert_pos = i
            break
    
    if insert_pos == -1:
        print(f"❌ Не могу найти закрывающую скобку в {dict_file}")
        return 0
    
    # Создаем секцию для новых метрик
    new_section = []
    new_section.append("\n")
    new_section.append(f"    # ============================================================================\n")
    new_section.append(f"    # АВТОМАТИЧЕСКИ ДОБАВЛЕННЫЕ МЕТРИКИ - {date_added}\n")
    new_section.append(f"    # ============================================================================\n")
    new_section.append(f"    # ⚠️ ВНИМАНИЕ: Эти метрики были найдены в логах парсинга, но не были\n")
    new_section.append(f"    # определены в словаре. Требуется вручную уточнить названия и единицы!\n")
    new_section.append("\n")
    
    for metric_id in sorted(new_metrics, key=int):
        new_section.append(f"{generate_metric_dict_entry(metric_id, date_added)}\n")
    
    # Вставляем новую секцию
    lines[insert_pos:insert_pos] = new_section
    
    # Записываем обратно
    with open(dict_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return len(new_metrics)


def main():
    """Основная функция."""
    # Пути к файлам
    project_root = Path(__file__).parent
    log_file = project_root / "streaming_pipeline.log"
    resource_dict_file = project_root / "Data2csv" / "RESOURCE_DICT.py"
    metric_dict_file = project_root / "Data2csv" / "METRIC_DICT.py"
    
    print(f"\n{'='*80}")
    print(f"🔄 АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ СЛОВАРЕЙ")
    print(f"{'='*80}\n")
    
    # Извлекаем unknown IDs из логов
    print(f"📖 Сканирование логов: {log_file.name}")
    unknown_resources, unknown_metrics = extract_unknown_ids_from_logs(log_file)
    
    print(f"   Найдено unknown resource IDs: {len(unknown_resources)}")
    print(f"   Найдено unknown metric IDs: {len(unknown_metrics)}")
    
    if not unknown_resources and not unknown_metrics:
        print(f"\n✅ Все ресурсы и метрики уже определены в словарях!")
        print(f"   Нет необходимости в обновлении.\n")
        return 0
    
    # Читаем существующие словари
    print(f"\n📚 Проверка существующих словарей...")
    existing_resources = read_existing_dict(resource_dict_file)
    existing_metrics = read_existing_dict(metric_dict_file)
    
    # Определяем новые ID (которых нет в словарях)
    new_resources = unknown_resources - existing_resources
    new_metrics = unknown_metrics - existing_metrics
    
    print(f"   Новых resource IDs для добавления: {len(new_resources)}")
    if new_resources:
        print(f"   {sorted(new_resources, key=int)}")
    
    print(f"   Новых metric IDs для добавления: {len(new_metrics)}")
    if new_metrics:
        print(f"   {sorted(new_metrics, key=int)}")
    
    if not new_resources and not new_metrics:
        print(f"\n✅ Все unknown IDs уже есть в словарях!")
        print(f"   Нет необходимости в обновлении.\n")
        return 0
    
    # Дата добавления
    date_added = datetime.now().strftime("%Y-%m-%d")
    
    # Обновляем словари
    print(f"\n🔧 Обновление словарей...")
    
    added_resources = 0
    if new_resources:
        added_resources = update_resource_dict(new_resources, resource_dict_file, date_added)
        print(f"   ✅ Добавлено {added_resources} новых ресурсов в RESOURCE_DICT.py")
    
    added_metrics = 0
    if new_metrics:
        added_metrics = update_metric_dict(new_metrics, metric_dict_file, date_added)
        print(f"   ✅ Добавлено {added_metrics} новых метрик в METRIC_DICT.py")
    
    # Итоговый отчет
    print(f"\n{'='*80}")
    print(f"✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО")
    print(f"{'='*80}")
    print(f"   Добавлено ресурсов: {added_resources}")
    print(f"   Добавлено метрик: {added_metrics}")
    print(f"   Дата добавления: {date_added}")
    print(f"\n⚠️  ВАЖНО: Новые записи помечены как UNKNOWN и требуют ручного уточнения!")
    print(f"   Проверьте файлы:")
    print(f"   - {resource_dict_file}")
    print(f"   - {metric_dict_file}")
    print(f"{'='*80}\n")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⚠️  Прервано пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



