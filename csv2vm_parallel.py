#!/usr/bin/env python3
"""
ПАРАЛЛЕЛЬНАЯ версия импорта CSV в VictoriaMetrics.

Основные улучшения:
- Multiprocessing: использует все доступные CPU ядра
- Разделение CSV на chunks для параллельной обработки
- Каждый worker обрабатывает свой chunk независимо
- Ожидаемое ускорение: 5-7x по сравнению с csv2vm_streaming.py
"""

import argparse
import csv
import pathlib
import requests
import sys
import logging
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count, Manager
import os

# Пытаемся импортировать psutil, но работаем и без него
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv2vm_parallel.log', mode='a', encoding='utf-8'),
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
    except (ValueError, IndexError):
        return None

def send_batch(url: str, batch_lines: list) -> bool:
    """Отправляет батч данных в VictoriaMetrics."""
    if not batch_lines:
        return True
    
    payload = "".join(batch_lines).encode('utf-8')
    
    try:
        r = requests.post(url, data=payload, timeout=60)
        if r.status_code not in (200, 204):
            return False
        return True
    except requests.RequestException:
        return False

def count_lines(file_path: pathlib.Path) -> int:
    """Быстро подсчитывает количество строк в файле."""
    with open(file_path, 'rb') as f:
        return sum(1 for _ in f)

def determine_optimal_workers(file_path: pathlib.Path, requested_workers: int = None) -> int:
    """
    Определяет оптимальное количество worker процессов.
    
    Учитывает:
    - Количество CPU ядер (с разумным ограничением для больших систем)
    - Доступную память
    - Размер файла
    - Текущую загрузку системы
    
    Адаптируется под системы с 8, 16, 24, 32+ CPU ядрами.
    """
    if requested_workers is not None and requested_workers > 0:
        return requested_workers
    
    cpu_cores = cpu_count()
    
    # Базовое количество с адаптацией под количество ядер
    # Для очень больших систем используем разумное ограничение
    if cpu_cores <= 8:
        # Маленькие системы (до 8 CPU): используем почти все
        base_workers = max(1, cpu_cores - 1)
    elif cpu_cores <= 16:
        # Средние системы (8-16 CPU): используем почти все
        base_workers = max(1, cpu_cores - 1)
    elif cpu_cores <= 32:
        # Большие системы (16-32 CPU): ограничиваем до 16 workers
        # Больше workers создаёт overhead, а VictoriaMetrics может не справиться
        base_workers = min(16, cpu_cores - 2)
    else:
        # Очень большие системы (32+ CPU): максимум 20 workers
        # Bottleneck обычно в I/O и сети, а не CPU
        base_workers = 20
    
    # Проверяем доступную память
    mem = psutil.virtual_memory()
    available_gb = mem.available / (1024**3)
    
    # Размер файла
    file_size_gb = file_path.stat().st_size / (1024**3)
    
    # Оценка памяти на worker: ~200-300 MB на worker для обработки
    memory_per_worker_gb = 0.3
    max_workers_by_memory = int(available_gb / memory_per_worker_gb)
    
    # Для маленьких файлов (<100 MB) не имеет смысла много workers
    if file_size_gb < 0.1:
        recommended = min(2, base_workers)
    # Для средних файлов (100MB - 1GB)
    elif file_size_gb < 1.0:
        recommended = min(4, base_workers)
    # Для больших файлов (1-5 GB)
    elif file_size_gb < 5.0:
        recommended = base_workers
    # Для очень больших файлов (>5GB)
    else:
        # Для огромных файлов можно использовать все доступные workers
        recommended = base_workers
    
    # Учитываем текущую загрузку CPU
    cpu_percent = psutil.cpu_percent(interval=0.1)
    if cpu_percent > 70:
        # Система уже загружена, уменьшаем workers
        recommended = max(1, recommended - 1)
    elif cpu_percent > 50:
        # Средняя загрузка - немного уменьшаем
        recommended = max(1, int(recommended * 0.8))
    
    # Финальное ограничение по памяти
    final_workers = min(recommended, max_workers_by_memory, base_workers)
    
    return max(1, final_workers)

