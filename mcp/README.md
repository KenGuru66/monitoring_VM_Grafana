# MCP Server для Huawei Storage VictoriaMetrics

MCP (Model Context Protocol) сервер для доступа к данным производительности и здоровья Huawei Storage из VictoriaMetrics.

**Возможности:**
- Performance метрики (CPU, Bandwidth, Latency, IOPS)
- Health метрики (ECC память, SMART диски, BBU батареи)

## Быстрый старт

### Установка зависимостей

```bash
pip install mcp httpx
```

### Запуск сервера

```bash
# Из директории проекта
python monitoring/mcp/server.py

# Или с указанием URL VictoriaMetrics
VM_URL=http://localhost:8428 python monitoring/mcp/server.py
```

### Настройка в Cursor

Добавьте в `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "huawei-storage-vm": {
      "command": "/usr/bin/python3",
      "args": ["/path/to/monitoring/mcp/server.py"],
      "env": {
        "VM_URL": "http://localhost:8428"
      }
    }
  }
}
```

## Доступные Tools (15 шт.)

### Базовые (метаданные)

| Tool | Описание | Параметры |
|------|----------|-----------|
| `list_arrays` | Список всех SN массивов | - |
| `list_resources` | Типы ресурсов | `sn` (опц.) |
| `list_metrics` | Список метрик | `sn`, `resource` (опц.) |
| `list_elements` | Элементы ресурса | `sn`, `resource` |

### Запросы данных (Performance)

| Tool | Описание | Параметры |
|------|----------|-----------|
| `query_metric` | Текущее значение | `sn`, `resource`, `metric`, `element` (опц.) |
| `query_range` | Значения за период | `sn`, `resource`, `metric`, `start`, `end`, `step` |
| `get_array_summary` | Сводка по массиву | `sn` |

### Аналитика (Performance)

| Tool | Описание | Параметры |
|------|----------|-----------|
| `get_performance_stats` | Статистики с Day/Night | `sn`, `start`, `end`, `time_period` |
| `compare_arrays` | Сравнение двух массивов | `sn1`, `sn2`, `start`, `end` |
| `get_top_loaded` | Топ массивов по нагрузке | `metric`, `limit`, `start` |
| `find_anomalies` | Поиск выбросов | `sn`, `metric`, `start`, `threshold_multiplier` |

### Health Metrics (ECC, SMART, BBU)

| Tool | Описание | Параметры |
|------|----------|-----------|
| `get_ecc_errors` | ECC/MCE ошибки памяти | `sn`, `start`, `end` |
| `get_smart_status` | SMART статус дисков | `sn`, `start`, `end` |
| `get_bbu_status` | Статус BBU батарей | `sn`, `start`, `end` |
| `get_health_summary` | Полная сводка здоровья | `sn`, `start`, `end` |

## Поддерживаемые метрики

### Performance Metrics

| Короткое имя | VM метрика | Единицы |
|--------------|------------|---------|
| `cpu` | huawei_avg_cpu_usage_percent | % |
| `bandwidth_read` | huawei_read_bandwidth_mb_s | MB/s |
| `bandwidth_write` | huawei_write_bandwidth_mb_s | MB/s |
| `latency_read` | huawei_avg_read_i_o_response_timeus | ms |
| `latency_write` | huawei_avg_write_i_o_response_timeus | ms |
| `iops_read` | huawei_read_i_o_s | IOPS |
| `iops_write` | huawei_write_i_o_s | IOPS |
| `rw_ratio` | huawei_ratio_of_read_i_os_to_total_i_os_percent | % |
| `cache` | huawei_avg_cache_usage_percent | % |

### Health Metrics

#### ECC Memory (лейблы: SN, controller, dimm)

| VM метрика | Описание |
|------------|----------|
| `huawei_ecc_total` | Общее количество ECC ошибок на контроллере |
| `huawei_ecc_dimm` | ECC ошибки по каждому DIMM модулю |
| `huawei_mce_dimm` | MCE (критические) ошибки по DIMM |

#### SMART Disk (лейблы: SN, disk_id)

| VM метрика | Описание |
|------------|----------|
| `huawei_smart_disk_health` | Общий показатель здоровья диска (0-100%) |
| `huawei_smart_reallocated_sectors` | ID_5 - переназначенные секторы |
| `huawei_smart_reallocated_events` | ID_196 - события переназначения |
| `huawei_smart_pending_sectors` | ID_197 - секторы в очереди на ремап |
| `huawei_smart_offline_uncorrectable` | ID_198 - неисправимые ошибки offline |
| `huawei_smart_available_spare` | ID_232 - доступный резерв (NVMe/SSD) |
| `huawei_smart_temperature` | Температура диска (°C) |

#### BBU Battery (лейблы: SN, bbu_id)

| VM метрика | Описание |
|------------|----------|
| `huawei_bbu_temperature` | Температура BBU (°C) |
| `huawei_bbu_capacity_percent` | Оставшаяся ёмкость (%) |
| `huawei_bbu_voltage` | Напряжение BBU (V) |

## Параметры времени

| Формат | Пример | Описание |
|--------|--------|----------|
| Относительное | `now-7d` | 7 дней назад |
| Относительное | `now-30d` | 30 дней назад |
| Относительное | `now-180d` | 6 месяцев назад |

## Фильтры времени суток (time_period)

