#!/usr/bin/env python
"""
Импорт TSV/CSV-файла OceanStor в VictoriaMetrics.

Скрипт читает экспортированные данные из Huawei OceanStor и загружает их
в VictoriaMetrics в формате Prometheus для дашборда HU Perf.

Формат входных данных (TSV/CSV с разделителями: табуляция, точка с запятой, запятая):
    Controller;KV CPU Usage (%);0A;85;2025-09-22T00:05:00Z;1758488700.0
    
    Колонка 0: Resource - тип ресурса (Controller, Disk, Pool, и т.д.)
    Колонка 1: Metric - название метрики (KV CPU Usage (%), Max Bandwidth (Mbps), и т.д.)
    Колонка 2: Element - идентификатор объекта (0A, 0B, disk01, и т.д.)
    Колонка 3: Value - значение метрики (85)
    Колонка 4: ISO timestamp - временная метка ISO-8601 (не используется)
    Колонка 5: Unix timestamp - временная метка в секундах (используется)

Формат выходных данных (Prometheus exposition format для HU Perf):
    hu_kv_cpu_usage_pct_variable{SN="2102353TJWF****00020",Resource="Controller",Element="0A"} 85 1758488700000
    
Структура лейблов совместима с дашбордом HU Perf:
    - SN: серийный номер массива (из имени файла)
    - Resource: тип ресурса (из колонки 0)
    - Element: идентификатор элемента (из колонки 2)
    - Name, Archive, CtrlID: опциональные, можно фильтровать в Grafana
"""

import argparse
import csv
import pathlib
import requests
import sys
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv2vm_import.log', mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Пытаемся импортировать tqdm, если нет - используем заглушку
try:
    from tqdm import tqdm
