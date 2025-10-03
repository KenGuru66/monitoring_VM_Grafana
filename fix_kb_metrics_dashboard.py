#!/usr/bin/env python3
"""
Скрипт для исправления метрик с KB в дашборде Grafana.

Проблема: Метрики называются *_kb (килобайты), но значения в байтах.
Решение: Добавить деление на 1024 для всех метрик с _kb в названии.
"""

import json
import re
import sys
from pathlib import Path

def fix_kb_metrics(dashboard_path):
    """Исправляет метрики KB в dashboard Grafana."""
    
    print(f"📖 Читаем dashboard: {dashboard_path}")
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        dashboard = json.load(f)
    
    metrics_fixed = 0
    metrics_with_kb = set()
    
    def fix_expr(expr):
        """Исправляет expression, добавляя деление на 1024 для метрик SIZE в KB.
        
        НЕ трогает метрики bandwidth_kb_s (это уже KB/s, не нужно делить).
        """
        nonlocal metrics_fixed
        
        # Паттерн для поиска метрик с _size_kb в названии
        # Примеры: huawei_avg_i_o_size_kb{...}, huawei_avg_read_i_o_size_kb{...}
        # ВАЖНО: НЕ захватываем метрики с _kb_s (это bandwidth в KB/s)
        # Используем negative lookahead (?!_s) чтобы исключить _kb_s
        pattern = r'(huawei_[a-z_]*size_kb)(?!_s)(\{[^}]*\})?'
        
        matches = re.findall(pattern, expr)
        if matches:
            for metric, labels in matches:
                metrics_with_kb.add(metric)
            
            # Проверяем, не обернуто ли уже в деление
            if '/1024' not in expr and '/ 1024' not in expr:
                # Оборачиваем метрику С лейблами в скобки и делим на 1024
                # Правильный синтаксис: (metric{labels})/1024
                fixed_expr = re.sub(pattern, r'(\1\2)/1024', expr)
                if fixed_expr != expr:
                    metrics_fixed += 1
                    print(f"   ✅ Исправлено: {metric}")
                    return fixed_expr
        
        return expr
    
    def process_panel(panel):
        """Рекурсивно обрабатывает панели dashboard."""
        nonlocal metrics_fixed
        
        # Обработка вложенных панелей (collapsed rows)
        if 'panels' in panel:
            for sub_panel in panel['panels']:
                process_panel(sub_panel)
        
        # Обработка targets (queries)
        if 'targets' in panel:
            for target in panel['targets']:
                if 'expr' in target:
                    original_expr = target['expr']
                    fixed_expr = fix_expr(original_expr)
                    
                    if fixed_expr != original_expr:
                        target['expr'] = fixed_expr
    
    # Обработка всех панелей
    if 'panels' in dashboard:
        for panel in dashboard['panels']:
            process_panel(panel)
    
    print(f"\n📊 Статистика:")
    print(f"   Найдено уникальных метрик с KB: {len(metrics_with_kb)}")
    print(f"   Исправлено выражений: {metrics_fixed}")
    
    if metrics_with_kb:
        print(f"\n🔍 Метрики, которые были исправлены:")
        for metric in sorted(metrics_with_kb):
            print(f"   - {metric}")
    
    if metrics_fixed > 0:
        # Создаем backup
        backup_path = dashboard_path.with_suffix('.json.backup')
        print(f"\n💾 Создаем backup: {backup_path}")
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(json.load(open(dashboard_path, 'r', encoding='utf-8')), f, indent=2)
        
        # Сохраняем исправленный dashboard
        print(f"💾 Сохраняем исправленный dashboard: {dashboard_path}")
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard, f, indent=2)
        
        print(f"\n✅ Dashboard исправлен!")
        print(f"   Все метрики с _kb теперь делятся на 1024")
        print(f"   Backup сохранен: {backup_path}")
    else:
        print(f"\n⚠️  Метрики с KB не найдены или уже исправлены")
    
    return metrics_fixed

def main():
    dashboard_path = Path(__file__).parent / "grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json"
    
    if not dashboard_path.exists():
        print(f"❌ Dashboard не найден: {dashboard_path}")
        sys.exit(1)
    
    print("="*80)
    print("  FIX KB METRICS IN GRAFANA DASHBOARD")
    print("="*80)
    print()
    
    metrics_fixed = fix_kb_metrics(dashboard_path)
    
    print()
    print("="*80)
    print()
    
    if metrics_fixed > 0:
        print("🔄 Следующие шаги:")
        print("   1. Перезагрузить Grafana: docker-compose restart grafana")
        print("   2. Обновить дашборд в браузере (Ctrl+R)")
        print("   3. Проверить графики Avg. I/O size")
        print()
        print("❓ Если нужно вернуть старую версию:")
        print(f"   mv {dashboard_path}.backup {dashboard_path}")

if __name__ == "__main__":
    main()

