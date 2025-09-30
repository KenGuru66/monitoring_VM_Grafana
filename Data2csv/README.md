# Huawei Performance Data Parser

Скрипт для парсинга бинарных файлов производительности Huawei Storage и преобразования их в CSV формат.

## Возможности

- ✅ Автоматическое извлечение и обработка ZIP архивов
- ✅ Рекурсивный поиск всех .tgz файлов в директориях
- ✅ Автоматическое определение серийного номера (SN) из имени файла
- ✅ Группировка данных по SN в отдельные CSV файлы
- ✅ Поддержка множества ресурсов: LUN, Host, Disk, Controller, Storage Pool, Disk Domain, FC Port
- ✅ Сбор 60+ метрик производительности
- ✅ Опциональная отправка данных в InfluxDB

## Установка зависимостей

```bash
pip3 install pandas click tqdm --break-system-packages
# Опционально для отправки в InfluxDB:
pip3 install influxdb --break-system-packages
```

## Использование

### Базовый пример - обработка ZIP архива

```bash
python3 Huawei_perf_parser_v0.1.py \
  -i "logs/Storage_History_Performance_Files.zip" \
  -o output
```

### Обработка директории с .tgz файлами

```bash
python3 Huawei_perf_parser_v0.1.py \
  -i /path/to/tgz/files \
  -o /path/to/output
```

### С фильтрацией по префиксу

Если нужно обработать только файлы определенной модели:

```bash
python3 Huawei_perf_parser_v0.1.py \
  -i "logs/Storage_History_Performance_Files.zip" \
  -o output \
  -p PerfData_OceanStorDorado5500V6
```

### С удалением исходных файлов после обработки

```bash
python3 Huawei_perf_parser_v0.1.py \
  -i /path/to/tgz/files \
  -o output \
  -d
```

### С отправкой в InfluxDB

```bash
python3 Huawei_perf_parser_v0.1.py \
  -i "logs/Storage_History_Performance_Files.zip" \
  -o output \
  --to_db
```

## Параметры

| Параметр | Описание | Обязательный |
|----------|----------|--------------|
| `-i, --input_path` | Путь к директории с .tgz файлами или ZIP архиву | ✅ Да |
| `-o, --output_path` | Путь к директории для вывода CSV файлов | ✅ Да |
| `-l, --log_path` | Путь к директории для логов (по умолчанию: `log`) | ❌ Нет |
| `-d, --is_delete_after_parse` | Удалять исходные файлы после парсинга | ❌ Нет |
| `-r, --resources` | Типы ресурсов для сбора (разделенные запятыми) | ❌ Нет |
| `-m, --metrics` | Типы метрик для сбора (разделенные запятыми) | ❌ Нет |
| `-p, --prefix` | Префикс для фильтрации файлов (напр., `PerfData_OceanStorDorado5500V6`) | ❌ Нет |
| `--to_db` | Отправлять данные в InfluxDB | ❌ Нет |

## Формат входных файлов

Скрипт ожидает файлы в формате:
```
PerfData_<MODEL>_SN_<SERIAL_NUMBER>_SP<N>_<TIMESTAMP>.tgz
```

Пример:
```
PerfData_OceanStorDorado5500V6_SN_2102353TJWFSP3100020_SP1_0_20250912100400.tgz
```

## Формат выходных файлов

CSV файлы создаются с именем серийного номера оборудования:
```
<SERIAL_NUMBER>.csv
```

Формат CSV:
```
Resource;Metric;Element;Value;Timestamp_ISO;Timestamp_Unix
Controller;Read cache hit ratio (%);0A;21;2025-09-11T00:05:00Z;1757538300.0
```

## Обрабатываемые ресурсы (по умолчанию)

- **Controller** (207)
- **FC Port** (212)
- **FC Replication Link** (225)
- **Storage Pool** (216)
- **Disk Domain** (266)
- **Disk** (10)
- **LUN** (11)
- **Host** (21)

## Обрабатываемые метрики (по умолчанию)

Включены 60+ метрик, включая:
- IOPS (Read, Write, Total, SCSI, iSCSI, NFS, CIFS)
- Bandwidth (Read, Write, Backend)
- Cache hit ratio
- CPU usage
- I/O response time
- I/O size distribution
- Queue depth
- И многие другие...

Полный список метрик см. в `METRIC_DICT.py`

## Логи

Логи записываются в директорию `log/`:
- `process_perf_files.log` - основной лог
- `process_perf_files_repeat.log` - детальный лог обработки

## Примеры реальных команд

```bash
# Из примера в документации:
python3 Huawei_perf_parser_v0.1.py \
  -i "logs/Storage_History_Performance_Files (1).zip" \
  -o output_test

# Для продакшн окружения с nohup:
nohup python3 Huawei_perf_parser_v0.1.py \
  -i /storage/hu/vtb/HS_2024/10.7.39.170/10.7.39.170 \
  -o /storage/hu/vtb/HS_2024/10.7.39.170/res \
  -e tgz \
  --to_db > progress.log 2>&1 &
```

## Производительность

Обработка занимает время в зависимости от:
- Количества файлов
- Размера файлов
- Ресурсов системы (CPU, диск)

Пример: ~150 файлов обрабатываются примерно за 13 минут на системе с 1 vCPU, создавая ~22 млн записей в CSV.

## Устранение неполадок

### ModuleNotFoundError: No module named 'influxdb'

Это предупреждение можно игнорировать, если вы не используете опцию `--to_db`.

### Could not extract serial number from file name

Убедитесь, что имена файлов соответствуют формату:
`PerfData_*_SN_<SERIALNUMBER>_SP*`

### File is not Complete

Проверьте целостность архивов. Возможно, файлы повреждены или загрузка была прервана.


