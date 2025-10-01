# Huawei Performance Data Processing Pipeline

Автоматизированная система обработки данных производительности Huawei OceanStor и импорта в VictoriaMetrics.

## 🚀 Быстрый старт

### Полный автоматический pipeline
```bash
# Один скрипт для полной обработки: парсинг + импорт
python3 huawei_to_vm_pipeline.py -i "Data2csv/logs/Storage_History_Performance_Files.zip"
```

## 🤖 Автоматическое определение workers

Система **автоматически** определяет оптимальное количество workers на основе:
- 🖥️ Количества CPU ядер (с адаптацией под 4-128 CPU)
- 💾 Доступной памяти
- 📁 Размера файла
- ⚡ Текущей загрузки системы

**Адаптация под разные системы:**
- 4-8 CPU → используется CPU - 1 workers
- 8-16 CPU → используется CPU - 1 workers
- 16-32 CPU → максимум 16 workers (bottleneck в I/O)
- 32+ CPU → максимум 20 workers (bottleneck в сети)

**Примеры файлов:**
- Файл 50 MB → 2 workers
- Файл 500 MB → 4 workers  
- Файл 2+ GB → max workers для системы

Вы можете **переопределить** автоопределение через `--workers N`

## 📊 Как это работает

### Этап 1: Парсинг (авто workers)
```
ZIP архив → Извлечение .tgz → Парсинг XML → CSV (2.1 GB)
           ↓                  ↓              ↓
        Worker 1           Worker 1       Worker 1
        Worker 2           Worker 2       Worker 2
        Worker 3           Worker 3       Worker 3
        ...                ...            ...
        
Время: 51 сек | CPU: 7 ядер @ 97-99%
```

### Этап 2: Импорт (7 workers параллельно)
```
CSV → Разделение на chunks → Prometheus формат → VictoriaMetrics
     ↓                       ↓                    ↓
  Worker 1 (3.1M rows)    Worker 1            HTTP POST
  Worker 2 (3.1M rows)    Worker 2            HTTP POST
  Worker 3 (3.1M rows)    Worker 3            HTTP POST
  ...                     ...                 ...
  
Время: 51.3 сек | Скорость: 427K rows/sec | CPU: 7 ядер
```

### Обход Python GIL
```python
# multiprocessing создаёт отдельные процессы (не threads)
# Каждый процесс обходит GIL → настоящая параллельность
from multiprocessing import Pool
with Pool(processes=7) as pool:
    pool.map(work, tasks)  # 7 CPU ядер работают одновременно
```

## 📊 Производительность

| Этап | Время | Скорость | CPU |
|------|-------|----------|-----|
| Парсинг | 51 сек | 5.4 файлов/сек | 7 ядер |
| Импорт | 51.3 сек | 427,239 rows/sec | 7 ядер |
| **ИТОГО** | **102 сек** | - | **7 ядер** |

**Улучшение vs single-thread:** 3x быстрее, 7x больше CPU

## 🛠️ Использование

### Ручная обработка
```bash
# Шаг 1: Парсинг
cd Data2csv
python3 Huawei_perf_parser_v0.2_parallel.py -i "logs/file.zip" -o output

# Шаг 2: Импорт
cd ..
python3 csv2vm_parallel.py Data2csv/output/*.csv
```

### Параметры
```bash
# Парсер
-i INPUT    # ZIP/TGZ файл
-o OUTPUT   # Директория для CSV
-w WORKERS  # Количество workers (default: CPU-1)

# Импортер
--url URL      # VictoriaMetrics URL
--workers N    # Количество workers
--batch SIZE   # Размер батча (default: 50000)
```

## 🧹 Очистка
```bash
# Удалить CSV
rm -rf Data2csv/output/*.csv

# Очистить VictoriaMetrics
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series -d 'match[]={__name__=~"hu_.*"}'
```

## 📁 Файлы
- `huawei_to_vm_pipeline.py` - Единый pipeline скрипт
- `csv2vm_parallel.py` - Параллельный импортер
- `Data2csv/Huawei_perf_parser_v0.2_parallel.py` - Параллельный парсер

---
**Версия:** 0.2 Parallel | **Статус:** Production Ready ✅
