#!/usr/bin/env python3
"""
STREAMING PIPELINE: Huawei Performance Data → VictoriaMetrics
Без промежуточных CSV файлов - прямая отправка в VM.

Оптимизировано для огромных файлов (500GB+, 40+ млрд строк):
- Streaming обработка (генераторы)
- Батчинг для эффективности
- Параллельная обработка .tgz файлов
- Минимальное использование памяти
- Мониторинг ресурсов в реальном времени
"""

import sys
import os
import re
import struct
import tarfile
import zipfile
import time
import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Поддержка .7z архивов
try:
    import py7zr
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count, Manager
import requests
from typing import Generator, Tuple
import shutil

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available, resource monitoring disabled")

# Импорт словарей из parsers/dictionaries/
# Поддержка запуска как модуля и напрямую
try:
    from parsers.dictionaries import METRIC_NAME_DICT, RESOURCE_NAME_DICT, METRIC_CONVERSION
except ImportError:
    # Запуск напрямую из директории parsers или корня проекта
    sys.path.insert(0, str(Path(__file__).parent))
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from dictionaries import METRIC_NAME_DICT, RESOURCE_NAME_DICT, METRIC_CONVERSION

# Настройка логирования с ротацией (50MB max, 5 backups = ~300MB total)
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(50 * 1024 * 1024)))  # 50MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

file_handler = RotatingFileHandler(
    'streaming_pipeline.log',
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT,
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler]
)
logger = logging.getLogger(__name__)

# Константы
BATCH_SIZE = 100000  # Строк в батче для отправки в VM (оптимизировано)
DEFAULT_RESOURCES = ["207", "212", "225", "216", "266", "10", "11", "21"]
DEFAULT_METRICS = ["18", "22", "25", "28", "23", "26", "1079", "1073", "627", "1074", 
                   "240", "1158", "1154", "1162", "1166", "1170", "1174"]


