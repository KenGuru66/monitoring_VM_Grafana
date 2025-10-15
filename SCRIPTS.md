# Описание основных скриптов

## Python скрипты парсинга данных

### 1. huawei_streaming_pipeline.py

**Назначение:** Потоковая обработка архивов Huawei и отправка метрик в VictoriaMetrics.

**Расположение:** `/app/huawei_streaming_pipeline.py`

**Использование:**
```bash
python huawei_streaming_pipeline.py -i <archive.zip> \
  --vm-url http://victoriametrics:8428/api/v1/import/prometheus \
  --batch-size 50000 \
  --all-metrics
```

**Параметры:**
- `-i, --input` - Путь к ZIP архиву с .tgz файлами
- `--vm-url` - URL VictoriaMetrics import endpoint
- `--batch-size` - Размер батча метрик (default: 100000)
- `--workers` - Количество параллельных workers (default: CPU-2)
- `--all-metrics` - Парсить ВСЕ метрики (default: True)

**Особенности:**
- Streaming обработка - минимум памяти
- Прямая отправка в VictoriaMetrics без промежуточных файлов
- Параллельная обработка .tgz файлов
- Оптимизировано для огромных файлов (500GB+)

**Вызывается из:** `api/main.py` → `run_pipeline_sync()` при `target=grafana`

---

### 2. Data2csv/Huawei_perf_parser_v0.2_parallel.py

**Назначение:** Экспорт данных Huawei в CSV формат (Wide format).

**Расположение:** `/app/Data2csv/Huawei_perf_parser_v0.2_parallel.py`

**Использование:**
```bash
python Huawei_perf_parser_v0.2_parallel.py \
  -i /path/to/archive.zip \
  -o /path/to/output/ \
  --all-metrics
```

**Параметры:**
- `-i, --input_path` - Путь к .zip архиву или директории с .tgz
- `-o, --output_path` - Директория для CSV файлов
- `-l, --log_path` - Директория для логов (default: 'log')
- `-d, --is_delete_after_parse` - Удалить исходные файлы после обработки
- `-r, --resources` - Типы ресурсов для сбора (default: ALL)
- `-m, --metrics` - Типы метрик для сбора (default: ALL)
- `-w, --num_workers` - Количество workers (default: CPU-1)
- `--all-metrics` - Парсить ВСЕ метрики и ресурсы

**Выходной формат:**
- Один CSV файл на серийный номер массива: `{SN}.csv`
- Формат: `Resource;Metric;Element;Value;Timestamp;UnixTime`
- Разделитель: точка с запятой (;)

**Вызывается из:** `api/main.py` → `run_csv_parser_sync()` при `target=csv`

---

### 3. perfmonkey/perf_zip2csv_wide.py

**Назначение:** Экспорт данных в формат perfmonkey (wide format).

**Расположение:** `/app/perfmonkey/perf_zip2csv_wide.py`

**Использование:**
```bash
python perf_zip2csv_wide.py <archive.zip> \
  -o <output_dir> \
  --workers 30
```

**Параметры:**
- `archive` - Путь к .zip архиву или директории с .tgz файлами
- `-o, --output` - Директория для CSV файлов
- `--workers` - Количество параллельных workers (default: CPU-2)
- `--verbose` - Подробное логирование

**Выходной формат:**
8 CSV файлов по типам ресурсов:
- `cpu_output.csv.gz` - Controller метрики
- `disk_output.csv.gz` - Disk (RAID Group) метрики
- `lun_output.csv.gz` - LUN метрики
- `host_output.csv.gz` - Host метрики
- `fcp_output.csv.gz` - FC Port метрики
- `pool_output.csv.gz` - Storage Pool метрики
- `disk_domain_output.csv.gz` - Disk Domain метрики
- `fc_repl_link_output.csv.gz` - FC Replication Link метрики

**Формат строки:**
```
PREFIX,#,BgnDateTime,EndDateTime,Serial,Field1,Field2,...,Metric1,Metric2,...
CPUPERF,1,01/14/25 00:00:00,01/14/25 00:00:00,2102354JMX1****00016,'0A','CPU',123,456,...
```

**Особенности:**
- Wide format: одна строка = один timestamp со всеми метриками
- Автоматическая нумерация строк
- Сортировка по времени
- Gzip сжатие выходных файлов

**Вызывается из:** `api/main.py` → `run_perfmonkey_parser_sync()` при `target=perfmonkey`

---

## API Backend (FastAPI)

### api/main.py

**Назначение:** RESTful API для web интерфейса.

**Основные функции:**

#### Upload & Processing
- `POST /api/upload` - Загрузка архива и запуск обработки
- `GET /api/status/{job_id}` - Получение статуса обработки
- `GET /api/jobs` - Список всех jobs

#### VictoriaMetrics Management
- `GET /api/arrays` - Список массивов в VM
- `DELETE /api/arrays/{sn}` - Удаление массива
- `DELETE /api/arrays` - Удаление всех массивов

#### CSV Files Management
- `GET /api/csv-jobs` - Список CSV processing jobs
- `GET /api/files/{job_id}` - Список файлов для job
- `GET /api/file/{job_id}/{filename}` - Download файла
- `DELETE /api/files/{job_id}` - Удаление файлов job

#### Background Tasks
- `run_pipeline_sync()` - Запуск streaming pipeline (Grafana)
- `run_csv_parser_sync()` - Запуск CSV parser (Wide)
- `run_perfmonkey_parser_sync()` - Запуск perfmonkey parser
- `gzip_csv_files()` - Multi-threaded сжатие CSV файлов
- `cleanup_old_jobs()` - Автоматическая очистка старых jobs (24h)

