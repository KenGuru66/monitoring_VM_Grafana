# Huawei OceanStor Performance Monitoring Pipeline

Автоматизированная система обработки данных производительности Huawei OceanStor с импортом в VictoriaMetrics и визуализацией в Grafana.

## 📋 Содержание

- [Описание](#описание)
- [Архитектура](#архитектура)
- [Быстрый старт](#быстрый-старт)
- [Установка](#установка)
- [Использование](#использование)
- [Структура проекта](#структура-проекта)
- [Проверка данных](#проверка-данных)
- [Очистка данных](#очистка-данных)

---

## 🎯 Описание

Этот проект предоставляет полный автоматический pipeline для:

1. **Парсинг** архивов Huawei Performance Data (ZIP → TGZ → XML → CSV)
2. **Импорт** данных в VictoriaMetrics (параллельная обработка)
3. **Визуализация** метрик в Grafana

### Основные возможности

✅ **Параллельная обработка** - использует все доступные CPU ядра  
✅ **Автоматическое определение workers** - адаптация под систему (4-128 CPU)  
✅ **Умная обработка памяти** - учет доступной RAM  
✅ **Batch импорт** - эффективная загрузка больших объемов данных  
✅ **Streaming обработка** - минимальное использование памяти  
✅ **Гибкая настройка метрик** - выбор DEFAULT или ALL метрик  

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                 HUAWEI PERFORMANCE DATA                     │
│              Storage_History_Performance.zip                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              ЭТАП 1: ПАРСИНГ (Parallel)                     │
│    Huawei_perf_parser_v0.2_parallel.py                      │
│                                                             │
│  ZIP → TGZ → XML → CSV (2+ GB)                              │
│  ├─ Worker 1  ├─ Worker 2  ├─ Worker 3  ...                │
│  └─ Время: ~50 сек | CPU: 97-99%                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│             ЭТАП 2: ИМПОРТ (Parallel)                       │
│           csv2vm_parallel.py                                │
│                                                             │
│  CSV → VictoriaMetrics (Prometheus format)                  │
│  ├─ Worker 1 → Batch 50k rows                              │
│  ├─ Worker 2 → Batch 50k rows                              │
│  └─ Время: ~3-5 мин | Throughput: 50k rows/sec             │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              VICTORIAMETRICS (TSDB)                         │
│           localhost:8428                                    │
│                                                             │
│  • Хранение: 6 месяцев                                      │
│  • Prometheus-совместимый API                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                GRAFANA DASHBOARDS                           │
│              localhost:3000                                 │
│                                                             │
│  • Auto-provisioned datasource                             │
│  • Pre-configured dashboards                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Быстрый старт

### 1. Запуск Docker сервисов

```bash
cd /data/projects/monitoring_VM_Grafana
docker-compose up -d
```

**Проверка:**
- VictoriaMetrics: http://localhost:8428
- Grafana: http://localhost:3000 (admin / changeme)

### 2. Базовый запуск pipeline

```bash
# Простой запуск (DEFAULT метрики)
python3 huawei_to_vm_pipeline.py -i "/path/to/Storage_History_Performance_Files.zip"

# С сохранением CSV файлов
python3 huawei_to_vm_pipeline.py -i "/path/to/archive.zip" --keep-csv

# Парсинг ВСЕХ метрик (вместо DEFAULT)
python3 huawei_to_vm_pipeline.py -i "/path/to/archive.zip" --all-metrics
```

### 3. Запуск в фоновом режиме

```bash
# Запуск с выводом в лог (рекомендуется)
nohup python3 huawei_to_vm_pipeline.py \
  -i "/data/perf_logs/Storage_History_Performance_Files(11-24).zip" \
  --all-metrics \
  > pipeline_all_metrics.log 2>&1 &

# Проверка статуса
tail -f pipeline_all_metrics.log

# Проверка процесса
ps aux | grep huawei_to_vm_pipeline
```

---

## 📦 Установка

### Требования

- **Python 3.8+**
- **Docker & Docker Compose**
- **Свободное место**: ~10+ GB для данных VictoriaMetrics

### 1. Установка зависимостей

```bash
# Создать виртуальное окружение (рекомендуется)
python3 -m venv venv
source venv/bin/activate

# Установить Python зависимости
pip install -r requirements.txt
```

**Зависимости:**
- `requests` - HTTP клиент для VictoriaMetrics API
- `pandas` - обработка данных
- `click` - CLI интерфейс парсера
- `tqdm` - прогресс-бары
- `psutil` - мониторинг системы (опционально, но рекомендуется)

### 2. Запуск Docker сервисов

```bash
docker-compose up -d
```

### 3. Проверка работоспособности

```bash
# VictoriaMetrics
curl http://localhost:8428/health
# Ожидается: OK

# Grafana
curl http://localhost:3000/api/health
# Ожидается: {"database":"ok",...}
```

---

## 💻 Использование

### Полный pipeline (рекомендуется)

```bash
python3 huawei_to_vm_pipeline.py -i "archive.zip" [OPTIONS]
```

**Опции:**

| Опция | Описание | По умолчанию |
|-------|----------|--------------|
| `-i, --input` | Путь к ZIP архиву (обязательно) | - |
| `-o, --output-dir` | Директория для CSV файлов | `Data2csv/output` |
| `--vm-url` | URL VictoriaMetrics API | `http://localhost:8428/api/v1/import/prometheus` |
| `-w, --workers` | Количество workers | auto (CPU-1) |
| `--batch-size` | Размер батча для импорта | 50000 |
| `--keep-csv` | Не удалять CSV после импорта | False |
| `--all-metrics` | Парсить ВСЕ метрики (не только DEFAULT) | False |

### Примеры использования

```bash
# 1. Базовый запуск с DEFAULT метриками
python3 huawei_to_vm_pipeline.py -i "Data2csv/logs/archive.zip"

# 2. Парсинг ВСЕХ метрик
python3 huawei_to_vm_pipeline.py -i "archive.zip" --all-metrics

# 3. С сохранением промежуточных CSV
python3 huawei_to_vm_pipeline.py -i "archive.zip" --keep-csv

# 4. Настройка количества workers
python3 huawei_to_vm_pipeline.py -i "archive.zip" --workers 8

# 5. Фоновый запуск с логированием
nohup python3 huawei_to_vm_pipeline.py \
  -i "/data/perf_logs/Storage_History_Performance_Files(11-24).zip" \
  --all-metrics \
  > pipeline_all_metrics.log 2>&1 &

# Мониторинг лога в реальном времени
tail -f pipeline_all_metrics.log
```

### Поэтапная обработка (опционально)

Если нужен больший контроль, можно запускать этапы отдельно:

#### Этап 1: Парсинг

```bash
python3 Data2csv/Huawei_perf_parser_v0.2_parallel.py \
  -i "archive.zip" \
  -o "Data2csv/output" \
  -w 7 \
  --all-metrics
```

#### Этап 2: Импорт

```bash
python3 csv2vm_parallel.py \
  "Data2csv/output/2102353TJWFSP3100020.csv" \
  --url "http://localhost:8428/api/v1/import/prometheus" \
  --batch 50000 \
  --workers 7
```

---

## 🤖 Автоматическое определение Workers

Система **автоматически** определяет оптимальное количество workers:

### Адаптация под CPU

| CPU ядер | Workers | Примечание |
|----------|---------|------------|
| 4-8 | CPU - 1 | Используем почти все ядра |
| 8-16 | CPU - 1 | Максимальная производительность |
| 16-32 | max 16 | Bottleneck в I/O, не CPU |
| 32+ | max 20 | Bottleneck в сети |

### Адаптация под размер файла

| Размер файла | Workers |
|--------------|---------|
| < 100 MB | 2 |
| 100 MB - 1 GB | 4 |
| 1-5 GB | Оптимальное для CPU |
| > 5 GB | Максимальное для CPU |

### Учет загрузки системы

- **CPU load > 70%** → уменьшение workers на 1
- **CPU load > 50%** → уменьшение workers на 20%
- **Доступная RAM** → ограничение по памяти (~300 MB/worker)

---

## 📁 Структура проекта

```
monitoring_VM_Grafana/
├── huawei_to_vm_pipeline.py          # Главный pipeline скрипт
├── csv2vm_parallel.py                # Импорт CSV → VictoriaMetrics
├── requirements.txt                  # Python зависимости
├── docker-compose.yml                # Docker сервисы (VM + Grafana)
├── README.md                         # Документация
│
├── Data2csv/                         # Парсер Huawei данных
│   ├── Huawei_perf_parser_v0.2_parallel.py
│   ├── METRIC_DICT.py               # Словарь метрик
│   ├── RESOURCE_DICT.py             # Словарь ресурсов
│   └── def_metrics                  # Определения метрик
│
└── grafana/                          # Grafana конфигурация
    └── provisioning/
        ├── datasources/             # Auto-provisioned VictoriaMetrics
        └── dashboards/              # Pre-configured dashboards
```

---

## 📊 Метрики и ресурсы

### DEFAULT метрики (быстрая обработка)

По умолчанию обрабатываются основные метрики производительности:

- **CPU**: Avg/Max CPU Usage
- **Memory**: Avg Memory Usage
- **IOPS**: Read/Write IOPS
- **Throughput**: Read/Write Bandwidth (MB/s)
- **Latency**: Read/Write Latency (ms)
- **Cache**: Hit Ratio

### ALL метрики (полная обработка)

С опцией `--all-metrics` обрабатываются **все** доступные метрики из METRIC_DICT и RESOURCE_DICT:

- Все типы контроллеров (Controller A/B)
- Disk Pool метрики
- Front-end & Back-end порты
- Расширенные метрики производительности

**⚠️ Примечание:** Обработка ALL метрик занимает больше времени и места в БД.

---

## 🔧 Конфигурация

### Docker сервисы

Настройка через переменные окружения в `docker-compose.yml`:

```yaml
VM_PORT=8428                    # Порт VictoriaMetrics
VM_RETENTION=6                  # Хранение данных (месяцы)
GRAFANA_PORT=3000              # Порт Grafana
GRAFANA_ADMIN_PASS=changeme    # Пароль администратора
```

### VictoriaMetrics

- **Хранилище**: `/data/vmdata` (host path)
- **Retention**: 6 месяцев (настраивается)
- **API**: http://localhost:8428

### Grafana

- **Datasource**: VictoriaMetrics (auto-provisioned)
- **Логин**: admin / changeme
- **Dashboards**: Pre-configured для Huawei OceanStor

---

## 📈 Производительность

### Типичные показатели

**Система:** 24 CPU cores, 64 GB RAM

| Этап | Время | Throughput | Workers |
|------|-------|------------|---------|
| Парсинг | ~50 сек | 40 MB/s | 7 |
| Импорт | ~3-5 мин | 50k rows/s | 7 |

**Файл:** ~2.1 GB CSV (50M+ rows)

### Оптимизация

1. **Больше workers** для больших файлов (если достаточно CPU/RAM)
2. **Увеличить batch-size** до 100000 для очень больших файлов
3. **SSD диск** для VictoriaMetrics storage значительно ускоряет импорт

---

## 🐛 Troubleshooting

### Pipeline прерывается

```bash
# Проверить логи
tail -f pipeline.log

# Проверить доступность VictoriaMetrics
curl http://localhost:8428/health
```

### Нехватка памяти

```bash
# Уменьшить количество workers
python3 huawei_to_vm_pipeline.py -i "archive.zip" --workers 4

# Уменьшить batch size
python3 huawei_to_vm_pipeline.py -i "archive.zip" --batch-size 25000
```

### VictoriaMetrics не отвечает

```bash
# Перезапуск сервиса
docker-compose restart victoriametrics

# Проверка логов
docker-compose logs victoriametrics
```

### CSV файлы не удаляются

```bash
# Ручная очистка
rm -f Data2csv/output/*.csv
```

### Дублирование данных / нужна очистка БД

```bash
# Удалить данные конкретного массива
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series \
  -d 'match[]={SN="2102353TJWFSP3100020"}'
curl -X POST http://localhost:8428/internal/force_merge
sleep 30  # Подождать завершения

# Полная очистка базы (см. раздел "Очистка данных")
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series \
  -d 'match[]={__name__=~".+"}'
curl -X POST http://localhost:8428/internal/force_merge
sleep 30  # Подождать завершения

# Обновить Grafana в браузере (Ctrl+R)
```

---

## 📝 Логи

Pipeline создает несколько лог-файлов:

- `pipeline.log` - основной лог pipeline
- `csv2vm_parallel.log` - детальный лог импорта
- `pipeline_all_metrics.log` - лог при использовании `--all-metrics`

Логи пишутся в реальном времени и содержат:
- ✅ Успешные операции
- ⚠️ Предупреждения
- ❌ Ошибки с trace

---

## 🔍 Проверка данных

### Проверка успешности импорта

```bash
# 1. Проверка статуса TSDB и количества метрик
curl http://localhost:8428/api/v1/status/tsdb

# 2. Список всех метрик в базе
curl http://localhost:8428/api/v1/label/__name__/values

# 3. Список серийных номеров (SN) в базе
curl http://localhost:8428/api/v1/label/SN/values

# 4. Проверка количества временных рядов (time series)
curl 'http://localhost:8428/api/v1/query?query=count({__name__=~"huawei_.+"})'

# 5. Проверка данных конкретного массива по SN
curl 'http://localhost:8428/api/v1/query?query=huawei_avg_cpu_usage_percent{SN="2102353TJWFSP3100020"}'

# 6. Временной диапазон импортированных данных
curl 'http://localhost:8428/api/v1/query?query=huawei_avg_cpu_usage_percent' | jq '.data.result[0]'
```

### Через Grafana

1. Открыть http://localhost:3000
2. Login: admin / changeme
3. Dashboards → Browse
4. Выбрать pre-configured dashboard

---

## 🗑️ Очистка данных

### Удаление данных конкретного массива (по SN)

```bash
# Шаг 1: Удалить все метрики для конкретного серийного номера
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series \
  -d 'match[]={SN="2102353TJWFSP3100020"}'

# Шаг 2: ОБЯЗАТЕЛЬНО! Принудительное слияние для физического удаления
curl -X POST http://localhost:8428/internal/force_merge

# Шаг 3: Подождать 10-30 секунд

# Шаг 4: Проверка удаления
curl http://localhost:8428/api/v1/label/SN/values

# Шаг 5: Обновить Grafana (Ctrl+R в браузере)
```

### Удаление конкретных метрик

```bash
# Удалить только метрики CPU
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series \
  -d 'match[]={__name__=~"huawei_.*cpu.*"}'

# Принудительное слияние
curl -X POST http://localhost:8428/internal/force_merge

# Удалить метрики за конкретный период
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series \
  -d 'match[]={__name__=~"huawei_.+"}' \
  -d 'start=2024-01-01T00:00:00Z' \
  -d 'end=2024-01-31T23:59:59Z'

# Принудительное слияние
curl -X POST http://localhost:8428/internal/force_merge
```

### Полная очистка базы данных

```bash
# ⚠️ ВНИМАНИЕ: Удаляет ВСЕ данные из VictoriaMetrics!

# Шаг 1: Пометить данные для удаления
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series \
  -d 'match[]={__name__=~".+"}'

# Шаг 2: ОБЯЗАТЕЛЬНО! Принудительное слияние для физического удаления
curl -X POST http://localhost:8428/internal/force_merge

# Шаг 3: Подождать 10-30 секунд для завершения операции

# Шаг 4: Проверка (должен вернуть пустой список)
curl http://localhost:8428/api/v1/label/__name__/values
```

**⚠️ Важно:** VictoriaMetrics не удаляет данные мгновенно! 

После `delete_series` данные только **помечаются** для удаления. Для физического удаления нужно:
1. Вызвать `/internal/force_merge` (принудительное слияние)
2. Подождать завершения операции (10-30 сек)
3. Обновить дашборд в Grafana (Ctrl+R или кнопка Refresh)

**Альтернативный способ (гарантированная очистка):**

```bash
# Остановка, удаление данных и перезапуск
docker-compose down
sudo rm -rf /data/vmdata/*
docker-compose up -d
```

### Проверка после удаления

```bash
# Список оставшихся метрик
curl http://localhost:8428/api/v1/label/__name__/values

# Количество временных рядов
curl http://localhost:8428/api/v1/status/tsdb

# Список серийных номеров
curl http://localhost:8428/api/v1/label/SN/values
```

**💡 Полезные команды:**

```bash
# Удалить данные ВСЕХ массивов Huawei
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series \
  -d 'match[]={__name__=~"huawei_.+"}'
curl -X POST http://localhost:8428/internal/force_merge

# Удалить данные за исключением определенного SN
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series \
  -d 'match[]={SN!="2102353TJWFSP3100020"}'
curl -X POST http://localhost:8428/internal/force_merge

# Удалить старые данные (например, старше 3 месяцев)
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series \
  -d 'match[]={__name__=~"huawei_.+"}' \
  -d 'end='$(date -d '3 months ago' -Iseconds)
curl -X POST http://localhost:8428/internal/force_merge
```

**🔧 Почему данные не удаляются сразу?**

VictoriaMetrics использует LSM-дерево для хранения. При вызове `delete_series`:
1. Данные **помечаются** для удаления (tombstone markers)
2. Физическое удаление происходит при слиянии (merge) блоков данных
3. По умолчанию merge происходит автоматически, но может занять время

**Решение:** Принудительное слияние через `/internal/force_merge`

**🔄 Типичный workflow полной очистки:**

```bash
# 1. Удаление
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series -d 'match[]={__name__=~".+"}'

# 2. Принудительное слияние
curl -X POST http://localhost:8428/internal/force_merge

# 3. Ожидание (10-30 секунд)
sleep 30

# 4. Проверка
curl http://localhost:8428/api/v1/label/__name__/values

# 5. Обновить Grafana в браузере (Ctrl+R)
```

---

## 📄 Лицензия

Проект для внутреннего использования.

---

## 👤 Автор

Monitoring VM Grafana Team

---

## 🔗 Полезные ссылки

- [VictoriaMetrics Documentation](https://docs.victoriametrics.com/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Exposition Format](https://prometheus.io/docs/instrumenting/exposition_formats/)

---

**🎉 Проект готов к использованию!**

Для быстрого старта:
```bash
docker-compose up -d
python3 huawei_to_vm_pipeline.py -i "your_archive.zip"
```