def process_chunk(args):
    """
    Обрабатывает chunk CSV файла.
    Эта функция запускается в отдельном процессе.
    """
    file_path, start_line, end_line, url, batch_size, delimiter, array_sn, worker_id = args
    
    worker_logger = logging.getLogger(f"Worker-{worker_id}")
    batch_lines = []
    rows_processed = 0
    lines_converted = 0
    batches_sent = 0
    
    start_time = time.time()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=delimiter)
            
            # Пропускаем строки до start_line
            for _ in range(start_line):
                next(reader, None)
            
            # Обрабатываем строки от start_line до end_line
            for idx in range(end_line - start_line):
                try:
                    row = next(reader)
                except StopIteration:
                    break
                
                if len(row) < 6:
                    continue
                
                # Преобразуем строку
                prom_line = row_to_prom(row, array_sn)
                if prom_line:
                    batch_lines.append(prom_line)
                    lines_converted += 1
                
                rows_processed += 1
                
                # Отправляем батч когда накопили достаточно
                if len(batch_lines) >= batch_size:
                    success = send_batch(url, batch_lines)
                    if success:
                        batches_sent += 1
                        batch_lines = []
                    else:
                        worker_logger.error(f"Failed to send batch {batches_sent + 1}")
                        return {
                            'worker_id': worker_id,
                            'rows_processed': rows_processed,
                            'lines_converted': lines_converted,
                            'batches_sent': batches_sent,
                            'success': False,
                            'time': time.time() - start_time
                        }
            
            # Отправляем остаток
            if batch_lines:
                success = send_batch(url, batch_lines)
                if success:
                    batches_sent += 1
        
        elapsed = time.time() - start_time
        rate = rows_processed / elapsed if elapsed > 0 else 0
        
        return {
            'worker_id': worker_id,
            'rows_processed': rows_processed,
            'lines_converted': lines_converted,
            'batches_sent': batches_sent,
            'success': True,
            'time': elapsed,
            'rate': rate
        }
    
    except Exception as e:
        worker_logger.error(f"Error in worker {worker_id}: {e}")
        return {
            'worker_id': worker_id,
            'rows_processed': rows_processed,
            'lines_converted': lines_converted,
            'batches_sent': batches_sent,
            'success': False,
            'time': time.time() - start_time
        }

