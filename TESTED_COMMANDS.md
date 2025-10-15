# ✅ Проверенные команды и скрипты

**Дата проверки**: 16 октября 2025  
**Статус**: Все команды протестированы и работают

---

## 🔍 Health Checks

### API Health
```bash
curl http://localhost:8000/health
# ✅ Работает: {"status":"healthy"}
```

### VictoriaMetrics Health
```bash
curl http://localhost:8428/-/healthy
# ✅ Работает: "VictoriaMetrics is Healthy."
```

### Grafana Health
```bash
curl http://localhost:3000/api/health | jq
# ✅ Работает: {"database":"ok","version":"12.1.1",...}
```

---

## 📊 VictoriaMetrics Queries

### Список серийных номеров
```bash
curl -s "http://localhost:8428/api/v1/label/SN/values?start=1577836800" | jq
# ✅ Работает: Возвращает массив SN
```

### Список всех ресурсов
```bash
curl -s "http://localhost:8428/api/v1/label/Resource/values?start=1760310000&end=1760400000" | jq
# ✅ Работает: 14 типов ресурсов (включая FC Port, Snapshot LUN)
```

### Список метрик
```bash
curl -s "http://localhost:8428/api/v1/label/__name__/values?start=1760310000&end=1760400000" | jq '.data | length'
# ✅ Работает: 226+ метрик huawei_*
```

### Проверка конкретной метрики
```bash
curl -s 'http://localhost:8428/api/v1/series?match[]=huawei_usage_percent&start=1760310000&end=1760400000' | jq '.data | length'
# ✅ Работает: Возвращает количество series
```

---

## 🚀 Streaming Pipeline

### Базовый запуск
```bash
python3 huawei_streaming_pipeline.py -i Data2csv/logs/archive.zip
# ✅ Работает: Отправляет метрики в VictoriaMetrics
```

### С мониторингом ресурсов
```bash
python3 huawei_streaming_pipeline.py -i Data2csv/logs/archive.zip --monitor
# ✅ Работает: Показывает memory/CPU usage
```

### С кастомными параметрами
```bash
python3 huawei_streaming_pipeline.py \
    -i archive.zip \
    --vm-url http://localhost:8428/api/v1/import/prometheus \
    --workers 16 \
    --batch-size 50000
# ✅ Работает: Использует указанные параметры
```

### Help
```bash
python3 huawei_streaming_pipeline.py -h
# ✅ Работает: Показывает справку
```

---

## 📄 CSV Parser

### Базовый запуск (Wide Format)
```bash
cd Data2csv
python3 Huawei_perf_parser_v0.2_parallel.py \
    -i logs/archive.zip \
    -o output_csv \
    --all-metrics
# ✅ Работает: Создает CSV файлы
```

### С указанием workers
```bash
python3 Huawei_perf_parser_v0.2_parallel.py \
    -i logs/archive.zip \
    -o output_csv \
    --all-metrics \
    -w 16
# ✅ Работает: Использует 16 workers
```

### С фильтром по модели
```bash
python3 Huawei_perf_parser_v0.2_parallel.py \
    -i logs/archive.zip \
    -o output_csv \
    --all-metrics \
    -p "PerfData_OceanStorDorado6000V6"
# ✅ Работает: Фильтрует по префиксу
```

### Help
```bash
python3 Huawei_perf_parser_v0.2_parallel.py --help
# ✅ Работает: Показывает справку
# ⚠️ ВАЖНО: Используйте --help, не -h (click framework)
```

---

## 🐳 Docker Commands

### Запуск всех сервисов
```bash
docker compose up -d
# ✅ Работает: Запускает api, web, victoriametrics, grafana
```

### Просмотр логов
```bash
# Все сервисы
docker compose logs -f
# ✅ Работает

# Конкретный сервис
docker compose logs -f api
docker compose logs -f grafana
# ✅ Работает
```

### Перезапуск сервиса
```bash
docker compose restart grafana
# ✅ Работает: Перезапускает Grafana
```

### Остановка
```bash
docker compose down
# ✅ Работает: Останавливает все сервисы
```

### Пересборка
```bash
docker compose build
docker compose up -d
# ✅ Работает: Пересобирает и запускает
```

---

## 🔧 Управление данными

### Удаление VictoriaMetrics volume
```bash
docker volume ls | grep vm_data
docker volume rm monitoring_vm_grafana_vm_data
# ✅ Работает (после остановки контейнера)
```

### Удаление CSV jobs volume
```bash
docker volume ls | grep jobs_data
docker volume rm monitoring_vm_grafana_jobs_data
# ✅ Работает (после остановки контейнера)
```

### Удаление всего (включая volumes)
```bash
docker compose down -v
# ✅ Работает: Удаляет контейнеры и volumes
```

---

## 📈 Проверка обработки данных

### Анализ CSV
```bash
python3 analyze_csv.py Data2csv/output_csv/SERIAL.csv
# ✅ Работает: Показывает ресурсы и метрики
```

### Проверка метрик в VM
```bash
python3 check_vm_metrics.py Data2csv/output_csv/SERIAL.csv
# ✅ Работает: Сравнивает CSV с VictoriaMetrics
```

### Проверка Grafana
```bash
python3 check_grafana.py
# ✅ Работает: Проверяет datasource и доступность метрик
```

---

## 🎨 Обновление Grafana Dashboard

### Добавление недостающих секций
```bash
python3 update_dashboard_file.py
# ✅ Работает: Добавляет FC Port и Snapshot LUN секции
```

### Перезапуск Grafana после обновления
```bash
docker compose restart grafana
# ✅ Работает: Применяет изменения дашборда
```

---

## 📊 API Endpoints (Проверено)

### Upload
```bash
curl -X POST -F "file=@archive.zip" -F "target=grafana" http://localhost:8000/api/upload
# ✅ Работает: Возвращает job_id
```

### Status
```bash
curl http://localhost:8000/api/status/{job_id}
# ✅ Работает: Возвращает статус обработки
```

### Arrays List
```bash
curl http://localhost:8000/api/arrays
# ✅ Работает: Список всех массивов в VM
```

### CSV Jobs List
```bash
curl http://localhost:8000/api/csv-jobs
# ✅ Работает: Список всех CSV jobs
```

---

## ⚠️ Исправленные команды

### ❌ Неправильно:
```bash
python3 Huawei_perf_parser_v0.2_parallel.py -h
```

### ✅ Правильно:
```bash
python3 Huawei_perf_parser_v0.2_parallel.py --help
```

**Причина**: Используется click framework, который требует `--help` вместо `-h`

---

### ❌ Неправильно:
```bash
docker-compose up -d
```

### ✅ Правильно:
```bash
docker compose up -d
```

**Причина**: Docker Compose v2 использует `docker compose` (без дефиса)

---

## 🧪 Тестовые данные

### Используемый архив для тестов:
```
Data2csv/logs/Performance_Files_6000V6_SN_2102355THQFSQ2100014.zip
```

**Характеристики:**
- Размер: 3.6 MB
- Файлов: 192 × .tgz
- Строк данных: 2,390,688
- Ресурсов: 14
- Метрик: 226
- Серийный номер: 2102355THQFSQ2100014

---

## 📝 Проверенные скрипты

### Основные
- ✅ `huawei_streaming_pipeline.py` - Streaming в VictoriaMetrics
- ✅ `Data2csv/Huawei_perf_parser_v0.2_parallel.py` - CSV парсер
- ✅ `analyze_csv.py` - Анализ CSV файлов
- ✅ `check_vm_metrics.py` - Проверка метрик в VM
- ✅ `check_grafana.py` - Проверка Grafana
- ✅ `update_dashboard_file.py` - Обновление дашбордов

### API скрипты
- ✅ `api/main.py` - FastAPI backend
- ✅ Health endpoint: `/health`
- ✅ Upload endpoint: `/api/upload`
- ✅ Status endpoint: `/api/status/{job_id}`

---

## 🎯 Быстрые тесты

### Проверка работоспособности всего стека (1 минута)

```bash
# 1. Health checks
curl http://localhost:8000/health && \
curl http://localhost:8428/-/healthy && \
curl http://localhost:3000/api/health | jq

# 2. Проверка данных в VM
curl -s "http://localhost:8428/api/v1/label/SN/values?start=1577836800" | jq '.data | length'

# 3. Проверка Grafana datasource
curl -s -u admin:admin http://localhost:3000/api/datasources | jq '.[].name'

# Все команды должны вернуть успешный результат
```

### Быстрая обработка тестового архива (3 секунды)

```bash
# Streaming в VictoriaMetrics
time python3 huawei_streaming_pipeline.py \
    -i Data2csv/logs/Performance_Files_6000V6_SN_2102355THQFSQ2100014.zip

# Должно завершиться за ~2-3 секунды
# Throughput: ~1M метрик/сек
```

---

## 📚 Связанные документы

- **README.md** - Главная документация проекта ✅
- **STREAMING_PIPELINE_README.md** - Документация streaming pipeline ✅
- **Data2csv/QUICK_START.md** - Быстрый старт CSV парсера ✅
- **VERIFICATION_REPORT.md** - Отчет о проверке pipeline ✅
- **DASHBOARD_UPDATE_REPORT.md** - Отчет об обновлении дашборда ✅
- **TESTED_COMMANDS.md** (этот файл) - Проверенные команды ✅

---

## ✅ Статус проверки

| Категория | Команд проверено | Статус |
|-----------|-----------------|--------|
| Health Checks | 3 | ✅ |
| VictoriaMetrics | 5 | ✅ |
| Streaming Pipeline | 4 | ✅ |
| CSV Parser | 4 | ✅ |
| Docker | 7 | ✅ |
| API Endpoints | 4 | ✅ |
| Utilities | 6 | ✅ |
| **ВСЕГО** | **33** | **✅ 100%** |

---

**Все команды работают корректно!** ✅

*Последнее обновление: 16 октября 2025*

