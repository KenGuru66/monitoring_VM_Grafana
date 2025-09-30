# 📊 Руководство по дашбордам Huawei OceanStor

## Доступные дашборды

### 1. **HU Perf** (оригинальный)
- Компактный дашборд с основными метриками
- 10 панелей + новая панель KV CPU Usage (%)
- Простая навигация

### 2. **HU Perf - Complete** (полный) ⭐ NEW
- Полный набор метрик для всех ресурсов
- **336 панелей** организованных в 6 групп
- Collapsible rows для удобной навигации

## 🗂️ Структура "HU Perf - Complete"

Дашборд организован по типам ресурсов. Каждая группа содержит 56 метрик:

### 📊 Группы ресурсов

1. **Controller** (Контроллеры)
   - CPU метрики (KV CPU, Avg CPU, Front-End/Back-End Partition CPU)
   - Bandwidth метрики (Read/Write/Total)
   - IOPS метрики
   - Cache метрики
   - I/O характеристики

2. **FC Port** (FC порты)
   - Использование портов
   - Пропускная способность
   - IOPS
   - Статистика I/O

3. **Storage Pool** (Пулы хранения)
   - Использование места
   - Производительность
   - Дедупликация
   - Компрессия

4. **Disk Domain** (Дисковые домены)
   - Использование дисков
   - Производительность
   - RAID метрики

5. **LUN** (Логические Unit Numbers)
   - Использование LUN
   - IOPS и Bandwidth
   - Latency
   - Cache hit ratio

6. **Host** (Хосты)
   - Подключенные хосты
   - I/O статистика
   - Protocol метрики (SCSI/iSCSI/NFS/CIFS)

## 📈 Список всех метрик (56 шт.)

### Performance Metrics
- Usage (%)
- Total/Read/Write IOPS (IO/s)
- Read/Write Bandwidth (MB/s)
- Back-End Traffic (MB/s)
- VAAI Bandwidth (MB/s)

### CPU & Processing
- Avg. CPU Usage (%)
- KV CPU Usage (%)
- Avg. Corrected CPU Usage (%)
- Front-End Partition CPU Usage (%)
- Back-End Partition CPU Usage (%)

### Cache & Memory
- Read Cache Hit Ratio (%)
- Write Cache Hit Ratio (%)
- Cache Water (%)

### Response Times
- Avg. Read I/O Response Time (us)
- Avg. Write I/O Response Time (us)
- Service Time (us)
- Average Queue Depth

### I/O Size Distribution
- Avg. Read/Write/Total I/O Size (KB)
- Read I/O Granularity Distribution: [0K,4K), [4K,8K), [8K,16K), [16K,32K), [32K,64K), [64K,128K), [128K,+∞)
- Write I/O Granularity Distribution: [0K,4K), [4K,8K), [8K,16K), [16K,32K), [32K,64K), [64K,128K), [128K,+∞)

### Protocol Specific
- SCSI IOPS (IO/s)
- iSCSI IOPS (IO/s)
- NFS Operation Count Per Second
- CIFS Operation Count Per Second

### Advanced Features
- Post-Process Deduplication Read/Write Bandwidth (MB/s)
- Post-Process Deduplication Fingerprint Read/Write Bandwidth (MB/s)
- Post-Process Deduplication and Reduction Read/Write Bandwidth (MB/s)
- Full Copy Read/Write Request Bandwidth (MB/s)
- ODX Read/Write Request Bandwidth (MB/s)
- WRITE SAME Command Bandwidth (MB/s)
- Unmap Command Bandwidth (MB/s)

### Storage Metrics
- Disk Max. Usage (%)

## 🚀 Как использовать

### 1. Открыть дашборд
```
http://localhost:3000
```

### 2. Выбрать "HU Perf - Complete" из списка дашбордов

### 3. Настроить фильтры (Variables)

#### **SN** (Serial Number)
Выберите серийный номер вашего массива
- Можно выбрать несколько
- "All" для всех массивов

#### **Resource** (Тип ресурса)
Выберите тип ресурса для фильтрации
- Controller
- FC Port
- Storage Pool
- Disk Domain
- LUN
- Host

#### **Element** (Элемент)
Выберите конкретный элемент
- 0A, 0B (для контроллеров)
- disk01, disk02 (для дисков)
- И т.д.

### 4. Навигация по группам

Каждая группа ресурсов **сворачивается** (collapsed) по умолчанию.
- **Кликните на заголовок группы** чтобы развернуть/свернуть
- Внутри группы панели расположены по 2 в ряд

### 5. Установить временной диапазон

В правом верхнем углу выберите:
- Last 6 hours (по умолчанию)
- Last 24 hours
- Last 7 days
- Custom range

## 📝 Примеры использования

### Анализ производительности контроллера
1. Разверните группу "📊 Controller"
2. Посмотрите:
   - KV CPU Usage (%) - загрузка CPU
   - Read/Write IOPS - операции в секунду
   - Read/Write Bandwidth - пропускная способность
   - Cache Hit Ratio - эффективность кэша

### Мониторинг пула хранения
1. Разверните группу "📊 Storage Pool"
2. Выберите Resource = "Storage Pool"
3. Проверьте:
   - Usage (%) - использование места
   - Total IOPS - нагрузка
   - Deduplication метрики

### Диагностика проблем с LUN
1. Разверните группу "📊 LUN"
2. Выберите конкретный LUN в Element
3. Анализируйте:
   - Response Time - задержки
   - Queue Depth - очередь
   - I/O Size Distribution - паттерны нагрузки

## 🔧 Регенерация дашборда

Если нужно изменить метрики или ресурсы:

1. Отредактируйте `resource_metric_mapping.py`:
```python
DEFAULT_RESOURCES = ["207", "212", ...]  # Добавьте/удалите ресурсы
DEFAULT_METRICS = ["18", "22", ...]      # Добавьте/удалите метрики
```

2. Запустите генератор:
```bash
python3 generate_dashboard.py
```

3. Перезапустите Grafana:
```bash
docker compose restart grafana
```

## 📊 Статистика

- **Ресурсов**: 6
- **Метрик на ресурс**: 56
- **Всего панелей**: 336
- **Формат данных**: Prometheus/VictoriaMetrics
- **Обновление**: Real-time

## 💡 Советы по производительности

1. **Не открывайте все группы одновременно** - это может замедлить браузер
2. **Используйте фильтры** для ограничения объема данных
3. **Сужайте временной диапазон** при детальном анализе
4. **Экспортируйте дашборд** для бэкапа через UI Grafana

## 🆘 Troubleshooting

### Нет данных на графиках
1. Проверьте что данные импортированы: `curl 'http://localhost:8428/api/v1/label/__name__/values'`
2. Убедитесь что выбран правильный SN
3. Проверьте временной диапазон

### Дашборд не появляется
1. Перезапустите Grafana: `docker compose restart grafana`
2. Проверьте логи: `docker compose logs grafana`

### Медленная загрузка
1. Выберите конкретный Resource вместо "All"
2. Уменьшите временной диапазон
3. Используйте фильтр Element для конкретных элементов

---

**Создано**: 30 сентября 2025  
**Версия**: 1.0  
**Совместимость**: Huawei OceanStor, VictoriaMetrics, Grafana 11.0+
