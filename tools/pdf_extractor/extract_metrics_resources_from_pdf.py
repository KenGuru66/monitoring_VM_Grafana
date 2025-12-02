#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер метрик и ресурсов из PDF документации Huawei OceanStor
=============================================================
Извлекает:
- Метрики (ID + название) из строк таблиц
- Ресурсы (ID + название) из строк Type с заголовками столбцов

Структура таблиц Performance Indicators в PDF:
  Row 0: ['Indicator', 'ID', 'Statistics Type', ...]  - заголовок
  Row 1: [None, None, 'Controller\nNFSV3', 'ControllerS\n3', ...]  - названия ресурсов
  Row 2: ['Type', '', '1000', '1053', ...]  - ID ресурсов
  Row 3+: ['Metric Name', 'ID', '√', '√', ...]  - метрики
"""

import json
from pathlib import Path
from collections import defaultdict
import pdfplumber

# ============================================================================
# CONFIGURATION
# ============================================================================

# Путь к PDF (относительно корня проекта или абсолютный)
PDF_PATH = Path("tools/pdf_extractor/OceanStor Dorado V700R001C10 REST Interface Reference.pdf")
OUTPUT_JSON = Path("temp/simple_metrics_resources.json")

# Диапазон страниц Appendix с Performance Indicators
APPENDIX_START = 4500  # Начало секции Performance Indicators
APPENDIX_END = 4712

# ============================================================================
# HELPERS
# ============================================================================

def clean_cell(cell) -> str:
    """Очистка содержимого ячейки от переносов строк и лишних пробелов.
    
    Важно: убирает переносы строк БЕЗ пробелов, чтобы склеивать слова:
    - 'ControllerS\n3' -> 'ControllerS3'
    - '129\n9' -> '1299'
    """
    if cell is None:
        return ""
    # Убираем переносы строк (склеиваем части)
    result = str(cell).strip().replace('\n', '').replace('\r', '')
    # Убираем лишние пробелы
    while '  ' in result:
        result = result.replace('  ', ' ')
    return result


def clean_metric_name(cell) -> str:
    """Очистка названия метрики с заменой переносов на пробелы.
    
    Для названий метрик переносы заменяются на пробелы:
    - 'Avg.\nHeadObjec\nt Response\nTime' -> 'Avg. HeadObject Response Time'
    """
    if cell is None:
        return ""
    result = str(cell).strip().replace('\n', ' ').replace('\r', ' ')
    # Убираем лишние пробелы
    while '  ' in result:
        result = result.replace('  ', ' ')
    return result


def extract_metric_id(cell) -> str:
    """Извлекает ID метрики из ячейки, склеивая части разбитые переносами.
    
    Примеры:
    - '90099' -> '90099'
    - '129\n9' -> '1299'  (ID разбит на две строки)
    """
    if cell is None:
        return ""
    # Убираем все переносы и пробелы
    result = str(cell).strip().replace('\n', '').replace('\r', '').replace(' ', '')
    return result


def is_valid_metric_id(cell) -> bool:
    """Проверка, является ли ячейка ID метрики (число от 2 до 100000)"""
    cell_str = extract_metric_id(cell)
    if not cell_str:
        return False
    try:
        num = int(cell_str)
        return 2 <= num <= 100000
    except ValueError:
        return False


def is_valid_resource_id(cell) -> bool:
    """Проверка, является ли ячейка ID ресурса (число от 10 до 100000)"""
    cell_str = extract_metric_id(cell)  # Используем ту же логику
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

def extract_all_metrics_and_resources(pdf_path: Path) -> dict:
    """
    Извлекает ВСЕ метрики и ресурсы из PDF.
    
    Структура таблиц Performance Indicators:
    - Row N-1: Названия ресурсов в заголовках столбцов
    - Row N: 'Type' + ID ресурсов
    - Row N+1...: Метрики с ID во втором столбце
    
    Returns:
        dict с ключами 'metrics' и 'resources'
    """
    print(f"\n{'='*80}")
    print("EXTRACTION: Metrics + Resources with Names")
    print(f"{'='*80}\n")
    
    all_metrics = {}  # metric_id -> {id, name, pages}
    all_resources = {}  # resource_id -> {id, name, pages}
    
    total_tables = 0
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(APPENDIX_START, min(APPENDIX_END, len(pdf.pages))):
            if (page_num - APPENDIX_START) % 50 == 0:
                print(f"  Page {page_num}/{APPENDIX_END}... (metrics: {len(all_metrics)}, resources: {len(all_resources)})")
            
            try:
                page = pdf.pages[page_num]
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    total_tables += 1
                    
                    # Ищем строку Type для ресурсов
                    for row_idx, row in enumerate(table):
                        if not row:
                            continue
                        
                        first_cell = clean_cell(row[0]).lower()
                        
                        # Нашли строку Type - извлекаем ресурсы с названиями
                        if first_cell == 'type':
                            # Получаем строку с названиями ресурсов (предыдущая строка)
                            resource_names_row = table[row_idx - 1] if row_idx > 0 else None
                            
                            for col_idx in range(1, len(row)):
                                resource_id = extract_metric_id(row[col_idx])
                                if is_valid_resource_id(resource_id):
                                    # Извлекаем название ресурса из заголовка столбца
                                    resource_name = ""
                                    if resource_names_row and col_idx < len(resource_names_row):
                                        # Очищаем название: убираем переносы строк
                                        resource_name = clean_cell(resource_names_row[col_idx])
                                    
                                    if resource_id not in all_resources:
                                        all_resources[resource_id] = {
                                            'id': resource_id,
                                            'name': resource_name,
                                            'pages': set()
                                        }
                                    else:
                                        # Обновляем название если текущее длиннее или предыдущее пустое
                                        if resource_name and (
                                            not all_resources[resource_id]['name'] or
                                            len(resource_name) > len(all_resources[resource_id]['name'])
                                        ):
                                            all_resources[resource_id]['name'] = resource_name
                                    
                                    all_resources[resource_id]['pages'].add(page_num)
                        
                        # Каждая строка может быть метрикой
                        # Ищем паттерн: [Название, ID, ...]
                        if len(row) >= 2:
                            # Для названий метрик используем пробелы вместо переносов
                            metric_name = clean_metric_name(row[0])
                            metric_id = extract_metric_id(row[1])
                            
                            # Проверяем что это метрика
                            if metric_name and len(metric_name) > 3 and is_valid_metric_id(metric_id):
                                # Фильтруем служебные строки
                                if metric_name.lower() in ['indicator', 'type', 'statistics type']:
                                    continue
                                
                                if metric_id not in all_metrics:
                                    all_metrics[metric_id] = {
                                        'id': metric_id,
                                        'name': metric_name,
                                        'pages': set()
                                    }
                                else:
                                    # Используем более длинное название
                                    if len(metric_name) > len(all_metrics[metric_id]['name']):
                                        all_metrics[metric_id]['name'] = metric_name
                                
                                all_metrics[metric_id]['pages'].add(page_num)
            
            except Exception as e:
                print(f"  ⚠️  Error on page {page_num}: {e}")
                continue
    
    print(f"\n✅ Extraction complete!")
    print(f"   Tables processed: {total_tables}")
    print(f"   Unique metrics: {len(all_metrics)}")
    print(f"   Unique resources: {len(all_resources)}")
    
    # Конвертируем sets в lists для JSON
    for metric_id in all_metrics:
        all_metrics[metric_id]['pages'] = sorted(list(all_metrics[metric_id]['pages']))
    
    for resource_id in all_resources:
        all_resources[resource_id]['pages'] = sorted(list(all_resources[resource_id]['pages']))
    
    return {
        'metrics': all_metrics,
        'resources': all_resources
    }

# ============================================================================
# COMPARISON
# ============================================================================

def compare_with_existing(data: dict):
    """Сравнивает с существующими словарями"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "parsers" / "dictionaries"))
    
    from METRIC_DICT import METRIC_NAME_DICT
    from RESOURCE_DICT import RESOURCE_NAME_DICT
    
    pdf_metrics = set(data['metrics'].keys())
    dict_metrics = set(METRIC_NAME_DICT.keys())
    
    pdf_resources = set(data['resources'].keys())
    dict_resources = set(RESOURCE_NAME_DICT.keys())
    
    common_m = pdf_metrics & dict_metrics
    new_m = pdf_metrics - dict_metrics
    missing_m = dict_metrics - pdf_metrics
    
    common_r = pdf_resources & dict_resources
    new_r = pdf_resources - dict_resources
    missing_r = dict_resources - pdf_resources
    
    print(f"\n{'='*80}")
    print("COMPARISON WITH EXISTING DICTIONARIES")
    print(f"{'='*80}")
    
    print(f"\n📊 METRICS:")
    print(f"   📄 PDF: {len(pdf_metrics)}")
    print(f"   📚 METRIC_DICT.py: {len(dict_metrics)}")
    print(f"   ✅ Common: {len(common_m)} ({len(common_m)/len(dict_metrics)*100:.1f}% coverage of dict)")
    print(f"   🆕 New in PDF: {len(new_m)}")
    print(f"   ⚠️  Only in dict: {len(missing_m)}")
    
    print(f"\n📦 RESOURCES:")
    print(f"   📄 PDF: {len(pdf_resources)}")
    print(f"   📚 RESOURCE_DICT.py: {len(dict_resources)}")
    print(f"   ✅ Common: {len(common_r)} ({len(common_r)/len(dict_resources)*100:.1f}% coverage of dict)")
    print(f"   🆕 New in PDF: {len(new_r)}")
    print(f"   ⚠️  Only in dict: {len(missing_r)}")
    
    # Показываем новые метрики
    if new_m and len(new_m) <= 30:
        print(f"\n🆕 NEW METRICS in PDF (not in dict):")
        for metric_id in sorted(new_m, key=lambda x: int(x)):
            metric = data['metrics'][metric_id]
            print(f"   {metric_id:>5s}: {metric['name'][:70]}")
    
    # Показываем новые ресурсы с названиями
    if new_r:
        print(f"\n🆕 NEW RESOURCES in PDF (not in dict):")
        for resource_id in sorted(new_r, key=lambda x: int(x)):
            resource = data['resources'][resource_id]
            name = resource.get('name', 'UNKNOWN')
            print(f"   {resource_id:>5s}: {name}")
    
    # Показываем все ресурсы из PDF с названиями для сравнения
    print(f"\n📦 ALL RESOURCES FROM PDF:")
    for resource_id in sorted(pdf_resources, key=lambda x: int(x)):
        resource = data['resources'][resource_id]
        name = resource.get('name', 'UNKNOWN')
        dict_name = RESOURCE_NAME_DICT.get(resource_id, '❌ NOT IN DICT')
        match_status = "✅" if name == dict_name or resource_id not in dict_resources else "⚠️"
        print(f"   {resource_id:>5s}: PDF='{name}' | DICT='{dict_name}' {match_status}")
    
    return {
        'metrics': {
            'pdf': len(pdf_metrics),
            'dict': len(dict_metrics),
            'common': len(common_m),
            'new': sorted(list(new_m), key=lambda x: int(x)),
            'missing': sorted(list(missing_m), key=lambda x: int(x))
        },
        'resources': {
            'pdf': len(pdf_resources),
            'dict': len(dict_resources),
            'common': len(common_r),
            'new': sorted(list(new_r), key=lambda x: int(x)),
            'missing': sorted(list(missing_r), key=lambda x: int(x))
        }
    }

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*80)
    print("SIMPLE METRICS & RESOURCES EXTRACTION")
    print("="*80)
    print(f"\nPDF: {PDF_PATH.name}")
    print(f"Pages: {APPENDIX_START}-{APPENDIX_END}\n")
    
    OUTPUT_JSON.parent.mkdir(exist_ok=True)
    
    # Extract
    data = extract_all_metrics_and_resources(PDF_PATH)
    
    # Show results
    print(f"\n📋 METRICS FOUND ({len(data['metrics'])}):")
    sample_metrics = list(data['metrics'].items())[:10]
    for metric_id, metric_data in sample_metrics:
        print(f"   {metric_id:>5s}: {metric_data['name'][:60]}")
    if len(data['metrics']) > 10:
        print(f"   ... and {len(data['metrics']) - 10} more")
    
    print(f"\n📦 RESOURCES FOUND ({len(data['resources'])}):")
    for resource_id in sorted(data['resources'].keys(), key=lambda x: int(x)):
        resource = data['resources'][resource_id]
        name = resource.get('name', 'UNKNOWN')
        print(f"   {resource_id:>5s}: {name}")
    
    # Save JSON
    output_data = {
        'metrics': {mid: {
            'id': mdata['id'],
            'name': mdata['name'],
            'pages': mdata['pages']
        } for mid, mdata in data['metrics'].items()},
        'resources': {rid: {
            'id': rdata['id'],
            'name': rdata.get('name', ''),
            'pages': rdata['pages']
        } for rid, rdata in data['resources'].items()}
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ JSON saved: {OUTPUT_JSON}")
    
    # Compare
    comparison = compare_with_existing(data)
    
    # Add comparison to output
    output_data['comparison'] = comparison
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*80)
    print("✅ COMPLETE!")
    print("="*80)
    print(f"\n📊 Results:")
    print(f"   Metrics: {len(data['metrics'])}")
    print(f"   Resources: {len(data['resources'])}")
    print(f"   Coverage: {comparison['metrics']['common']}/{comparison['metrics']['dict']} metrics ({comparison['metrics']['common']/comparison['metrics']['dict']*100:.1f}%)")
    print(f"   File: {OUTPUT_JSON}\n")

if __name__ == "__main__":
    main()

