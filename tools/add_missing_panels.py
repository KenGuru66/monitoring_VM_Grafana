#!/usr/bin/env python3
"""
Скрипт для добавления недостающих панелей в Grafana дашборд.

Анализирует метрики из VictoriaMetrics и добавляет панели для тех метрик,
которые отсутствуют в дашборде Grafana.
"""
import json
import sys
import copy
from pathlib import Path
from collections import defaultdict

# Добавляем путь к словарям
sys.path.insert(0, str(Path(__file__).parent.parent / 'parsers'))
from dictionaries import METRIC_NAME_DICT

# Конфигурация
DASHBOARD_PATH = Path(__file__).parent.parent / 'grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json'


def sanitize_metric_name(name: str) -> str:
    """Преобразует название метрики в формат Prometheus."""
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
    return "huawei_" + result.strip("_")


def get_reverse_metric_mapping() -> dict:
    """Создаёт обратный маппинг: sanitized_name -> original_name"""
    mapping = {}
    for metric_id, name in METRIC_NAME_DICT.items():
        sanitized = sanitize_metric_name(name)
        mapping[sanitized] = name
    return mapping


def get_unit_for_metric(metric_name: str) -> str:
    """Определяет единицу измерения для метрики на основе имени."""
    name_lower = metric_name.lower()
    
    if 'percent' in name_lower or '(%)' in metric_name:
        return 'percent'
    elif 'mb_s' in name_lower or '(MB/s)' in metric_name:
        return 'MBs'
    elif 'kb_s' in name_lower or '(KB/s)' in metric_name:
        return 'KBs'
    elif 'bandwidth' in name_lower:
        return 'KBs'
    elif 'timeus' in name_lower or 'time_us' in name_lower or '(us)' in metric_name:
        return 'µs'
    elif 'timems' in name_lower or 'time_ms' in name_lower or '(ms)' in metric_name:
        return 'ms'
    elif 'ops' in name_lower or 'requests' in name_lower:
        return 'ops'
    else:
        return 'short'


def create_panel_template(
    panel_id: int,
    title: str,
    metric_name: str,
    resource: str,
    grid_pos: dict,
    unit: str = 'short'
) -> dict:
    """Создаёт шаблон панели для Grafana."""
    return {
        "datasource": {
            "type": "prometheus",
            "uid": "victoriametrics"
        },
        "fieldConfig": {
            "defaults": {
                "color": {
                    "mode": "palette-classic"
                },
                "custom": {
                    "axisBorderShow": False,
                    "axisCenteredZero": False,
                    "axisColorMode": "text",
                    "axisLabel": "",
                    "axisPlacement": "auto",
                    "barAlignment": 0,
                    "barWidthFactor": 0.6,
                    "drawStyle": "line",
                    "fillOpacity": 10,
                    "gradientMode": "none",
                    "hideFrom": {
                        "legend": False,
                        "tooltip": False,
                        "viz": False
                    },
                    "insertNulls": False,
                    "lineInterpolation": "linear",
                    "lineWidth": 1,
                    "pointSize": 5,
                    "scaleDistribution": {
                        "type": "linear"
                    },
                    "showPoints": "never",
                    "spanNulls": False,
                    "stacking": {
                        "group": "A",
                        "mode": "none"
                    },
                    "thresholdsStyle": {
                        "mode": "off"
                    }
                },
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {
                            "color": "green",
                            "value": None
                        }
                    ]
                },
                "unit": unit
            },
            "overrides": []
        },
        "gridPos": grid_pos,
        "id": panel_id,
        "options": {
            "legend": {
                "calcs": ["mean", "max"],
                "displayMode": "table",
                "placement": "bottom",
                "showLegend": True
            },
            "tooltip": {
                "mode": "multi",
                "sort": "desc"
            }
        },
        "targets": [
            {
                "datasource": {
                    "type": "prometheus",
                    "uid": "victoriametrics"
                },
                "editorMode": "code",
                "expr": f'{metric_name}{{SN=~"$SN", Resource="{resource}", Element=~"$Element"}}',
                "legendFormat": "{{Element}}",
                "range": True,
                "refId": "A"
            }
        ],
        "title": title,
        "type": "timeseries"
    }


