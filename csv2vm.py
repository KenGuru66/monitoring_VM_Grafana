#!/usr/bin/env python
"""
Импорт TSV/CSV-файла OceanStor в VictoriaMetrics.

Скрипт читает экспортированные данные из Huawei OceanStor и загружает их
в VictoriaMetrics в формате Prometheus. Имя файла используется как значение
лейбла 'array' (например, 2102353TJ****100020.csv → array="2102353TJ****100020").

Формат входных данных (TSV/CSV с разделителями: табуляция, точка с запятой, запятая):
    Controller;KV CPU Usage (%);0A;85;2025-09-22T00:05:00Z;1758488700.0
    
    Колонка 0: тип лейбла (например, "Controller")
    Колонка 1: название метрики (например, "KV CPU Usage (%)")
    Колонка 2: значение лейбла (например, "0A")
    Колонка 3: значение метрики (например, "85")
    Колонка 4: временная метка ISO-8601 (не используется)
    Колонка 5: временная метка Unix timestamp в секундах (используется)

Формат выходных данных (Prometheus exposition format):
    huawei_kv_cpu_usage_percent{array="2102353TJWFSP3100020",controller="0A"} 85 1758488700000
"""

import argparse
import csv
import pathlib
import requests
import sys
from tqdm import tqdm

# URL endpoint для импорта данных в VictoriaMetrics
DEFAULT_URL = "http://localhost:8428/api/v1/import/prometheus"

