#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПРОСТОЙ парсер: собираем только списки метрик и ресурсов
=========================================================
БЕЗ связей между ними!
"""

import json
from pathlib import Path
from collections import defaultdict
import pdfplumber

# ============================================================================
# CONFIGURATION
# ============================================================================

PDF_PATH = Path("Data2csv/pdf/OceanStor Dorado V700R001C10 REST Interface Reference.pdf")
OUTPUT_JSON = Path("temp/simple_metrics_resources.json")

APPENDIX_START = 4100
APPENDIX_END = 4712

# ============================================================================
# HELPERS
# ============================================================================

def clean_cell(cell) -> str:
    """Очистка содержимого ячейки"""
    if cell is None:
        return ""
    return str(cell).strip().replace('\n', ' ')

def is_valid_metric_id(cell) -> bool:
    """Проверка, является ли ячейка ID метрики"""
    cell_str = clean_cell(cell)
    if not cell_str:
        return False
    try:
        num = int(cell_str)
        return 2 <= num <= 100000
    except ValueError:
        return False

def is_valid_resource_id(cell) -> bool:
    """Проверка, является ли ячейка ID ресурса"""
    cell_str = clean_cell(cell)
    if not cell_str:
        return False
    try:
        num = int(cell_str)
        return 10 <= num <= 100000  # Ресурсы обычно >= 10
    except ValueError:
        return False

# ============================================================================
# EXTRACTION
# ============================================================================

def extract_all_metrics_and_resources(pdf_path: Path) -> dict:
    """
    Извлекает ВСЕ метрики и ресурсы из PDF
    """
    print(f"\n{'='*80}")
    print("SIMPLE EXTRACTION: Metrics + Resources Lists")
    print(f"{'='*80}\n")
    
    all_metrics = {}  # metric_id -> {name, pages}
    all_resources = {}  # resource_id -> {pages}
    
    total_tables = 0
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(APPENDIX_START, min(APPENDIX_END, len(pdf.pages))):
            if (page_num - APPENDIX_START) % 100 == 0:
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
                        
                        # Нашли строку Type - извлекаем ресурсы
                        if first_cell == 'type':
                            for col_idx in range(1, len(row)):
                                cell = clean_cell(row[col_idx])
                                if is_valid_resource_id(cell):
                                    resource_id = cell
                                    if resource_id not in all_resources:
                                        all_resources[resource_id] = {'id': resource_id, 'pages': set()}
                                    all_resources[resource_id]['pages'].add(page_num)
                        
                        # Каждая строка может быть метрикой
                        # Ищем паттерн: [Название, ID, ...]
                        if len(row) >= 2:
                            metric_name = clean_cell(row[0])
                            metric_id = clean_cell(row[1])
                            
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
    sys.path.insert(0, str(Path("Data2csv")))
    
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
    
    # Показываем новые ресурсы
    if new_r:
        print(f"\n🆕 NEW RESOURCES in PDF (not in dict):")
        for resource_id in sorted(new_r, key=lambda x: int(x)):
            print(f"   {resource_id}")
    
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
        print(f"   {resource_id}")
    
    # Save JSON
    output_data = {
        'metrics': {mid: {
            'id': mdata['id'],
            'name': mdata['name'],
            'pages': mdata['pages']
        } for mid, mdata in data['metrics'].items()},
        'resources': {rid: {
            'id': rdata['id'],
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

