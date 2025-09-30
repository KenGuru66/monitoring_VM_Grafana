# 🚀 Быстрый старт - HU Perf Complete

## Импорт данных

```bash
# Импорт CSV в VictoriaMetrics
python3 csv2vm.py ваш_файл.csv

# Пример
python3 csv2vm.py 2102353TJWFSP3100020.csv
```

## Открыть Grafana

```
http://localhost:3000
```

## Доступные дашборды

1. **HU Perf** - компактный (11 панелей)
2. **HU Perf - Complete** - полный (336 панелей) ⭐

## Структура "HU Perf - Complete"

```
📊 Controller (56 метрик)
   ├─ CPU метрики
   ├─ IOPS
   ├─ Bandwidth
   ├─ Cache
   └─ Latency

📊 FC Port (56 метрик)
📊 Storage Pool (56 метрик)
📊 Disk Domain (56 метрик)
📊 LUN (56 метрик)
📊 Host (56 метрик)
```

## Как использовать

1. Выберите **SN** (серийный номер массива)
2. Выберите **Resource** (тип ресурса) - опционально
3. Выберите **Element** (конкретный элемент) - опционально
4. **Кликните на группу** чтобы развернуть панели
5. Установите **временной диапазон**

## Форматы данных CSV

Ваш CSV должен иметь формат:

```csv
Resource;Metric;Element;Value;ISO_Time;Unix_Time
Controller;KV CPU Usage (%);0A;85;2025-09-22T00:05:00Z;1758488700.0
```

Колонки:
- **Resource**: тип ресурса (Controller, FC Port, Storage Pool, etc.)
- **Metric**: название метрики (Usage (%), Total IOPS (IO/s), etc.)
- **Element**: ID элемента (0A, 0B, disk01, etc.)
- **Value**: значение метрики
- **ISO_Time**: ISO-8601 timestamp (не используется)
- **Unix_Time**: Unix timestamp в секундах

## Примеры метрик

### Performance
- `Usage (%)`
- `Total IOPS (IO/s)`
- `Read IOPS (IO/s)`
- `Write IOPS (IO/s)`
- `Read Bandwidth (MB/s)`
- `Write Bandwidth (MB/s)`

### CPU
- `Avg. CPU Usage (%)`
- `KV CPU Usage (%)`
- `Front-End Partition CPU Usage (%)`
- `Back-End Partition CPU Usage (%)`

### Cache
- `Read Cache Hit Ratio (%)`
- `Write Cache Hit Ratio (%)`
- `Cache Water (%)`

### Latency
- `Avg. Read I/O Response Time (us)`
- `Avg. Write I/O Response Time (us)`
- `Service Time (us)`

## Кастомизация

### Изменить набор метрик

1. Редактируйте `resource_metric_mapping.py`:
```python
DEFAULT_RESOURCES = ["207", "212", ...]
DEFAULT_METRICS = ["18", "22", ...]
```

2. Регенерируйте дашборд:
```bash
python3 generate_dashboard.py
```

3. Перезапустите Grafana:
```bash
docker compose restart grafana
```

## Управление данными

### Удалить все метрики
```bash
curl -X POST http://localhost:8428/api/v1/admin/tsdb/delete_series -d 'match[]={__name__=~"hu_.*"}'
```

### Проверить метрики
```bash
curl 'http://localhost:8428/api/v1/label/__name__/values' | python3 -m json.tool | grep hu_
```

### Проверить конкретную метрику
```bash
curl 'http://localhost:8428/api/v1/query?query=hu_kv_cpu_usage_pct_variable'
```

## Troubleshooting

### Нет данных
1. Проверьте импорт: `curl 'http://localhost:8428/api/v1/label/__name__/values'`
2. Проверьте фильтры (SN, Resource, Element)
3. Проверьте временной диапазон

### Медленная загрузка
1. Не разворачивайте все группы сразу
2. Используйте фильтр Resource
3. Уменьшите временной диапазон

### Дашборд не появился
1. Перезапустите Grafana: `docker compose restart grafana`
2. Проверьте логи: `docker compose logs grafana`

## Полезные команды

```bash
# Статус контейнеров
docker compose ps

# Логи Grafana
docker compose logs -f grafana

# Логи VictoriaMetrics
docker compose logs -f victoriametrics

# Перезапуск всего
docker compose restart

# Остановка
docker compose down

# Запуск
docker compose up -d
```

## Документация

- 📖 Полное руководство: `DASHBOARD_GUIDE.md`
- 🔧 Маппинг метрик: `resource_metric_mapping.py`
- 📊 Генератор: `generate_dashboard.py`
- 💾 Импорт: `csv2vm.py --help`

---

**Версия**: 1.0  
**Дата**: 30.09.2025
