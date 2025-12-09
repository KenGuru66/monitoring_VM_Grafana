#!/usr/bin/env python3
"""
PERF WATCHER: Автоматический мониторинг и парсинг Performance Dumps

Мониторит директорию с SFTP dumps и автоматически парсит новые .tgz файлы,
отправляя метрики в VictoriaMetrics.

Особенности:
- Watchdog + polling hybrid для надежности
- Задержка перед обработкой (ждём завершения загрузки по SFTP)
- Проверка стабильности размера файла
- Retry при ошибках
- Удаление файлов после успешной обработки
- Graceful shutdown

Запуск:
    python -m parsers.perf_watcher
    
Или с параметрами:
    python -m parsers.perf_watcher --watch-dir /data/perf-dumps/dumps --vm-url http://localhost:8428
"""

import sys
import os
import re
import time
import signal
import logging
import threading
import tarfile
import shutil
from pathlib import Path
from queue import Queue, Empty
from datetime import datetime
from typing import Optional, Set
from dataclasses import dataclass, field

import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

# Импорт существующих модулей парсинга
try:
    from parsers.streaming_pipeline import (
        stream_prometheus_metrics,
        send_batch_to_vm,
        extract_serial_from_filename,
        BATCH_SIZE as DEFAULT_BATCH_SIZE,
    )
    from parsers.dictionaries import METRIC_NAME_DICT, RESOURCE_NAME_DICT
except ImportError:
    # Запуск напрямую
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from parsers.streaming_pipeline import (
        stream_prometheus_metrics,
        send_batch_to_vm,
        extract_serial_from_filename,
        BATCH_SIZE as DEFAULT_BATCH_SIZE,
    )
    from parsers.dictionaries import METRIC_NAME_DICT, RESOURCE_NAME_DICT

# Конфигурация из переменных окружения
VM_URL = os.getenv("VM_URL", "http://victoriametrics:8428")
VM_IMPORT_URL = os.getenv("VM_IMPORT_URL", f"{VM_URL}/api/v1/import/prometheus")
WATCH_DIR = os.getenv("WATCH_DIR", "/data/perf-dumps/dumps")
FILE_WAIT_SECONDS = int(os.getenv("FILE_WAIT_SECONDS", "30"))
DELETE_AFTER_PROCESS = os.getenv("DELETE_AFTER_PROCESS", "true").lower() == "true"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", str(DEFAULT_BATCH_SIZE)))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
FILE_STABILITY_CHECK_SECONDS = int(os.getenv("FILE_STABILITY_CHECK_SECONDS", "5"))

# Настройка логирования
LOG_DIR = Path("/app/logs") if Path("/app").exists() else Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'perf_watcher.log', mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class FileTask:
    """Задача на обработку файла."""
    path: Path
    added_time: float = field(default_factory=time.time)
    retries: int = 0
    
    @property
    def ready_time(self) -> float:
        """Время когда файл будет готов к обработке."""
        return self.added_time + FILE_WAIT_SECONDS


class TgzFileHandler(FileSystemEventHandler):
    """Обработчик событий файловой системы для .tgz файлов."""
    
    def __init__(self, task_queue: Queue, processing_files: Set[str]):
        super().__init__()
        self.task_queue = task_queue
        self.processing_files = processing_files
    
    def on_created(self, event):
        """Обработка события создания файла."""
        if event.is_directory:
            return
            
        path = Path(event.src_path)
        
        # Проверяем что это .tgz файл с performance данными
        if not path.suffix == '.tgz':
            return
        if not path.name.startswith('PerfData_'):
            return
            
        # Проверяем что файл не в обработке
        if str(path) in self.processing_files:
            return
            
        logger.info(f"📥 Обнаружен новый файл: {path.name}")
        self.task_queue.put(FileTask(path=path))


class PerfWatcher:
    """
    Основной класс watcher сервиса.
    
    Мониторит директорию и обрабатывает новые .tgz файлы.
    """
    
    def __init__(
        self,
        watch_dir: str = WATCH_DIR,
        vm_import_url: str = VM_IMPORT_URL,
        batch_size: int = BATCH_SIZE,
        delete_after_process: bool = DELETE_AFTER_PROCESS,
        max_retries: int = MAX_RETRIES,
    ):
        self.watch_dir = Path(watch_dir)
        self.vm_import_url = vm_import_url
        self.batch_size = batch_size
        self.delete_after_process = delete_after_process
        self.max_retries = max_retries
        
        # Очередь задач на обработку
        self.task_queue: Queue[FileTask] = Queue()
        
        # Файлы в процессе обработки (для избежания дублей)
        self.processing_files: Set[str] = set()
        
        # Обработанные файлы в текущей сессии (для статистики)
        self.processed_count = 0
        self.failed_count = 0
        self.total_metrics_sent = 0
        
        # Флаг для graceful shutdown
        self.shutdown_event = threading.Event()
        
        # Watchdog observer
        self.observer: Optional[Observer] = None
        
        # Все известные ресурсы и метрики
        self.resources = list(RESOURCE_NAME_DICT.keys())
        self.metrics = list(METRIC_NAME_DICT.keys())
        
        logger.info(f"📊 Загружено {len(self.metrics)} метрик, {len(self.resources)} ресурсов")
    
    def start(self):
        """Запуск watcher сервиса."""
        logger.info("=" * 80)
        logger.info("🚀 PERF WATCHER STARTED")
        logger.info("=" * 80)
        logger.info(f"Watch directory:  {self.watch_dir}")
        logger.info(f"VM Import URL:    {self.vm_import_url}")
        logger.info(f"File wait time:   {FILE_WAIT_SECONDS}s")
        logger.info(f"Delete after:     {self.delete_after_process}")
        logger.info(f"Batch size:       {self.batch_size:,}")
        logger.info(f"Max retries:      {self.max_retries}")
        logger.info("=" * 80)
        
        # Проверяем доступность VictoriaMetrics
        if not self._check_vm_health():
            logger.error("❌ VictoriaMetrics недоступен!")
            return False
        
        # Проверяем существование директории
        if not self.watch_dir.exists():
            logger.error(f"❌ Директория не существует: {self.watch_dir}")
            return False
        
        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Сканируем существующие файлы
        self._scan_existing_files()
        
        # Запускаем watchdog
        self._start_watchdog()
        
        # Запускаем worker для обработки очереди
        worker_thread = threading.Thread(target=self._process_queue_worker, daemon=True)
        worker_thread.start()
        
        # Запускаем периодическое сканирование (backup для watchdog)
        poll_thread = threading.Thread(target=self._poll_worker, daemon=True)
        poll_thread.start()
        
        # Основной цикл (ждём shutdown)
        try:
            while not self.shutdown_event.is_set():
                self.shutdown_event.wait(timeout=1.0)
        except KeyboardInterrupt:
            pass
        
        self._shutdown()
        return True
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown."""
        sig_name = signal.Signals(signum).name
        logger.info(f"⚠️  Получен сигнал {sig_name}, завершение работы...")
        self.shutdown_event.set()
    
    def _check_vm_health(self) -> bool:
        """Проверка доступности VictoriaMetrics."""
        try:
            # Извлекаем base URL из import URL
            base_url = self.vm_import_url.rsplit('/api/', 1)[0]
            response = requests.get(f"{base_url}/-/healthy", timeout=5)
            if response.status_code == 200:
                logger.info("✅ VictoriaMetrics доступен")
                return True
        except Exception as e:
            logger.warning(f"⚠️  Не удалось проверить VM health: {e}")
        
        # Пробуем отправить тестовую метрику
        try:
            test_metric = 'perf_watcher_health{status="ok"} 1\n'
            response = requests.post(self.vm_import_url, data=test_metric.encode(), timeout=5)
            if response.status_code in (200, 204):
                logger.info("✅ VictoriaMetrics доступен (проверка через import)")
                return True
        except Exception as e:
            logger.error(f"❌ VictoriaMetrics недоступен: {e}")
        
        return False
    
    def _scan_existing_files(self):
        """Сканирование существующих .tgz файлов при старте."""
        logger.info("🔍 Сканирование существующих файлов...")
        
        # Находим все .tgz файлы рекурсивно
        tgz_files = list(self.watch_dir.rglob("PerfData_*.tgz"))
        
        if not tgz_files:
            logger.info("📁 Новых файлов не найдено")
            return
        
        # Сортируем по времени модификации (старые первыми)
        tgz_files.sort(key=lambda f: f.stat().st_mtime)
        
        logger.info(f"📁 Найдено {len(tgz_files)} файлов для обработки")
        
        # Добавляем в очередь с нулевой задержкой (файлы уже загружены)
        for tgz_file in tgz_files:
            task = FileTask(path=tgz_file, added_time=0)  # Сразу готов к обработке
            self.task_queue.put(task)
    
    def _start_watchdog(self):
        """Запуск watchdog observer."""
        event_handler = TgzFileHandler(self.task_queue, self.processing_files)
        
        self.observer = Observer()
        # Рекурсивное наблюдение за всеми подпапками
        self.observer.schedule(event_handler, str(self.watch_dir), recursive=True)
        self.observer.start()
        
        logger.info(f"👁️  Watchdog запущен для {self.watch_dir}")
    
    def _poll_worker(self):
        """Периодическое сканирование директории (backup для watchdog)."""
        while not self.shutdown_event.is_set():
            self.shutdown_event.wait(timeout=POLL_INTERVAL_SECONDS)
            
            if self.shutdown_event.is_set():
                break
            
            # Сканируем директорию
            try:
                tgz_files = list(self.watch_dir.rglob("PerfData_*.tgz"))
                
                for tgz_file in tgz_files:
                    # Пропускаем файлы в обработке
                    if str(tgz_file) in self.processing_files:
                        continue
                    
                    # Проверяем не добавлен ли уже в очередь
                    # (простая проверка через processing_files)
                    task = FileTask(path=tgz_file, added_time=0)
                    self.task_queue.put(task)
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при сканировании: {e}")
    
    def _process_queue_worker(self):
        """Worker для обработки очереди файлов."""
        while not self.shutdown_event.is_set():
            try:
                # Получаем задачу из очереди с таймаутом
                task = self.task_queue.get(timeout=1.0)
            except Empty:
                continue
            
            # Проверяем shutdown
            if self.shutdown_event.is_set():
                # Возвращаем задачу в очередь (будет обработана при следующем запуске)
                self.task_queue.put(task)
                break
            
            # Проверяем файл не в обработке
            if str(task.path) in self.processing_files:
                continue
            
            # Ждём готовности файла (задержка после появления)
            wait_time = task.ready_time - time.time()
            if wait_time > 0:
                logger.debug(f"⏳ Ожидание {wait_time:.1f}s для {task.path.name}")
                # Возвращаем в очередь и ждём
                self.task_queue.put(task)
                time.sleep(min(wait_time, 5.0))  # Не ждём слишком долго за раз
                continue
            
            # Проверяем что файл существует
            if not task.path.exists():
                logger.warning(f"⚠️  Файл не существует: {task.path}")
                continue
            
            # Проверяем стабильность размера файла
            if not self._check_file_stability(task.path):
                logger.debug(f"⏳ Файл ещё загружается: {task.path.name}")
                task.added_time = time.time()  # Сбрасываем таймер
                self.task_queue.put(task)
                continue
            
            # Обрабатываем файл
            self.processing_files.add(str(task.path))
            
            try:
                success = self._process_file(task.path)
                
                if success:
                    self.processed_count += 1
                    
                    if self.delete_after_process:
                        try:
                            task.path.unlink()
                            logger.info(f"🗑️  Удалён: {task.path.name}")
                        except Exception as e:
                            logger.error(f"❌ Не удалось удалить {task.path}: {e}")
                else:
                    # Retry
                    task.retries += 1
                    if task.retries < self.max_retries:
                        logger.warning(f"⚠️  Retry {task.retries}/{self.max_retries} для {task.path.name}")
                        task.added_time = time.time()  # Добавляем задержку перед retry
                        self.task_queue.put(task)
                    else:
                        logger.error(f"❌ Превышено количество попыток для {task.path.name}")
                        self.failed_count += 1
                        
            finally:
                self.processing_files.discard(str(task.path))
    
    def _check_file_stability(self, path: Path) -> bool:
        """Проверка что размер файла не меняется (загрузка завершена)."""
        try:
            size1 = path.stat().st_size
            time.sleep(FILE_STABILITY_CHECK_SECONDS)
            size2 = path.stat().st_size
            return size1 == size2 and size1 > 0
        except Exception:
            return False
    
    def _process_file(self, tgz_path: Path) -> bool:
        """
        Обработка одного .tgz файла.
        
        Returns:
            True если обработка успешна, False при ошибке
        """
        logger.info(f"⚙️  Обработка: {tgz_path.name}")
        start_time = time.time()
        
        # Создаём временную директорию для распаковки
        temp_dir = Path(f"/tmp/perf_watcher_{os.getpid()}_{time.time()}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Извлекаем серийный номер из имени файла
            array_sn = extract_serial_from_filename(tgz_path.name)
            
            # Распаковываем .tgz
            dat_file = self._extract_tgz(tgz_path, temp_dir)
            if not dat_file:
                logger.error(f"❌ Не удалось распаковать {tgz_path.name}")
                return False
            
            # Парсим и отправляем метрики
            metrics_sent = 0
            batches_sent = 0
            batch = []
            
            for metric_line in stream_prometheus_metrics(
                dat_file, array_sn, self.resources, self.metrics
            ):
                batch.append(metric_line)
                
                if len(batch) >= self.batch_size:
                    if send_batch_to_vm(batch, self.vm_import_url):
                        metrics_sent += len(batch)
                        batches_sent += 1
                        batch = []
                    else:
                        logger.error(f"❌ Ошибка отправки batch в VM")
                        return False
            
            # Отправляем остаток
            if batch:
                if send_batch_to_vm(batch, self.vm_import_url):
                    metrics_sent += len(batch)
                    batches_sent += 1
                else:
                    logger.error(f"❌ Ошибка отправки последнего batch в VM")
                    return False
            
            elapsed = time.time() - start_time
            rate = metrics_sent / elapsed if elapsed > 0 else 0
            
            self.total_metrics_sent += metrics_sent
            
            logger.info(
                f"✅ {tgz_path.name}: {metrics_sent:,} метрик за {elapsed:.1f}s "
                f"({rate:,.0f} m/s) | SN: {array_sn}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки {tgz_path.name}: {e}", exc_info=True)
            return False
            
        finally:
            # Cleanup временной директории
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"⚠️  Не удалось удалить temp dir: {e}")
    
    def _extract_tgz(self, tgz_path: Path, temp_dir: Path) -> Optional[Path]:
        """
        Распаковка .tgz файла.
        
        Returns:
            Path к .dat файлу или None при ошибке
        """
        try:
            with tarfile.open(tgz_path, 'r:gz') as tar:
                names = tar.getnames()
                
                if len(names) != 1:
                    logger.warning(f"⚠️  Неожиданное количество файлов в архиве: {len(names)}")
                
                # Извлекаем первый файл (обычно .dat)
                tar.extractall(temp_dir)
                
                # Находим .dat файл
                dat_files = list(temp_dir.glob("*.dat"))
                if dat_files:
                    return dat_files[0]
                
                # Если нет .dat, возвращаем первый извлечённый файл
                extracted = temp_dir / names[0]
                if extracted.exists():
                    return extracted
                    
        except Exception as e:
            logger.error(f"❌ Ошибка распаковки {tgz_path}: {e}")
        
        return None
    
    def _shutdown(self):
        """Graceful shutdown."""
        logger.info("🛑 Завершение работы...")
        
        # Останавливаем watchdog
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5.0)
        
        # Выводим статистику
        logger.info("=" * 80)
        logger.info("📊 ИТОГОВАЯ СТАТИСТИКА")
        logger.info("=" * 80)
        logger.info(f"Обработано файлов:  {self.processed_count}")
        logger.info(f"Ошибок:             {self.failed_count}")
        logger.info(f"Метрик отправлено:  {self.total_metrics_sent:,}")
        logger.info(f"В очереди:          {self.task_queue.qsize()}")
        logger.info("=" * 80)
        logger.info("👋 Perf Watcher завершён")


def main():
    """Точка входа."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Perf Watcher: автоматический парсинг Performance Dumps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Переменные окружения:
  VM_URL                    VictoriaMetrics URL (default: http://victoriametrics:8428)
  WATCH_DIR                 Директория для мониторинга (default: /data/perf-dumps/dumps)
  FILE_WAIT_SECONDS         Задержка перед обработкой (default: 30)
  DELETE_AFTER_PROCESS      Удалять файлы после обработки (default: true)
  BATCH_SIZE                Размер батча метрик (default: 100000)
  MAX_RETRIES               Количество попыток при ошибке (default: 3)

Примеры:
  # Запуск с настройками по умолчанию
  python -m parsers.perf_watcher
  
  # Запуск с указанием директории
  python -m parsers.perf_watcher --watch-dir /data/perf-dumps/dumps
  
  # Запуск без удаления файлов
  python -m parsers.perf_watcher --no-delete
        """
    )
    
    parser.add_argument(
        '--watch-dir', '-w',
        type=str,
        default=WATCH_DIR,
        help=f'Директория для мониторинга (default: {WATCH_DIR})'
    )
    parser.add_argument(
        '--vm-url',
        type=str,
        default=VM_URL,
        help=f'VictoriaMetrics URL (default: {VM_URL})'
    )
    parser.add_argument(
        '--no-delete',
        action='store_true',
        help='Не удалять файлы после обработки'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=BATCH_SIZE,
        help=f'Размер батча метрик (default: {BATCH_SIZE})'
    )
    
    args = parser.parse_args()
    
    # Формируем VM import URL
    vm_import_url = f"{args.vm_url}/api/v1/import/prometheus"
    
    # Создаём и запускаем watcher
    watcher = PerfWatcher(
        watch_dir=args.watch_dir,
        vm_import_url=vm_import_url,
        batch_size=args.batch_size,
        delete_after_process=not args.no_delete,
    )
    
    success = watcher.start()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

