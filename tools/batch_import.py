#!/usr/bin/env python3
"""
Batch Import Script для массового импорта Huawei Performance логов в VictoriaMetrics

Скрипт последовательно обрабатывает ZIP архивы с performance данными,
запускает streaming pipeline для импорта в VictoriaMetrics и проверяет
успешность импорта.

Использование:
    python3 batch_import.py /path/to/logs/
    python3 batch_import.py /path/to/logs/ --skip-existing
    python3 batch_import.py /path/to/logs/ --dry-run
"""

import sys
import os
import re
import zipfile
import subprocess
import argparse
import logging
import time
import signal
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, field
import shutil

# Поддержка .7z архивов
try:
    import py7zr
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False

# Импорт VictoriaMetricsClient из tools/
try:
    from tools.victoriametrics_client import VictoriaMetricsClient
    VM_CLIENT_AVAILABLE = True
except ImportError:
    try:
        # Fallback для запуска из корня проекта
        from victoriametrics_client import VictoriaMetricsClient
        VM_CLIENT_AVAILABLE = True
    except ImportError:
        VM_CLIENT_AVAILABLE = False
        print("Warning: VictoriaMetricsClient not available, verification will be skipped")


@dataclass
class ImportResult:
    """Результат импорта одного архива."""
    archive_name: str
    serial_number: Optional[str] = None
    status: str = "pending"  # pending, success, failed, skipped
    import_time: float = 0.0
    error_message: Optional[str] = None
    data_in_vm: bool = False
    last_datapoint: Optional[str] = None
    metrics_sent: int = 0
    
    
@dataclass
class BatchStats:
    """Статистика batch импорта."""
    total_archives: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_time: float = 0.0
    results: List[ImportResult] = field(default_factory=list)
    

# Глобальная переменная для graceful shutdown
INTERRUPTED = False


def signal_handler(signum, frame):
    """Обработчик сигнала прерывания (Ctrl+C)."""
    global INTERRUPTED
    INTERRUPTED = True
    logger.warning("\n⚠️  Прерывание получено! Завершаю текущую операцию...")


