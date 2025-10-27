#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для анализа всех ресурсов в архиве.
Показывает, какие Resource IDs реально присутствуют в данных.
"""

import struct
import json
import sys
import zipfile
import tarfile
import tempfile
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'Data2csv'))
from Data2csv.RESOURCE_DICT import RESOURCE_NAME_DICT


def analyze_dat_file(file_path: Path):
    """Анализирует .dat файл и возвращает список найденных Resource IDs."""
    resources_found = set()
    
    try:
        with open(file_path, 'rb') as f:
            # Читаем заголовок файла
            bit_correct = f.read(32)
            bit_msg_version = struct.unpack('<I', f.read(4))[0]
            bit_equip_sn = f.read(256).decode('utf-8', errors='ignore').strip('\x00')
            bit_equip_name = f.read(41).decode('utf-8', errors='ignore').strip('\x00')
            bit_equip_data_length = struct.unpack('<I', f.read(4))[0]
            
            # Читаем временные блоки
            while f.tell() < len(bit_correct) + 4 + 256 + 41 + 4 + bit_equip_data_length:
                try:
                    bit_map_type = struct.unpack('<I', f.read(4))[0]
                    bit_map_length = struct.unpack('<I', f.read(4))[0]
                    bit_map_value = f.read(bit_map_length).decode('utf-8', errors='ignore')
                    
                    # Парсим JSON карту
                    try:
                        map_data = json.loads(bit_map_value)
                    except json.JSONDecodeError:
                        continue
                    
                    # Собираем все Resource IDs из Map
                    resource_map = map_data.get('Map', {})
                    for resource_id in resource_map.keys():
                        resources_found.add(resource_id)
                    
                    # Пропускаем бинарные данные (не читаем их)
                    # Вычисляем размер данных
                    time_diff = int(map_data.get('EndTime', 0)) - int(map_data.get('StartTime', 0))
                    archive_interval = int(map_data.get('Archive', 60))
                    num_points = max(1, time_diff // archive_interval)
                    
                    for resource_id, resource_data in resource_map.items():
                        num_elements = len(resource_data.get('IDs', []))
                        num_metrics = len(resource_data.get('DataTypes', []))
                        data_size = num_points * num_elements * num_metrics * 4
                        f.read(data_size)
                    
                except struct.error:
                    break
                except Exception as e:
                    break
            
            return bit_equip_sn, resources_found
            
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
        return None, set()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_archive_resources.py <path_to_zip_archive>")
        sys.exit(1)
    
    archive_path = Path(sys.argv[1])
    if not archive_path.exists():
        print(f"❌ Файл не найден: {archive_path}")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print(f"🔍 АНАЛИЗ АРХИВА: {archive_path.name}")
    print(f"{'='*80}\n")
    
    # Статистика по ресурсам
    all_resources = defaultdict(int)
    serial_numbers = set()
    files_checked = 0
    
    # Создаем временную директорию
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Извлекаем ZIP
        print(f"📦 Извлечение ZIP архива...")
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(temp_path)
        
        # Находим все .tgz файлы
        tgz_files = list(temp_path.rglob("*.tgz"))
        print(f"✅ Найдено {len(tgz_files)} .tgz файлов\n")
        
        # Анализируем первые 20 файлов для статистики
        sample_size = min(20, len(tgz_files))
        print(f"📊 Анализ первых {sample_size} файлов...\n")
        
        for tgz_file in tgz_files[:sample_size]:
            try:
                # Извлекаем .dat из .tgz
                with tarfile.open(tgz_file, 'r:gz') as tar:
                    members = tar.getmembers()
                    if members:
                        tar.extract(members[0], temp_path / "extracted")
                        dat_file = temp_path / "extracted" / members[0].name
                        
                        # Анализируем
                        sn, resources = analyze_dat_file(dat_file)
                        if sn:
                            serial_numbers.add(sn)
                        
                        for resource_id in resources:
                            all_resources[resource_id] += 1
                        
                        files_checked += 1
                        
                        # Cleanup
                        dat_file.unlink()
                        
            except Exception as e:
                print(f"⚠️ Ошибка при обработке {tgz_file.name}: {e}")
                continue
    
    # Выводим результаты
    print(f"\n{'='*80}")
    print(f"📊 РЕЗУЛЬТАТЫ АНАЛИЗА")
    print(f"{'='*80}\n")
    
    print(f"📁 Файлов проанализировано: {files_checked}")
    print(f"📌 Серийные номера: {', '.join(serial_numbers)}\n")
    
    print(f"🔍 НАЙДЕННЫЕ РЕСУРСЫ В ДАННЫХ:")
    print(f"{'─'*80}")
    print(f"{'Resource ID':<15} {'Название':<40} {'Встречается в файлах':<25}")
    print(f"{'─'*80}")
    
    for resource_id in sorted(all_resources.keys(), key=lambda x: int(x) if x.isdigit() else 999999):
        resource_name = RESOURCE_NAME_DICT.get(resource_id, f"UNKNOWN_RESOURCE_{resource_id}")
        count = all_resources[resource_id]
        percentage = (count / files_checked * 100) if files_checked > 0 else 0
        
        status = "✅" if not resource_name.startswith("UNKNOWN") else "❌"
        print(f"{status} {resource_id:<13} {resource_name:<40} {count}/{files_checked} ({percentage:.0f}%)")
    
    print(f"{'─'*80}")
    print(f"\nВсего уникальных ресурсов: {len(all_resources)}")
    
    # Проверяем NFSv3 специально
    print(f"\n{'='*80}")
    print(f"🔍 ПРОВЕРКА NFSv3 РЕСУРСА")
    print(f"{'='*80}")
    
    nfsv3_id = "1000"
    if nfsv3_id in all_resources:
        print(f"✅ NFSv3 ресурс (ID: {nfsv3_id}) НАЙДЕН!")
        print(f"   Встречается в {all_resources[nfsv3_id]}/{files_checked} файлах")
    else:
        print(f"❌ NFSv3 ресурс (ID: {nfsv3_id}) НЕ НАЙДЕН в архиве!")
        print(f"\n💡 Возможные причины:")
        print(f"   1. NFSv3 не был настроен на этом массиве")
        print(f"   2. NFSv3 метрики не собирались в период сбора логов")
        print(f"   3. Неправильный Resource ID (может быть другой ID)")
        print(f"\n🔍 Проверьте другие Controller ресурсы:")
        for rid in sorted(all_resources.keys()):
            rname = RESOURCE_NAME_DICT.get(rid, "")
            if "Controller" in rname or "NFS" in rname.upper():
                print(f"   • ID {rid}: {rname}")
    
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()

