#!/usr/bin/env python3
"""
ОПТИМИЗИРОВАННАЯ версия импорта CSV в VictoriaMetrics с потоковой обработкой.

Основные улучшения:
- Потоковое чтение: читает и отправляет данные порциями, не загружая весь файл в память
- Меньше использование RAM: ~10-50 MB вместо 2-3 GB
- Быстрее старт: начинает отправку данных сразу после чтения первого батча
- Прогресс в реальном времени: показывает скорость обработки строк/сек
"""

import argparse
import csv
import pathlib
import requests
import sys
import logging
import time
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv2vm_streaming.log', mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# URL endpoint для импорта данных в VictoriaMetrics
DEFAULT_URL = "http://localhost:8428/api/v1/import/prometheus"

def detect_delimiter(path: pathlib.Path) -> str:
    """Автоматически определяет разделитель CSV файла."""
    with open(path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        if '\t' in first_line:
            return '\t'
        elif ';' in first_line:
            return ';'
        return ','

def sanitize_metric_name(name: str) -> str:
    """Преобразует строку в валидное имя метрики Prometheus."""
    result = name.strip().lower()
    result = result.replace(" (%)", "_pct")
    result = result.replace("(%)", "_pct")
    result = result.replace(" (mbps)", "_mbps")
    result = result.replace(" (iops)", "_iops")
    result = result.replace("(", "").replace(")", "")
    result = result.replace(" ", "_")
    result = result.replace("-", "_")
    result = result.replace("/", "_")
    result = result.replace("%", "percent")
    result = result.replace(".", "")
    result = result.replace(",", "")
    result = result.replace(":", "")
    result = result.replace("[", "").replace("]", "")
    result = result.replace("+", "plus")
    result = result.replace("∞", "inf")
    return result

def row_to_prom(row: list, array_sn: str) -> str:
    """Преобразует строку CSV в формат Prometheus."""
    if len(row) < 6:
        return None
    
    try:
        resource = row[0].strip()
        metric_name = "hu_" + sanitize_metric_name(row[1]) + "_variable"
        element = row[2].strip()
        value = row[3].strip()
        ts_unix_sec = float(row[5].strip())
        ts_unix_ms = int(ts_unix_sec * 1000)
        
        labels = {
            "Element": element,
            "Resource": resource,
            "SN": array_sn
        }
        
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{metric_name}{{{label_str}}} {value} {ts_unix_ms}\n"
    except (ValueError, IndexError) as e:
        logger.debug(f"Error processing row: {e}")
        return None

def send_batch(url: str, batch_lines: list, batch_num: int) -> bool:
    """Отправляет батч данных в VictoriaMetrics."""
    if not batch_lines:
        return True
    
    payload = "".join(batch_lines).encode('utf-8')
    
    try:
        r = requests.post(url, data=payload, timeout=60)
        if r.status_code not in (200, 204):
            logger.error(f"Batch {batch_num}: HTTP {r.status_code} - {r.text[:200]}")
            return False
        return True
    except requests.RequestException as e:
        logger.error(f"Batch {batch_num}: {e}")
        return False

def main_streaming(path: pathlib.Path, url: str, batch: int):
    """
    Главная функция с потоковой обработкой.
    
    Читает CSV порциями и сразу отправляет в VictoriaMetrics,
    не загружая весь файл в память.
    """
    logger.info("="*80)
    logger.info(f"CSV2VM Streaming Import Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    logger.info(f"🚀 Starting STREAMING import from: {path}")
    logger.info(f"📍 VictoriaMetrics URL: {url}")
    logger.info(f"📦 Batch size: {batch:,} lines")
    
    array_sn = path.stem
    logger.info(f"🔢 Array SN: {array_sn}")
    
    delimiter = detect_delimiter(path)
    logger.info(f"📋 Detected delimiter: {'TAB' if delimiter == chr(9) else repr(delimiter)}")
    
    # Потоковая обработка
    logger.info(f"📖 Starting streaming processing...")
    
    batch_lines = []
    batch_num = 0
    total_rows_processed = 0
    total_lines_converted = 0
    skipped_rows = 0
    start_time = time.time()
    last_log_time = start_time
    
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=delimiter)
        
        for idx, row in enumerate(reader):
            # Пропускаем строки с недостаточным количеством колонок
            if len(row) < 6:
                skipped_rows += 1
                continue
            
            # Проверяем заголовок
            if idx == 0:
                try:
                    float(row[3])
                except (ValueError, IndexError):
                    logger.info(f"   Skipping header row")
                    skipped_rows += 1
                    continue
            
            # Преобразуем строку
            prom_line = row_to_prom(row, array_sn)
            if prom_line:
                batch_lines.append(prom_line)
                total_lines_converted += 1
            
            total_rows_processed += 1
            
            # Когда накопили батч - отправляем
            if len(batch_lines) >= batch:
                batch_num += 1
                success = send_batch(url, batch_lines, batch_num)
                
                if not success:
                    logger.error(f"Failed to send batch {batch_num}, aborting")
                    sys.exit(1)
                
                # Логируем прогресс каждые 10 батчей или каждые 30 секунд
                current_time = time.time()
                if batch_num % 10 == 0 or (current_time - last_log_time) >= 30:
                    elapsed = current_time - start_time
                    rate = total_rows_processed / elapsed if elapsed > 0 else 0
                    logger.info(
                        f"   📊 Batch {batch_num}: {total_rows_processed:,} rows processed, "
                        f"{total_lines_converted:,} lines sent, "
                        f"Rate: {rate:,.0f} rows/sec"
                    )
                    last_log_time = current_time
                
                # Очищаем батч
                batch_lines = []
    
    # Отправляем остаток
    if batch_lines:
        batch_num += 1
        logger.info(f"   Sending final batch {batch_num} with {len(batch_lines):,} lines...")
        success = send_batch(url, batch_lines, batch_num)
        if not success:
            logger.error(f"Failed to send final batch")
            sys.exit(1)
    
    # Итоговая статистика
    total_time = time.time() - start_time
    avg_rate = total_rows_processed / total_time if total_time > 0 else 0
    
    logger.info("="*80)
    logger.info(f"✅ Import completed successfully!")
    logger.info(f"📊 Statistics:")
    logger.info(f"   - Total rows processed: {total_rows_processed:,}")
    logger.info(f"   - Lines converted: {total_lines_converted:,}")
    logger.info(f"   - Rows skipped: {skipped_rows:,}")
    logger.info(f"   - Batches sent: {batch_num}")
    logger.info(f"   - Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    logger.info(f"   - Average rate: {avg_rate:,.0f} rows/sec")
    logger.info(f"   - Array SN: {array_sn}")
    logger.info("="*80)
    
    print(f"✅ Imported {total_lines_converted:,} rows for SN={array_sn} in {total_time:.1f}s")

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="STREAMING Import OceanStor CSV/TSV to VictoriaMetrics (Optimized)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Оптимизированная версия с потоковой обработкой:
- Не загружает весь файл в память
- Начинает отправку данных сразу
- Показывает прогресс в реальном времени
- Использует в 100 раз меньше RAM

Примеры использования:
  %(prog)s 2102353TJWFSP3100020.csv
  %(prog)s 2102353TJWFSP3100020.csv --batch 50000
  %(prog)s data.csv --url http://victoriametrics:8428/api/v1/import/prometheus
        """)
    
    p.add_argument("file", type=pathlib.Path, help="CSV/TSV file to import")
    p.add_argument("--url", default=DEFAULT_URL, 
                   help=f"VictoriaMetrics import endpoint (default: {DEFAULT_URL})")
    p.add_argument("--batch", type=int, default=50000, 
                   help="lines per batch request (default: 50000)")
    
    args = p.parse_args()
    
    if not args.file.exists():
        logger.error(f"❌ File not found: {args.file}")
        sys.exit(f"❌ File not found: {args.file}")
    
    try:
        main_streaming(args.file, args.url, args.batch)
        logger.info(f"Script completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except KeyboardInterrupt:
        logger.warning("⚠️ Import interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise


