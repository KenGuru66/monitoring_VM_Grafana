#!/usr/bin/env python3
"""
Обновление файла дашборда напрямую (для provisioned dashboards)
"""
import json
import sys
from pathlib import Path

DASHBOARD_FILE = Path("/data/projects/monitoring_VM_Grafana/grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json")

# Метрики для FC Port
FC_PORT_METRICS = {
    "huawei_average_dataturbo_i_o_response_timeus": {"unit": "µs", "title": "Average DataTurbo I/O response time"},
    "huawei_average_dataturbo_read_i_o_response_timeus": {"unit": "µs", "title": "Average DataTurbo read I/O response time"},
    "huawei_average_dataturbo_write_i_o_response_timeus": {"unit": "µs", "title": "Average DataTurbo write I/O response time"},
    "huawei_average_response_time_of_other_dataturbo_i_osus": {"unit": "µs", "title": "Average response time of other DataTurbo I/Os"},
    "huawei_avg_i_o_response_time_us": {"unit": "µs", "title": "Avg. I/O Response Time"},
    "huawei_avg_i_o_size_kb": {"unit": "deckbytes", "title": "Avg. I/O size"},
    "huawei_avg_read_i_o_link_transmission_latencyus": {"unit": "µs", "title": "Avg. Read I/O Link Transmission Latency"},
    "huawei_avg_read_i_o_response_timeus": {"unit": "µs", "title": "Avg. Read I/O Response Time"},
    "huawei_avg_read_i_o_size_kb": {"unit": "deckbytes", "title": "Avg. read I/O size"},
    "huawei_avg_write_i_o_link_transmission_latencyus": {"unit": "µs", "title": "Avg. Write I/O Link Transmission Latency"},
    "huawei_avg_write_i_o_response_timeus": {"unit": "µs", "title": "Avg. Write I/O Response Time"},
    "huawei_avg_write_i_o_size_kb": {"unit": "deckbytes", "title": "Avg. write I/O size"},
    "huawei_block_bandwidth_mb_s": {"unit": "MBs", "title": "Block bandwidth"},
    "huawei_dataturbo_read_bandwidth_kb_s": {"unit": "KBs", "title": "DataTurbo Read Bandwidth"},
    "huawei_dataturbo_write_bandwidth_kb_s": {"unit": "KBs", "title": "DataTurbo Write Bandwidth"},
    "huawei_max_bandwidth_mb_s": {"unit": "MBs", "title": "Max. bandwidth"},
    "huawei_max_iops_io_s": {"unit": "iops", "title": "Max. IOPS"},
    "huawei_max_i_o_response_time_us": {"unit": "µs", "title": "Max. I/O Response Time"},
    "huawei_other_dataturbo_ops": {"unit": "ops", "title": "Other DataTurbo OPS"},
    "huawei_queue_length": {"unit": "short", "title": "Queue length"},
    "huawei_ratio_of_read_i_os_to_total_i_os_percent": {"unit": "percent", "title": "Ratio of read I/Os to total I/Os"},
    "huawei_ratio_of_write_i_os_to_total_i_os_percent": {"unit": "percent", "title": "Ratio of write I/Os to total I/Os"},
    "huawei_read_bandwidth_mb_s": {"unit": "MBs", "title": "Read bandwidth"},
    "huawei_read_i_o_granularity_distribution_0k4kpercent": {"unit": "percent", "title": "Read I/O Granularity Distribution: [0K,4K)"},
    "huawei_read_i_o_granularity_distribution_128kinf_percent": {"unit": "percent", "title": "Read I/O Granularity Distribution: [128K,+∞)"},
    "huawei_read_i_o_granularity_distribution_16k32k_percent": {"unit": "percent", "title": "Read I/O granularity distribution: [16K,32K)"},
    "huawei_read_i_o_granularity_distribution_32k64k_percent": {"unit": "percent", "title": "Read I/O granularity distribution: [32K,64K)"},
    "huawei_read_i_o_granularity_distribution_4k8k_percent": {"unit": "percent", "title": "Read I/O granularity distribution: [4K,8K)"},
    "huawei_read_i_o_granularity_distribution_64k128k_percent": {"unit": "percent", "title": "Read I/O granularity distribution: [64K,128K)"},
    "huawei_read_i_o_granularity_distribution_8k16k_percent": {"unit": "percent", "title": "Read I/O granularity distribution: [8K,16K)"},
    "huawei_read_iops_io_s": {"unit": "iops", "title": "Read IOPS"},
    "huawei_service_timeus": {"unit": "µs", "title": "Service Time"},
    "huawei_total_dataturbo_bandwidth_kb_s": {"unit": "KBs", "title": "Total DataTurbo Bandwidth"},
    "huawei_total_dataturbo_ops": {"unit": "ops", "title": "Total DataTurbo OPS"},
    "huawei_total_dataturbo_read_ops": {"unit": "ops", "title": "Total DataTurbo Read OPS"},
    "huawei_total_dataturbo_write_ops": {"unit": "ops", "title": "Total DataTurbo write OPS"},
    "huawei_total_iops_io_s": {"unit": "iops", "title": "Total IOPS"},
    "huawei_usage_percent": {"unit": "percent", "title": "Usage"},
    "huawei_write_bandwidth_mb_s": {"unit": "MBs", "title": "Write bandwidth"},
    "huawei_write_i_o_granularity_distribution_0k4kpercent": {"unit": "percent", "title": "Write I/O Granularity Distribution: [0K,4K)"},
    "huawei_write_i_o_granularity_distribution_128kinf_percent": {"unit": "percent", "title": "Write I/O Granularity Distribution: [128K,+∞)"},
    "huawei_write_i_o_granularity_distribution_16k32k_percent": {"unit": "percent", "title": "Write I/O granularity distribution: [16K,32K)"},
    "huawei_write_i_o_granularity_distribution_32k64k_percent": {"unit": "percent", "title": "Write I/O granularity distribution: [32K,64K)"},
    "huawei_write_i_o_granularity_distribution_4k8k_percent": {"unit": "percent", "title": "Write I/O granularity distribution: [4K,8K)"},
    "huawei_write_i_o_granularity_distribution_64k128k_percent": {"unit": "percent", "title": "Write I/O granularity distribution: [64K,128K)"},
    "huawei_write_i_o_granularity_distribution_8k16k_percent": {"unit": "percent", "title": "Write I/O granularity distribution: [8K,16K)"},
    "huawei_write_iops_io_s": {"unit": "iops", "title": "Write IOPS"},
}

# Метрики для Snapshot LUN
SNAPSHOT_LUN_METRICS = {
    "huawei_read_requests_redirected_to_the_source_lun": {"unit": "short", "title": "Read requests redirected to the source LUN"},
    "huawei_read_requests_to_the_snapshot_lun": {"unit": "short", "title": "Read requests to the snapshot LUN"},
    "huawei_write_requests_to_the_snapshot_lun": {"unit": "short", "title": "Write requests to the snapshot LUN"},
}


def create_panel(metric_name, metric_info, panel_id, x, y, resource_name):
    """Создать панель для метрики"""
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
                    "drawStyle": "line",
                    "fillOpacity": 0,
                    "gradientMode": "none",
                    "hideFrom": {"legend": False, "tooltip": False, "viz": False},
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
                    "steps": [{"color": "green", "value": None}, {"color": "red", "value": 80}]
                },
                "unit": metric_info["unit"]
            },
            "overrides": []
        },
        "gridPos": {"h": 8, "w": 12, "x": x, "y": y},
        "id": panel_id,
        "options": {
            "legend": {"calcs": [], "displayMode": "list", "placement": "bottom", "showLegend": True},
            "tooltip": {"hideZeros": False, "mode": "multi", "sort": "none"}
        },
        "pluginVersion": "12.1.1",
        "targets": [
            {
                "datasource": {"type": "prometheus", "uid": "P4169E866C3094E38"},
                "editorMode": "code",
                "expr": f'{metric_name}{{SN=~"$SN", Resource=~"{resource_name}", Element=~"$Element"}}',
                "instant": False,
                "legendFormat": "{{Element}}",
                "range": True,
                "refId": "A"
            }
        ],
        "title": metric_info["title"],
        "type": "timeseries"
    }


