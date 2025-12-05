#!/usr/bin/env python3
"""
Grafana Metrics Validator

Автоматическая проверка соответствия между:
1. Запросами метрик в Grafana dashboard JSON
2. Фактическими метриками в VictoriaMetrics
3. Названиями в METRIC_DICT.py

Использование:
    python3 validate_grafana_metrics.py \
        --dashboard ../grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json \
        --vm-url http://10.5.10.163:8428 \
        --sn 2102355TJUN0QB100013 \
        --output report.txt
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from difflib import SequenceMatcher

import requests

# Добавляем путь к словарям
sys.path.insert(0, str(Path(__file__).parent.parent / "parsers" / "dictionaries"))
sys.path.insert(0, str(Path(__file__).parent.parent / "parsers"))

try:
    from dictionaries import METRIC_NAME_DICT, RESOURCE_NAME_DICT
except ImportError:
    from METRIC_DICT import METRIC_NAME_DICT
    from RESOURCE_DICT import RESOURCE_NAME_DICT


def sanitize_metric_name(name: str) -> str:
    """
    Преобразует название метрики в формат Prometheus.
    Копия из streaming_pipeline.py для консистентности.
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


def load_metric_dict() -> Dict[str, str]:
    """
    Загружает METRIC_DICT и создаёт маппинг:
    sanitized_name -> original_name
    """
    mapping = {}
    for metric_id, original_name in METRIC_NAME_DICT.items():
        sanitized = "huawei_" + sanitize_metric_name(original_name)
        mapping[sanitized] = original_name
    return mapping


def extract_grafana_queries(dashboard_path: str) -> Dict[str, List[Dict]]:
    """
    Извлекает все запросы метрик из Grafana dashboard JSON.
    
    Returns:
        Dict[resource, List[{metric, panel_title, expr}]]
    """
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        dashboard = json.load(f)
    
    queries_by_resource = defaultdict(list)
    
    def extract_from_panel(panel, parent_title=""):
        """Рекурсивно извлекает запросы из панели."""
        panel_title = panel.get('title', 'Unknown')
        
        # Обрабатываем targets
        targets = panel.get('targets', [])
        for target in targets:
            expr = target.get('expr', '')
            if expr and 'huawei_' in expr:
                # Извлекаем имя метрики
                match = re.match(r'([a-z_0-9]+)\{', expr)
                if match:
                    metric_name = match.group(1)
                    
                    # Извлекаем Resource
                    resource_match = re.search(r'Resource="([^"]+)"', expr)
                    resource = resource_match.group(1) if resource_match else "Unknown"
                    
                    queries_by_resource[resource].append({
                        'metric': metric_name,
                        'panel_title': panel_title,
                        'expr': expr
                    })
        
        # Рекурсивно обрабатываем вложенные панели
        for nested_panel in panel.get('panels', []):
            extract_from_panel(nested_panel, panel_title)
    
    # Обрабатываем все панели
    for panel in dashboard.get('panels', []):
        extract_from_panel(panel)
    
    return dict(queries_by_resource)


def get_vm_metrics(vm_url: str, sn: Optional[str] = None, time_point: Optional[str] = None) -> Dict[str, Set[str]]:
    """
    Получает список метрик из VictoriaMetrics.
    
    Args:
        vm_url: URL VictoriaMetrics
        sn: Serial number для фильтрации
        time_point: Временная точка для запроса (ISO format, например '2025-10-13T12:00:00Z')
    
    Returns:
        Dict[resource, Set[metric_names]]
    """
    metrics_by_resource = defaultdict(set)
    
    # Если указано время, используем query вместо series (для исторических данных)
    if time_point:
        return get_vm_metrics_by_query(vm_url, sn, time_point)
    
    # Получаем все ресурсы
    try:
        if sn:
            response = requests.get(
                f"{vm_url}/api/v1/label/Resource/values",
                params={'match[]': f'{{SN="{sn}"}}'},
                timeout=30
            )
        else:
            response = requests.get(
                f"{vm_url}/api/v1/label/Resource/values",
                timeout=30
            )
        response.raise_for_status()
        resources = response.json().get('data', [])
    except Exception as e:
        print(f"Ошибка получения ресурсов из VM: {e}")
        return {}
    
    # Для каждого ресурса получаем метрики
    for resource in resources:
        try:
            if sn:
                match_query = f'{{SN="{sn}",Resource="{resource}"}}'
            else:
                match_query = f'{{Resource="{resource}"}}'
            
            response = requests.get(
                f"{vm_url}/api/v1/series",
                params={'match[]': match_query},
                timeout=30
            )
            response.raise_for_status()
            
            series = response.json().get('data', [])
            for s in series:
                metric_name = s.get('__name__', '')
                if metric_name:
                    metrics_by_resource[resource].add(metric_name)
        except Exception as e:
            print(f"Ошибка получения метрик для {resource}: {e}")
    
    return dict(metrics_by_resource)


