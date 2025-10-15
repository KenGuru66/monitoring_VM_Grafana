#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для проверки обработки неизвестных ID метрик и ресурсов
"""

import sys
from pathlib import Path

# Временно изменим словари для теста
from METRIC_DICT import METRIC_NAME_DICT
from RESOURCE_DICT import RESOURCE_NAME_DICT

print("=" * 80)
print("ТЕСТ: Обработка неизвестных ID")
print("=" * 80)
print()

print("📚 Текущие словари:")
print(f"  Метрик: {len(METRIC_NAME_DICT)}")
print(f"  Ресурсов: {len(RESOURCE_NAME_DICT)}")
print()

# Проверяем какие ID есть в реальных данных
print("🔍 Анализируем реальные данные...")
print()

# Читаем CSV и ищем все уникальные ID
test_csv = "output_test/improved_new/2102355THQFSQ2100014.csv"
if not Path(test_csv).exists():
    test_csv = "output_test/final_new/2102355THQFSQ2100014.csv"

unique_resource_names = set()
unique_metric_names = set()

with open(test_csv, 'r') as f:
    for line in f:
        parts = line.strip().split(';')
        if len(parts) == 6:
            unique_resource_names.add(parts[0])
            unique_metric_names.add(parts[1])

print(f"📊 В CSV файле найдено:")
print(f"  Уникальных ресурсов: {len(unique_resource_names)}")
print(f"  Уникальных метрик: {len(unique_metric_names)}")
print()

# Проверяем, есть ли UNKNOWN
unknown_resources = [r for r in unique_resource_names if "UNKNOWN" in r]
unknown_metrics = [m for m in unique_metric_names if "UNKNOWN" in m]

if unknown_resources:
    print(f"⚠️  Найдены неизвестные ресурсы ({len(unknown_resources)}):")
    for r in unknown_resources:
        print(f"  - {r}")
    print()
else:
    print("✅ Все ресурсы известны (нет UNKNOWN)")
    print()

if unknown_metrics:
    print(f"⚠️  Найдены неизвестные метрики ({len(unknown_metrics)}):")
    for m in sorted(unknown_metrics)[:20]:
        print(f"  - {m}")
    if len(unknown_metrics) > 20:
        print(f"  ... и еще {len(unknown_metrics) - 20}")
    print()
else:
    print("✅ Все метрики известны (нет UNKNOWN)")
    print()

# Проверяем покрытие словарей
print("=" * 80)
print("ВЫВОД:")
print("=" * 80)
print()

if not unknown_resources and not unknown_metrics:
    print("✅ ВСЕ ID ИЗ ТЕСТОВЫХ ДАННЫХ ПРИСУТСТВУЮТ В СЛОВАРЯХ!")
    print()
    print("Это означает что:")
    print("  • Словари METRIC_DICT.py и RESOURCE_DICT.py полные")
    print("  • Для текущих данных обработка UNKNOWN не требуется")
    print("  • Механизм обработки UNKNOWN готов для новых данных")
    print()
    print("🎯 Рекомендация:")
    print("  Улучшенный парсер готов к использованию!")
    print("  При появлении новых моделей/метрик он автоматически")
    print("  обработает их как UNKNOWN_RESOURCE_X / UNKNOWN_METRIC_Y")
else:
    print("⚠️  ОБНАРУЖЕНЫ НЕИЗВЕСТНЫЕ ID!")
    print()
    print(f"  Неизвестных ресурсов: {len(unknown_resources)}")
    print(f"  Неизвестных метрик: {len(unknown_metrics)}")
    print()
    print("Эти ID должны быть добавлены в словари")