def find_row_by_resource(dashboard: dict, resource: str) -> tuple:
    """
    Находит row-панель по названию ресурса.
    Возвращает (индекс в panels, объект row).
    """
    # Маппинг названий ресурсов к названиям групп в дашборде
    resource_to_row = {
        "Controller": "🎛️ Controller",
        "Controller NFSV3": "📁 Controller NFSV3",
        "Controller NFSV4": "📂 Controller NFSV4",
        "Controller NFSV4.1": "📋 Controller NFSV4.1",
        "Controller SMB2/3": "🗃️ Controller SMB2/3",
        "Disk": "💿 Disk",
        "Disk Domain": "💽 Disk Domain",
        "ETH_EXP_Port": "🌐 ETH_EXP_Port",
        "Ethernet Port": "🔗 Ethernet Port",
        "Host": "🖥️ Host",
        "LUN": "💾 LUN",
        "LUN Priority": "⭐ LUN Priority",
        "Logical Port": "🔌 Logical Port",
        "Storage Pool": "🏊 Storage Pool",
        "FC Port": "⚡ FC Port",
        "Snapshot LUN": "📸 Snapshot LUN",
        "ETH Expansion Port": "🔌 ETH Expansion Port (CTE0) - Network Metrics"
    }
    
    row_title = resource_to_row.get(resource, resource)
    
    for idx, panel in enumerate(dashboard.get('panels', [])):
        if panel.get('type') == 'row':
            title = panel.get('title', '')
            # Проверяем точное совпадение или частичное (для гибкости)
            if title == row_title or resource in title:
                return idx, panel
    
    return None, None


def get_max_y_in_row(row_panel: dict) -> int:
    """Получает максимальную Y-координату панелей в row."""
    max_y = 0
    for panel in row_panel.get('panels', []):
        pos = panel.get('gridPos', {})
        panel_bottom = pos.get('y', 0) + pos.get('h', 8)
        if panel_bottom > max_y:
            max_y = panel_bottom
    return max_y


def add_panels_to_dashboard(dashboard: dict, missing_metrics: dict, reverse_mapping: dict) -> tuple:
    """
    Добавляет недостающие панели в дашборд.
    
    Args:
        dashboard: Загруженный JSON дашборда
        missing_metrics: dict {resource: [metric_names]}
        reverse_mapping: dict {sanitized_name: original_name}
    
    Returns:
        (modified_dashboard, count_added)
    """
    # Находим максимальный ID
    max_id = 5039
    def find_max_id(panels):
        nonlocal max_id
        for p in panels:
            if p.get('id', 0) > max_id:
                max_id = p.get('id')
            if p.get('panels'):
                find_max_id(p.get('panels'))
    
    find_max_id(dashboard.get('panels', []))
    next_id = max_id + 1
    
    total_added = 0
    
    for resource, metrics in missing_metrics.items():
        print(f"\nОбработка ресурса: {resource} ({len(metrics)} метрик)")
        
        row_idx, row_panel = find_row_by_resource(dashboard, resource)
        if row_idx is None:
            print(f"  ⚠️ Row для '{resource}' не найден, пропускаем")
            continue
        
        print(f"  Найден row: {row_panel.get('title')}")
        
        # Получаем текущую максимальную Y-позицию в группе
        current_max_y = get_max_y_in_row(row_panel)
        
        # Добавляем панели
        panels_added = 0
        x_pos = 0  # Чередуем: 0, 12, 0, 12...
        y_pos = current_max_y
        
        for metric in metrics:
            # Получаем человекочитаемое название
            original_name = reverse_mapping.get(metric, metric.replace('huawei_', '').replace('_', ' ').title())
            
            # Определяем единицу измерения
            unit = get_unit_for_metric(metric)
            
            # Создаём панель
            grid_pos = {"h": 8, "w": 12, "x": x_pos, "y": y_pos}
            
            panel = create_panel_template(
                panel_id=next_id,
                title=original_name,
                metric_name=metric,
                resource=resource,
                grid_pos=grid_pos,
                unit=unit
            )
            
            # Добавляем в row
            if 'panels' not in row_panel:
                row_panel['panels'] = []
            row_panel['panels'].append(panel)
            
            print(f"  + {original_name} (ID: {next_id})")
            
            next_id += 1
            panels_added += 1
            
            # Обновляем позицию для следующей панели
            x_pos = 12 if x_pos == 0 else 0
            if x_pos == 0:  # Перешли на новую строку
                y_pos += 8
        
        total_added += panels_added
        print(f"  ✅ Добавлено {panels_added} панелей")
    
    return dashboard, total_added


