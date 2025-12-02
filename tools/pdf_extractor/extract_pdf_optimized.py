#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Оптимизированное извлечение метрик и ресурсов из PDF (pdfplumber)
=================================================================
Использует pdfplumber для более точного извлечения таблиц.
Извлекает названия ресурсов из заголовков столбцов таблиц.

Структура таблиц Performance Indicators в PDF:
  Row 0: ['Indicator', 'ID', 'Statistics Type', ...]  - заголовок
  Row 1: [None, None, 'Controller\nNFSV3', 'ControllerS\n3', ...]  - названия ресурсов
  Row 2: ['Type', '', '1000', '1053', ...]  - ID ресурсов
  Row 3+: ['Metric Name', 'ID', '√', '√', ...]  - метрики
"""

import re
import json
import pdfplumber
from pathlib import Path
from collections import defaultdict

# ============================================================================
# CONFIGURATION
# ============================================================================

# Путь к PDF (относительно директории скрипта)
PDF_PATH = Path(__file__).parent / "OceanStor Dorado V700R001C10 REST Interface Reference.pdf"
OUTPUT_DIR = Path(__file__).parent
DICT_FILE = Path(__file__).parent.parent.parent / "parsers" / "dictionaries" / "METRIC_DICT.py"
RESOURCE_DICT_FILE = Path(__file__).parent.parent.parent / "parsers" / "dictionaries" / "RESOURCE_DICT.py"

# Диапазон страниц Appendix с Performance Indicators
APPENDIX_START = 4500
APPENDIX_END = 4712


# ============================================================================
# HELPERS
# ============================================================================

def clean_cell(cell) -> str:
    """Очистка содержимого ячейки от переносов строк (склеивание слов)"""
    if cell is None:
        return ""
    result = str(cell).strip().replace('\n', '').replace('\r', '')
    while '  ' in result:
        result = result.replace('  ', ' ')
    return result


def clean_metric_name(cell) -> str:
    """Очистка названия метрики с заменой переносов на пробелы"""
    if cell is None:
        return ""
    result = str(cell).strip().replace('\n', ' ').replace('\r', ' ')
    while '  ' in result:
        result = result.replace('  ', ' ')
    return result


def extract_metric_id(cell) -> str:
    """Извлекает ID метрики из ячейки, склеивая части разбитые переносами"""
    if cell is None:
        return ""
    return str(cell).strip().replace('\n', '').replace('\r', '').replace(' ', '')


def is_valid_metric_id(cell) -> bool:
    """Проверка, является ли ячейка ID метрики"""
    cell_str = extract_metric_id(cell)
    if not cell_str:
        return False
    try:
        num = int(cell_str)
        return 2 <= num <= 100000
    except ValueError:
        return False


def is_valid_resource_id(cell) -> bool:
    """Проверка, является ли ячейка ID ресурса"""
    cell_str = extract_metric_id(cell)
    if not cell_str:
        return False
    try:
        num = int(cell_str)
        return 10 <= num <= 100000
    except ValueError:
        return False


# ============================================================================
# EXTRACTION
# ============================================================================

def extract_metrics_and_resources(pdf_path: Path) -> tuple:
    """
    Извлекает метрики и ресурсы из PDF с использованием pdfplumber.
    
    Returns:
        tuple: (metrics_dict, resources_dict)
    """
    print(f"📖 Открываем PDF: {pdf_path.name}...")
    
    metrics = {}  # metric_id -> {name, section, pages}
    resources = {}  # resource_id -> {name, pages}
    
    current_section = "Unknown"
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"   Всего страниц: {total_pages}")
        print(f"   Обрабатываем страницы {APPENDIX_START}-{APPENDIX_END}...")
        
        for page_num in range(APPENDIX_START, min(APPENDIX_END, total_pages)):
            if (page_num - APPENDIX_START) % 50 == 0:
                print(f"   Page {page_num}/{APPENDIX_END}... (metrics: {len(metrics)}, resources: {len(resources)})")
            
            try:
                page = pdf.pages[page_num]
                text = page.extract_text() or ""
                
                # Определяем текущую секцию из текста страницы
                if "4.3.1" in text or "Block Storage" in text:
                    current_section = "Block Storage"
                elif "4.3.2" in text or "File Storage" in text:
                    current_section = "File Storage"
                elif "4.3.3" in text or "Data Protection" in text:
                    current_section = "Data Protection"
                elif "4.3.4" in text or "4.4.4" in text:
                    current_section = "IO"
                elif "4.3.5" in text or "4.4.5" in text or "Protocol" in text:
                    current_section = "Protocol"
                
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # Ищем строку Type для ресурсов
                    for row_idx, row in enumerate(table):
                        if not row:
                            continue
                        
                        first_cell = clean_cell(row[0]).lower()
                        
                        # Нашли строку Type - извлекаем ресурсы с названиями
                        if first_cell == 'type':
                            resource_names_row = table[row_idx - 1] if row_idx > 0 else None
                            
                            for col_idx in range(1, len(row)):
                                resource_id = extract_metric_id(row[col_idx])
                                if is_valid_resource_id(resource_id):
                                    resource_name = ""
                                    
                                    if resource_names_row and col_idx < len(resource_names_row):
                                        resource_name = clean_cell(resource_names_row[col_idx])
                                    
                                    if resource_id not in resources:
                                        resources[resource_id] = {
                                            'name': resource_name,
                                            'pages': set()
                                        }
                                    elif resource_name and len(resource_name) > len(resources[resource_id].get('name', '')):
                                        resources[resource_id]['name'] = resource_name
                                    
                                    resources[resource_id]['pages'].add(page_num)
                        
                        # Извлекаем метрики
                        if len(row) >= 2:
                            metric_name = clean_metric_name(row[0])
                            metric_id = extract_metric_id(row[1])
                            
                            if metric_name and len(metric_name) > 3 and is_valid_metric_id(metric_id):
                                if metric_name.lower() in ['indicator', 'type', 'statistics type']:
                                    continue
                                
                                if metric_id not in metrics:
                                    metrics[metric_id] = {
                                        'name': metric_name,
                                        'section': current_section,
                                        'pages': set()
                                    }
                                elif len(metric_name) > len(metrics[metric_id]['name']):
                                    metrics[metric_id]['name'] = metric_name
                                
                                metrics[metric_id]['pages'].add(page_num)
            
            except Exception as e:
                print(f"   ⚠️  Error on page {page_num}: {e}")
                continue
    
    # Конвертируем sets в lists
    for metric_id in metrics:
        metrics[metric_id]['pages'] = sorted(list(metrics[metric_id]['pages']))
    
    for resource_id in resources:
        resources[resource_id]['pages'] = sorted(list(resources[resource_id]['pages']))
    
    print(f"\n✅ Extraction complete!")
    print(f"   Unique metrics: {len(metrics)}")
    print(f"   Unique resources: {len(resources)}")
    
    return metrics, resources


def compare_with_existing(metrics: dict, resources: dict) -> dict:
    """Сравнивает извлеченные данные с существующими словарями"""
    print(f"\n🔍 Сравниваем с существующими словарями...")
    
    # Читаем существующие словари
    with open(DICT_FILE, 'r', encoding='utf-8') as f:
        metric_content = f.read()
    
    with open(RESOURCE_DICT_FILE, 'r', encoding='utf-8') as f:
        resource_content = f.read()
    
    # Извлекаем существующие ID
    existing_metric_ids = set(re.findall(r'"(\d+)":', metric_content))
    existing_resource_ids = set(re.findall(r'"(\d+)":', resource_content))
    
    extracted_metric_ids = set(metrics.keys())
    extracted_resource_ids = set(resources.keys())
    
    # Метрики
    new_metrics = extracted_metric_ids - existing_metric_ids
    common_metrics = extracted_metric_ids & existing_metric_ids
    missing_metrics = existing_metric_ids - extracted_metric_ids
    
    # Ресурсы
    new_resources = extracted_resource_ids - existing_resource_ids
    common_resources = extracted_resource_ids & existing_resource_ids
    missing_resources = existing_resource_ids - extracted_resource_ids
    
    print(f"\n   📊 METRICS:")
    print(f"      Извлечено из PDF: {len(extracted_metric_ids)}")
    print(f"      В METRIC_DICT.py: {len(existing_metric_ids)}")
    print(f"      ✅ Новые: {len(new_metrics)}")
    print(f"      ✓ Общие: {len(common_metrics)}")
    print(f"      ⚠️  Только в словаре: {len(missing_metrics)}")
    
    print(f"\n   📦 RESOURCES:")
    print(f"      Извлечено из PDF: {len(extracted_resource_ids)}")
    print(f"      В RESOURCE_DICT.py: {len(existing_resource_ids)}")
    print(f"      ✅ Новые: {len(new_resources)}")
    print(f"      ✓ Общие: {len(common_resources)}")
    print(f"      ⚠️  Только в словаре: {len(missing_resources)}")
    
    return {
        'metrics': {
            'new': sorted(new_metrics, key=lambda x: int(x)),
            'common': sorted(common_metrics, key=lambda x: int(x)),
            'missing': sorted(missing_metrics, key=lambda x: int(x))
        },
        'resources': {
            'new': sorted(new_resources, key=lambda x: int(x)),
            'common': sorted(common_resources, key=lambda x: int(x)),
            'missing': sorted(missing_resources, key=lambda x: int(x))
        }
    }


def save_results(metrics: dict, resources: dict, comparison: dict):
    """Сохраняет результаты в JSON и Markdown"""
    print(f"\n💾 Сохраняем результаты...")
    
    # JSON
    json_file = OUTPUT_DIR / "extracted_metrics_detailed.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metrics': metrics,
            'resources': resources,
            'comparison': comparison
        }, f, ensure_ascii=False, indent=2)
    print(f"   ✅ {json_file.name}")
    
    # Markdown отчет
    md_file = OUTPUT_DIR / "PDF_EXTRACTION_REPORT.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# Отчет об извлечении метрик и ресурсов из PDF\n\n")
        f.write(f"**Источник:** {PDF_PATH.name}\n\n")
        f.write("---\n\n")
        
        f.write("## Статистика\n\n")
        f.write(f"- **Извлечено метрик:** {len(metrics)}\n")
        f.write(f"- **Извлечено ресурсов:** {len(resources)}\n")
        f.write(f"- **Новых метрик:** {len(comparison['metrics']['new'])}\n")
        f.write(f"- **Новых ресурсов:** {len(comparison['resources']['new'])}\n\n")
        
        # Таблица ресурсов
        f.write("## Извлеченные ресурсы\n\n")
        f.write("| Resource ID | Resource Name | Pages |\n")
        f.write("|-------------|---------------|-------|\n")
        for rid in sorted(resources.keys(), key=lambda x: int(x)):
            r = resources[rid]
            pages = ', '.join(map(str, r['pages'][:3]))
            if len(r['pages']) > 3:
                pages += '...'
            f.write(f"| {rid} | {r['name']} | {pages} |\n")
        f.write("\n")
        
        # Новые метрики
        if comparison['metrics']['new']:
            f.write("## Новые метрики (не в словаре)\n\n")
            f.write("| Metric ID | Metric Name | Section |\n")
            f.write("|-----------|-------------|----------|\n")
            for mid in comparison['metrics']['new']:
                if mid in metrics:
                    m = metrics[mid]
                    f.write(f"| {mid} | {m['name']} | {m['section']} |\n")
            f.write("\n")
    
    print(f"   ✅ {md_file.name}")
    
    return json_file, md_file


def main():
    print("🚀 Оптимизированное извлечение метрик и ресурсов из PDF\n")
    
    if not PDF_PATH.exists():
        print(f"❌ PDF файл не найден: {PDF_PATH}")
        return
    
    # Извлекаем метрики и ресурсы
    metrics, resources = extract_metrics_and_resources(PDF_PATH)
    
    # Сравниваем с существующими словарями
    comparison = compare_with_existing(metrics, resources)
    
    # Сохраняем результаты
    json_file, md_file = save_results(metrics, resources, comparison)
    
    # Выводим ресурсы для проверки
    print(f"\n📦 RESOURCES FROM PDF:")
    for rid in sorted(resources.keys(), key=lambda x: int(x)):
        r = resources[rid]
        print(f"   {rid:>5s}: {r['name']}")
    
    print(f"\n{'='*80}")
    print(f"🎉 Готово!")
    print(f"   Извлечено метрик: {len(metrics)}")
    print(f"   Извлечено ресурсов: {len(resources)}")
    print(f"   Файлы: {json_file.name}, {md_file.name}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
