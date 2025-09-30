#!/usr/bin/env python3
"""
Генератор дашборда Grafana для Huawei OceanStor.
Создает дашборд с группировкой по ресурсам.
"""

import json
from resource_metric_mapping import RESOURCE_MAPPING, METRIC_MAPPING, DEFAULT_RESOURCES, DEFAULT_METRICS
from csv2vm import sanitize_metric_name

def create_panel(title, metric_name, y_pos, panel_id, unit="short"):
    """Создает панель для графика"""
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
            "expr": f"{metric_name}{{SN=~\"$SN\", Resource=~\"$Resource\", Element=~\"$Element\"}}",
            "fullMetaSearch": False,
            "includeNullMetadata": True,
            "instant": False,
            "legendFormat": "{{Resource}}_{{Element}}_{{SN}}",
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
    if "(%)" in metric_title or "pct" in metric_title.lower():
        return "percent"
    elif "(MB/s)" in metric_title or "bandwidth" in metric_title.lower():
        return "MBs"
    elif "(IO/s)" in metric_title or "iops" in metric_title.lower():
        return "iops"
    elif "(KB)" in metric_title:
        return "deckbytes"
    elif "(us)" in metric_title or "time" in metric_title.lower():
        return "µs"
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
        
        # Создаем row для группировки
        row = create_row(f"📊 {resource_name}", y_position, panel_id)
        row_panels = []
        panel_id += 1
        y_position += 1
        
        # Добавляем панели для каждой метрики
        inner_y = 0
        for i, metric_id in enumerate(DEFAULT_METRICS):
            metric_title = METRIC_MAPPING[metric_id]
            
            # Генерируем имя метрики для Prometheus
            metric_name = "hu_" + sanitize_metric_name(metric_title) + "_variable"
            
            # Определяем единицу измерения
            unit = get_unit_for_metric(metric_title)
            
            # Располагаем панели по 2 в ряд (12 ширина каждая)
            x_pos = 0 if i % 2 == 0 else 12
            if i > 0 and i % 2 == 0:
                inner_y += 8
            
            panel = create_panel(metric_title, metric_name, inner_y, panel_id, unit)
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
        "tags": ["oceanstor", "performance"],
        "templating": {
            "list": [
                {
                    "current": {"text": "All", "value": "$__all"},
                    "datasource": {"type": "prometheus", "uid": "P4169E866C3094E38"},
                    "definition": "label_values(SN)",
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
        "title": "HU Perf - Complete",
        "uid": "hu-perf-complete",
        "version": 1
    }
    
    return dashboard

if __name__ == "__main__":
    dashboard = generate_dashboard()
    output_file = "grafana/provisioning/dashboards/HU Perf-Complete.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Дашборд создан: {output_file}")
    print(f"📊 Ресурсов: {len(DEFAULT_RESOURCES)}")
    print(f"📈 Метрик на ресурс: {len(DEFAULT_METRICS)}")
    print(f"🎯 Всего панелей: {len(DEFAULT_RESOURCES) * len(DEFAULT_METRICS)}")