def create_row_with_panels(title, metrics, resource_name, start_panel_id):
    """Создать row с панелями"""
    panels = []
    panel_id = start_panel_id
    y = 0
    
    for i, (metric_name, metric_info) in enumerate(metrics.items()):
        x = 0 if i % 2 == 0 else 12
        if i > 0 and i % 2 == 0:
            y += 8
        
        panel = create_panel(metric_name, metric_info, panel_id, x, y, resource_name)
        panels.append(panel)
        panel_id += 1
    
    row = {
        "collapsed": True,
        "datasource": {"type": "prometheus", "uid": "P4169E866C3094E38"},
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0},
        "id": start_panel_id - 1,
        "panels": panels,
        "title": title,
        "type": "row"
    }
    
    return row, panel_id


def main():
    print("="*80)
    print("🔧 UPDATING DASHBOARD FILE")
    print("="*80)
    print()
    
    # Читаем текущий дашборд
    print(f"📥 Reading dashboard from: {DASHBOARD_FILE}")
    with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
        dashboard = json.load(f)
    
    print(f"✅ Current dashboard has {len(dashboard['panels'])} panels")
    print()
    
    # Находим максимальный ID панели
    max_panel_id = max(panel.get('id', 0) for panel in dashboard['panels'])
    print(f"📊 Max panel ID: {max_panel_id}")
    
    # Проверяем, есть ли уже секции FC Port и Snapshot LUN
    existing_titles = [p.get('title', '') for p in dashboard['panels'] if p.get('type') == 'row']
    
    panels_to_add = []
    
    if "📊 FC Port" not in existing_titles:
        print("✨ Adding FC Port section (47 panels)...")
        fc_port_row, max_panel_id = create_row_with_panels(
            "📊 FC Port",
            FC_PORT_METRICS,
            "FC Port",
            max_panel_id + 1
        )
        panels_to_add.append(fc_port_row)
        print(f"   ✅ FC Port section created (ID: {fc_port_row['id']})")
    else:
        print("ℹ️  FC Port section already exists")
    
    if "📊 Snapshot LUN" not in existing_titles:
        print("✨ Adding Snapshot LUN section (3 panels)...")
        snapshot_lun_row, max_panel_id = create_row_with_panels(
            "📊 Snapshot LUN",
            SNAPSHOT_LUN_METRICS,
            "Snapshot LUN",
            max_panel_id + 1
        )
        panels_to_add.append(snapshot_lun_row)
        print(f"   ✅ Snapshot LUN section created (ID: {snapshot_lun_row['id']})")
    else:
        print("ℹ️  Snapshot LUN section already exists")
    
    if not panels_to_add:
        print("\n✅ No sections need to be added!")
        return 0
    
    # Добавляем новые секции в конец
    dashboard['panels'].extend(panels_to_add)
    
    # Создаем бэкап
    backup_file = DASHBOARD_FILE.with_suffix('.json.backup')
    print(f"\n💾 Creating backup: {backup_file}")
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(json.load(open(DASHBOARD_FILE)), f, indent=2)
    
    # Сохраняем обновленный дашборд
    print(f"💾 Saving updated dashboard... ({len(dashboard['panels'])} panels)")
    with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2)
    
    print()
    print("="*80)
    print("🎉 SUCCESS!")
    print("="*80)
    print(f"Added {len(panels_to_add)} new section(s):")
    for panel in panels_to_add:
        print(f"  ✓ {panel['title']} ({len(panel['panels'])} panels)")
    print()
    print("⚠️  NOTE: Grafana needs to be restarted to load the updated dashboard")
    print("   Run: docker-compose restart grafana")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