**Конфигурация (environment variables):**
```bash
UPLOAD_DIR=/app/uploads          # Временные загрузки
WORK_DIR=/app/jobs               # Выходные CSV файлы
VM_URL=http://victoriametrics:8428
VM_IMPORT_URL=http://victoriametrics:8428/api/v1/import/prometheus
GRAFANA_URL=http://localhost:3000
MAX_UPLOAD_SIZE=10737418240      # 10GB
JOB_TIMEOUT=86400                # 24 hours
JOB_TTL_HOURS=24                 # Auto-cleanup
```

---

## Словари метрик и ресурсов

### Data2csv/METRIC_DICT.py

Содержит маппинг ID метрик → Человеко-читаемые названия.

**Формат:**
```python
METRIC_NAME_DICT = {
    "18": "Usage (%)",
    "22": "Total IOPS (IO/s)",
    "23": "Read bandwidth (MB/s)",
    ...
}
```

### Data2csv/RESOURCE_DICT.py

Содержит маппинг ID ресурсов → Типы ресурсов.

**Формат:**
```python
RESOURCE_NAME_DICT = {
    "207": "Controller",
    "212": "FC Port",
    "216": "Storage Pool",
    "10": "Disk",
    "11": "LUN",
    "21": "Host",
    ...
}
```

---

## Utility скрипты

### 4. analyze_csv.py

**Назначение:** Анализ CSV файлов - извлечение ресурсов и метрик.

**Использование:**
```bash
python analyze_csv.py <csv_file_path>
```

**Выходные данные:**
- Общее количество строк
- Уникальные ресурсы
- Уникальные метрики
- Sanitized имена метрик (для Prometheus)

**Использование:** Для проверки содержимого CSV и подготовки к сравнению с VictoriaMetrics

---

### 5. check_vm_metrics.py

**Назначение:** Проверка соответствия метрик между CSV и VictoriaMetrics.

**Использование:**
```bash
python check_vm_metrics.py <csv_file_path> <vm_url>
```

**Параметры:**
- `csv_file_path` - Путь к эталонному CSV файлу
- `vm_url` - URL VictoriaMetrics (например, http://localhost:8428)

**Проверяет:**
- ✅ Все ресурсы из CSV присутствуют в VM
- ✅ Все метрики из CSV присутствуют в VM
- ✅ Количество точек данных совпадает

**Особенности:**
- Автоматически определяет временной диапазон данных
- Использует Prometheus queries для подсчета
- Поддерживает sanitized metric names

---

### 6. check_grafana.py

**Назначение:** Проверка доступности метрик в Grafana.

**Использование:**
```bash
python check_grafana.py
```

**Environment variables:**
- `GRAFANA_URL` - URL Grafana (default: http://localhost:3000)
- `GRAFANA_API_KEY` - API key или admin:admin

**Проверяет:**
- ✅ Grafana health
- ✅ Наличие datasource VictoriaMetrics
- ✅ Возможность запросов метрик через Grafana API

---

### 7. update_dashboard_file.py

**Назначение:** Обновление Grafana dashboard с добавлением новых секций.

**Использование:**
```bash
python update_dashboard_file.py
```

**Функции:**
- Добавляет секции для FC Port (47 метрик)
- Добавляет секции для Snapshot LUN (3 метрики)
- Обновляет количество панелей в dashboard
- Создает резервную копию перед изменением

**Выходные файлы:**
- `grafana/dashboards/huawei_performance.json` - обновленный dashboard
- `grafana/dashboards/huawei_performance.json.backup_*` - резервная копия

---

## Вспомогательные функции

### Multi-threaded Compression (api/main.py)

```python
def gzip_single_file(csv_file: Path) -> dict:
    """Сжатие одного CSV файла."""
    
def gzip_csv_files(directory: Path):
    """Параллельное сжатие всех CSV в директории.
    
    - Использует ThreadPoolExecutor
    - До 16 потоков одновременно
    - Compression level: 6
    - ~16x ускорение на системах с 32 vCPU
    """
```

### Job Cleanup (api/main.py)

```python
async def periodic_cleanup():
    """Периодическая очистка старых jobs.
    
    - Запускается каждый час
    - Удаляет jobs старше JOB_TTL_HOURS (default: 24h)
    """
```

---

## Использование в Docker

Все скрипты вызываются через `api/main.py` в Docker контейнере:

```python
# Grafana mode
cmd = [
    "python3",
    "/app/huawei_streaming_pipeline.py",
    "-i", str(zip_path),
    "--vm-url", VM_IMPORT_URL,
    "--batch-size", "50000",
    "--all-metrics"
]

# CSV Wide mode
cmd = [
    "python3",
    "/app/Data2csv/Huawei_perf_parser_v0.2_parallel.py",
    "-i", str(zip_path),
    "-o", str(job_dir),
    "--all-metrics"
]

# Perfmonkey mode
cmd = [
    "python3",
    "/app/perfmonkey/perf_zip2csv_wide.py",
    str(zip_path),
    "-o", str(job_dir),
    "--workers", "30"
]
```

---

## Зависимости

### Python (requirements.txt)
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6
requests>=2.31.0
pandas>=2.1.0
tqdm>=4.66.0
psutil>=5.9.0
click>=8.1.0
```

### System
- Python 3.11
- Docker >= 20.10
- Docker Compose >= 2.0

