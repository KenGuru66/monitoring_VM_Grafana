#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Детальное сравнение ВСЕХ значений метрик между оригинальным и новым парсером
"""

import sys
from collections import defaultdict
from datetime import datetime

def parse_original_line(line):
    """Парсит строку из оригинального CSV (формат: resource,metric,instance,value,time,unix_time)"""
    parts = line.strip().split(',')
    if len(parts) != 6:
        return None
    
    resource, metric, instance, value, time_str, unix_time = parts
    
    # Конвертируем время в единый формат
    try:
        dt = datetime.strptime(time_str, '%Y/%m/%d %H:%M')
        normalized_time = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    except:
        normalized_time = time_str
    
    # Ключ для сравнения
    key = (resource, metric, instance, normalized_time)
    return key, value

def parse_new_line(line):
    """Парсит строку из нового CSV (формат: resource;metric;instance;value;time;unix_time)"""
    parts = line.strip().split(';')
    if len(parts) != 6:
        return None
    
    resource, metric, instance, value, time_str, unix_time = parts
    
    # Ключ для сравнения (время уже в правильном формате)
    key = (resource, metric, instance, time_str)
    return key, value

def main():
    original_file = 'output_test/original_6000v6/OceanStorDorado6000V6_2102355THQFSQ2100014_20251013000000.csv'
    new_file = 'output_test/parallel_6000v6/2102355THQFSQ2100014.csv'
    
    print("=" * 80)
    print("ДЕТАЛЬНОЕ СРАВНЕНИЕ ВСЕХ ЗНАЧЕНИЙ МЕТРИК")
    print("=" * 80)
    print()
    
    # Загружаем данные из оригинального файла
    print("📖 Загружаем оригинальный файл...")
    original_data = {}
    original_count = 0
    
    with open(original_file, 'r', encoding='utf-8') as f:
        for line in f:
            result = parse_original_line(line)
            if result:
                key, value = result
                original_data[key] = value
                original_count += 1
                if original_count % 500000 == 0:
                    print(f"  Загружено {original_count:,} строк...")
    
    print(f"✅ Загружено {original_count:,} строк из оригинального файла")
    print()
    
    # Загружаем данные из нового файла
    print("📖 Загружаем новый файл...")
    new_data = {}
    new_count = 0
    
    with open(new_file, 'r', encoding='utf-8') as f:
        for line in f:
            result = parse_new_line(line)
            if result:
                key, value = result
                new_data[key] = value
                new_count += 1
                if new_count % 500000 == 0:
                    print(f"  Загружено {new_count:,} строк...")
    
    print(f"✅ Загружено {new_count:,} строк из нового файла")
    print()
    
    # Сравнение
    print("🔍 Сравнение данных...")
    print()
    
    # Статистика
    only_in_original = set(original_data.keys()) - set(new_data.keys())
    only_in_new = set(new_data.keys()) - set(original_data.keys())
    common_keys = set(original_data.keys()) & set(new_data.keys())
    
    print(f"📊 Статистика:")
    print(f"  Только в оригинале:     {len(only_in_original):,}")
    print(f"  Только в новом:         {len(only_in_new):,}")
    print(f"  Общие ключи:            {len(common_keys):,}")
    print()
    
    # Проверка значений для общих ключей
    value_differences = []
    exact_matches = 0
    
    for key in common_keys:
        orig_val = original_data[key]
        new_val = new_data[key]
        
        # Сравнение значений (учитываем что могут быть int vs float)
        try:
            orig_num = float(orig_val)
            new_num = float(new_val)
            if abs(orig_num - new_num) < 0.0001:  # Практически равны
                exact_matches += 1
            else:
                value_differences.append((key, orig_val, new_val))
        except ValueError:
            # Строковое сравнение
            if orig_val == new_val:
                exact_matches += 1
            else:
                value_differences.append((key, orig_val, new_val))
    
    print(f"✅ Точных совпадений значений: {exact_matches:,} ({exact_matches/len(common_keys)*100:.2f}%)")
    print(f"❌ Различий в значениях:       {len(value_differences):,} ({len(value_differences)/len(common_keys)*100:.2f}%)")
    print()
    
    # Показываем примеры различий
    if value_differences:
        print("🔍 Примеры различий в значениях (первые 20):")
        print()
        for i, (key, orig_val, new_val) in enumerate(value_differences[:20]):
            resource, metric, instance, time = key
            print(f"{i+1}. {resource} | {metric}")
            print(f"   Instance: {instance}, Time: {time}")
            print(f"   Оригинал: {orig_val}")
            print(f"   Новый:    {new_val}")
            print()
    
    if only_in_original:
        print(f"⚠️  Строки только в оригинале (первые 10):")
        for i, key in enumerate(list(only_in_original)[:10]):
            resource, metric, instance, time = key
            print(f"  {i+1}. {resource} | {metric} | {instance} | {time} = {original_data[key]}")
        print()
    
    if only_in_new:
        print(f"⚠️  Строки только в новом (первые 10):")
        for i, key in enumerate(list(only_in_new)[:10]):
            resource, metric, instance, time = key
            print(f"  {i+1}. {resource} | {metric} | {instance} | {time} = {new_data[key]}")
        print()
    
    # Итоговый вердикт
    print("=" * 80)
    print("📋 ИТОГОВЫЙ ВЕРДИКТ:")
    print("=" * 80)
    
    if len(value_differences) == 0 and len(only_in_original) == 0 and len(only_in_new) == 0:
        print("✅ ВСЕ ЗНАЧЕНИЯ ИДЕНТИЧНЫ НА 100%!")
        print("   Оба парсера выдают полностью одинаковые результаты.")
    else:
        if len(value_differences) > 0:
            print(f"⚠️  Найдено {len(value_differences):,} различий в значениях")
        if len(only_in_original) > 0:
            print(f"⚠️  {len(only_in_original):,} строк присутствуют только в оригинале")
        if len(only_in_new) > 0:
            print(f"⚠️  {len(only_in_new):,} строк присутствуют только в новом")
    
    print()
    
    # Статистика по ресурсам
    print("📊 Статистика по типам ресурсов:")
    resource_stats_orig = defaultdict(int)
    resource_stats_new = defaultdict(int)
    
    for key in original_data.keys():
        resource_stats_orig[key[0]] += 1
    
    for key in new_data.keys():
        resource_stats_new[key[0]] += 1
    
    all_resources = sorted(set(list(resource_stats_orig.keys()) + list(resource_stats_new.keys())))
    
    for resource in all_resources:
        orig_count = resource_stats_orig.get(resource, 0)
        new_count = resource_stats_new.get(resource, 0)
        match = "✅" if orig_count == new_count else "❌"
        print(f"  {match} {resource:30s}: orig={orig_count:8,} new={new_count:8,}")

if __name__ == "__main__":
    main()