def setup_logging(log_dir: Path = Path(".")) -> Tuple[logging.Logger, str]:
    """
    Настройка логирования.
    
    Args:
        log_dir: Директория для лог-файла
        
    Returns:
        Tuple[Logger, имя лог-файла]
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"batch_import_{timestamp}.log"
    log_path = log_dir / log_filename
    
    # Настройка форматирования
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Создаем logger
    logger = logging.getLogger('batch_import')
    logger.setLevel(logging.DEBUG)
    
    # File handler
    file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Добавляем handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_filename


def extract_serial_number(archive_path: Path) -> Optional[str]:
    """
    Извлекает серийный номер массива из имени .tgz файлов внутри архива.
    
    Поддерживает .zip и .7z архивы.
    Ищет паттерн: PerfData_*_SN_<SERIAL>_SP* или извлекает из имени файла.
    
    Args:
        archive_path: Путь к архиву (.zip или .7z)
        
    Returns:
        Серийный номер или None если не найден
    """
    try:
        file_list = []
        suffix = archive_path.suffix.lower()
        
        # Получаем список файлов в архиве в зависимости от формата
        if suffix == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
        elif suffix == '.7z':
            if not PY7ZR_AVAILABLE:
                logger.warning(f"py7zr не установлен, не могу прочитать .7z архив")
            else:
                with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                    file_list = archive.getnames()
        
        # Ищем .tgz файлы с паттерном SN
        pattern = r"PerfData_.*_SN_([0-9A-Z]+)_SP"
        
        for filename in file_list:
            if filename.endswith('.tgz'):
                match = re.search(pattern, filename)
                if match:
                    return match.group(1)
        
        # Fallback 1: Ищем серийный номер в имени архива
        # Формат имени: Data_<Model>_<Timestamp>_<SN>.7z
        # Например: Data_Dorado6000V3_20251023163227_2102352KRR10KC000013.7z
        # SN всегда начинается с "21" и содержит 20+ символов (цифры и буквы)
        match = re.search(r"_(21[0-9A-Z]{18,})\.(zip|7z)$", archive_path.name, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Fallback 2: Серийный номер в имени родительской директории
        # Формат: IP_SN (например: 10.105.152.20_2102352KRR10KC000013)
        parent_name = archive_path.parent.name
        match = re.search(r"_(21[0-9A-Z]{18,})$", parent_name)
        if match:
            return match.group(1)
        
        # Fallback 3: попробуем извлечь IP из имени (старый формат)
        match = re.search(r"\(([0-9.]+)\)", archive_path.name)
        if match:
            return match.group(1).replace(".", "_")
        
        return None
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении SN из {archive_path.name}: {e}")
        return None


def extract_perf_zip_from_7z(archive_path: Path, temp_dir: Path, logger: logging.Logger) -> Optional[Path]:
    """
    Извлекает Perf ZIP файл из .7z архива.
    
    Структура внутри .7z:
    DataCollect/History_Performance_Data/<IP>/(<IP>)..._Perf_*.zip
    
    Args:
        archive_path: Путь к .7z архиву
        temp_dir: Временная директория для извлечения
        logger: Logger
        
    Returns:
        Путь к извлечённому .zip файлу или None
    """
    if not PY7ZR_AVAILABLE:
        logger.error("❌ py7zr не установлен! Установите: pip install py7zr")
        return None
    
    try:
        with py7zr.SevenZipFile(archive_path, mode='r') as archive:
            all_names = archive.getnames()
            
            # Ищем файлы с паттерном *_Perf_*.zip в History_Performance_Data
            perf_zip_files = [
                name for name in all_names 
                if '_Perf_' in name and name.endswith('.zip') and 'History_Performance_Data' in name
            ]
            
            if not perf_zip_files:
                logger.warning(f"⚠️  Perf ZIP файлы не найдены внутри {archive_path.name}")
                return None
            
            if len(perf_zip_files) > 1:
                logger.info(f"📦 Найдено {len(perf_zip_files)} Perf ZIP файлов, используем первый")
            
            perf_zip_name = perf_zip_files[0]
            logger.info(f"📦 Извлекаю: {perf_zip_name}")
            
            # Извлекаем только нужный файл
            archive.extract(temp_dir, targets=[perf_zip_name])
            
            extracted_path = temp_dir / perf_zip_name
            if extracted_path.exists():
                return extracted_path
            else:
                logger.error(f"❌ Файл не найден после извлечения: {extracted_path}")
                return None
                
    except Exception as e:
        logger.error(f"❌ Ошибка при извлечении из .7z: {e}")
        return None


def run_streaming_pipeline(zip_path: Path, vm_url: str, logger: logging.Logger) -> Tuple[bool, str, int]:
    """
    Запускает huawei_streaming_pipeline.py через subprocess.
    
    Args:
        zip_path: Путь к ZIP архиву
        vm_url: URL VictoriaMetrics
        logger: Logger для вывода
        
    Returns:
        Tuple[успех, логи, количество метрик]
    """
    # Путь к streaming pipeline (в parsers/ или корне для обратной совместимости)
    pipeline_script = Path(__file__).parent.parent / "parsers" / "streaming_pipeline.py"
    if not pipeline_script.exists():
        # Fallback на старый путь
        pipeline_script = Path(__file__).parent.parent / "huawei_streaming_pipeline.py"
    
    if not pipeline_script.exists():
        logger.error(f"Не найден скрипт: {pipeline_script}")
        return False, "Pipeline script not found", 0
    
    # Формируем команду
    cmd = [
        sys.executable,
        str(pipeline_script),
        "-i", str(zip_path),
        "--vm-url", f"{vm_url}/api/v1/import/prometheus",
        "--monitor"
    ]
    
    logger.info(f"Запуск: {' '.join(cmd)}")
    
    try:
        # Запускаем процесс с перехватом вывода
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        output_lines = []
        metrics_sent = 0
        
        # Читаем вывод в реальном времени
        for line in process.stdout:
            output_lines.append(line)
            
            # Логируем важные строки
            if "Processing" in line or "✅" in line or "ERROR" in line or "WARNING" in line:
                logger.debug(line.strip())
            
            # Извлекаем количество отправленных метрик
            if "Metrics sent:" in line:
                match = re.search(r"Metrics sent:\s+([\d,]+)", line)
                if match:
                    metrics_sent = int(match.group(1).replace(",", ""))
            
            # Проверяем прерывание
            if INTERRUPTED:
                process.terminate()
                process.wait(timeout=5)
                return False, "Interrupted by user", 0
        
        # Ждем завершения
        return_code = process.wait()
        
        full_output = "".join(output_lines)
        
        if return_code == 0:
            logger.info(f"✅ Pipeline завершился успешно")
            return True, full_output, metrics_sent
        else:
            logger.error(f"❌ Pipeline завершился с ошибкой (код: {return_code})")
            return False, full_output, metrics_sent
            
    except Exception as e:
        logger.error(f"Ошибка при запуске pipeline: {e}")
        return False, str(e), 0


def verify_data_in_vm(client: VictoriaMetricsClient, sn: str, logger: logging.Logger) -> Tuple[bool, Optional[str]]:
    """
    Проверяет наличие данных для серийного номера в VictoriaMetrics.
    
    Args:
        client: VictoriaMetricsClient
        sn: Серийный номер массива
        logger: Logger для вывода
        
    Returns:
        Tuple[данные есть, дата последней точки]
    """
    try:
        last_timestamp = client.get_last_datapoint_time(sn)
        
        if last_timestamp:
            last_date = datetime.fromtimestamp(last_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"✅ Данные в VM найдены. Последняя точка: {last_date}")
            return True, last_date
        else:
            logger.warning(f"⚠️  Данные для SN {sn} не найдены в VictoriaMetrics")
            return False, None
            
    except Exception as e:
        logger.error(f"Ошибка при проверке данных в VM: {e}")
        return False, None


def process_archive(
    archive_path: Path,
    vm_url: str,
    vm_client: Optional[VictoriaMetricsClient],
    skip_existing: bool,
    dry_run: bool,
    logger: logging.Logger
) -> ImportResult:
    """
    Обработка одного архива.
    
    Поддерживает:
    - .zip файлы с Perf данными (прямой запуск pipeline)
    - .7z файлы с вложенной структурой (извлечение Perf .zip и запуск)
    
    Структура .7z:
    DataCollect/History_Performance_Data/<IP>/(<IP>)..._Perf_*.zip → .tgz файлы
    
    Args:
        archive_path: Путь к архиву (.zip или .7z)
        vm_url: URL VictoriaMetrics
        vm_client: VictoriaMetricsClient или None
        skip_existing: Пропускать если данные уже есть в VM
        dry_run: Режим без реального импорта
        logger: Logger
        
    Returns:
        ImportResult с результатами обработки
    """
    result = ImportResult(archive_name=archive_path.name)
    start_time = time.time()
    temp_dir = None
    
    logger.info("="*80)
    logger.info(f"📦 Обработка: {archive_path.name}")
    logger.info("="*80)
    
    try:
        # Шаг 1: Извлечение серийного номера
        logger.info("🔍 Извлечение серийного номера...")
        sn = extract_serial_number(archive_path)
        result.serial_number = sn
        
        if sn:
            logger.info(f"✅ Серийный номер: {sn}")
        else:
            logger.warning(f"⚠️  Не удалось извлечь серийный номер из {archive_path.name}")
            sn = f"UNKNOWN_{archive_path.stem}"
            result.serial_number = sn
        
        # Шаг 2: Проверка существующих данных (если skip_existing)
        if skip_existing and vm_client and sn and not sn.startswith("UNKNOWN_"):
            logger.info("🔍 Проверка наличия данных в VictoriaMetrics...")
            data_exists, last_date = verify_data_in_vm(vm_client, sn, logger)
            
            if data_exists:
                logger.info(f"⏭️  Пропуск: данные уже есть в VM (последняя точка: {last_date})")
                result.status = "skipped"
                result.data_in_vm = True
                result.last_datapoint = last_date
                result.import_time = time.time() - start_time
                return result
        
        # Шаг 3: Dry-run режим
        if dry_run:
            logger.info("🧪 DRY-RUN режим: импорт не выполняется")
            result.status = "skipped"
            result.import_time = time.time() - start_time
            return result
        
        # Шаг 4: Определяем тип архива и получаем путь к Perf ZIP
        suffix = archive_path.suffix.lower()
        perf_zip_path = None
        
        if suffix == '.zip':
            # Прямой .zip файл с Perf данными
            perf_zip_path = archive_path
            logger.info(f"📦 Тип: ZIP (прямой Perf файл)")
            
        elif suffix == '.7z':
            # .7z архив с вложенной структурой - извлекаем Perf ZIP
            logger.info(f"📦 Тип: 7z (вложенная структура)")
            
            # Создаём временную директорию для извлечения
            temp_dir = Path(f"temp_batch_extract_{archive_path.stem}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir()
            
            # Извлекаем Perf ZIP из .7z
            perf_zip_path = extract_perf_zip_from_7z(archive_path, temp_dir, logger)
            
            if not perf_zip_path:
                logger.error(f"❌ Не удалось извлечь Perf ZIP из {archive_path.name}")
                result.status = "failed"
                result.error_message = "Failed to extract Perf ZIP from 7z"
                result.import_time = time.time() - start_time
                return result
        else:
            logger.error(f"❌ Неподдерживаемый формат: {suffix}")
            result.status = "failed"
            result.error_message = f"Unsupported format: {suffix}"
            result.import_time = time.time() - start_time
            return result
        
        # Шаг 5: Запуск streaming pipeline
        logger.info("🚀 Запуск streaming pipeline...")
        success, output, metrics_sent = run_streaming_pipeline(perf_zip_path, vm_url, logger)
        result.metrics_sent = metrics_sent
        
        if not success:
            logger.error(f"❌ Импорт завершился с ошибкой")
            result.status = "failed"
            result.error_message = "Pipeline execution failed"
            result.import_time = time.time() - start_time
            return result
        
        logger.info(f"✅ Pipeline завершился успешно. Метрик отправлено: {metrics_sent:,}")
        
        # Шаг 6: Проверка данных в VM (если доступен клиент)
        if vm_client and sn and not sn.startswith("UNKNOWN_"):
            logger.info("🔍 Проверка импортированных данных в VictoriaMetrics...")
            # Даем VM время на индексацию (небольшая задержка)
            time.sleep(2)
            
            data_exists, last_date = verify_data_in_vm(vm_client, sn, logger)
            result.data_in_vm = data_exists
            result.last_datapoint = last_date
            
            if data_exists:
                result.status = "success"
            else:
                result.status = "success"  # Pipeline успешен, но данных не видно (может быть задержка индексации)
                logger.warning("⚠️  Данные не найдены в VM, но pipeline выполнен успешно")
        else:
            # VM client недоступен - считаем успешным если pipeline завершился без ошибок
            result.status = "success"
            logger.info("✅ Импорт завершен (проверка VM пропущена)")
        
        result.import_time = time.time() - start_time
        logger.info(f"⏱️  Время обработки: {result.import_time:.1f}s")
        
        return result
        
    finally:
        # Cleanup: удаляем временные файлы
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"🧹 Временная директория удалена: {temp_dir}")
            except Exception as e:
                logger.warning(f"⚠️  Не удалось удалить временную директорию: {e}")


def generate_report(stats: BatchStats, log_filename: str, logger: logging.Logger):
    """
    Генерирует финальный отчет по batch импорту.
    
    Args:
        stats: BatchStats со статистикой
        log_filename: Имя лог-файла
        logger: Logger для вывода
    """
    logger.info("\n" + "="*80)
    logger.info("📊 BATCH IMPORT SUMMARY")
    logger.info("="*80)
    
    # Основная статистика
    logger.info(f"Total archives found:    {stats.total_archives}")
    logger.info(f"Total archives processed: {stats.processed}/{stats.total_archives}")
    logger.info(f"  - Successful imports:   {stats.successful}")
    logger.info(f"  - Failed imports:       {stats.failed}")
    logger.info(f"  - Skipped:              {stats.skipped}")
    logger.info("")
    
    # Временная статистика
    hours = int(stats.total_time // 3600)
    minutes = int((stats.total_time % 3600) // 60)
    seconds = int(stats.total_time % 60)
    
    logger.info(f"Total time: {hours}h {minutes}m {seconds}s")
    
    if stats.processed > 0:
        avg_time = stats.total_time / stats.processed
        logger.info(f"Average time per archive: {avg_time:.1f}s")
    logger.info("")
    
    # Массивы с данными в VM
    arrays_with_data = [r for r in stats.results if r.data_in_vm]
    arrays_without_data = [r for r in stats.results if r.status == "success" and not r.data_in_vm]
    
    if arrays_with_data:
        logger.info(f"Arrays with data in VictoriaMetrics: {len(arrays_with_data)}")
        for result in arrays_with_data[:10]:  # Показываем первые 10
            logger.info(f"  - {result.serial_number} (last data: {result.last_datapoint})")
        if len(arrays_with_data) > 10:
            logger.info(f"  ... и еще {len(arrays_with_data) - 10} массивов")
        logger.info("")
    
    # Массивы без данных в VM
    if arrays_without_data:
        logger.info(f"Arrays without data in VictoriaMetrics: {len(arrays_without_data)}")
        for result in arrays_without_data:
            logger.info(f"  - {result.serial_number} ({result.archive_name})")
        logger.info("")
    
    # Ошибки
    failed_results = [r for r in stats.results if r.status == "failed"]
    if failed_results:
        logger.info(f"Failed imports: {len(failed_results)}")
        for result in failed_results:
            logger.info(f"  - {result.archive_name}")
            if result.error_message:
                logger.info(f"    Error: {result.error_message}")
        logger.info("")
    
    # Общее количество метрик
    total_metrics = sum(r.metrics_sent for r in stats.results)
    if total_metrics > 0:
        logger.info(f"Total metrics sent: {total_metrics:,}")
        logger.info("")
    
    logger.info(f"Details in log: {log_filename}")
    logger.info("="*80)


def main():
    """Главная функция."""
    global logger
    
    # Настройка обработчика сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Парсинг аргументов
    parser = argparse.ArgumentParser(
        description="Batch Import для массового импорта Huawei Performance логов в VictoriaMetrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:

  # Базовый запуск (импорт всех архивов)
  %(prog)s /data/vtb_hc/perf/
  
  # С пропуском уже импортированных
  %(prog)s /data/vtb_hc/perf/ --skip-existing
  
  # Dry-run (без реального импорта)
  %(prog)s /data/vtb_hc/perf/ --dry-run
  
  # С кастомным VM URL
  %(prog)s /data/vtb_hc/perf/ --vm-url http://10.5.10.163:8428
        """
    )
    
    parser.add_argument(
        'log_dir',
        type=str,
        default='/data/vtb_hc/perf/',
        nargs='?',
        help='Директория с ZIP архивами (default: /data/vtb_hc/perf/)'
    )
    parser.add_argument(
        '--vm-url',
        type=str,
        default='http://localhost:8428',
        help='URL VictoriaMetrics (default: http://localhost:8428)'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Пропускать архивы, данные которых уже есть в VM'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Режим без реального импорта (только анализ)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Количество параллельных workers для streaming pipeline (не используется в текущей версии)'
    )
    
    args = parser.parse_args()
    
    # Настройка логирования
    logger, log_filename = setup_logging()
    
    logger.info("="*80)
    logger.info("🚀 BATCH IMPORT STARTED")
    logger.info("="*80)
    logger.info(f"Log directory: {args.log_dir}")
    logger.info(f"VM URL: {args.vm_url}")
    logger.info(f"Skip existing: {args.skip_existing}")
    logger.info(f"Dry-run: {args.dry_run}")
    logger.info("="*80)
    logger.info("")
    
    # Проверка директории
    log_dir_path = Path(args.log_dir)
    if not log_dir_path.exists():
        logger.error(f"❌ Директория не найдена: {log_dir_path}")
        sys.exit(1)
    
    # Инициализация VM клиента
    vm_client = None
    if VM_CLIENT_AVAILABLE:
        try:
            vm_client = VictoriaMetricsClient(vm_url=args.vm_url)
            if vm_client.check_availability():
                logger.info("✅ VictoriaMetrics доступна")
            else:
                logger.warning("⚠️  VictoriaMetrics недоступна, проверка данных будет пропущена")
                vm_client = None
        except Exception as e:
            logger.warning(f"⚠️  Не удалось инициализировать VM клиент: {e}")
            vm_client = None
    else:
        logger.warning("⚠️  VictoriaMetricsClient не доступен, проверка данных будет пропущена")
    
    # Поиск архивов (.zip и .7z) - рекурсивно во всех поддиректориях
    logger.info("🔍 Поиск архивов (.zip, .7z)...")
    
    # Рекурсивный поиск всех поддерживаемых форматов
    archive_files = []
    archive_files.extend(log_dir_path.rglob("*.zip"))
    archive_files.extend(log_dir_path.rglob("*.7z"))
    
    # Сортируем по имени для предсказуемого порядка
    archive_files = sorted(archive_files, key=lambda x: x.name)
    
    if not archive_files:
        logger.error(f"❌ Архивы (.zip, .7z) не найдены в {log_dir_path}")
        sys.exit(1)
    
    # Статистика по типам архивов
    zip_count = sum(1 for f in archive_files if f.suffix.lower() == '.zip')
    sevenz_count = sum(1 for f in archive_files if f.suffix.lower() == '.7z')
    
    logger.info(f"✅ Найдено {len(archive_files)} архивов:")
    if zip_count > 0:
        logger.info(f"   - ZIP: {zip_count}")
    if sevenz_count > 0:
        logger.info(f"   - 7z:  {sevenz_count}")
        if not PY7ZR_AVAILABLE:
            logger.warning("⚠️  py7zr не установлен! .7z файлы будут пропущены")
            logger.warning("   Установите: pip install py7zr")
            archive_files = [f for f in archive_files if f.suffix.lower() != '.7z']
    logger.info("")
    
    # Инициализация статистики
    stats = BatchStats(total_archives=len(archive_files))
    start_time = time.time()
    
    # Обработка архивов
    for idx, archive_file in enumerate(archive_files, 1):
        if INTERRUPTED:
            logger.warning("⚠️  Прервано пользователем")
            break
        
        logger.info(f"[{idx}/{len(archive_files)}] Обработка {archive_file.name}...")
        
        try:
            result = process_archive(
                archive_file,
                args.vm_url,
                vm_client,
                args.skip_existing,
                args.dry_run,
                logger
            )
            
            stats.results.append(result)
            stats.processed += 1
            
            if result.status == "success":
                stats.successful += 1
            elif result.status == "failed":
                stats.failed += 1
            elif result.status == "skipped":
                stats.skipped += 1
            
        except Exception as e:
            logger.error(f"❌ Необработанная ошибка при обработке {archive_file.name}: {e}")
            result = ImportResult(
                archive_name=archive_file.name,
                status="failed",
                error_message=str(e)
            )
            stats.results.append(result)
            stats.processed += 1
            stats.failed += 1
        
        logger.info("")
    
    # Финальная статистика
    stats.total_time = time.time() - start_time
    
    # Генерация отчета
    generate_report(stats, log_filename, logger)
    
    # Возвращаем код выхода
    if stats.failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Прервано пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