def get_vm_metrics_by_query(vm_url: str, sn: Optional[str], time_point: str) -> Dict[str, Set[str]]:
    """
    Получает метрики через query (для исторических данных).
    
    Args:
        vm_url: URL VictoriaMetrics
        sn: Serial number для фильтрации
        time_point: Временная точка для запроса
    
    Returns:
        Dict[resource, Set[metric_names]]
    """
    metrics_by_resource = defaultdict(set)
    
    try:
        # Получаем все ресурсы через count by query
        if sn:
            query = f'count by (Resource) ({{SN="{sn}"}})'
        else:
            query = 'count by (Resource) ({__name__=~"huawei_.*"})'
        
        response = requests.get(
            f"{vm_url}/api/v1/query",
            params={'query': query, 'time': time_point},
            timeout=60
        )
        response.raise_for_status()
        
        results = response.json().get('data', {}).get('result', [])
        resources = [r.get('metric', {}).get('Resource') for r in results if r.get('metric', {}).get('Resource')]
    except Exception as e:
        print(f"Ошибка получения ресурсов из VM: {e}")
        return {}
    
    # Для каждого ресурса получаем метрики
    for resource in resources:
        try:
            if sn:
                query = f'{{SN="{sn}",Resource="{resource}"}}'
            else:
                query = f'{{Resource="{resource}"}}'
            
            response = requests.get(
                f"{vm_url}/api/v1/query",
                params={'query': query, 'time': time_point},
                timeout=60
            )
            response.raise_for_status()
            
            results = response.json().get('data', {}).get('result', [])
            for r in results:
                metric_name = r.get('metric', {}).get('__name__', '')
                if metric_name:
                    metrics_by_resource[resource].add(metric_name)
        except Exception as e:
            print(f"Ошибка получения метрик для {resource}: {e}")
    
    return dict(metrics_by_resource)


def find_similar_metric(metric: str, available_metrics: Set[str], threshold: float = 0.7) -> Optional[str]:
    """
    Находит наиболее похожую метрику используя SequenceMatcher.
    """
    best_match = None
    best_ratio = 0
    
    for available in available_metrics:
        ratio = SequenceMatcher(None, metric, available).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = available
    
    return best_match


def compare_metrics(
    grafana_queries: Dict[str, List[Dict]],
    vm_metrics: Dict[str, Set[str]],
    metric_dict: Dict[str, str]
) -> Dict:
    """
    Сравнивает метрики из трёх источников.
    
    Returns:
        Dict с результатами сравнения
    """
    results = {
        'errors': [],      # Метрики в Grafana, но нет в VM
        'warnings': [],    # Метрики в VM, но нет в Grafana
        'ok': [],          # Совпадающие метрики
        'suggestions': {}, # Предложения по исправлению
        'stats': {
            'total_grafana': 0,
            'total_vm': 0,
            'matching': 0,
            'missing_in_vm': 0,
            'missing_in_grafana': 0
        }
    }
    
    # Собираем все уникальные метрики из Grafana по ресурсам
    grafana_metrics_by_resource = defaultdict(set)
    for resource, queries in grafana_queries.items():
        for q in queries:
            grafana_metrics_by_resource[resource].add(q['metric'])
    
    # Все ресурсы
    all_resources = set(grafana_queries.keys()) | set(vm_metrics.keys())
    
    for resource in sorted(all_resources):
        grafana_set = grafana_metrics_by_resource.get(resource, set())
        vm_set = vm_metrics.get(resource, set())
        
        results['stats']['total_grafana'] += len(grafana_set)
        results['stats']['total_vm'] += len(vm_set)
        
        # Метрики в Grafana, но нет в VM
        missing_in_vm = grafana_set - vm_set
        for metric in missing_in_vm:
            # Ищем похожую метрику в VM
            all_vm_metrics = set()
            for v in vm_metrics.values():
                all_vm_metrics.update(v)
            
            suggestion = find_similar_metric(metric, all_vm_metrics)
            
            # Проверяем есть ли в словаре
            in_dict = metric in metric_dict
            
            results['errors'].append({
                'metric': metric,
                'resource': resource,
                'in_dict': in_dict,
                'suggestion': suggestion
            })
            results['stats']['missing_in_vm'] += 1
        
        # Метрики в VM, но нет в Grafana
        missing_in_grafana = vm_set - grafana_set
        for metric in missing_in_grafana:
            in_dict = metric in metric_dict
            results['warnings'].append({
                'metric': metric,
                'resource': resource,
                'in_dict': in_dict,
                'original_name': metric_dict.get(metric, 'N/A')
            })
            results['stats']['missing_in_grafana'] += 1
        
        # Совпадающие метрики
        matching = grafana_set & vm_set
        for metric in matching:
            results['ok'].append({
                'metric': metric,
                'resource': resource
            })
            results['stats']['matching'] += 1
    
    return results


