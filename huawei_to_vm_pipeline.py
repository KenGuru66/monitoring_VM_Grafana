#!/usr/bin/env python3
"""
Полный автоматический pipeline обработки Huawei Performance Data.

Выполняет:
1. Парсинг .tgz файлов из ZIP архива в CSV (параллельно)
2. Импорт CSV в VictoriaMetrics (параллельно)
3. Опциональная очистка промежуточных CSV файлов

Использование:
    python3 huawei_to_vm_pipeline.py -i "Data2csv/logs/archive.zip"
"""

import argparse
import subprocess
import sys
import os
import pathlib
import logging
import time
from datetime import datetime
import glob

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log', mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_command(cmd, description):
    """Выполняет команду и логирует результат."""
    logger.info(f"{'='*80}")
    logger.info(f"🚀 {description}")
    logger.info(f"Command: {' '.join(cmd)}")
    logger.info(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - start_time
        
        logger.info(f"✅ {description} - УСПЕШНО")
        logger.info(f"⏱️  Время выполнения: {elapsed:.1f} секунд")
        
        # Логируем последние строки вывода
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            logger.info("📊 Вывод (последние 10 строк):")
            for line in lines[-10:]:
                logger.info(f"   {line}")
        
        return True, elapsed
        
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ {description} - ОШИБКА")
        logger.error(f"⏱️  Время до ошибки: {elapsed:.1f} секунд")
        logger.error(f"Код возврата: {e.returncode}")
        if e.stdout:
            logger.error(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        return False, elapsed

def main():
    parser = argparse.ArgumentParser(
        description="Полный pipeline: Huawei Performance Data → VictoriaMetrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Базовый запуск
  %(prog)s -i "Data2csv/logs/Storage_History_Performance_Files.zip"
  
  # С сохранением CSV файлов
  %(prog)s -i "Data2csv/logs/archive.zip" --keep-csv
  
  # С настройкой количества workers
  %(prog)s -i "Data2csv/logs/archive.zip" --workers 6
  
  # С указанием URL VictoriaMetrics
  %(prog)s -i "Data2csv/logs/archive.zip" --vm-url "http://victoriametrics:8428/api/v1/import/prometheus"

Pipeline выполняет:
  1. Парсинг .tgz → CSV (параллельно, 7 workers)
  2. Импорт CSV → VictoriaMetrics (параллельно, 7 workers)
  3. Очистка временных файлов (опционально)
        """)
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        required=True,
        help='Путь к входному ZIP архиву с .tgz файлами'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='Data2csv/output',
        help='Директория для промежуточных CSV файлов (default: Data2csv/output)'
    )
    
    parser.add_argument(
        '--vm-url',
        type=str,
        default='http://localhost:8428/api/v1/import/prometheus',
        help='URL endpoint VictoriaMetrics для импорта (default: localhost:8428)'
    )
    
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=None,
        help='Количество worker процессов (default: CPU count - 1)'
    )
    
    parser.add_argument(
        '--keep-csv',
        action='store_true',
        default=False,
        help='Не удалять CSV файлы после импорта'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50000,
        help='Размер батча для импорта (default: 50000)'
    )
    
    args = parser.parse_args()
    
    # Проверяем существование входного файла
    input_path = pathlib.Path(args.input)
    if not input_path.exists():
        logger.error(f"❌ Входной файл не найден: {args.input}")
        sys.exit(1)
    
    # Начало pipeline
    logger.info("╔" + "═"*78 + "╗")
    logger.info("║" + " "*78 + "║")
    logger.info("║" + "  HUAWEI PERFORMANCE DATA → VICTORIAMETRICS PIPELINE".center(78) + "║")
    logger.info("║" + " "*78 + "║")
    logger.info("╚" + "═"*78 + "╝")
    logger.info("")
    logger.info(f"📅 Дата запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📁 Входной файл: {args.input}")
    logger.info(f"📂 Выходная директория: {args.output_dir}")
    logger.info(f"🌐 VictoriaMetrics URL: {args.vm_url}")
    logger.info(f"👷 Workers: {args.workers if args.workers else 'auto (CPU-1)'}")
    logger.info("")
    
    pipeline_start = time.time()
    
    # ========================================================================
    # ЭТАП 1: ПАРСИНГ
    # ========================================================================
    
    parse_cmd = [
        'python3',
        'Data2csv/Huawei_perf_parser_v0.2_parallel.py',
        '-i', str(input_path),
        '-o', args.output_dir
    ]
    
    if args.workers:
        parse_cmd.extend(['-w', str(args.workers)])
    
    success, parse_time = run_command(parse_cmd, "ЭТАП 1: Парсинг .tgz файлов в CSV")
    
    if not success:
        logger.error("❌ Pipeline прерван из-за ошибки парсинга")
        sys.exit(1)
    
    # Ищем созданные CSV файлы
    csv_files = glob.glob(os.path.join(args.output_dir, '*.csv'))
    
    if not csv_files:
        logger.error(f"❌ CSV файлы не найдены в {args.output_dir}")
        sys.exit(1)
    
    logger.info("")
    logger.info(f"✅ Найдено CSV файлов: {len(csv_files)}")
    for csv_file in csv_files:
        size = os.path.getsize(csv_file) / (1024**3)  # GB
        logger.info(f"   📄 {os.path.basename(csv_file)} ({size:.2f} GB)")
    logger.info("")
    
    # ========================================================================
    # ЭТАП 2: ИМПОРТ В VICTORIAMETRICS
    # ========================================================================
    
    total_import_time = 0
    
    for idx, csv_file in enumerate(csv_files, 1):
        import_cmd = [
            'python3',
            'csv2vm_parallel.py',
            csv_file,
            '--url', args.vm_url,
            '--batch', str(args.batch_size)
        ]
        
        if args.workers:
            import_cmd.extend(['--workers', str(args.workers)])
        
        description = f"ЭТАП 2.{idx}: Импорт {os.path.basename(csv_file)} в VictoriaMetrics"
        success, import_time = run_command(import_cmd, description)
        
        if not success:
            logger.error("❌ Pipeline прерван из-за ошибки импорта")
            if not args.keep_csv:
                logger.info("⚠️  CSV файлы сохранены для отладки")
            sys.exit(1)
        
        total_import_time += import_time
    
    # ========================================================================
    # ЭТАП 3: ОЧИСТКА (опционально)
    # ========================================================================
    
    if not args.keep_csv:
        logger.info("")
        logger.info("="*80)
        logger.info("🧹 ЭТАП 3: Очистка промежуточных CSV файлов")
        logger.info("="*80)
        
        for csv_file in csv_files:
            try:
                os.remove(csv_file)
                logger.info(f"   ✅ Удалён: {os.path.basename(csv_file)}")
            except Exception as e:
                logger.warning(f"   ⚠️  Не удалось удалить {csv_file}: {e}")
        
        logger.info("✅ Очистка завершена")
    else:
        logger.info("")
        logger.info("ℹ️  CSV файлы сохранены (--keep-csv)")
    
    # ========================================================================
    # ИТОГИ
    # ========================================================================
    
    total_time = time.time() - pipeline_start
    
    logger.info("")
    logger.info("╔" + "═"*78 + "╗")
    logger.info("║" + " "*78 + "║")
    logger.info("║" + "  ✅ PIPELINE ЗАВЕРШЁН УСПЕШНО!".center(78) + "║")
    logger.info("║" + " "*78 + "║")
    logger.info("╚" + "═"*78 + "╝")
    logger.info("")
    logger.info("📊 СТАТИСТИКА:")
    logger.info(f"   📈 Этап 1 (Парсинг):  {parse_time:.1f} сек")
    logger.info(f"   📈 Этап 2 (Импорт):   {total_import_time:.1f} сек")
    logger.info(f"   ⏱️  Общее время:      {total_time:.1f} сек ({total_time/60:.1f} мин)")
    logger.info(f"   📁 CSV файлов:        {len(csv_files)}")
    logger.info(f"   💾 Хранение CSV:      {'Да' if args.keep_csv else 'Нет (удалены)'}")
    logger.info("")
    logger.info(f"🎯 Данные импортированы в VictoriaMetrics: {args.vm_url.replace('/api/v1/import/prometheus', '')}")
    logger.info("")
    logger.info("="*80)
    
    print("\n✅ Pipeline выполнен успешно!")
    print(f"⏱️  Время: {total_time:.1f} сек ({total_time/60:.1f} мин)")
    print(f"📊 Проверить данные: curl {args.vm_url.replace('/api/v1/import/prometheus', '/api/v1/status/tsdb')}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Pipeline прерван пользователем (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

