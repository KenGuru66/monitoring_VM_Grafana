# perf_zip2csv.py - Huawei Performance Archive to CSV Converter

Утилита для преобразования архивов производительности Huawei Storage в отдельные CSV файлы по типам ресурсов.

## ✨ Особенности

- ✅ Автоматическая распаковка `.zip` → `.tgz` → `.dat`
- ✅ Парсинг бинарных файлов производительности Huawei
- ✅ Генерация отдельных CSV для каждого типа ресурса
- ✅ Параллельная обработка файлов (threading)
- ✅ Progress bar с `tqdm`
- ✅ Минимальные зависимости

## 📦 Установка

```bash
# Установка зависимостей
pip install pandas tqdm

# Для тестов (опционально)
pip install pytest
```

## 🚀 Использование

### Базовое использование

```bash
python perf_zip2csv.py Storage_History_Performance_Files.zip -o output/
```

### С параллельной обработкой

```bash
python perf_zip2csv.py archive.zip -o csvs/ --workers 8
```

### С подробным логированием

```bash
python perf_zip2csv.py archive.zip -o csvs/ --verbose
```

### Обработка директории с .tgz файлами

```bash
python perf_zip2csv.py /path/to/tgz_dir/ -o csvs/
```

## 📊 Выходные файлы

Скрипт создаёт отдельные CSV файлы для каждого типа ресурса:

```
output/
├── cpu_output.csv       # Controller/CPU метрики
├── disk_output.csv      # Disk метрики (RAID groups)
├── lun_output.csv       # LUN метрики
├── host_output.csv      # Host метрики
├── fcp_output.csv       # FC Port метрики
└── pool_output.csv      # Storage Pool метрики
```

### Формат CSV

```csv
Resource;Metric;Element;Value;Time;UnixTime
Controller;Avg. CPU usage (%);0B;26;2025-09-25T00:05:00Z;1727222700
Controller;Read cache hit ratio (%);0B;70;2025-09-25T00:05:00Z;1727222700
Disk;Total IOPS (IO/s);CTE0.1;12157;2025-09-25T00:05:00Z;1727222700
```

**Колонки:**
- `Resource` - Тип ресурса (Controller, Disk, LUN, Host, FC Port, Pool)
- `Metric` - Название метрики
- `Element` - Имя элемента/устройства
- `Value` - Значение метрики
- `Time` - Временная метка ISO 8601
- `UnixTime` - Unix timestamp

## 📝 Пример вывода

```
2025-10-08 15:52:34,849 - INFO - Processing: Storage_History_Performance_Files.zip
2025-10-08 15:52:34,849 - INFO - Output dir: output_csvs
2025-10-08 15:52:34,849 - INFO - Workers: 4
2025-10-08 15:52:34,849 - INFO - Extracting .tgz files from ZIP...
2025-10-08 15:52:34,921 - INFO - Found 276 .tgz files
2025-10-08 15:52:34,921 - INFO - Parsing performance data...
Processing: 100%|████████████████████| 276/276 [05:23<00:00, 0.85file/s]
2025-10-08 15:57:58,124 - INFO - Merging results...
2025-10-08 15:57:58,234 - INFO - Writing CSV files...
2025-10-08 15:57:59,456 - INFO - ✓ cpu_output.csv: 1,024,000 rows (Controller)
2025-10-08 15:58:01,123 - INFO - ✓ disk_output.csv: 512,000 rows (Disk)
2025-10-08 15:58:02,789 - INFO - ✓ lun_output.csv: 256,000 rows (LUN)
2025-10-08 15:58:04,234 - INFO - ✓ host_output.csv: 128,000 rows (Host)
2025-10-08 15:58:05,567 - INFO - ✓ fcp_output.csv: 64,000 rows (FC Port)
2025-10-08 15:58:06,123 - INFO - ✓ pool_output.csv: 32,000 rows (Storage Pool)

================================================================================
SUMMARY
================================================================================
cpu_output.csv                   1,024,000 rows  (Controller)
disk_output.csv                    512,000 rows  (Disk)
fcp_output.csv                      64,000 rows  (FC Port)
host_output.csv                    128,000 rows  (Host)
lun_output.csv                     256,000 rows  (LUN)
pool_output.csv                     32,000 rows  (Storage Pool)
================================================================================
TOTAL                            2,016,000 rows
================================================================================
```

## 🔧 Опции командной строки

```
usage: perf_zip2csv.py [-h] -o OUTPUT [--workers WORKERS] [--verbose] archive

positional arguments:
  archive               Path to .zip archive or directory containing .tgz files

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output directory for CSV files
  --workers WORKERS     Number of parallel workers (default: 4)
  --verbose             Enable verbose logging
```

## 🧪 Тестирование

```bash
# Запуск unit tests
pytest tests/test_parser.py -v

# Быстрый тест на маленьком архиве
python perf_zip2csv.py test_sample.zip -o test_output/ --verbose
```

## 📚 Использование CSV

### В Python/Pandas

```python
import pandas as pd

# Загрузить данные CPU
df_cpu = pd.read_csv('output/cpu_output.csv', sep=';')

# Фильтр по метрике
cpu_usage = df_cpu[df_cpu['Metric'] == 'Avg. CPU usage (%)']

# Конвертировать в datetime
df_cpu['Time'] = pd.to_datetime(df_cpu['Time'])

# Pivot для анализа
pivot = df_cpu.pivot_table(
    values='Value',
    index='Time',
    columns='Element',
    aggfunc='mean'
)
```

### В Excel

1. Открыть CSV в Excel
2. Data → Text to Columns → Delimited → Semicolon
3. Использовать Pivot Tables для анализа

### Импорт в другие системы

CSV файлы готовы для импорта в:
- InfluxDB
- Prometheus + Pushgateway
- TimescaleDB
- Elasticsearch
- Любую TSDB с CSV import

## ⚠️ Важные замечания

1. **Формат данных**: Скрипт использует правильную логику парсинга бинарных файлов Huawei из `Data2csv/` директории
2. **Словари метрик**: Требуется наличие `METRIC_DICT.py` и `RESOURCE_DICT.py` в `Data2csv/`
3. **Память**: Скрипт оптимизирован для минимального использования памяти (streaming)
4. **Временные файлы**: Автоматически удаляются после обработки

## 🐛 Troubleshooting

### Ошибка "Cannot import METRIC_DICT"

```bash
# Проверьте наличие файлов
ls -l Data2csv/METRIC_DICT.py Data2csv/RESOURCE_DICT.py
```

### Медленная обработка

```bash
# Увеличьте количество workers
python perf_zip2csv.py archive.zip -o csvs/ --workers 16
```

### Ошибки парсинга

```bash
# Включите verbose для диагностики
python perf_zip2csv.py archive.zip -o csvs/ --verbose
```

## 📄 Лицензия

Часть проекта Huawei OceanStor Performance Monitoring Pipeline

## 🤝 Связь

По вопросам обращаться к maintainer проекта.