| Значение | Описание | Время (МСК) |
|----------|----------|-------------|
| `all` | Всё время | 24/7 |
| `day` | Дневное время | 08:00 - 22:00 |
| `night` | Ночное время | 22:00 - 08:00 |

## Статистики в ответах

- `max` - максимальное значение
- `avg` - среднее значение
- `median` - медиана (P50)
- `p95` - 95-й перцентиль

## Примеры использования

### Получить список массивов

```python
# В Cursor: "Покажи все массивы"
→ list_arrays()
# Результат: ["2102352VUV10L6000008", "2102352VUV10L6000009", ...]
```

### Получить CPU за неделю

```python
# В Cursor: "CPU usage на массиве X за неделю"
→ query_range(
    sn="2102352VUV10L6000008",
    resource="Controller", 
    metric="huawei_avg_cpu_usage_percent",
    start="now-7d",
    end="now",
    step="1h"
)
```

### Сравнить два массива

```python
# В Cursor: "Сравни массивы X и Y"
→ compare_arrays(
    sn1="2102352VUV10L6000008",
    sn2="2102352VUV10L6000009",
    start="now-7d",
    end="now"
)
```

### Топ 5 по CPU

```python
# В Cursor: "Топ 5 массивов по CPU"
→ get_top_loaded(metric="cpu", limit=5, start="now-7d")
```

### Найти аномалии

```python
# В Cursor: "Найди аномалии latency"
→ find_anomalies(
    sn="2102352VUV10L6000008",
    metric="latency_read",
    start="now-7d",
    threshold_multiplier=1.5
)
```

### Получить ECC ошибки памяти

```python
# В Cursor: "Покажи ECC ошибки на массиве X"
→ get_ecc_errors(sn="2102352VUV10LA000026")
# Результат:
# {
#   "controllers": [{"controller": "CTE0.0A", "total_ecc": 29728}],
#   "dimms": [
#     {"controller": "CTE0.0A", "dimm": "DIMM120", "ecc_errors": 14465},
#     {"controller": "CTE0.0A", "dimm": "DIMM060", "ecc_errors": 14205}
#   ],
#   "has_critical": false
# }
```

### Получить SMART статус дисков

```python
# В Cursor: "Проверь здоровье дисков на массиве X"
→ get_smart_status(sn="2102352VUV10LA000026")
# Результат:
# {
#   "disks": [
#     {"disk_id": "CTE0.A_ROOT.0", "health": 100, "status": "healthy"},
#     {"disk_id": "DAE010.A_ROOT.0", "reallocated_sectors": 50, "status": "warning"}
#   ],
#   "summary": {"total_disks": 4, "healthy": 3, "warning": 1, "critical": 0}
# }
```

### Получить статус BBU

```python
# В Cursor: "Покажи статус батарей BBU"
→ get_bbu_status(sn="2102352VUV10LA000026")
# Результат:
# {
#   "bbus": [
#     {"bbu_id": "CTE0.BBU0", "temperature": 25, "capacity_percent": 95, "status": "healthy"}
#   ],
#   "summary": {"total_bbus": 2, "healthy": 2}
# }
```

### Полная сводка здоровья массива

```python
# В Cursor: "Дай полную сводку здоровья массива X"
→ get_health_summary(sn="2102352VUV10LA000026")
# Результат:
# {
#   "overall_status": "warning",
#   "ecc": {"total_errors": 29728, "dimms_with_errors": 6, "has_mce": false},
#   "smart": {"total_disks": 4, "healthy": 3, "warning": 1, "critical": 0},
#   "bbu": {"total_bbus": 2, "healthy": 2},
#   "recommendations": [
#     "DIMM DIMM120 на CTE0.0A имеет 14465 ECC ошибок - рекомендуется замена"
#   ]
# }
```

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `VM_URL` | http://localhost:8428 | URL VictoriaMetrics |

## Архитектура

```
Cursor IDE ←→ MCP Server (stdio) ←→ VictoriaMetrics HTTP API
```

## Файлы

```
monitoring/mcp/
├── __init__.py    # Инициализация модуля
├── server.py      # MCP сервер с tools
└── README.md      # Документация
```

## Troubleshooting

### Ошибка "too many points"

VictoriaMetrics ограничивает количество точек (30000). Сервер автоматически выбирает step:
- ≤7 дней: 5m
- ≤30 дней: 15m  
- ≤90 дней: 1h
- >90 дней: 6h

### Нет данных

1. Проверьте доступность VM: `curl http://localhost:8428/health`
2. Проверьте наличие данных: `curl "http://localhost:8428/api/v1/label/SN/values"`
3. Проверьте период — данные могут быть только за определённые даты
4. Для Health метрик используйте `start="now-180d"` — данные из логов могут быть старыми

### Нет Health метрик (ECC, SMART, BBU)

Health метрики публикуются при выполнении Health Check:
```bash
docker compose exec api python /app/health_check/health_check.py /app/jobs/archive.7z
```

Проверьте наличие метрик:
```bash
curl "http://localhost:8428/api/v1/query?query=huawei_ecc_total"
curl "http://localhost:8428/api/v1/query?query=huawei_smart_disk_health"
```

### MCP сервер не запускается

1. Проверьте Python: `/usr/bin/python3 --version`
2. Проверьте зависимости: `pip show mcp httpx`
3. Проверьте путь в mcp.json

