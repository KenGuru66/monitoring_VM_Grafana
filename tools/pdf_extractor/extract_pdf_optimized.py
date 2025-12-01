#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Оптимизированное извлечение метрик из PDF (только Appendix секция)
"""

import re
import json
import PyPDF2
from pathlib import Path
from collections import defaultdict

def extract_appendix_pages(pdf_path):
    """Извлекает только страницы из Appendix"""
    print(f"📖 Открываем PDF: {pdf_path.name}...")
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        total_pages = len(reader.pages)
        print(f"   Всего страниц: {total_pages}")
        
        # Ищем начало и конец Appendix
        appendix_start = None
        appendix_end = None
        
        # Быстрый поиск начала Appendix
        for page_num in range(min(100, total_pages)):
            text = reader.pages[page_num].extract_text()
            if 'Appendix' in text or 'Performance Indicators' in text:
                appendix_start = page_num
                print(f"   ✅ Найден Appendix на странице {page_num + 1}")
                break
        
        if not appendix_start:
            print("   ❌ Appendix не найден!")
            return ""
        
        # Извлекаем текст с конца документа (обычно Appendix в конце)
        # Берем последние 500 страниц для безопасности
        start_page = max(appendix_start, total_pages - 500)
        
        print(f"   📄 Извлекаем страницы {start_page + 1} - {total_pages}...")
        
        appendix_text = []
        for page_num in range(start_page, total_pages):
            if (page_num - start_page) % 50 == 0:
                print(f"      Обработано: {page_num - start_page}/{total_pages - start_page}")
            
            text = reader.pages[page_num].extract_text()
            appendix_text.append(text)
        
        full_text = '\n'.join(appendix_text)
        print(f"   ✅ Извлечено: {len(full_text):,} символов")
        
        return full_text

def extract_metrics_advanced(text):
    """Продвинутое извлечение метрик с различными паттернами"""
    metrics = {}
    resources = {}
    
    print("\n🔍 Извлекаем метрики...")
    
    lines = text.split('\n')
    
    # Паттерны для метрик
    metric_patterns = [
        # "Metric Name" | "ID" | other columns
        r'^(.+?)\s+(\d{1,6})\s+[√✓✔]',
        # ID at start: "123 Metric Name"
        r'^(\d{1,6})\s+([A-Z].{10,})',
        # "Metric Name (unit)" | "ID"
        r'^(.+?\(.+?\))\s+(\d{1,6})',
        # Simple: "Name    ID"
        r'^([A-Za-z].{15,}?)\s{2,}(\d{1,6})\s*$',
    ]
    
    # Паттерны для ресурсов (TYPE в документации)
    resource_patterns = [
        r'TYPE:\s*(\d+)\s*=\s*(.+)',
        r'Resource\s+ID:\s*(\d+)\s+(.+)',
        r'Object\s+Type:\s*(\d+)\s+(.+)',
    ]
    
    in_table = False
    current_section = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if not line or len(line) < 5:
            continue
        
        # Определяем текущую секцию
        if 'Performance Indicators' in line:
            current_section = line
            in_table = True
            print(f"\n   📊 Секция: {current_section}")
            continue
        
        # Пропускаем заголовки таблиц
        if re.search(r'\b(Indicator|Name|ID|Description|Unit|Type|Object)\b', line, re.I):
            if not any(p in line for p in ['Performance', 'Request', 'Operation', 'Response']):
                continue
        
        # Пробуем извлечь метрику
        for pattern in metric_patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()
                
                # Определяем, где ID, а где название
                if groups[0].isdigit():
                    metric_id = groups[0]
                    metric_name = groups[1].strip()
                else:
                    metric_id = groups[1]
                    metric_name = groups[0].strip()
                
                # Очистка названия
                metric_name = re.sub(r'\s+', ' ', metric_name)
                metric_name = metric_name.strip('.,;:|()[]')
                
                # Валидация
                if (metric_name and 
                    len(metric_name) > 5 and 
                    not metric_name.lower().startswith(('table', 'figure', 'note', 'parameter')) and
                    metric_id not in metrics):
                    
                    metrics[metric_id] = {
                        'name': metric_name,
                        'section': current_section or 'Unknown'
                    }
                    print(f"      ✅ Metric {metric_id}: {metric_name[:60]}...")
                break
        
        # Пробуем извлечь ресурс
        for pattern in resource_patterns:
            match = re.search(pattern, line)
            if match:
                resource_id = match.group(1)
                resource_name = match.group(2).strip()
                
                resources[resource_id] = resource_name
                print(f"      ✅ Resource {resource_id}: {resource_name}")
                break
    
    print(f"\n   📊 Всего найдено метрик: {len(metrics)}")
    print(f"   📊 Всего найдено ресурсов: {len(resources)}")
    
    return metrics, resources

def compare_with_existing(extracted_metrics, dict_file):
    """Сравнивает извлеченные метрики с существующим словарем"""
    print(f"\n🔍 Сравниваем с существующим словарем...")
    
    # Читаем существующий словарь
    with open(dict_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Извлекаем существующие ID
    existing_ids = set(re.findall(r'"(\d+)":', content))
    
    extracted_ids = set(extracted_metrics.keys())
    
    new_ids = extracted_ids - existing_ids
    existing_ids_found = extracted_ids & existing_ids
    missing_ids = existing_ids - extracted_ids
    
    print(f"\n   📊 Статистика:")
    print(f"      Извлечено из PDF: {len(extracted_ids)}")
    print(f"      В текущем словаре: {len(existing_ids)}")
    print(f"      ✅ Новые метрики: {len(new_ids)}")
    print(f"      ✓ Уже есть: {len(existing_ids_found)}")
    print(f"      ⚠️  Отсутствуют в PDF: {len(missing_ids)}")
    
    return {
        'new': sorted(new_ids, key=int),
        'existing': sorted(existing_ids_found, key=int),
        'missing': sorted(missing_ids, key=int)
    }

def save_results(metrics, resources, comparison, output_dir):
    """Сохраняет результаты"""
    print(f"\n💾 Сохраняем результаты...")
    
    # JSON с метриками
    json_file = output_dir / "extracted_metrics_detailed.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metrics': metrics,
            'resources': resources,
            'comparison': comparison
        }, f, ensure_ascii=False, indent=2)
    print(f"   ✅ {json_file.name}")
    
    # Markdown отчет
    md_file = output_dir / "PDF_EXTRACTION_REPORT.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# 📊 Отчет об извлечении метрик из PDF\n\n")
        f.write("**Источник:** OceanStor Dorado 6.1.8 REST Interface Reference.pdf\n\n")
        f.write("---\n\n")
        
        f.write("## 📈 Статистика\n\n")
        f.write(f"- **Извлечено метрик:** {len(metrics)}\n")
        f.write(f"- **Извлечено ресурсов:** {len(resources)}\n")
        f.write(f"- **Новые метрики:** {len(comparison['new'])}\n")
        f.write(f"- **Уже существующие:** {len(comparison['existing'])}\n\n")
        
        if comparison['new']:
            f.write("## ➕ Новые метрики (не в словаре)\n\n")
            f.write("| Metric ID | Metric Name | Section |\n")
            f.write("|-----------|-------------|----------|\n")
            for mid in comparison['new']:
                if mid in metrics:
                    m = metrics[mid]
                    f.write(f"| {mid} | {m['name']} | {m['section']} |\n")
            f.write("\n")
        
        if resources:
            f.write("## 🔧 Извлеченные ресурсы\n\n")
            f.write("| Resource ID | Resource Name |\n")
            f.write("|-------------|---------------|\n")
            for rid in sorted(resources.keys(), key=int):
                f.write(f"| {rid} | {resources[rid]} |\n")
            f.write("\n")
    
    print(f"   ✅ {md_file.name}")
    
    return json_file, md_file

def main():
    pdf_dir = Path(__file__).parent.parent / "Data2csv" / "pdf"
    pdf_file = pdf_dir / "OceanStor Dorado 6.1.8 REST Interface Reference.pdf"
    dict_file = Path(__file__).parent.parent / "Data2csv" / "METRIC_DICT.py"
    output_dir = Path(__file__).parent
    
    print("🚀 Оптимизированное извлечение метрик из PDF\n")
    
    # Извлекаем только Appendix
    text = extract_appendix_pages(pdf_file)
    
    # Извлекаем метрики и ресурсы
    metrics, resources = extract_metrics_advanced(text)
    
    # Сравниваем с существующим словарем
    comparison = compare_with_existing(metrics, dict_file)
    
    # Сохраняем результаты
    json_file, md_file = save_results(metrics, resources, comparison, output_dir)
    
    print(f"\n{'='*80}")
    print(f"🎉 Готово!")
    print(f"   Извлечено метрик: {len(metrics)}")
    print(f"   Новых метрик: {len(comparison['new'])}")
    print(f"   Файлы: {json_file.name}, {md_file.name}")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()