def generate_report(results: Dict, sn: str, output_path: Optional[str] = None) -> str:
    """
    Генерирует текстовый отчёт.
    """
    lines = []
    lines.append("=" * 80)
    lines.append("GRAFANA METRICS VALIDATION REPORT")
    lines.append("=" * 80)
    lines.append(f"SN: {sn}")
    lines.append("")
    
    # Статистика
    stats = results['stats']
    lines.append("SUMMARY:")
    lines.append(f"  Total metrics in Grafana queries: {stats['total_grafana']}")
    lines.append(f"  Total metrics in VictoriaMetrics: {stats['total_vm']}")
    lines.append(f"  Matching metrics: {stats['matching']}")
    lines.append(f"  Missing in VM (ERRORS): {stats['missing_in_vm']}")
    lines.append(f"  Missing in Grafana (WARNINGS): {stats['missing_in_grafana']}")
    lines.append("")
    
    # Ошибки - метрики в Grafana, но нет в VM
    if results['errors']:
        lines.append("-" * 80)
        lines.append("[ERRORS] Metrics in Grafana but NOT in VictoriaMetrics:")
        lines.append("-" * 80)
        
        # Группируем по ресурсам
        errors_by_resource = defaultdict(list)
        for err in results['errors']:
            errors_by_resource[err['resource']].append(err)
        
        for resource in sorted(errors_by_resource.keys()):
            lines.append(f"\n  Resource: {resource}")
            for err in errors_by_resource[resource]:
                lines.append(f"    - {err['metric']}")
                if err['suggestion']:
                    lines.append(f"      Suggestion: {err['suggestion']}")
                if not err['in_dict']:
                    lines.append(f"      (NOT in METRIC_DICT)")
        lines.append("")
    
    # Предупреждения - метрики в VM, но нет в Grafana (только первые 20)
    if results['warnings']:
        lines.append("-" * 80)
        lines.append("[WARNINGS] Metrics in VictoriaMetrics but NOT in Grafana (first 20):")
        lines.append("-" * 80)
        
        warnings_by_resource = defaultdict(list)
        for warn in results['warnings'][:50]:  # Ограничиваем
            warnings_by_resource[warn['resource']].append(warn)
        
        count = 0
        for resource in sorted(warnings_by_resource.keys()):
            if count >= 20:
                break
            lines.append(f"\n  Resource: {resource}")
            for warn in warnings_by_resource[resource]:
                if count >= 20:
                    break
                lines.append(f"    - {warn['metric']}")
                if warn['original_name'] != 'N/A':
                    lines.append(f"      Original: {warn['original_name']}")
                count += 1
        
        if len(results['warnings']) > 20:
            lines.append(f"\n  ... and {len(results['warnings']) - 20} more")
        lines.append("")
    
    # OK метрики (только счётчик)
    lines.append("-" * 80)
    lines.append(f"[OK] Matching metrics: {stats['matching']}")
    lines.append("-" * 80)
    
    report = "\n".join(lines)
    
    # Сохраняем в файл если указан путь
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to: {output_path}")
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description='Validate Grafana metrics against VictoriaMetrics and METRIC_DICT'
    )
    parser.add_argument(
        '--dashboard', '-d',
        required=True,
        help='Path to Grafana dashboard JSON file'
    )
    parser.add_argument(
        '--vm-url', '-v',
        default='http://localhost:8428',
        help='VictoriaMetrics URL (default: http://localhost:8428)'
    )
    parser.add_argument(
        '--sn', '-s',
        help='Serial number to filter metrics (optional)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path for report (optional)'
    )
    parser.add_argument(
        '--resource', '-r',
        help='Filter by specific resource (e.g., "Controller NFSV3")'
    )
    parser.add_argument(
        '--time', '-t',
        help='Time point for historical data (ISO format, e.g., "2025-10-13T12:00:00Z")'
    )
    
    args = parser.parse_args()
    
    print("Loading METRIC_DICT...")
    metric_dict = load_metric_dict()
    print(f"  Loaded {len(metric_dict)} metrics from dictionary")
    
    print(f"\nExtracting queries from Grafana dashboard: {args.dashboard}")
    grafana_queries = extract_grafana_queries(args.dashboard)
    total_queries = sum(len(q) for q in grafana_queries.values())
    print(f"  Found {total_queries} queries across {len(grafana_queries)} resources")
    
    print(f"\nFetching metrics from VictoriaMetrics: {args.vm_url}")
    if args.sn:
        print(f"  Filtering by SN: {args.sn}")
    if args.time:
        print(f"  Using time point: {args.time}")
    vm_metrics = get_vm_metrics(args.vm_url, args.sn, args.time)
    total_vm = sum(len(m) for m in vm_metrics.values())
    print(f"  Found {total_vm} metrics across {len(vm_metrics)} resources")
    
    # Фильтруем по ресурсу если указан
    if args.resource:
        grafana_queries = {k: v for k, v in grafana_queries.items() if k == args.resource}
        vm_metrics = {k: v for k, v in vm_metrics.items() if k == args.resource}
    
    print("\nComparing metrics...")
    results = compare_metrics(grafana_queries, vm_metrics, metric_dict)
    
    print("\nGenerating report...")
    report = generate_report(results, args.sn or "ALL", args.output)
    
    print("\n" + report)
    
    # Возвращаем код ошибки если есть проблемы
    if results['errors']:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