def main():
    print("=" * 60)
    print("ДОБАВЛЕНИЕ НЕДОСТАЮЩИХ ПАНЕЛЕЙ В GRAFANA ДАШБОРД")
    print("=" * 60)
    
    # Загружаем дашборд
    print(f"\nЗагрузка дашборда: {DASHBOARD_PATH}")
    with open(DASHBOARD_PATH) as f:
        dashboard = json.load(f)
    
    # Создаём обратный маппинг метрик
    reverse_mapping = get_reverse_metric_mapping()
    print(f"Загружено {len(reverse_mapping)} метрик из METRIC_DICT")
    
    # Определяем недостающие метрики (из validation_report_final.txt)
    missing_metrics = {
        "Controller": [
            "huawei_ai_cache_hit_ratio_percent"
        ],
        "Controller NFSV3": [
            "huawei_avg_nfs_compound_response_timeus",
            "huawei_avg_nfs_create_response_timeus",
            "huawei_avg_nfs_remove_response_timeus",
            "huawei_avg_nfs_rmdir_response_timeus",
            "huawei_avg_nfs_setattr_response_timeus",
            "huawei_avg_nfsv3_getacl_response_timeus",
            "huawei_avg_nfsv3_setacl_response_timeus",
            "huawei_avg_nfsv4_getacl_response_timeus",
            "huawei_avg_nfsv4_setacl_response_timeus",
            "huawei_avg_operation_response_time_us",
            "huawei_max_operation_response_time_us",
            "huawei_min_operation_response_time_us",
            "huawei_nfsv3_getacl_ops",
            "huawei_nfsv3_setacl_ops",
            "huawei_nfsv4_compound_requests",
            "huawei_nfsv4_getacl_ops",
            "huawei_nfsv4_setacl_ops",
            "huawei_read_i_o_latency_distribution_1s_3spercent",
            "huawei_read_i_o_latency_distribution_200ms_1spercent",
            "huawei_read_i_o_latency_distribution_3s_5spercent",
            "huawei_read_i_o_latency_distribution_5s_8spercent",
            "huawei_read_i_o_latency_distribution_8s_infpercent",
            "huawei_total_nfs_link_ops",
            "huawei_total_nfs_open_ops",
            "huawei_total_nfs_rmdir_ops",
            "huawei_total_nfs_setattr_ops",
            "huawei_write_i_o_latency_distribution_1s_3spercent",
            "huawei_write_i_o_latency_distribution_200ms_1spercent",
            "huawei_write_i_o_latency_distribution_3s_5spercent",
            "huawei_write_i_o_latency_distribution_5s_8spercent",
            "huawei_write_i_o_latency_distribution_8s_infpercent"
        ],
        "Controller NFSV4": [
            "huawei_avg_nfs_access_response_timeus",
            "huawei_avg_nfs_compound_response_timeus",
            "huawei_avg_nfs_create_response_timeus",
            "huawei_avg_nfs_fsstat_response_timeus",
            "huawei_avg_nfs_getattr_response_timeus",
            "huawei_avg_nfs_link_response_timeus",
            "huawei_avg_nfs_lookup_response_timeus",
            "huawei_avg_nfs_mkdir_response_timeus",
            "huawei_avg_nfs_open_response_timeus",
            "huawei_avg_nfs_readdir_plus_response_timeus",
            "huawei_avg_nfs_readdir_response_timeus",
            "huawei_avg_nfs_readlink_response_timeus",
            "huawei_avg_nfs_remove_response_timeus",
            "huawei_avg_nfs_rename_response_timeus",
            "huawei_avg_nfs_rmdir_response_timeus",
            "huawei_avg_nfs_setattr_response_timeus",
            "huawei_avg_nfs_symlink_response_timeus",
            "huawei_avg_nfsv3_getacl_response_timeus",
            "huawei_avg_nfsv3_setacl_response_timeus",
            "huawei_avg_nfsv4_getacl_response_timeus",
            "huawei_avg_nfsv4_setacl_response_timeus",
            "huawei_avg_operation_response_time_us",
            "huawei_max_operation_response_time_us",
            "huawei_min_operation_response_time_us",
            "huawei_nfsv3_getacl_ops",
            "huawei_nfsv3_setacl_ops",
            "huawei_nfsv4_compound_requests",
            "huawei_nfsv4_getacl_ops",
            "huawei_nfsv4_setacl_ops",
            "huawei_read_i_o_latency_distribution_1s_3spercent",
            "huawei_read_i_o_latency_distribution_200ms_1spercent",
            "huawei_read_i_o_latency_distribution_3s_5spercent",
            "huawei_read_i_o_latency_distribution_5s_8spercent",
            "huawei_read_i_o_latency_distribution_8s_infpercent",
            "huawei_total_nfs_access_ops",
            "huawei_total_nfs_create_ops",
            "huawei_total_nfs_fsstat_ops",
            "huawei_total_nfs_getattr_ops",
            "huawei_total_nfs_link_ops",
            "huawei_total_nfs_lookup_ops",
            "huawei_total_nfs_mkdir_ops",
            "huawei_total_nfs_open_ops",
            "huawei_total_nfs_readdir_ops",
            "huawei_total_nfs_readdir_plus_ops",
            "huawei_total_nfs_readlink_ops",
            "huawei_total_nfs_remove_ops",
            "huawei_total_nfs_rename_ops",
            "huawei_total_nfs_rmdir_ops",
            "huawei_total_nfs_setattr_ops",
            "huawei_total_nfs_symlink_ops",
            "huawei_write_i_o_latency_distribution_1s_3spercent",
            "huawei_write_i_o_latency_distribution_200ms_1spercent",
            "huawei_write_i_o_latency_distribution_3s_5spercent",
            "huawei_write_i_o_latency_distribution_5s_8spercent",
            "huawei_write_i_o_latency_distribution_8s_infpercent"
        ],
        "Controller NFSV4.1": [
            "huawei_avg_nfs_access_response_timeus",
            "huawei_avg_nfs_compound_response_timeus",
            "huawei_avg_nfs_create_response_timeus",
            "huawei_avg_nfs_fsstat_response_timeus",
            "huawei_avg_nfs_getattr_response_timeus",
            "huawei_avg_nfs_link_response_timeus",
            "huawei_avg_nfs_lookup_response_timeus",
            "huawei_avg_nfs_mkdir_response_timeus",
            "huawei_avg_nfs_open_response_timeus",
            "huawei_avg_nfs_readdir_plus_response_timeus",
            "huawei_avg_nfs_readdir_response_timeus",
            "huawei_avg_nfs_readlink_response_timeus",
            "huawei_avg_nfs_remove_response_timeus",
            "huawei_avg_nfs_rename_response_timeus",
            "huawei_avg_nfs_rmdir_response_timeus",
            "huawei_avg_nfs_setattr_response_timeus",
            "huawei_avg_nfs_symlink_response_timeus",
            "huawei_avg_nfsv3_getacl_response_timeus",
            "huawei_avg_nfsv3_setacl_response_timeus",
            "huawei_avg_nfsv4_getacl_response_timeus",
            "huawei_avg_nfsv4_setacl_response_timeus",
            "huawei_avg_operation_response_time_us",
            "huawei_max_operation_response_time_us",
            "huawei_min_operation_response_time_us",
            "huawei_nfsv3_getacl_ops",
            "huawei_nfsv3_setacl_ops",
            "huawei_nfsv4_compound_requests",
            "huawei_nfsv4_getacl_ops",
            "huawei_nfsv4_setacl_ops",
            "huawei_read_i_o_latency_distribution_1s_3spercent",
            "huawei_read_i_o_latency_distribution_200ms_1spercent",
            "huawei_read_i_o_latency_distribution_3s_5spercent",
            "huawei_read_i_o_latency_distribution_5s_8spercent",
            "huawei_read_i_o_latency_distribution_8s_infpercent",
            "huawei_total_nfs_access_ops",
            "huawei_total_nfs_create_ops",
            "huawei_total_nfs_fsstat_ops",
            "huawei_total_nfs_getattr_ops",
            "huawei_total_nfs_link_ops",
            "huawei_total_nfs_lookup_ops",
            "huawei_total_nfs_mkdir_ops",
            "huawei_total_nfs_open_ops",
            "huawei_total_nfs_readdir_ops",
            "huawei_total_nfs_readdir_plus_ops",
            "huawei_total_nfs_readlink_ops",
            "huawei_total_nfs_remove_ops",
            "huawei_total_nfs_rename_ops",
            "huawei_total_nfs_rmdir_ops",
            "huawei_total_nfs_setattr_ops",
            "huawei_total_nfs_symlink_ops",
            "huawei_write_i_o_latency_distribution_1s_3spercent",
            "huawei_write_i_o_latency_distribution_200ms_1spercent",
            "huawei_write_i_o_latency_distribution_3s_5spercent",
            "huawei_write_i_o_latency_distribution_5s_8spercent",
            "huawei_write_i_o_latency_distribution_8s_infpercent"
        ],
        "Controller SMB2/3": [
            "huawei_avg_cifs_create_response_timeus",
            "huawei_avg_cifs_getacl_response_timeus",
            "huawei_avg_cifs_querydir_response_timeus",
            "huawei_avg_cifs_queryinfo_response_timeus",
            "huawei_avg_cifs_setacl_response_timeus",
            "huawei_avg_cifs_setinfo_response_timeus",
            "huawei_avg_operation_response_time_us",
            "huawei_avg_response_time_of_cifs_offload_read_i_os_us",
            "huawei_avg_response_time_of_cifs_offload_write_i_os_us",
            "huawei_cifs_getacl_ops",
            "huawei_cifs_offload_read_bandwidth_mb_s",
            "huawei_cifs_offload_read_ops",
            "huawei_cifs_offload_write_bandwidth_mb_s",
            "huawei_cifs_offload_write_ops",
            "huawei_cifs_setacl_ops",
            "huawei_max_operation_response_time_us",
            "huawei_min_operation_response_time_us",
            "huawei_read_i_o_latency_distribution_1s_3spercent",
            "huawei_read_i_o_latency_distribution_200ms_1spercent",
            "huawei_read_i_o_latency_distribution_3s_5spercent",
            "huawei_read_i_o_latency_distribution_5s_8spercent",
            "huawei_read_i_o_latency_distribution_8s_infpercent",
            "huawei_total_cifs_create_ops",
            "huawei_total_cifs_querydir_ops",
            "huawei_total_cifs_queryinfo_ops",
            "huawei_total_cifs_setinfo_ops",
            "huawei_write_i_o_latency_distribution_1s_3spercent",
            "huawei_write_i_o_latency_distribution_200ms_1spercent",
            "huawei_write_i_o_latency_distribution_3s_5spercent",
            "huawei_write_i_o_latency_distribution_5s_8spercent",
            "huawei_write_i_o_latency_distribution_8s_infpercent"
        ],
        "Disk Domain": [
            "huawei_back_end_read_response_time_us",
            "huawei_back_end_write_response_time_us"
        ],
        "FC Port": [
            "huawei_receiving_bandwidth_for_replication_kb_s",
            "huawei_transmitting_bandwidth_for_replication_kb_s"
        ],
        "Snapshot LUN": [
            "huawei_write_requests_less_than_grain_size_to_snapshot_lun"
        ],
        "Storage Pool": [
            "huawei_back_end_read_response_time_us",
            "huawei_back_end_write_response_time_us",
            "huawei_service_timeexcluding_queue_timeus"
        ]
    }
    
    total_missing = sum(len(m) for m in missing_metrics.values())
    print(f"\nВсего недостающих метрик: {total_missing}")
    
    # Добавляем панели
    dashboard, count_added = add_panels_to_dashboard(dashboard, missing_metrics, reverse_mapping)
    
    # Сохраняем результат
    print(f"\n{'=' * 60}")
    print(f"ИТОГО: Добавлено {count_added} панелей")
    print(f"{'=' * 60}")
    
    print(f"\nСохранение дашборда: {DASHBOARD_PATH}")
    with open(DASHBOARD_PATH, 'w') as f:
        json.dump(dashboard, f, indent=2)
    
    print("✅ Готово!")
    
    return count_added


if __name__ == '__main__':
    count = main()
    sys.exit(0 if count > 0 else 1)