class ResourceMonitor:
    """Мониторинг использования ресурсов."""
    
    def __init__(self):
        self.start_time = time.time()
        self.start_memory = None
        self.peak_memory = 0
        self.metrics_sent = 0
        
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            self.start_memory = process.memory_info().rss / (1024**3)  # GB
    
    def update(self, metrics_count=0):
        """Обновить статистику."""
        self.metrics_sent += metrics_count
        
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            current_memory = process.memory_info().rss / (1024**3)
            self.peak_memory = max(self.peak_memory, current_memory)
    
    def report(self):
        """Вывести отчет."""
        elapsed = time.time() - self.start_time
        
        logger.info("="*80)
        logger.info("📊 RESOURCE USAGE REPORT")
        logger.info("="*80)
        
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            current_memory = process.memory_info().rss / (1024**3)
            memory_delta = current_memory - self.start_memory if self.start_memory else 0
            
            logger.info(f"💾 Memory:")
            logger.info(f"   Start:   {self.start_memory:.2f} GB")
            logger.info(f"   Current: {current_memory:.2f} GB")
            logger.info(f"   Peak:    {self.peak_memory:.2f} GB")
            logger.info(f"   Delta:   {memory_delta:+.2f} GB")
            
            logger.info(f"💻 CPU:")
            logger.info(f"   Usage:   {psutil.cpu_percent(interval=0.1):.1f}%")
            logger.info(f"   Cores:   {cpu_count()}")
        
        logger.info(f"📈 Metrics:")
        logger.info(f"   Sent:    {self.metrics_sent:,}")
        logger.info(f"   Rate:    {self.metrics_sent/elapsed:,.0f} metrics/sec")
        
        logger.info(f"⏱️  Time:    {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        logger.info("="*80)


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
    return result.strip("_")


def construct_data_header(result):
    """Построить заголовок данных."""
    data_header = {}
    if result:
        result = result.groups()
        map_header = result[0]
        map_content = result[1]

        list_map_header = map_header.split(",")
        for each_key in list_map_header:
            list_key_value = each_key.split(":")
            map_key = list_key_value[0].replace('"', '')
            map_value = list_key_value[1].replace('"', '')
            data_header[map_key] = map_value.strip()

        data_header['Map'] = []
        result = re.findall(
            '"([0-9]+)":{"IDs":\\[(("[0-9a-zA-Z]+",?)+)\\],'
            '"Names":\\[(("[.0-9A-Za-z$ \\[\\]\\(\\):_-]*",?)+)\\],'
            '"DataTypes":\\[(([0-9]+,?)+)\\]}',
            map_content
        )
        if result:
            for each_result in result:
                object_type = {}
                object_type['ObjectTypes'] = each_result[0]
                object_type['IDs'] = each_result[1].replace('"', '').split(',')
                object_type['Names'] = each_result[3].replace('"', '').split(',')
                object_type['DataTypes'] = each_result[5].replace('"', '').split(',')
                data_header['Map'].append(object_type)
    return data_header


def construct_data_type(data_header):
    """Построить структуру типов данных."""
    list_data_type = []
    size_collect_once = 0
    if 'Map' in data_header:
        for resource_type in data_header['Map']:
            size_collect_once += (
                len(resource_type['IDs']) *
                len(resource_type['DataTypes']) * 4
            )
            for index_ids, _ in enumerate(resource_type['IDs']):
                for index_data_type in resource_type['DataTypes']:
                    list_index = [
                        resource_type['ObjectTypes'],
                        index_data_type,
                        resource_type['Names'][index_ids], []
                    ]
                    list_data_type.append(list_index)

    return list_data_type, size_collect_once


def stream_prometheus_metrics(file_path: Path, array_sn: str, resources: list, 
                              metrics: list, allow_unknown: bool = True) -> Generator[str, None, int]:
    """
    STREAMING генератор метрик в формате Prometheus.
    Возвращает строки готовые для отправки в VictoriaMetrics.
    
    Args:
        file_path: Путь к .dat файлу
        array_sn: Серийный номер массива
        resources: Список ID ресурсов для обработки
        metrics: Список ID метрик для обработки
        allow_unknown: Если True, обрабатывает ВСЕ ID (даже неизвестные)
    
    Yields:
        str: Метрика в формате Prometheus
    
    Returns:
        int: Количество обработанных метрик
    """
    metrics_count = 0
    unknown_resources = set()
    unknown_metrics = set()
    
    try:
        with open(file_path, "rb") as fin:
            # Читаем заголовок
            bit_correct = fin.read(32)
            bit_msg_version = fin.read(4)
            bit_equip_sn = fin.read(256).decode('utf-8')
            bit_equip_name = fin.read(41).decode('utf-8')
            bit_equip_data_length = fin.read(4)

            process_finish_flag = False

            bit_map_type = fin.read(4)
            bit_map_length, = struct.unpack("<l", fin.read(4))
            bit_map_value = fin.read(bit_map_length - 8)
            
            if len(bit_map_value) < bit_map_length - 8:
                logger.error(f"Read Data Header Failed for {file_path}")
                return metrics_count

            while not process_finish_flag:
                result = re.match(
                    '{(.*),"Map":{(.*)}}', bit_map_value.decode('utf-8')
                )
                data_header = construct_data_header(result)
                list_data_type, size_collect_once = construct_data_type(data_header)

                times_collect = int(
                    (int(data_header['EndTime']) - int(data_header['StartTime'])) /
                    int(data_header['Archive'])
                )
                
                # Извлекаем интервал сбора для добавления в label
                archive_interval = int(data_header['Archive'])

                # Читаем данные блоками
                for i in range(times_collect):
                    buffer_read = fin.read(size_collect_once)
                    if len(buffer_read) < size_collect_once:
                        process_finish_flag = True
                        break
                    
                    for index_in_buffer in range(0, size_collect_once, 4):
                        bytes_read_4 = buffer_read[index_in_buffer: index_in_buffer + 4]
                        bytes_read_int, = struct.unpack("<l", bytes_read_4)
                        list_data_type[int(index_in_buffer / 4)][3].append(str(bytes_read_int))

                # Генерируем timestamps
                start_time = datetime.fromtimestamp(int(data_header['StartTime']))
                next_time = start_time
                time_list = []
                for i, _ in enumerate(list_data_type[0][3]):
                    time_list.append(next_time)
                    next_time += timedelta(seconds=int(data_header['Archive']))

                # STREAMING: отдаем метрики по одной, не накапливая в памяти
                for data_type in list_data_type:
                    resource_id = str(data_type[0])
                    metric_id = str(data_type[1])
                    
                    # Фильтруем нужные ресурсы и метрики
                    if resource_id not in resources or metric_id not in metrics:
                        continue

                    # Проверяем, известны ли ID
                    resource_name = RESOURCE_NAME_DICT.get(resource_id, f"UNKNOWN_RESOURCE_{resource_id}")
                    metric_base_name = METRIC_NAME_DICT.get(metric_id, f"UNKNOWN_METRIC_{metric_id}")
                    
                    # Собираем ТОЛЬКО те ID, которых НЕТ в словарях (для логирования)
                    # Если ID уже добавлен в словарь (даже с именем UNKNOWN_XXX), warning не нужен
                    if resource_id not in RESOURCE_NAME_DICT:
                        unknown_resources.add(resource_id)
                    if metric_id not in METRIC_NAME_DICT:
                        unknown_metrics.add(metric_id)
                    
                    metric_name = "huawei_" + sanitize_metric_name(metric_base_name)
                    element = data_type[2]

                    # Генерируем метрики для каждого временного интервала
                    for index, point_value in enumerate(data_type[3]):
                        try:
                            ts_unix_ms = int(time.mktime(time_list[index].timetuple()) * 1000)
                            
                            # Применяем конверсию единиц измерения если нужно
                            # Для метрик, где сырые данные в других единицах (KB/s→MB/s, us→ms)
                            value = float(point_value)
                            if metric_id in METRIC_CONVERSION:
                                value = value / METRIC_CONVERSION[metric_id]
                            
                            # Формат Prometheus с добавлением scrape_interval для универсальности
                            # scrape_interval (в секундах) - реальный интервал сбора данных из .dat файла
                            prom_line = f'{metric_name}{{Element="{element}",Resource="{resource_name}",SN="{array_sn}",scrape_interval="{archive_interval}"}} {value} {ts_unix_ms}\n'
                            
                            yield prom_line
                            metrics_count += 1
                            
                        except (ValueError, IndexError) as e:
                            continue

                # Очищаем данные для освобождения памяти
                for data_type in list_data_type:
                    data_type[3].clear()

                bit_map_type = fin.read(4)
                if bit_map_type == b'':
                    process_finish_flag = True
                elif bit_map_type == b'\x00\x00\x00\x00':
                    bit_map_length, = struct.unpack("<l", fin.read(4))
                    if bit_map_length < 8:
                        process_finish_flag = True
                    else:
                        bit_map_value = fin.read(bit_map_length - 8)
                        if len(bit_map_value) < bit_map_length - 8:
                            return metrics_count
                else:
                    process_finish_flag = True
                    
    except Exception as exc_info:
        logger.error(f"Error processing {file_path}: {exc_info}")
    
    # Логируем неизвестные ID если они есть
    if unknown_resources:
        logger.warning(f"Found {len(unknown_resources)} unknown resource IDs in {file_path.name}: {sorted(unknown_resources)}")
    if unknown_metrics:
        logger.warning(f"Found {len(unknown_metrics)} unknown metric IDs in {file_path.name}: {sorted(unknown_metrics)}")
    
    return metrics_count


def send_batch_to_vm(batch: list, vm_url: str) -> bool:
    """Отправить батч метрик в VictoriaMetrics."""
    if not batch:
        return True
    
    payload = "".join(batch).encode('utf-8')
    
    try:
        response = requests.post(vm_url, data=payload, timeout=30)
        if response.status_code not in (200, 204):
            logger.error(f"VM returned {response.status_code}: {response.text[:200]}")
            return False
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send batch to VM: {e}")
        return False


def decompress_tgz(file_tgz: Path) -> Path:
    """Распаковать .tgz файл."""
    tar = tarfile.open(file_tgz)
    names = tar.getnames()
    temp_file_path = Path("temp") / f"temp_{os.getpid()}_{time.time()}"
    temp_file_path.mkdir(parents=True, exist_ok=True)
    
    if len(names) == 1:
        tar.extract(names[0], temp_file_path)
        return temp_file_path / names[0]
    
    logger.error(f"perf file content error: {file_tgz}")
    return None


def process_single_tgz_streaming(args) -> dict:
    """
    Обработать один .tgz файл в streaming режиме.
    Парсит данные и сразу отправляет в VictoriaMetrics батчами.
    """
    tgz_file, vm_url, batch_size, resources, metrics, array_sn = args
    
    worker_id = os.getpid()
    logger.info(f"[Worker {worker_id}] Processing {tgz_file.name}")
    
    start_time = time.time()
    metrics_sent = 0
    batches_sent = 0
    
    try:
        # Распаковываем
        decompressed_file = decompress_tgz(tgz_file)
        if not decompressed_file:
            return {
                'file': tgz_file.name,
                'success': False,
                'metrics': 0,
                'time': time.time() - start_time
            }
        
        # Стримим метрики и отправляем батчами
        batch = []
        
        for metric_line in stream_prometheus_metrics(decompressed_file, array_sn, resources, metrics):
            batch.append(metric_line)
            
            # Когда батч заполнен - отправляем
            if len(batch) >= batch_size:
                if send_batch_to_vm(batch, vm_url):
                    metrics_sent += len(batch)
                    batches_sent += 1
                    batch = []
                else:
                    logger.error(f"[Worker {worker_id}] Failed to send batch")
                    return {
                        'file': tgz_file.name,
                        'success': False,
                        'metrics': metrics_sent,
                        'time': time.time() - start_time
                    }
        
        # Отправляем остаток
        if batch:
            if send_batch_to_vm(batch, vm_url):
                metrics_sent += len(batch)
                batches_sent += 1
        
        # Cleanup
        if decompressed_file.exists():
            decompressed_file.unlink()
        
        elapsed = time.time() - start_time
        rate = metrics_sent / elapsed if elapsed > 0 else 0
        
        logger.info(f"[Worker {worker_id}] ✅ {tgz_file.name}: {metrics_sent:,} metrics in {elapsed:.1f}s ({rate:,.0f} m/s)")
        
        return {
            'file': tgz_file.name,
            'success': True,
            'metrics': metrics_sent,
            'batches': batches_sent,
            'time': elapsed,
            'rate': rate
        }
        
    except Exception as e:
        logger.error(f"[Worker {worker_id}] Error: {e}")
        return {
            'file': tgz_file.name,
            'success': False,
            'metrics': 0,
            'time': time.time() - start_time
        }


def extract_serial_from_filename(filename: str) -> str:
    """Извлечь серийный номер из имени файла."""
    match = re.search(r"_SN_([0-9A-Z]+)_SP\d+", filename)
    if match:
        return match.group(1)
    
    # Fallback: попытаться извлечь из имени архива
    match = re.search(r"\(([0-9.]+)\)", filename)
    if match:
        return match.group(1).replace(".", "_")
    
    return "UNKNOWN_SN"


def main():
    parser = argparse.ArgumentParser(
        description="STREAMING Pipeline: Huawei Performance → VictoriaMetrics (БЕЗ промежуточных CSV)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Оптимизировано для огромных файлов (500GB+):
  
  • Streaming обработка - минимум памяти
  • Прямая отправка в VictoriaMetrics
  • БЕЗ промежуточных CSV файлов
  • Параллельная обработка .tgz файлов
  • Мониторинг ресурсов

Примеры:

  # Базовый запуск (используется localhost по умолчанию)
  %(prog)s -i logs.zip
  
  # С мониторингом
  %(prog)s -i logs.zip --monitor
  
  # Указать другой VM URL
  %(prog)s -i logs.zip --vm-url http://10.5.10.163:8428/api/v1/import/prometheus
        """)
    
    parser.add_argument('-i', '--input', type=str, required=True,
                       help='ZIP архив с .tgz файлами')
    parser.add_argument('--vm-url', type=str, 
                       default='http://localhost:8428/api/v1/import/prometheus',
                       help='VictoriaMetrics import endpoint (default: http://localhost:8428/api/v1/import/prometheus)')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE,
                       help=f'Размер батча (default: {BATCH_SIZE})')
    parser.add_argument('-w', '--workers', type=int, default=None,
                       help='Количество параллельных workers (default: CPU-2)')
    parser.add_argument('--all-metrics', action='store_true', default=True,
                       help='Парсить ВСЕ метрики (по умолчанию: True)')
    parser.add_argument('--monitor', action='store_true',
                       help='Включить подробный мониторинг ресурсов')
    
    args = parser.parse_args()
    
    # Инициализация
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"File not found: {input_path}")
        sys.exit(1)
    
    monitor = ResourceMonitor() if args.monitor else None
    
    logger.info("="*80)
    logger.info("🚀 STREAMING PIPELINE STARTED")
    logger.info("="*80)
    logger.info(f"Input:  {input_path}")
    logger.info(f"VM URL: {args.vm_url}")
    logger.info(f"Batch:  {args.batch_size:,} metrics")
    
    if args.all_metrics:
        resources = list(RESOURCE_NAME_DICT.keys())
        metrics = list(METRIC_NAME_DICT.keys())
        logger.info(f"Mode:   ALL METRICS ({len(metrics)} metrics, {len(resources)} resources)")
    else:
        resources = DEFAULT_RESOURCES
        metrics = DEFAULT_METRICS
        logger.info(f"Mode:   DEFAULT ({len(metrics)} metrics, {len(resources)} resources)")
    
    # Определяем workers
    num_workers = args.workers if args.workers else max(1, cpu_count() - 2)
    logger.info(f"Workers: {num_workers}")
    logger.info("="*80)
    
    start_time = time.time()
    
    # Извлекаем архив (поддержка .zip и .7z)
    temp_dir = Path("temp_streaming_extract")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    
    # Определяем тип архива и извлекаем
    input_suffix = input_path.suffix.lower()
    
    if input_suffix == '.7z':
        if not PY7ZR_AVAILABLE:
            logger.error("❌ py7zr не установлен! Установите: pip install py7zr")
            sys.exit(1)
        logger.info(f"📦 Extracting 7z archive...")
        with py7zr.SevenZipFile(input_path, mode='r') as archive:
            archive.extractall(temp_dir)
    elif input_suffix == '.zip':
        logger.info(f"📦 Extracting ZIP...")
        with zipfile.ZipFile(input_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
    else:
        logger.error(f"❌ Неподдерживаемый формат архива: {input_suffix}")
        logger.error("   Поддерживаются: .zip, .7z")
        sys.exit(1)
    
    # Находим .tgz файлы
    tgz_files = list(temp_dir.rglob("*.tgz"))
    logger.info(f"✅ Found {len(tgz_files)} .tgz files")
    
    if not tgz_files:
        logger.error("No .tgz files found!")
        sys.exit(1)
    
    # Определяем серийный номер
    array_sn = extract_serial_from_filename(tgz_files[0].name)
    logger.info(f"📌 Array SN: {array_sn}")
    logger.info("="*80)
    
    # Параллельная обработка
    process_args = [
        (f, args.vm_url, args.batch_size, resources, metrics, array_sn)
        for f in tgz_files
    ]
    
    logger.info(f"🔥 Processing {len(tgz_files)} files with {num_workers} workers...")
    
    with Pool(processes=num_workers) as pool:
        results = pool.map(process_single_tgz_streaming, process_args)
    
    # Статистика
    total_time = time.time() - start_time
    total_metrics = sum(r['metrics'] for r in results)
    total_batches = sum(r.get('batches', 0) for r in results)
    success_count = sum(1 for r in results if r['success'])
    
    if monitor:
        monitor.update(total_metrics)
        monitor.report()
    
    logger.info("="*80)
    logger.info("✅ STREAMING PIPELINE COMPLETED")
    logger.info("="*80)
    logger.info(f"📊 Results:")
    logger.info(f"   Files processed: {success_count}/{len(tgz_files)}")
    logger.info(f"   Metrics sent:    {total_metrics:,}")
    logger.info(f"   Batches sent:    {total_batches:,}")
    logger.info(f"   Total time:      {total_time:.1f}s ({total_time/60:.1f} min)")
    logger.info(f"   Throughput:      {total_metrics/total_time:,.0f} metrics/sec")
    logger.info(f"   Array SN:        {array_sn}")
    logger.info("")
    logger.info(f"💡 Tip: Check logs for 'unknown.*IDs' to find any missing metrics/resources")
    logger.info(f"   grep -i 'unknown.*IDs' streaming_pipeline.log")
    logger.info("="*80)
    
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    temp_path = Path("temp")
    if temp_path.exists():
        for item in temp_path.iterdir():
            if item.is_dir():
                try:
                    shutil.rmtree(item)
                except:
                    pass
    
    print(f"\n✅ Done! Sent {total_metrics:,} metrics in {total_time:.1f}s")
    print(f"📊 Check VictoriaMetrics: {args.vm_url.replace('/api/v1/import/prometheus', '')}")
    
    # Автоматическое обновление словарей если есть unknown IDs
    auto_update_script = Path(__file__).parent / "auto_update_dictionaries.py"
    if auto_update_script.exists():
        logger.info("\n🔄 Запуск автоматического обновления словарей...")
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, str(auto_update_script)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(result.stdout)
            else:
                logger.warning(f"⚠️  Auto-update завершился с кодом {result.returncode}")
                if result.stderr:
                    logger.warning(result.stderr)
        except Exception as e:
            logger.warning(f"⚠️  Не удалось запустить auto-update: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)