def detect_delimiter(path: pathlib.Path) -> str:
    """
    Автоматически определяет разделитель CSV файла.
    
    Проверяет первую строку файла на наличие табуляции, точки с запятой
    или запятой и возвращает найденный разделитель.
    
    Args:
        path: Путь к CSV/TSV файлу
        
    Returns:
        Символ разделителя: '\t', ';' или ','
    """
    with open(path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        if '\t' in first_line:
            return '\t'
        elif ';' in first_line:
            return ';'
        return ','

def sanitize_metric_name(name: str) -> str:
    """
    Преобразует строку в валидное имя метрики Prometheus.
    
    Правила Prometheus для имен метрик:
    - только буквы (a-z, A-Z), цифры (0-9) и подчеркивания (_)
    - не может начинаться с цифры
    
    Args:
        name: Исходное имя (например, "KV CPU Usage (%)")
        
    Returns:
        Очищенное имя (например, "kv_cpu_usage_percent")
    """
    return (name.strip().lower()
            .replace(" ", "_")         # пробелы → подчеркивания
            .replace("%", "percent")   # % → percent
            .replace("(", "")          # убираем скобки
            .replace(")", "")
            .replace("-", "_")         # дефисы → подчеркивания
            .replace("/", "_"))        # слэши → подчеркивания

def row_to_prom(row: list, array_sn: str) -> str:
    """
    Преобразует строку CSV в формат Prometheus exposition format.
    
    Входная строка:
        ['Controller', 'KV CPU Usage (%)', '0A', '85', '2025-09-22T00:05:00Z', '1758488700.0']
    
    Выходная строка:
        huawei_kv_cpu_usage_percent{array="2102353TJWFSP3100020",controller="0A"} 85 1758488700000
    
    Args:
        row: Список значений из CSV строки
        array_sn: Серийный номер массива (из имени файла)
        
    Returns:
        Строка в формате Prometheus или None если данных недостаточно
    """
    # Проверяем, что в строке достаточно колонок
    if len(row) < 6:
        return None
    
    # Колонка 0: тип лейбла (controller, disk, pool и т.д.)
    label_key = sanitize_metric_name(row[0])
    
    # Колонка 1: название метрики + префикс huawei_
    metric_name = "huawei_" + sanitize_metric_name(row[1])
    
    # Колонка 2: значение лейбла (например, "0A", "0B")
    controller_value = row[2].strip()
    
    # Колонка 3: значение метрики
    value = row[3].strip()
    
    # Колонка 5: Unix timestamp в секундах → конвертируем в миллисекунды
    # VictoriaMetrics ожидает timestamp в миллисекундах
    ts_unix_sec = float(row[5].strip())
    ts_unix_ms = int(ts_unix_sec * 1000)
    
    # Формируем лейблы (сортируем для детерминированного порядка)
    labels = {
        label_key: controller_value,  # например, controller="0A"
        "array": array_sn             # например, array="2102353TJWFSP3100020"
    }
    
    # Создаем строку лейблов: array="...",controller="..."
    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    
    # Формат Prometheus: metric_name{labels} value timestamp
    return f"{metric_name}{{{label_str}}} {value} {ts_unix_ms}\n"

def main(path: pathlib.Path, url: str, batch: int):
    """
    Главная функция: читает CSV/TSV и загружает данные в VictoriaMetrics.
    
    Процесс:
    1. Определяет разделитель CSV автоматически
    2. Читает все строки и преобразует в формат Prometheus
    3. Загружает данные порциями (batches) в VictoriaMetrics
    4. Показывает прогресс-бар и итоговую статистику
    
    Args:
        path: Путь к CSV/TSV файлу
        url: URL endpoint VictoriaMetrics для импорта
        batch: Количество строк в одном batch-запросе
    """
    # Извлекаем серийный номер массива из имени файла (без расширения)
    # Например: "2102353TJWFSP3100020.csv" → "2102353TJWFSP3100020"
    array_sn = path.stem
    
    # Автоматически определяем разделитель
    delimiter = detect_delimiter(path)
    
    # Читаем файл и преобразуем строки в формат Prometheus
    lines = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=delimiter)
        for idx, row in enumerate(reader):
            # Пропускаем строки с недостаточным количеством колонок
            if len(row) < 6:
                continue
            
            # Проверяем первую строку: если колонка 3 не число, это заголовок
            if idx == 0:
                try:
                    float(row[3])  # пытаемся преобразовать в число
                except (ValueError, IndexError):
                    continue  # это заголовок, пропускаем
            
            # Преобразуем строку в формат Prometheus
            prom_line = row_to_prom(row, array_sn)
            if prom_line:
                lines.append(prom_line)
    
    # Проверяем, что хоть какие-то данные были прочитаны
    if not lines:
        sys.exit("❌ No valid data rows found")
    
    # Загружаем данные порциями (batches) для эффективности
    # Прогресс-бар показывает количество обработанных batches
    for i in tqdm(range(0, len(lines), batch), desc="upload"):
        # Формируем payload: объединяем строки и кодируем в UTF-8
        payload = "".join(lines[i:i + batch]).encode('utf-8')
        
        try:
            # POST запрос к VictoriaMetrics
            r = requests.post(url, data=payload)
            
            # VictoriaMetrics возвращает 200 или 204 при успехе
            if r.status_code not in (200, 204):
                sys.exit(f"❌ batch {i//batch}: HTTP {r.status_code} - {r.text}")
        except requests.RequestException as e:
            sys.exit(f"❌ batch {i//batch}: {e}")
    
    # Успешное завершение
    print(f"✅ imported {len(lines)} rows for array {array_sn}")

if __name__ == "__main__":
    # Настройка аргументов командной строки
    p = argparse.ArgumentParser(
        description="Import OceanStor CSV/TSV to VictoriaMetrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s data.csv
  %(prog)s 2102353TJWFSP3100020.csv --url http://victoriametrics:8428/api/v1/import/prometheus
  %(prog)s data.tsv --batch 5000

Формат входного файла (TSV/CSV):
  Controller;KV CPU Usage (%%);0A;85;2025-09-22T00:05:00Z;1758488700.0
  
Поддерживаемые разделители: табуляция, точка с запятой, запятая
        """)
    
    p.add_argument("file", type=pathlib.Path, 
                   help="CSV/TSV file to import")
    p.add_argument("--url", default=DEFAULT_URL, 
                   help=f"VictoriaMetrics import endpoint (default: {DEFAULT_URL})")
    p.add_argument("--batch", type=int, default=10000, 
                   help="lines per batch request (default: 10000)")
    
    args = p.parse_args()
    
    # Проверяем существование файла
    if not args.file.exists():
        sys.exit(f"❌ File not found: {args.file}")
    
    # Запускаем импорт
    main(args.file, args.url, args.batch)