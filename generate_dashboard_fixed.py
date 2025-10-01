#!/usr/bin/env python3
"""
Исправленный генератор дашборда Grafana для Huawei OceanStor.
Создает дашборд с правильной группировкой по ресурсам и их метрикам.
"""

import json
import sys
import os

# Добавляем текущую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from resource_metric_mapping_fixed import RESOURCE_MAPPING, METRIC_MAPPING, RESOURCE_TO_METRICS, DEFAULT_RESOURCES

def sanitize_metric_name(metric_name):
    """
    Преобразует название метрики в формат, подходящий для Prometheus.
    Например: "Avg. CPU Usage (%)" -> "avg_cpu_usage_percent"
    """
    # Заменяем % на percent
    name = metric_name.replace("(%)", "percent").replace(" (%)", "_percent")
    name = name.replace("(", "").replace(")", "")
    
    # Заменяем единицы измерения
    name = name.replace("(MB/s)", "mb_s").replace("(KB/s)", "kb_s").replace("(KB)", "kb")
    name = name.replace("(IO/s)", "io_s").replace("(us)", "us").replace("(ms)", "ms")
    
    # Убираем спецсимволы
    name = name.replace("/", "_").replace("-", "_").replace(".", "").replace(",", "")
    name = name.replace(":", "").replace("[", "").replace("]", "").replace("+∞", "inf")
    
    # Заменяем пробелы на подчеркивания
    name = "_".join(name.lower().split())
    
    # Убираем повторяющиеся подчеркивания
    while "__" in name:
        name = name.replace("__", "_")
    
    return name.strip("_")

def create_panel(title, metric_id, metric_title, resource_id, y_pos, panel_id, unit="short"):
    """Создает панель для графика с жестко заданным Resource ID"""
    
    # Генерируем имя метрики для Prometheus
    metric_name = "huawei_" + sanitize_metric_name(metric_title)
    
    return {
        "datasource": {
            "type": "prometheus",
            "uid": "P4169E866C3094E38"
        },
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "axisBorderShow": False,
                    "axisCenteredZero": False,
                    "axisColorMode": "text",
                    "axisLabel": "",
                    "axisPlacement": "auto",
                    "barAlignment": 0,
                    "barWidthFactor": 0.6,
                    "drawStyle": "line",
                    "fillOpacity": 0,
                    "gradientMode": "none",
                    "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                    "insertNulls": False,
                    "lineInterpolation": "linear",
                    "lineWidth": 1,
                    "pointSize": 5,
                    "scaleDistribution": {"type": "linear"},
                    "showPoints": "auto",
                    "spanNulls": False,
                    "stacking": {"group": "A", "mode": "none"},
                    "thresholdsStyle": {"mode": "off"}
                },
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "red", "value": 80}
                    ]
                },
                "unit": unit
            },
            "overrides": []
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": y_pos},
        "id": panel_id,
        "options": {
            "legend": {
                "calcs": [],
                "displayMode": "list",
                "placement": "bottom",
                "showLegend": True
            },
            "tooltip": {"hideZeros": False, "mode": "multi", "sort": "none"}
        },
        "pluginVersion": "12.1.1",
        "targets": [{
            "datasource": {"type": "prometheus", "uid": "P4169E866C3094E38"},
            "disableTextWrap": False,
            "editorMode": "builder",
            # ИСПРАВЛЕНО: Жестко задан Resource ID для каждой секции
            # Используем SN вместо array
            # Resource жестко задан для каждой секции, $Resource влияет только на список Element
            "expr": f'{metric_name}{{SN=~"$SN", Resource="{resource_id}", Element=~"$Element"}}',
            "fullMetaSearch": False,
            "includeNullMetadata": True,
            "instant": False,
            "legendFormat": "{{Element}}",
            "range": True,
            "refId": "A",
            "useBackend": False
        }],
        "title": title,
        "transformations": [{
            "id": "renameByRegex",
            "options": {"regex": "(.*)\\s+", "renamePattern": "$1"}
        }],
        "type": "timeseries"
    }

def get_unit_for_metric(metric_title):
    """Определяет единицу измерения по названию метрики"""
    if "(%)" in metric_title or "percent" in metric_title.lower() or "ratio" in metric_title.lower():
        return "percent"
    elif "(MB/s)" in metric_title:
        return "MBs"
    elif "(KB/s)" in metric_title:
        return "KBs"
    elif "(IO/s)" in metric_title or "iops" in metric_title.lower():
        return "iops"
    elif "(KB)" in metric_title:
        return "deckbytes"
    elif "(us)" in metric_title:
        return "µs"
    elif "(ms)" in metric_title or "time" in metric_title.lower():
        return "ms"
    else:
        return "short"

def create_row(title, y_pos, row_id):
    """Создает строку-группу (collapsible row)"""
    return {
        "collapsed": True,
        "datasource": {"type": "prometheus", "uid": "P4169E866C3094E38"},
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": y_pos},
        "id": row_id,
        "panels": [],
        "title": title,
        "type": "row"
    }

def generate_dashboard():
    """Генерирует полный дашборд"""
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
        
        # Добавляем панели ТОЛЬКО для метрик, применимых к этому ресурсу
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
        "tags": ["oceanstor", "performance", "huawei"],
        "templating": {
            "list": [
                {
                    "current": {"text": "All", "value": "$__all"},
                    "datasource": {"type": "prometheus", "uid": "P4169E866C3094E38"},
                    "definition": "label_values(array)",
                    "includeAll": True,
                    "multi": True,
                    "name": "array",
                    "options": [],
                    "query": {"qryType": 1, "query": "label_values(array)", "refId": "PrometheusVariableQueryEditor-VariableQuery"},
                    "refresh": 2,
                    "regex": "",
                    "sort": 1,
                    "type": "query"
                },
                {
                    "current": {"text": "All", "value": ["$__all"]},
                    "datasource": {"type": "prometheus", "uid": "P4169E866C3094E38"},
                    "definition": "label_values({array=~\"$array\"},Element)",
                    "includeAll": True,
                    "multi": True,
                    "name": "Element",
                    "options": [],
                    "query": {"qryType": 1, "query": "label_values({array=~\"$array\"},Element)", "refId": "PrometheusVariableQueryEditor-VariableQuery"},
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
        "title": "Huawei OceanStor Performance",
        "uid": "huawei-oceanstor-perf",
        "version": 1
    }
    
    return dashboard

if __name__ == "__main__":
    dashboard = generate_dashboard()
    output_file = "grafana/provisioning/dashboards/Huawei-OceanStor-Performance.json"
    
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
        print(f"   • {resource_name:20s} - {metric_count:2d} метрик")
    print("="*80)

