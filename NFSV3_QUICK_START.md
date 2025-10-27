# 🚀 NFSv3 Metrics - Quick Start Guide

## 📌 Проблема

NFSv3 метрики (ID 1099-1138) для Resource "Controller NFSV3" не были правильно определены в `METRIC_DICT.py`.

## ✅ Решение

### Шаг 1: Прочитать полную инструкцию

```bash
cat NFSV3_METRICS_TROUBLESHOOTING.md
```

### Шаг 2: Распарсить архив NFSv3

```bash
python3 Data2csv/Huawei_perf_parser_v0.2_parallel.py \
    -i Data2csv/logs/Perf_3000v6_NFSv3.zip \
    -o ./temp \
    --all-metrics
```

### Шаг 3: Запустить анализ корреляции

```bash
python3 analyze_nfsv3_correlation.py temp/[SN].csv
```

### Шаг 4: Сопоставить с графиками

Для каждого графика из утилиты:
1. Найти пик значения и время (с timezone!)
2. Конвертировать в UTC
3. Искать в CSV:

```bash
# Пример: найти метрику со значением 10,552 в 07:35 UTC
grep "^Controller NFSV3;.*OPS(Number/s);0A" temp/[SN].csv | \
    grep "2025-10-11T07:35:00Z" | \
    awk -F';' '$4 == "10552.0" {print $2}'
```

### Шаг 5: Проверить корреляцию с Response Time

```bash
# 1. Найти высокий Response Time
grep "^Controller NFSV3;NFS V3 CREATE Response Time(us);0A" temp/[SN].csv | \
    awk -F';' '$4 > 3000 {print $5, $4}' | head -5

# 2. Проверить OPS в тот момент
grep "^Controller NFSV3;.*OPS(Number/s);0A" temp/[SN].csv | \
    grep "[TIMESTAMP]" | \
    awk -F';' '{print $2, $4}' | sort -t' ' -k2 -rn | head -10
```

### Шаг 6: Обновить METRIC_DICT.py

```python
"1100": "NFS V3 CREATE OPS(Number/s)",  # ✅ Подтверждено: значение, время, RT
```

### Шаг 7: Перепарсить и проверить

```bash
rm -f temp/*.csv
python3 Data2csv/Huawei_perf_parser_v0.2_parallel.py \
    -i Data2csv/logs/Perf_3000v6_NFSv3.zip \
    -o ./temp \
    --all-metrics

# Проверка
grep "NFS V3 CREATE OPS" temp/[SN].csv | head -5
```

## 📊 Текущий статус

### Подтверждено (3 метрики):

```python
"1100": "NFS V3 CREATE OPS(Number/s)",   # ✅ 275 в 02:01, RT=3,111
"1101": "NFS V3 REMOVE OPS(Number/s)",   # ✅ 10,552 в 07:35, RT=815
"1114": "NFS V3 GETATTR OPS(Number/s)",  # ✅ 618 в 00:05
```

### Требуют определения (37 метрик):

- OPS: 1099, 1102-1113, 1115-1120
- Response Times: 1121-1138

## 📚 Дополнительно

- **Полная инструкция:** `NFSV3_METRICS_TROUBLESHOOTING.md`
- **Скрипт анализа:** `analyze_nfsv3_correlation.py`
- **Troubleshooting Grafana:** `TROUBLESHOOTING_GRAFANA_DASHBOARDS.md`


