#!/usr/bin/env python3
"""
Скрипт для исправления названий метрик в Grafana dashboard.

Проблема: После изменения sanitize_metric_name() некоторые метрики
изменили формат названия (убрано подчеркивание перед единицами измерения).

Примеры:
- Avg. I/O size(KB) → huawei_avg_i_o_sizekb (не _size_kb)
- Average DataTurbo I/O response time(us) → huawei_average_dataturbo_i_o_response_timeus
"""

import json
import sys
from pathlib import Path

# Файл dashboard
DASHBOARD_FILE = Path("grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json")
BACKUP_FILE = Path("grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json.backup")

# Маппинг неправильных названий → правильные
METRIC_FIXES = {
    # I/O Size метрики (убираем подчеркивание перед kb)
    "huawei_avg_i_o_size_kb": "huawei_avg_i_o_sizekb",
    "huawei_avg_read_i_o_size_kb": "huawei_avg_read_i_o_sizekb",
    "huawei_avg_write_i_o_size_kb": "huawei_avg_write_i_o_sizekb",
    
    # DataTurbo метрики уже правильные (без подчеркивания перед us):
    # huawei_average_dataturbo_i_o_response_timeus ✅
    # huawei_average_dataturbo_read_i_o_response_timeus ✅
    # huawei_average_dataturbo_write_i_o_response_timeus ✅
    # huawei_average_response_time_of_other_dataturbo_i_osus ✅
    # huawei_dataturbo_read_bandwidth_kb_s ✅
    # huawei_dataturbo_write_bandwidth_kb_s ✅
    # huawei_other_dataturbo_ops ✅
    # huawei_total_dataturbo_bandwidth_kb_s ✅
    # huawei_total_dataturbo_ops ✅
    # huawei_total_dataturbo_read_ops ✅
    # huawei_total_dataturbo_write_ops ✅
}

def main():
    print("=" * 80)
    print("🔧 ИСПРАВЛЕНИЕ НАЗВАНИЙ МЕТРИК В GRAFANA DASHBOARD")
    print("=" * 80)
    print(f"📁 Файл: {DASHBOARD_FILE}")
    print()
    
    # Проверяем существование файла
    if not DASHBOARD_FILE.exists():
        print(f"❌ Файл не найден: {DASHBOARD_FILE}")
        sys.exit(1)
    
    # Создаем backup
    print("💾 Создание backup...")
    with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Backup сохранен: {BACKUP_FILE}")
    print()
    
    # Выполняем замены
    print("🔄 Выполнение замен:")
    total_replacements = 0
    
    for old_metric, new_metric in METRIC_FIXES.items():
        count = content.count(old_metric)
        if count > 0:
            content = content.replace(old_metric, new_metric)
            print(f"   ✅ {old_metric} → {new_metric}: {count} замен")
            total_replacements += count
        else:
            print(f"   ⚠️  {old_metric}: не найдено (возможно уже исправлено)")
    
    print()
    print(f"📊 Всего выполнено замен: {total_replacements}")
    
    # Проверяем валидность JSON
    print()
    print("🔍 Проверка валидности JSON...")
    try:
        json_data = json.loads(content)
        print("✅ JSON валиден")
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка JSON: {e}")
        print("⚠️  Откат изменений...")
        with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        sys.exit(1)
    
    # Сохраняем исправленный файл
    print()
    print("💾 Сохранение исправленного файла...")
    with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Файл успешно обновлен")
    print()
    print("=" * 80)
    print("✅ ЗАВЕРШЕНО УСПЕШНО")
    print("=" * 80)
    print()
    print("📝 Следующие шаги:")
    print("   1. Перезагрузить Grafana: docker compose restart grafana")
    print("   2. Проверить dashboard в браузере")
    print("   3. Если все ОК, удалить backup: rm", BACKUP_FILE)
    print()

if __name__ == "__main__":
    main()

