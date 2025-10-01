#!/usr/bin/env python3
"""
Генератор дашборда на основе реального маппинга из данных.
"""

import json
import sys

# Пытаемся импортировать реальный маппинг
try:
    from resource_metric_mapping_real import (
        RESOURCE_MAPPING, METRIC_MAPPING, RESOURCE_TO_METRICS, DEFAULT_RESOURCES
    )
    print("✅ Используется маппинг из реальных данных: resource_metric_mapping_real.py")
except ImportError:
    print("⚠️  Файл resource_metric_mapping_real.py не найден")
    print("   Запустите сначала: python3 build_dashboard_from_real_data.py")
    sys.exit(1)

from generate_dashboard_fixed import (
    create_panel, get_unit_for_metric, create_row, sanitize_metric_name
)

def generate_dashboard():
    """Генерирует дашборд на основе реальных данных"""
    panels = []
    panel_id = 1
    y_position = 0
    
    # Создаем группу панелей для каждого ресурса
    for resource_id in DEFAULT_RESOURCES:
        resource_name = RESOURCE_MAPPING[resource_id]
        metric_ids = RESOURCE_TO_METRICS[resource_id]
        
        # Создаем row для группировки
        row = create_row(f"📊 {resource_name}", y_position, panel_id)
        row_panels = []
        panel_id += 1
        y_position += 1
        
        # Добавляем панели ТОЛЬКО для метрик, которые реально есть в данных
        inner_y = 0
        for i, metric_id in enumerate(metric_ids):
            if metric_id not in METRIC_MAPPING:
                print(f"⚠️  Метрика {metric_id} не найдена в METRIC_MAPPING, пропускаем")
                continue
                
            metric_title = METRIC_MAPPING[metric_id]
            
            # Определяем единицу измерения
            unit = get_unit_for_metric(metric_title)
            
            # Располагаем панели по 2 в ряд (12 ширина каждая)
            x_pos = 0 if i % 2 == 0 else 12
            if i > 0 and i % 2 == 0:
                inner_y += 8
            
            panel = create_panel(metric_title, metric_id, metric_title, resource_id, inner_y, panel_id, unit)
            panel["gridPos"]["x"] = x_pos
            
            # Обновляем заголовок панели - убираем префикс ресурса
            panel["title"] = metric_title
            
            row_panels.append(panel)
            panel_id += 1
        
        # Добавляем панели в row
        row["panels"] = row_panels
        panels.append(row)
        y_position += 1
    
    # Создаем полный дашборд
    dashboard = {
        "annotations": {
            "list": [{
                "builtIn": 1,
                "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                "enable": True,
                "hide": True,
                "iconColor": "rgba(0, 211, 255, 1)",
                "name": "Annotations & Alerts",
                "type": "dashboard"
            }]
        },
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 0,
        "id": None,
        "links": [],
        "panels": panels,
        "preload": False,
        "refresh": "",
        "schemaVersion": 41,
        "tags": ["oceanstor", "performance", "huawei", "real-data"],
        "templating": {
            "list": [
                {
                    "current": {"text": "All", "value": "$__all"},
                    "datasource": {"type": "prometheus", "uid": "P4169E866C3094E38"},
                    "definition": "label_values(SN)",
                    "description": "Серийный номер массива",
                    "includeAll": True,
                    "multi": True,
                    "name": "SN",
                    "options": [],
                    "query": {"qryType": 1, "query": "label_values(SN)", "refId": "PrometheusVariableQueryEditor-VariableQuery"},
                    "refresh": 2,
                    "regex": "",
                    "sort": 1,
                    "type": "query"
                },
                {
                    "current": {"text": "All", "value": ["$__all"]},
                    "datasource": {"type": "prometheus", "uid": "P4169E866C3094E38"},
                    "definition": "label_values({SN=~\"$SN\"},Resource)",
                    "description": "Тип ресурса (Controller, LUN, Disk и т.д.)",
                    "includeAll": True,
                    "multi": True,
                    "name": "Resource",
                    "options": [],
                    "query": {"qryType": 1, "query": "label_values({SN=~\"$SN\"},Resource)", "refId": "PrometheusVariableQueryEditor-VariableQuery"},
                    "refresh": 2,
                    "regex": "",
                    "sort": 1,
                    "type": "query"
                },
                {
                    "current": {"text": "All", "value": ["$__all"]},
                    "datasource": {"type": "prometheus", "uid": "P4169E866C3094E38"},
                    "definition": "label_values({SN=~\"$SN\", Resource=~\"$Resource\"},Element)",
                    "description": "Элемент (0A, 0B, CTE0.A.IOM0.P0 и т.д.)",
                    "includeAll": True,
                    "multi": True,
                    "name": "Element",
                    "options": [],
                    "query": {"qryType": 1, "query": "label_values({SN=~\"$SN\", Resource=~\"$Resource\"},Element)", "refId": "PrometheusVariableQueryEditor-VariableQuery"},
                    "refresh": 2,
                    "regex": "",
                    "sort": 1,
                    "type": "query"
                }
            ]
        },
        "time": {"from": "now-6h", "to": "now"},
        "timepicker": {},
        "timezone": "",
        "title": "Huawei OceanStor - Real Data",
        "uid": "huawei-oceanstor-real",
        "version": 1
    }
    
    return dashboard

if __name__ == "__main__":
    dashboard = generate_dashboard()
    output_file = "grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)
    
    # Подсчет статистики
    total_panels = sum(len(panel.get("panels", [])) for panel in dashboard["panels"])
    
    print("="*80)
    print("✅ ДАШБОРД СОЗДАН УСПЕШНО!")
    print("="*80)
    print(f"📁 Файл: {output_file}")
    print(f"📊 Ресурсов: {len(DEFAULT_RESOURCES)}")
    print(f"🎯 Всего панелей: {total_panels}")
    print()
    print("📋 Детальная статистика:")
    for resource_id in DEFAULT_RESOURCES:
        resource_name = RESOURCE_MAPPING[resource_id]
        metric_count = len(RESOURCE_TO_METRICS[resource_id])
        print(f"   • {resource_name:30s} - {metric_count:3d} метрик")
    print("="*80)

