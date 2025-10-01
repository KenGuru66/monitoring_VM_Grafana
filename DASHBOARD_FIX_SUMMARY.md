# 🔧 Исправление Дашборда Grafana

## ❌ Проблемы, которые были обнаружены

### 1. Неправильные названия метрик
**Было**: `hu_avg._corrected_cpu_usage_pct_variable`  
**Стало**: `huawei_avg_corrected_cpu_usage_percent`

- Префикс `hu_` заменен на `huawei_`
- Удален суффикс `_variable`
- Точки в названиях недопустимы в Prometheus

### 2. Все секции имели одинаковые метрики
**Было**: Все 6 секций (Controller, FC Port, Storage Pool, Disk Domain, LUN, Host) имели одинаковый набор из 56 метрик

**Стало**: Каждая секция имеет только применимые к ней метрики:
- **Controller** (Resource="207") - 39 метрик (CPU, Cache, Back-end traffic)
- **FC Port** (Resource="212") - 26 метрик (IOPS, Bandwidth, Performance)
- **Storage Pool** (Resource="216") - 13 метрик (Usage, Performance)
- **Disk Domain** (Resource="266") - 27 метрик (Disk Usage, Performance)
- **LUN** (Resource="11") - 42 метрики (SCSI/ISCSI, Deduplication, VAAI)
- **Host** (Resource="21") - 26 метрик (Performance)

### 3. Нет привязки секций к ресурсам
**Было**: Все секции использовали переменную `$Resource`, позволяя выбирать любой ресурс  
**Стало**: Каждая секция жестко привязана к своему Resource ID:
- Controller → `Resource="207"`
- FC Port → `Resource="212"`
- Storage Pool → `Resource="216"`
- Disk Domain → `Resource="266"`
- LUN → `Resource="11"`
- Host → `Resource="21"`

## ✅ Что было исправлено

### 1. Исправлен `csv2vm_parallel.py`
- Обновлена функция `sanitize_metric_name()` для консистентных названий
- Изменен префикс метрик с `hu_` на `huawei_`
- Убран суффикс `_variable`

### 2. Создан новый генератор дашборда
- **Файл**: `generate_dashboard_fixed.py`
- **Новый маппинг**: `resource_metric_mapping_fixed.py`
- **Результат**: `grafana/provisioning/dashboards/Huawei-OceanStor-Performance.json`

### 3. Правильное распределение метрик
Каждая секция теперь показывает только релевантные метрики:

#### 📊 Controller (39 метрик)
- ✅ CPU метрики: Avg. CPU, KV CPU, Front-End CPU, Back-End CPU
- ✅ Cache метрики: Read/Write Cache Hit Ratio, Cache Water
- ✅ Back-End Traffic
- ✅ NFS/CIFS Operations
- ✅ I/O Granularity Distribution

#### 📊 FC Port (26 метрик)
- ✅ IOPS: Total, Read, Write
- ✅ Bandwidth: Read, Write
- ✅ Performance: Queue Depth, Response Time, I/O Size
- ✅ I/O Granularity Distribution

#### 📊 Storage Pool (13 метрик)
- ✅ Usage
- ✅ IOPS & Bandwidth
- ✅ Performance metrics

#### 📊 Disk Domain (27 метрик)
- ✅ Disk Max. Usage
- ✅ IOPS & Bandwidth
- ✅ Performance metrics
- ✅ I/O Granularity Distribution

#### 📊 LUN (42 метрики)
- ✅ Usage
- ✅ SCSI/ISCSI IOPS
- ✅ Deduplication & Compression
- ✅ VAAI Commands
- ✅ Full Copy, ODX
- ✅ I/O Granularity Distribution

#### 📊 Host (26 метрик)
- ✅ IOPS & Bandwidth
- ✅ Performance metrics
- ✅ I/O Granularity Distribution

## 📋 Что нужно сделать

### Шаг 1: Очистить VictoriaMetrics
Старые метрики с неправильными названиями нужно удалить:

```bash
# Остановить VictoriaMetrics
docker compose stop victoriametrics

# Удалить данные VictoriaMetrics
sudo rm -rf victoria-metrics-data/

# Запустить VictoriaMetrics
docker compose up -d victoriametrics
```

### Шаг 2: Пере-импортировать данные
Используйте обновленный `csv2vm_parallel.py`:

```bash
# Если у вас есть CSV файл
python3 csv2vm_parallel.py Data2csv/output/2102353TJWFSP3100020.csv

# Или используйте полный pipeline
python3 huawei_to_vm_pipeline.py -i "Data2csv/logs/Storage_History_Performance_Files (1).zip"
```

### Шаг 3: Обновить дашборд в Grafana
1. Откройте Grafana: http://localhost:3000
2. Перейдите в Dashboards
3. Найдите дашборд "Huawei OceanStor Performance"
4. Или подождите автоматической перезагрузки (provisioning)

### Шаг 4: Проверить данные
1. Выберите массив в переменной `$array`
2. Выберите элементы в переменной `$Element`
3. Разверните секции (Controller, FC Port, LUN и т.д.)
4. Убедитесь, что графики показывают данные

## 🎯 Результат

- ✅ Правильные названия метрик: `huawei_kv_cpu_usage_percent`
- ✅ CPU метрики только в секции Controller
- ✅ Disk метрики только в секциях Disk Domain и LUN
- ✅ Каждая секция показывает только применимые метрики
- ✅ Жесткая привязка секций к Resource ID
- ✅ Уменьшено количество панелей с 336 до 173 (только релевантные)

## 📊 Статистика

**Было**:
- 6 секций × 56 одинаковых метрик = **336 панелей**
- Все метрики во всех секциях (неправильно!)

**Стало**:
- Controller: 39 метрик
- FC Port: 26 метрик
- Storage Pool: 13 метрик
- Disk Domain: 27 метрик
- LUN: 42 метрики
- Host: 26 метрик
- **Итого: 173 панели** (только релевантные!)

## 📝 Файлы проекта

### ✅ Актуальные файлы
- `generate_dashboard_fixed.py` - Исправленный генератор
- `resource_metric_mapping_fixed.py` - Правильный маппинг
- `csv2vm_parallel.py` - Обновленный импортер
- `grafana/provisioning/dashboards/Huawei-OceanStor-Performance.json` - Новый дашборд

### ❌ Устаревшие файлы (можно удалить)
- `generate_dashboard.py` - Старый генератор
- `resource_metric_mapping.py` - Старый маппинг
- `grafana/provisioning/dashboards/HU Perf-Complete.json` - Старый дашборд

