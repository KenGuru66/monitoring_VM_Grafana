# Использование Huawei → VictoriaMetrics Pipeline

## 🚀 Быстрый старт (РЕКОМЕНДУЕТСЯ)

### Автоматический полный pipeline
```bash
# Один скрипт делает всё: парсинг + импорт + очистка
python3 huawei_to_vm_pipeline.py -i "Data2csv/logs/Storage_History_Performance_Files.zip"
```

**Результат:**
- ⏱️ ~107 секунд для полной обработки
- 📊 21.9M строк импортировано в VictoriaMetrics
- 🧹 Промежуточные CSV автоматически удалены

---

## 🤖 Автоматическое определение workers (НОВОЕ!)

Система **автоматически** выбирает оптимальное количество workers на основе:

| Фактор | Влияние |
|--------|---------|
| CPU ядра | Базовое: CPU - 1 |
| Память | Ограничение: ~300 MB на worker |
| Размер файла | Маленький (<100 MB) → 2 workers<br>Средний (100MB-1GB) → 4 workers<br>Большой (>1GB) → max workers |
| Загрузка CPU | Если >70% → уменьшаем workers |

**Вы можете переопределить:** `--workers N`

## 📋 Параметры запуска

### Pipeline скрипт (huawei_to_vm_pipeline.py)

```bash
python3 huawei_to_vm_pipeline.py \
  -i INPUT_ZIP              # ZIP архив с .tgz файлами
  [-o OUTPUT_DIR]           # Директория для CSV (default: Data2csv/output)
  [--vm-url URL]            # VictoriaMetrics URL
  [--workers N]             # Количество workers (default: CPU-1)
  [--keep-csv]              # Не удалять CSV после импорта
  [--batch-size SIZE]       # Размер батча (default: 50000)
```

### Примеры

```bash
# Базовый запуск
python3 huawei_to_vm_pipeline.py -i "Data2csv/logs/archive.zip"

# С сохранением CSV файлов для дальнейшего анализа
python3 huawei_to_vm_pipeline.py -i "Data2csv/logs/archive.zip" --keep-csv

# С настройкой количества workers (для систем с большим количеством ядер)
python3 huawei_to_vm_pipeline.py -i "Data2csv/logs/archive.zip" --workers 15

# С указанием удалённого VictoriaMetrics
python3 huawei_to_vm_pipeline.py \
  -i "Data2csv/logs/archive.zip" \
  --vm-url "http://10.0.0.5:8428/api/v1/import/prometheus"
```

---

## 🔧 Ручная обработка (опционально)

Если нужен больший контроль над процессом:

### Шаг 1: Парсинг
```bash
cd Data2csv
python3 Huawei_perf_parser_v0.2_parallel.py \
  -i "logs/Storage_History_Performance_Files.zip" \
  -o output
```

### Шаг 2: Импорт
```bash
cd ..
python3 csv2vm_parallel.py Data2csv/output/*.csv
```

### Шаг 3: Очистка (опционально)
```bash
rm -rf Data2csv/output/*.csv
```

---

## 📊 Как это работает

### Этап 1: Парсинг (50 сек)
```
ZIP архив (276 .tgz files)
    ↓
[7 Workers параллельно]
    ├── Worker 1: файлы 1-39
    ├── Worker 2: файлы 40-79
    ├── Worker 3: файлы 80-118
    └── ...
    ↓
CSV файл (2.1 GB, 21.9M строк)
```

### Этап 2: Импорт (51-56 сек)
```
CSV (21.9M строк)
    ↓
Разделение на 7 chunks по 3.1M строк
    ↓
[7 Workers параллельно]
    ├── Worker 1: rows 0-3.1M → HTTP POST → VM
    ├── Worker 2: rows 3.1M-6.2M → HTTP POST → VM
    ├── Worker 3: rows 6.2M-9.4M → HTTP POST → VM
    └── ...
    ↓
VictoriaMetrics (21.9M datapoints)
```

### Этап 3: Очистка
- Автоматическое удаление CSV (если не указан `--keep-csv`)

---

## 🧹 Очистка данных

### Удалить CSV файлы
```bash
rm -rf Data2csv/output/*.csv
```

### Очистить VictoriaMetrics
```bash
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series \
  -d 'match[]={__name__=~"hu_.*"}'
```

### Полная очистка (CSV + VictoriaMetrics)
```bash
rm -rf Data2csv/output/*.csv && \
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series \
  -d 'match[]={__name__=~"hu_.*"}'
```

---

## 📊 Проверка результатов

### Статистика VictoriaMetrics
```bash
curl -s 'http://localhost:8428/api/v1/status/tsdb' | \
  python3 -c "import sys,json; d=json.load(sys.stdin)['data']; \
  print('Series:', d.get('totalSeries',0)); \
  print('Datapoints:', d.get('totalDatapoints',0))"
```

### Список импортированных метрик
```bash
curl -s 'http://localhost:8428/api/v1/label/__name__/values' | \
  python3 -m json.tool | grep hu_
```

### Пример запроса метрики
```bash
curl -s 'http://localhost:8428/api/v1/query?query=hu_read_bandwidth_mbps_variable' | \
  python3 -m json.tool
```

---

## 📈 Производительность

| Метрика | Значение |
|---------|----------|
| **Парсинг** | 50-51 сек |
| **Импорт** | 51-56 сек |
| **Общее время** | ~107 сек (1.8 мин) |
| **CPU использование** | 7 ядер @ 80-99% |
| **Скорость импорта** | 426K rows/sec |

---

## 💡 Рекомендации

1. **Для production:** Используйте автоматический pipeline
   ```bash
   python3 huawei_to_vm_pipeline.py -i "archive.zip"
   ```

2. **Для отладки:** Используйте `--keep-csv` для сохранения промежуточных файлов
   ```bash
   python3 huawei_to_vm_pipeline.py -i "archive.zip" --keep-csv
   ```

3. **Для систем с 16+ ядрами:** Увеличьте workers
   ```bash
   python3 huawei_to_vm_pipeline.py -i "archive.zip" --workers 15
   ```

4. **Для ограниченной памяти:** Уменьшите batch size
   ```bash
   python3 huawei_to_vm_pipeline.py -i "archive.zip" --batch-size 25000
   ```

---

## 🐛 Troubleshooting

**Проблема:** "File not found"
- **Решение:** Проверьте путь к ZIP файлу

**Проблема:** "Connection refused" при импорте
- **Решение:** Убедитесь, что VictoriaMetrics запущена
  ```bash
  curl http://localhost:8428/health
  ```

**Проблема:** Импорт медленный
- **Решение:** Проверьте, что используется параллельная версия и все CPU заняты
  ```bash
  top  # Должны видеть 7+ процессов Python
  ```

**Проблема:** Не хватает памяти
- **Решение:** Уменьшите workers или batch size
  ```bash
  python3 huawei_to_vm_pipeline.py -i "archive.zip" --workers 4 --batch-size 25000
  ```

---

## 📁 Логи

Все операции логируются в:
- `pipeline.log` - единый pipeline скрипт
- `csv2vm_parallel.log` - импорт в VictoriaMetrics
- `Data2csv/parser.log` - парсинг .tgz файлов

---

**Версия:** 0.2 Parallel | **Дата:** 2025-10-01
