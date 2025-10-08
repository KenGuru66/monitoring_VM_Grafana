# Huawei Performance Data Parser (Wide Format)

## Описание

`perf_zip2csv_wide.py` - скрипт для парсинга архивов производительности Huawei storage в формат CSV с широкой структурой (wide format), совместимый с perfmonkey.

## Формат данных

### Wide Format (одна строка на timestamp)

Скрипт создаёт отдельные CSV файлы для каждого типа ресурса:

- `cpu_output.csv` - Controller/CPU метрики
- `disk_output.csv` - Disk/RAID Group метрики  
- `lun_output.csv` - LUN метрики
- `host_output.csv` - Host метрики
- `fcp_output.csv` - FC Port метрики
- `pool_output.csv` - Storage Pool метрики

Каждая строка содержит все метрики для конкретного элемента в конкретный момент времени.

### Структура строки

```
PREFIX,#,BgnDateTime,EndDateTime,Serial,<MetaFields...>,<Metrics...>
```

Например для CPU:
```
CPUPERF,1,09/25/25 00:05:00,09/25/25 00:05:00,111111,0B,'CPU',70,22,0,1268,1,604,...
```

## Использование

### Базовое использование

```bash
python3 perf_zip2csv_wide.py <archive.zip> -o <output_dir>
```

### Примеры

```bash
# Обработка ZIP архива
python3 perf_zip2csv_wide.py Storage_History_Performance_Files.zip -o output/

# Обработка директории с .tgz файлами
python3 perf_zip2csv_wide.py /path/to/tgz_dir -o output/

# Указать количество воркеров (по умолчанию CPU_COUNT - 2)
python3 perf_zip2csv_wide.py archive.zip -o output/ --workers 16

# Включить детальное логирование
python3 perf_zip2csv_wide.py archive.zip -o output/ --verbose
```

## Параметры

- `archive` - Путь к ZIP архиву или директории с .tgz файлами (обязательный)
- `-o, --output` - Директория для сохранения CSV файлов (обязательный)
- `--workers N` - Количество параллельных процессов (по умолчанию: CPU_COUNT - 2)
- `--verbose` - Детальное логирование

## Производительность

- Многопоточная обработка с ProcessPoolExecutor
- Streaming запись в файлы (минимальное использование памяти)
- Производительность: ~60,000+ строк/сек на 8 ядрах

Пример производительности:
```
Processing 276 .tgz files (689,949 rows total)
Time: 10.6 seconds
Throughput: 65,231 rows/sec
Workers: 8
```

## Требования

- Python 3.6+
- Модули: pathlib, tqdm, multiprocessing, concurrent.futures
- Data2csv/METRIC_DICT.py и Data2csv/RESOURCE_DICT.py

## Особенности

1. **Автоопределение Serial Number** - извлекается из имени .tgz файла
2. **Wide Format** - все метрики в одной строке (удобно для импорта)
3. **CSV совместимость** - запятые внутри скобок заменяются на подчёркивания:
   - `[0K,4K)` → `[0K_4K)`
   - `[128K,+∞)` → `[128K_+8)`
4. **Префиксы** по типам ресурсов:
   - CPUPERF - Controller
   - RGPERF - RAID Group (Disk)
   - LDEVPERF - LUN
   - HAPERF - Host
   - PORTPERF - FC Port
   - POOLPERF - Storage Pool

## Метрики

Скрипт извлекает следующие метрики для каждого типа ресурса:

### Controller (CPU)
- Cache hit ratios, CPU usage, Queue length
- Bandwidth, IOPS (Total/Read/Write)
- I/O size, I/O granularity distribution
- Response times

### Disk (RAID Group)
- Usage, Bandwidth, IOPS
- I/O size, I/O granularity distribution
- Response times

### LUN
- Bandwidth, IOPS, Queue length
- I/O size, I/O granularity distribution
- Response times, Cache hit ratios

### Host
- Bandwidth, IOPS
- I/O size, I/O granularity distribution
- Response times

### FC Port
- Usage, Bandwidth, IOPS
- I/O granularity distribution
- Replication bandwidth, Link latency

### Storage Pool
- Deduplication/Compression ratios
- Disk usage, Bandwidth, IOPS
- Back-end traffic, Response times

## Формат даты

Даты в формате: `MM/DD/YY HH:MM:SS`

Пример: `09/25/25 00:05:00`

## Troubleshooting

### Проблема: Скрипт завис
- Проверьте доступную память
- Уменьшите количество workers: `--workers 2`

### Проблема: Неправильный формат CSV
- Убедитесь, что используете актуальные METRIC_DICT.py и RESOURCE_DICT.py
- Проверьте кодировку входных файлов

### Проблема: Пустые файлы
- Проверьте, что в .tgz файлах есть данные для этих ресурсов
- Посмотрите логи: `--verbose`

## Сравнение с perf_zip2csv.py (Long Format)

| Параметр | Long Format | Wide Format |
|----------|-------------|-------------|
| Строк на timestamp | N (по числу метрик) | 1 |
| Размер файла | Больше | Меньше |
| Импорт в БД | Проще | Требует парсинга |
| Читаемость | Хуже | Лучше |
| Совместимость | Custom | Perfmonkey |

## Примеры вывода

### CPU Output
```csv
CPUPERF,#,BgnDateTime,EndDateTime,Serial,Slot,Type,Read cache hit ratio (%),Write cache hit ratio (%),...
CPUPERF,1,09/25/25 00:05:00,09/25/25 00:05:00,111111,0B,'CPU',70,22,0,1268,1,604,5348,...
```

### LUN Output
```csv
LDEVPERF,#,BgnDateTime,EndDateTime,Serial,DefMp,DaCnt,Rg,Ld,Alias,Max. bandwidth (MB/s),...
LDEVPERF,1,09/25/25 00:05:00,09/25/25 00:05:00,111111,'?','1','01-01',prd.zvirt.01,'-',12,0,6,...
```

## Лицензия

Based on Huawei_perf_parser_v0.2_parallel.py

## Автор

Modified for wide format output compatible with perfmonkey