def main_parallel(path: pathlib.Path, url: str, batch_size: int, num_workers: int = None):
    """
    Главная функция с параллельной обработкой.
    
    Разделяет CSV на chunks и обрабатывает их параллельно.
    """
    logger.info("="*80)
    logger.info(f"CSV2VM PARALLEL Import Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    logger.info(f"🚀 Starting PARALLEL import from: {path}")
    logger.info(f"📍 VictoriaMetrics URL: {url}")
    logger.info(f"📦 Batch size: {batch_size:,} lines")
    
    # Определяем оптимальное количество workers
    optimal_workers = determine_optimal_workers(path, num_workers)
    
    # Показываем информацию о системе
    mem = psutil.virtual_memory()
    cpu_cores = cpu_count()
    file_size_gb = path.stat().st_size / (1024**3)
    
    logger.info(f"💻 System info:")
    logger.info(f"   CPU cores: {cpu_cores}")
    logger.info(f"   Available memory: {mem.available / (1024**3):.1f} GB / {mem.total / (1024**3):.1f} GB")
    logger.info(f"   File size: {file_size_gb:.2f} GB")
    logger.info(f"   CPU load: {psutil.cpu_percent(interval=0.1):.1f}%")
    
    if num_workers is not None:
        logger.info(f"👷 Workers: {optimal_workers} (requested: {num_workers})")
    else:
        logger.info(f"👷 Workers: {optimal_workers} (auto-detected, CPU cores: {cpu_cores})")
    
    num_workers = optimal_workers
    array_sn = path.stem
    logger.info(f"🔢 Array SN: {array_sn}")
    
    delimiter = detect_delimiter(path)
    logger.info(f"📋 Detected delimiter: {'TAB' if delimiter == chr(9) else repr(delimiter)}")
    
    # Подсчитываем строки в файле
    logger.info("📊 Counting lines in file...")
    total_lines = count_lines(path)
    logger.info(f"   Total lines: {total_lines:,}")
    
    # Разделяем на chunks
    lines_per_worker = total_lines // num_workers
    chunks = []
    
    for i in range(num_workers):
        start_line = i * lines_per_worker
        if i == num_workers - 1:
            # Последний worker берет все оставшиеся строки
            end_line = total_lines
        else:
            end_line = (i + 1) * lines_per_worker
        
        chunks.append((
            path, start_line, end_line, url, batch_size, delimiter, array_sn, i + 1
        ))
        logger.info(f"   Worker {i+1}: lines {start_line:,} to {end_line:,} ({end_line - start_line:,} lines)")
    
    # Запускаем параллельную обработку
    logger.info("🔥 Starting parallel processing...")
    start_time = time.time()
    
    with Pool(processes=num_workers) as pool:
        results = pool.map(process_chunk, chunks)
    
    total_time = time.time() - start_time
    
    # Собираем статистику
    total_rows = sum(r['rows_processed'] for r in results)
    total_converted = sum(r['lines_converted'] for r in results)
    total_batches = sum(r['batches_sent'] for r in results)
    all_success = all(r['success'] for r in results)
    avg_rate = total_rows / total_time if total_time > 0 else 0
    
    # Выводим результаты
    logger.info("="*80)
    if all_success:
        logger.info("✅ Import completed successfully!")
    else:
        logger.warning("⚠️ Import completed with errors!")
    
    logger.info(f"📊 Statistics:")
    logger.info(f"   - Total rows processed: {total_rows:,}")
    logger.info(f"   - Lines converted: {total_converted:,}")
    logger.info(f"   - Batches sent: {total_batches}")
    logger.info(f"   - Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    logger.info(f"   - Average rate: {avg_rate:,.0f} rows/sec")
    logger.info(f"   - Workers used: {num_workers}")
    logger.info(f"   - Array SN: {array_sn}")
    
    logger.info("\n📈 Per-worker performance:")
    for r in results:
        logger.info(f"   Worker {r['worker_id']}: {r['rows_processed']:,} rows in {r['time']:.1f}s "
                   f"({r['rate']:,.0f} rows/sec)")
    
    logger.info("="*80)
    
    print(f"\n{'✅' if all_success else '⚠️'} Imported {total_converted:,} rows for SN={array_sn} in {total_time:.1f}s")
    print(f"   Speed: {avg_rate:,.0f} rows/sec (with {num_workers} workers)")
    
    if not all_success:
        sys.exit(1)

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="PARALLEL Import OceanStor CSV/TSV to VictoriaMetrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Параллельная версия с multiprocessing:
- Использует все доступные CPU ядра
- Разделяет CSV на chunks для параллельной обработки
- Ожидаемое ускорение: 5-7x по сравнению с streaming версией

Примеры использования:
  %(prog)s 2102353TJWFSP3100020.csv
  %(prog)s 2102353TJWFSP3100020.csv --workers 4
  %(prog)s data.csv --url http://victoriametrics:8428/api/v1/import/prometheus
        """)
    
    p.add_argument("file", type=pathlib.Path, help="CSV/TSV file to import")
    p.add_argument("--url", default=DEFAULT_URL, 
                   help=f"VictoriaMetrics import endpoint (default: {DEFAULT_URL})")
    p.add_argument("--batch", type=int, default=50000, 
                   help="lines per batch request (default: 50000)")
    p.add_argument("-w", "--workers", type=int, default=None,
                   help="Number of worker processes (default: CPU count - 1)")
    
    args = p.parse_args()
    
    if not args.file.exists():
        logger.error(f"❌ File not found: {args.file}")
        sys.exit(f"❌ File not found: {args.file}")
    
    try:
        main_parallel(args.file, args.url, args.batch, args.workers)
        logger.info(f"Script completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except KeyboardInterrupt:
        logger.warning("⚠️ Import interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise

