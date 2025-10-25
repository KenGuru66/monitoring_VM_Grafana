# 🔧 Инструкция по Траблшутингу Grafana Dashboards
## Huawei Storage Performance Monitoring Project

**Версия:** 1.0  
**Дата:** Октябрь 2025  
**Автор:** AI Assistant  

---

## 📋 Содержание

1. [Обзор](#обзор)
2. [Архитектура данных](#архитектура-данных)
3. [Структура архивов](#структура-архивов)
4. [Пошаговый траблшутинг](#пошаговый-траблшутинг)
5. [Реальный пример: трассировка метрики](#реальный-пример)
6. [Частые проблемы и решения](#частые-проблемы-и-решения)
7. [Полезные команды](#полезные-команды)

---

## 🎯 Обзор

Эта инструкция поможет вам:
- ✅ Проследить путь данных от сырых логов до Grafana
- ✅ Найти и сравнить значения в разных форматах данных
- ✅ Диагностировать проблемы с отображением в dashboard
- ✅ Исправить несоответствия в названиях метрик

---

## 🏗️ Архитектура данных

### Путь данных: от логов до Grafana

```
┌─────────────────────────────────────────────────────────────────┐
│                         ПУТЬ ДАННЫХ                              │
└─────────────────────────────────────────────────────────────────┘

1️⃣ СЫРЫЕ ЛОГИ (.zip архивы)
   ├── Storage_History_Performance_*.zip
   └── Содержит: .tgz файлы

2️⃣ АРХИВЫ TGZ (.tgz файлы)
   ├── PerfData_OceanStorDorado6000V6_SN_2102355THQFSQ2100014_SP0_0_20251020000400.tgz
   └── Содержит: .dat файл (бинарные данные)

3️⃣ БИНАРНЫЕ ДАННЫЕ (.dat файлы)
   ├── PerfData_*.dat
   ├── Структура:
   │   ├── Заголовок файла (SN, Equipment Name)
   │   ├── Временные блоки (StartTime, EndTime, Archive=интервал)
   │   ├── Карта метрик (Resource ID, Metric ID, Element Names)
   │   └── Бинарные значения (4 байта на значение, signed int32)
   └── Парсеры:
       ├── huawei_streaming_pipeline.py → VictoriaMetrics
       └── Huawei_perf_parser_v0.2_parallel.py → CSV

4️⃣ CSV ФАЙЛЫ (опционально)
   ├── 2102355THQFSQ2100014.csv
   ├── Формат: Resource;Metric;Element;Value;Timestamp;UnixTime
   └── Применяется METRIC_CONVERSION (KB→MB, us→ms)

5️⃣ VICTORIAMETRICS (Time-series БД)
   ├── URL: http://localhost:8428
   ├── Формат Prometheus:
   │   huawei_metric_name{Element="X",Resource="Y",SN="Z",scrape_interval="60"} value timestamp_ms
   └── Применяется:
       ├── sanitize_metric_name() - очистка названий
       └── METRIC_CONVERSION - конверсия единиц

6️⃣ GRAFANA (Визуализация)
   ├── URL: http://localhost:3000
   ├── Dashboard: Huawei-OceanStor-Real-Data.json
   └── Queries: PromQL запросы к VictoriaMetrics
```

---

## 📦 Структура архивов

### Иерархия файлов

```
Storage_History_Performance_DOrado6000v6_FC_link_trans.zip
├── 2025-10-20/
│   ├── PerfData_..._SN_2102355THQFSQ2100014_SP0_0_20251020000400.tgz
│   │   └── PerfData_..._SP0_0_20251020000400.dat (бинарный)
│   ├── PerfData_..._SN_2102355THQFSQ2100014_SP1_0_20251020000400.tgz
│   │   └── PerfData_..._SP1_0_20251020000400.dat
│   └── ... (300 файлов)
└── 2025-10-21/
    └── ... (еще файлы)
```

### Структура имени файла

```
PerfData_OceanStorDorado6000V6_SN_2102355THQFSQ2100014_SP0_0_20251020000400.tgz
         └─────┬─────┘              └──────┬──────┘  └┬┘ └──────┬──────┘
              Model                    Serial Number  │    Дата и время
                                                   SP  │    (YYYYMMDDHHMMSS)
                                                    0  └─ Controller 0 or 1
```

### Структура .dat файла (бинарный)

```
[Заголовок файла]
├── bit_correct (32 байта)
├── bit_msg_version (4 байта)
├── bit_equip_sn (256 байт) → "SN_2102355THQFSQ2100014"
├── bit_equip_name (41 байт) → "OceanStorDorado6000V6"
└── bit_equip_data_length (4 байта)

[Временной блок 1]
├── bit_map_type (4 байта)
├── bit_map_length (4 байта)
├── bit_map_value (JSON внутри):
│   ├── "StartTime": "1760918640"  (Unix timestamp)
│   ├── "EndTime": "1760919540"
│   ├── "Archive": "60"  (интервал сбора, секунды)
│   └── "Map": {
│       "212": {  ← Resource ID (FC Port)
│         "IDs": ["0", "1", ...],  ← ID элементов
│         "Names": ["CTE0.A.IOM0.P0", ...],
│         "DataTypes": ["1183", ...]  ← Metric IDs
│       }
│     }
└── [Бинарные данные метрик]
    └── 4 байта (signed int32) × количество_элементов × количество_метрик × количество_точек

[Временной блок 2]
└── ... (повторяется)
```

---

## 🔍 Пошаговый траблшутинг

### Шаг 1: Проверка данных в Grafana

**Проблема:** Dashboard показывает "No data"

**Действия:**

1. **Откройте Grafana dashboard:**
   ```
   http://localhost:3000/d/huawei-oceanstor-real/huawei-oceanstor-real-data
   ```

2. **Проверьте временной диапазон:**
   - Кликните на время в правом верхнем углу
   - Убедитесь, что диапазон покрывает период ваших данных
   - ⚠️ **ВАЖНО:** Данные из архивов могут быть в "будущем" или "прошлом"

3. **Проверьте переменные:**
   - `$SN` - серийный номер массива
   - `$Element` - конкретный элемент (порт, диск, LUN)
   - `$Resource` - тип ресурса (FC Port, Controller, Disk)

4. **Проверьте Query в панели:**
   - Кликните на название панели → Edit
   - Проверьте PromQL запрос, например:
     ```
     huawei_read_i_o_granularity_distribution_128kinfpercent{SN=~"$SN", Resource=~"FC Port", Element=~"$Element"}
     ```

---

### Шаг 2: Проверка данных в VictoriaMetrics

**Проверка 1: Есть ли вообще данные для SN?**

```bash
curl -s "http://localhost:8428/api/v1/label/SN/values?start=1571875200&end=1730000000" | jq -r '.data[]'
```

**Ожидаемый результат:**
```
2102355THQFSQ2100014
```

**Если пусто** → данные не загружены, нужно запустить streaming pipeline.

---

**Проверка 2: Какие ресурсы есть для этого SN?**

```bash
curl -s "http://localhost:8428/api/v1/label/Resource/values?match[]=\{SN=\"2102355THQFSQ2100014\"\}&start=1571875200&end=1730000000" | jq -r '.data[]'
```

**Ожидаемый результат:**
```
Controller
FC Port
Disk
LUN
...
```

---

**Проверка 3: Какие метрики есть для FC Port?**

```bash
curl -s "http://localhost:8428/api/v1/series?match[]=%7BSN=%222102355THQFSQ2100014%22,Resource=%22FC+Port%22%7D&start=1571875200&end=1730000000" | jq -r '.data[].__name__' | grep granularity | sort -u
```

**Ожидаемый результат:**
```
huawei_read_i_o_granularity_distribution_0k4kpercent
huawei_read_i_o_granularity_distribution_128kinfpercent
huawei_read_i_o_granularity_distribution_16k32k_percent
...
```

---

**Проверка 4: Узнать временной диапазон данных**

```bash
curl -s "http://localhost:8428/api/v1/query_range?query=huawei_read_bandwidth_mb_s%7BSN=%222102355THQFSQ2100014%22,Resource=%22FC+Port%22%7D&start=1571875200&end=1761341929&step=86400" | jq '.data.result[0] | {metric: .metric, first: .values[0], last: .values[-1]}'
```

**Ожидаемый результат:**
```json
{
  "metric": {
    "__name__": "huawei_read_bandwidth_mb_s",
    "Element": "CTE0.A.IOM0.P0",
    "Resource": "FC Port",
    "SN": "2102355THQFSQ2100014",
    "scrape_interval": "60"
  },
  "first": [1760918400, "405"],  ← Unix timestamp, значение
  "last": [1761091200, "695"]
}
```

**Конвертация Unix timestamp в дату:**
```bash
date -d @1760918400 '+%Y-%m-%d %H:%M:%S'
# Результат: 2025-10-20 00:00:00
```

---

**Проверка 5: Получить конкретное значение метрики**

```bash
curl -s "http://localhost:8428/api/v1/query_range?query=huawei_read_i_o_granularity_distribution_128kinfpercent%7BSN=%222102355THQFSQ2100014%22,Resource=%22FC+Port%22,Element=%22CTE0.A.IOM0.P0%22%7D&start=1760918400&end=1761091200&step=3600" | jq '.data.result[0] | {metric: .metric, values: .values | length, first: .values[0], last: .values[-1]}'
```

---

### Шаг 3: Проверка данных в сырых .dat файлах

**Используем специальный скрипт `debug_metric_value.py`:**

```bash
# 1. Распаковать .tgz файл
unzip -p Data2csv/logs/ARCHIVE.zip "2025-10-20/PerfData_*_SP0_0_20251020000400.tgz" | tar -xzf - -C temp_debug/

# 2. Запустить скрипт поиска значения
python3 debug_metric_value.py \
    temp_debug/PerfData_*.dat \
    212 \
    1183 \
    "CTE0.A.IOM0.P0" \
    "2025-10-20 00:01:00"
```

**Параметры:**
- `212` - Resource ID (FC Port, см. `Data2csv/RESOURCE_DICT.py`)
- `1183` - Metric ID (Read I/O Granularity Distribution: [128K,+∞), см. `Data2csv/METRIC_DICT.py`)
- `"CTE0.A.IOM0.P0"` - Element Name (имя порта)
- `"2025-10-20 00:01:00"` - целевое время

**Вывод скрипта:**
```
================================================================================
🔍 ПОИСК ЗНАЧЕНИЯ МЕТРИКИ В СЫРОМ .DAT ФАЙЛЕ
================================================================================
📁 Файл: PerfData_OceanStorDorado6000V6_SN_2102355THQFSQ2100014_SP0_0_20251020000400.dat
📊 Ресурс: FC Port (ID: 212)
📈 Метрика: Read I/O Granularity Distribution: [128K,+∞)(%) (ID: 1183)
🎯 Элемент: CTE0.A.IOM0.P0
⏰ Целевое время: 2025-10-20 00:01:00
================================================================================

📋 Заголовок файла:
   Serial Number: SN_2102355THQFSQ2100014
   Equipment Name: OceanStorDorado6000V6

📅 Временной блок:
   Начало: 2025-10-20 00:04:00
   Конец:  2025-10-20 00:19:00
   Интервал сбора: 60s
   Количество точек: 15

✅ Найдена метрика!
   Ресурс: 212 (FC Port)
   Метрика: 1183 (Read I/O Granularity Distribution: [128K,+∞)(%))
   Элемент: CTE0.A.IOM0.P0

📊 Значения в этом блоке:
   [  0] 2025-10-20 00:04:00 | Значение:     15
   [  1] 2025-10-20 00:05:00 | Значение:     16
   [  2] 2025-10-20 00:06:00 | Значение:     19
   [  3] 2025-10-20 00:07:00 | Значение:     14
   [  4] 2025-10-20 00:08:00 | Значение:     16
   ...
```

---

### Шаг 4: Проверка данных в CSV (опционально)

**Генерация CSV:**

```bash
python3 Data2csv/Huawei_perf_parser_v0.2_parallel.py \
    -i Data2csv/logs/ARCHIVE.zip \
    -o temp_csv/ \
    --all-metrics
```

**Поиск значения в CSV:**

```bash
# Формат CSV: Resource;Metric;Element;Value;Timestamp;UnixTime
grep "FC Port;Read I/O Granularity Distribution: \[128K,+∞\](%);CTE0.A.IOM0.P0" \
    temp_csv/2102355THQFSQ2100014.csv | \
    grep "2025-10-20T00:0[4-6]" | \
    head -5
```

**Пример вывода:**
```
FC Port;Read I/O Granularity Distribution: [128K,+∞)(%);CTE0.A.IOM0.P0;15.0;2025-10-20T00:04:00Z;1760918640.0
FC Port;Read I/O Granularity Distribution: [128K,+∞)(%);CTE0.A.IOM0.P0;16.0;2025-10-20T00:05:00Z;1760918700.0
FC Port;Read I/O Granularity Distribution: [128K,+∞)(%);CTE0.A.IOM0.P0;19.0;2025-10-20T00:06:00Z;1760918760.0
```

---

## 📊 Реальный пример: трассировка метрики

### Проблема

Dashboard для FC Port, панель **"Read I/O Granularity Distribution: [128K,+∞)"** показывает "No data".

### Метрика

- **Название:** Read I/O Granularity Distribution: [128K,+∞)(%)
- **Resource ID:** 212 (FC Port)
- **Metric ID:** 1183
- **Element:** CTE0.A.IOM0.P0
- **Время:** 2025-10-20 00:04:00

---

### 🔍 Диагностика

#### 1️⃣ Проверяем VictoriaMetrics

```bash
# Получаем список всех метрик granularity
curl -s "http://localhost:8428/api/v1/label/__name__/values?start=1571875200&end=1730000000" | \
    jq -r '.data[]' | grep granularity

# Результат:
# huawei_read_i_o_granularity_distribution_128kinfpercent  ← ЕСТЬ!
```

✅ Метрика **существует** в VictoriaMetrics.

---

#### 2️⃣ Проверяем Query в Grafana Dashboard

```bash
# Смотрим что написано в dashboard JSON
grep -A5 "Read I/O Granularity Distribution: \[128K,+∞\)" \
    grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json | \
    grep "expr"

# Результат для FC Port (строка 90318):
# "expr": "huawei_read_i_o_granularity_distribution_128kinf_percent{...}"
#                                                            ^^^
#                                                    ПОДЧЕРКИВАНИЕ!
```

❌ **Проблема найдена!** В dashboard используется:
```
huawei_read_i_o_granularity_distribution_128kinf_percent
                                            ^^^
```

А в VictoriaMetrics метрика называется:
```
huawei_read_i_o_granularity_distribution_128kinfpercent
                                            ^^^
                                        БЕЗ ПОДЧЕРКИВАНИЯ
```

---

#### 3️⃣ Исправляем Dashboard

```bash
# Найти и заменить в JSON
sed -i 's/128kinf_percent/128kinfpercent/g' \
    grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json

# Перезагрузить Grafana
docker compose restart grafana
```

---

#### 4️⃣ Проверяем значения

**В сыром .dat файле:**
```
2025-10-20 00:04:00 | Значение: 15
2025-10-20 00:05:00 | Значение: 16
2025-10-20 00:06:00 | Значение: 19
```

**В VictoriaMetrics:**
```bash
curl -s "http://localhost:8428/api/v1/query?query=huawei_read_i_o_granularity_distribution_128kinfpercent%7BSN=%222102355THQFSQ2100014%22,Resource=%22FC+Port%22,Element=%22CTE0.A.IOM0.P0%22%7D&time=1760918640" | jq '.data.result[0].value'

# Результат: [1760918640, "15"]
```

✅ **Значения совпадают!**

---

### 🎯 Почему возникла проблема?

#### Функция sanitize_metric_name() в streaming pipeline

```python
def sanitize_metric_name(name: str) -> str:
    """Преобразует название метрики в формат Prometheus."""
    result = name.replace("(%)", "percent").replace(" (%)", "_percent")
    result = result.replace("(", "").replace(")", "")
    result = result.replace("+∞", "inf").replace("+", "plus").replace("∞", "inf")
    result = result.replace("/", "_").replace("-", "_")
    # ...
    result = "_".join(result.lower().split())  # ← Убирает пробелы
    while "__" in result:
        result = result.replace("__", "_")     # ← Убирает двойные подчеркивания
    return result.strip("_")
```

**Трансформация названия:**
```
Read I/O Granularity Distribution: [128K,+∞)(%)
                ↓ replace (%)", "percent")
Read I/O Granularity Distribution: [128K,+∞)percent
                ↓ replace "+∞", "inf"
Read I/O Granularity Distribution: [128Kinf)percent
                ↓ replace "[", "", "]", ""
Read I/O Granularity Distribution: 128Kinfpercent
                ↓ "_".join(lower().split())
read_i_o_granularity_distribution_128kinfpercent
                ↓ добавляем префикс "huawei_"
huawei_read_i_o_granularity_distribution_128kinfpercent
```

✅ **Правильное название** (БЕЗ подчеркивания перед "percent")

---

## 🚨 Частые проблемы и решения

### Проблема 1: "No data" в Grafana

**Причины:**
1. ❌ Неправильный временной диапазон
2. ❌ Неправильное название метрики в Query
3. ❌ Данные не загружены в VictoriaMetrics
4. ❌ Неправильные фильтры (`$SN`, `$Element`, `$Resource`)

**Решение:**
1. Проверьте наличие данных в VM (см. Шаг 2)
2. Сравните название метрики в Query и VM
3. Проверьте временной диапазон данных
4. Проверьте переменные dashboard

---

### Проблема 2: Несоответствие названий метрик

**Симптомы:**
- Dashboard Query: `huawei_metric_name_wrong`
- VictoriaMetrics: `huawei_metric_name_correct`

**Причина:**
Метрика была переименована в `sanitize_metric_name()`, но dashboard не обновлён.

**Решение:**
```bash
# 1. Узнать правильное название в VM
curl -s "http://localhost:8428/api/v1/label/__name__/values" | \
    jq -r '.data[]' | grep <pattern>

# 2. Обновить dashboard JSON
sed -i 's/OLD_NAME/NEW_NAME/g' \
    grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json

# 3. Перезагрузить Grafana
docker compose restart grafana
```

---

### Проблема 3: Данные есть в VM, но не в Grafana

**Причина:** Кеш Grafana или проблемы с datasource.

**Решение:**
```bash
# 1. Проверить datasource
curl http://localhost:3000/api/datasources

# 2. Обновить страницу с Shift+F5 (hard refresh)

# 3. Перезагрузить Grafana
docker compose restart grafana

# 4. Проверить логи
docker compose logs grafana | grep -i error
```

---

### Проблема 4: Unknown Metric IDs в логах

**Симптомы:**
```
WARNING - Found 5 unknown metric IDs in file.dat: ['1234', '5678', ...]
```

**Причина:**
Новые метрики появились в логах, но не добавлены в `METRIC_DICT.py`.

**Решение:**
```bash
# 1. Найти unknown IDs в логах
grep -i "unknown.*IDs" streaming_pipeline.log | \
    grep -oP 'metric IDs.*: \K\[.*\]' | \
    tr ',' '\n' | sort -u

# 2. Добавить в Data2csv/METRIC_DICT.py
# "1234": "New Metric Name",

# 3. Перезапустить парсинг
python3 huawei_streaming_pipeline.py -i logs.zip
```

---

### Проблема 5: Неправильные единицы измерения

**Симптомы:**
- Bandwidth показывает огромные значения (KB вместо MB)
- Latency показывает огромные значения (us вместо ms)

**Причина:**
Метрика не добавлена в `METRIC_CONVERSION.py`.

**Решение:**
```python
# Добавить в Data2csv/METRIC_CONVERSION.py
METRIC_CONVERSION = {
    "311": 1024,  # Throughput (MB/s) - реально в KB/s
    "384": 1000,  # Avg. Read I/O Response Time(us) - делим на 1000 для ms
    # ...
}
```

---

## 🛠️ Полезные команды

### VictoriaMetrics API

```bash
# Получить все SN
curl -s "http://localhost:8428/api/v1/label/SN/values?start=1571875200" | jq

# Получить все метрики для SN
curl -s "http://localhost:8428/api/v1/series?match[]=%7BSN=%22${SN}%22%7D" | \
    jq -r '.data[].__name__' | sort -u

# Получить значение метрики в момент времени
curl -s "http://localhost:8428/api/v1/query?query=${METRIC}%7BSN=%22${SN}%22%7D&time=${UNIX_TS}" | jq

# Получить диапазон значений
curl -s "http://localhost:8428/api/v1/query_range?query=${METRIC}&start=${START}&end=${END}&step=300" | jq

# Удалить все данные для SN
curl -X POST "http://localhost:8428/api/v1/admin/tsdb/delete_series?match[]=%7BSN=%22${SN}%22%7D"
```

---

### Работа с архивами

```bash
# Просмотр содержимого ZIP
unzip -l archive.zip | head -20

# Просмотр содержимого TGZ
tar -tzf file.tgz

# Извлечь конкретный файл из ZIP
unzip -p archive.zip "2025-10-20/PerfData_*_SP0_0_*.tgz" | tar -xzf -

# Найти файлы по дате
unzip -l archive.zip | grep "20251020"
```

---

### Парсинг данных

```bash
# Streaming → VictoriaMetrics (БЕЗ CSV)
python3 huawei_streaming_pipeline.py \
    -i archive.zip \
    --vm-url http://localhost:8428/api/v1/import/prometheus \
    --all-metrics

# CSV парсинг (Wide format)
python3 Data2csv/Huawei_perf_parser_v0.2_parallel.py \
    -i archive.zip \
    -o output_csv/ \
    --all-metrics

# Поиск значения в сырых данных
python3 debug_metric_value.py \
    file.dat \
    <resource_id> \
    <metric_id> \
    "<element>" \
    "YYYY-MM-DD HH:MM:SS"
```

---

### Grafana

```bash
# Перезагрузка
docker compose restart grafana

# Логи
docker compose logs -f grafana

# Проверка datasource
curl http://localhost:3000/api/datasources

# Валидация JSON dashboard
jq . grafana/provisioning/dashboards/Huawei-OceanStor-Real-Data.json > /dev/null
```

---

### Поиск в словарях

```bash
# Найти Metric ID по названию
grep -i "granularity.*128" Data2csv/METRIC_DICT.py

# Найти Resource ID
grep -i "FC Port" Data2csv/RESOURCE_DICT.py

# Проверить конверсию метрики
grep "\"311\"" Data2csv/METRIC_CONVERSION.py
```

---

## 📝 Чек-лист траблшутинга

Когда dashboard показывает "No data":

- [ ] **Шаг 1:** Проверить, что данные загружены в VictoriaMetrics
  ```bash
  curl -s "http://localhost:8428/api/v1/label/SN/values" | jq
  ```

- [ ] **Шаг 2:** Проверить временной диапазон данных
  ```bash
  curl -s "http://localhost:8428/api/v1/query_range?..." | jq '.data.result[0].values | [.[0], .[-1]]'
  ```

- [ ] **Шаг 3:** Установить правильный временной диапазон в Grafana
  - Кликнуть на время в правом верхнем углу
  - Установить Custom range

- [ ] **Шаг 4:** Проверить название метрики в Query
  ```bash
  grep "expr.*${PANEL_NAME}" grafana/provisioning/dashboards/*.json
  ```

- [ ] **Шаг 5:** Сравнить с названием в VictoriaMetrics
  ```bash
  curl -s "http://localhost:8428/api/v1/label/__name__/values" | jq -r '.data[]' | grep <pattern>
  ```

- [ ] **Шаг 6:** Исправить название, если нужно
  ```bash
  sed -i 's/wrong_name/correct_name/g' grafana/provisioning/dashboards/*.json
  docker compose restart grafana
  ```

- [ ] **Шаг 7:** Проверить значения в сырых данных
  ```bash
  python3 debug_metric_value.py ...
  ```

---

## 🎓 Дополнительные ресурсы

- **README.md** - Общее описание проекта
- **Data2csv/METRIC_DICT.py** - 743 метрики
- **Data2csv/RESOURCE_DICT.py** - 51 тип ресурсов
- **Data2csv/METRIC_CONVERSION.py** - 49 метрик с конверсией
- **huawei_streaming_pipeline.py** - Streaming парсер
- **Data2csv/Huawei_perf_parser_v0.2_parallel.py** - CSV парсер

---

## 📧 Контакты

Если у вас возникли вопросы или нужна помощь:
1. Проверьте эту инструкцию
2. Проверьте README.md
3. Проверьте логи: `streaming_pipeline.log`, `api.log`
4. Используйте `debug_metric_value.py` для детальной диагностики

---

**Последнее обновление:** Октябрь 2025  
**Версия:** 1.0  