except ImportError:
    # Простая заглушка для tqdm если модуль не установлен
    def tqdm(iterable, desc=None):
        return iterable

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
        Очищенное имя (например, "kv_cpu_usage_pct")
    """
    result = name.strip().lower()
    # Сначала заменяем специальные паттерны
    result = result.replace(" (%)", "_pct")      # " (%)" → "_pct"
    result = result.replace("(%)", "_pct")       # "(%)" → "_pct"
    result = result.replace(" (mbps)", "_mbps")  # " (Mbps)" → "_mbps"
    result = result.replace(" (iops)", "_iops")  # " (IOPS)" → "_iops"
    # Убираем оставшиеся скобки
    result = result.replace("(", "").replace(")", "")
    # Заменяем разделители на подчеркивания
    result = result.replace(" ", "_")            # пробелы → подчеркивания
    result = result.replace("-", "_")            # дефисы → подчеркивания
    result = result.replace("/", "_")            # слэши → подчеркивания
    result = result.replace("%", "percent")      # оставшиеся % → percent
    return result

def row_to_prom(row: list, array_sn: str) -> str:
    """
    Преобразует строку CSV в формат Prometheus для дашборда HU Perf.
    
    Входная строка:
        ['Controller', 'KV CPU Usage (%)', '0A', '85', '2025-09-22T00:05:00Z', '1758488700.0']
    
    Выходная строка:
        hu_kv_cpu_usage_pct_variable{SN="2102353TJWF****00020",Resource="Controller",Element="0A"} 85 1758488700000
    
    Args:
        row: Список значений из CSV строки
        array_sn: Серийный номер массива (из имени файла)
        
    Returns:
        Строка в формате Prometheus или None если данных недостаточно
    """
    # Проверяем, что в строке достаточно колонок
    if len(row) < 6:
        return None
    
    # Колонка 0: Resource (Controller, Disk, Pool и т.д.)
    resource = row[0].strip()
    
    # Колонка 1: название метрики
    # Формат: hu_{metric}_variable
    metric_name = "hu_" + sanitize_metric_name(row[1]) + "_variable"
    
    # Колонка 2: Element - идентификатор объекта (0A, 0B, disk01 и т.д.)
    element = row[2].strip()
    
    # Колонка 3: значение метрики
    value = row[3].strip()
    
    # Колонка 5: Unix timestamp в секундах → конвертируем в миллисекунды
    # VictoriaMetrics ожидает timestamp в миллисекундах
    ts_unix_sec = float(row[5].strip())
    ts_unix_ms = int(ts_unix_sec * 1000)
    
    # Формируем лейблы в формате HU Perf (сортируем для детерминированного порядка)
    # Обязательные лейблы: SN, Resource, Element
    # Опциональные (для совместимости с дашбордом): Name, Archive, CtrlID
    labels = {
        "Element": element,      # например, Element="0A"
        "Resource": resource,    # например, Resource="Controller"
        "SN": array_sn          # например, SN="2102353TJWF****00020"
    }
    
    # Создаем строку лейблов: Element="...",Resource="...",SN="..."
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
    logger.info(f"🚀 Starting import from: {path}")
    logger.info(f"📍 VictoriaMetrics URL: {url}")
    logger.info(f"📦 Batch size: {batch} lines")
    
    # Извлекаем серийный номер массива из имени файла (без расширения)
    # Например: "2102353TJWF****00020.csv" → "2102353TJWF****00020"
    array_sn = path.stem
    logger.info(f"🔢 Array SN: {array_sn}")
    
    # Автоматически определяем разделитель
    delimiter = detect_delimiter(path)
    logger.info(f"📋 Detected delimiter: {'TAB' if delimiter == chr(9) else repr(delimiter)}")
    
    # Читаем файл и преобразуем строки в формат Prometheus
    logger.info(f"📖 Reading CSV file...")
    lines = []
    skipped_rows = 0
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=delimiter)
        for idx, row in enumerate(reader):
            # Логируем прогресс каждые 1 млн строк
            if idx > 0 and idx % 1000000 == 0:
                logger.info(f"   Processed {idx:,} rows, converted {len(lines):,} lines...")
            
            # Пропускаем строки с недостаточным количеством колонок
            if len(row) < 6:
                skipped_rows += 1
                continue
            
            # Проверяем первую строку: если колонка 3 не число, это заголовок
            if idx == 0:
                try:
                    float(row[3])  # пытаемся преобразовать в число
                except (ValueError, IndexError):
                    logger.info(f"   Skipping header row")
                    skipped_rows += 1
                    continue  # это заголовок, пропускаем
            
            # Преобразуем строку в формат Prometheus
            prom_line = row_to_prom(row, array_sn)
            if prom_line:
                lines.append(prom_line)
    
    logger.info(f"✅ Read complete: {len(lines):,} valid lines, {skipped_rows:,} skipped")
    
    # Проверяем, что хоть какие-то данные были прочитаны
    if not lines:
        logger.error("❌ No valid data rows found")
        sys.exit("❌ No valid data rows found")
    
    # Загружаем данные порциями (batches) для эффективности
    # Прогресс-бар показывает количество обработанных batches
    total_batches = (len(lines) + batch - 1) // batch
    logger.info(f"🚀 Starting upload to VictoriaMetrics: {total_batches} batches")
    
    uploaded_lines = 0
    for i in tqdm(range(0, len(lines), batch), desc="upload"):
        batch_num = i // batch + 1
        current_batch_size = min(batch, len(lines) - i)
        
        # Формируем payload: объединяем строки и кодируем в UTF-8
        payload = "".join(lines[i:i + batch]).encode('utf-8')
        
        try:
            # POST запрос к VictoriaMetrics
            r = requests.post(url, data=payload, timeout=60)
            
            # VictoriaMetrics возвращает 200 или 204 при успехе
            if r.status_code not in (200, 204):
                logger.error(f"❌ Batch {batch_num}/{total_batches}: HTTP {r.status_code} - {r.text}")
                sys.exit(f"❌ batch {batch_num}: HTTP {r.status_code} - {r.text}")
            
            uploaded_lines += current_batch_size
            # Логируем каждые 10 батчей
            if batch_num % 10 == 0:
                logger.info(f"   Progress: {batch_num}/{total_batches} batches, {uploaded_lines:,}/{len(lines):,} lines ({100*uploaded_lines//len(lines)}%)")
                
        except requests.RequestException as e:
            logger.error(f"❌ Batch {batch_num}/{total_batches}: {e}")
            sys.exit(f"❌ batch {batch_num}: {e}")
    
    # Успешное завершение
    logger.info(f"✅ Import completed successfully!")
    logger.info(f"📊 Total imported: {len(lines):,} rows for SN={array_sn}")
    print(f"✅ imported {len(lines)} rows for SN={array_sn}")

if __name__ == "__main__":
    # Настройка аргументов командной строки
    p = argparse.ArgumentParser(
        description="Import OceanStor CSV/TSV to VictoriaMetrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s 2102353TJWFSP3100020.csv
  %(prog)s 2102353TJWFSP3100020.csv --url http://victoriametrics:8428/api/v1/import/prometheus
  %(prog)s data.tsv --batch 5000

Формат входного файла (TSV/CSV):
  Controller;KV CPU Usage (%%);0A;85;2025-09-22T00:05:00Z;1758488700.0
  
  Колонки: Resource;Metric;Element;Value;ISO_timestamp;Unix_timestamp
  
Поддерживаемые разделители: табуляция, точка с запятой, запятая

Результирующий формат метрик для HU Perf дашборда:
  hu_kv_cpu_usage_pct_variable{SN="2102353TJWFSP3100020",Resource="Controller",Element="0A"} 85 1758488700000
        """)
    
    p.add_argument("file", type=pathlib.Path, 
                   help="CSV/TSV file to import")
    p.add_argument("--url", default=DEFAULT_URL, 
                   help=f"VictoriaMetrics import endpoint (default: {DEFAULT_URL})")
    p.add_argument("--batch", type=int, default=10000, 
                   help="lines per batch request (default: 10000)")
    
    args = p.parse_args()
    
    # Логируем начало работы скрипта
    logger.info("="*80)
    logger.info(f"CSV2VM Import Script Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    # Проверяем существование файла
    if not args.file.exists():
        logger.error(f"❌ File not found: {args.file}")
        sys.exit(f"❌ File not found: {args.file}")
    
    # Запускаем импорт
    try:
        main(args.file, args.url, args.batch)
        logger.info("="*80)
        logger.info(f"Script completed successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise