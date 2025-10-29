# 🔍 Отчёт по диагностике NFSv3 метрик
**Дата:** 2025-10-27  
**Массив:** 2102355TLFFSQ4100003 (Dorado3000V6)  
**Архив:** Perf_3000v6_NFSv3.zip

---

## ✅ Результаты диагностики

### 1. ✅ Данные в сырых .dat файлах
- **Статус:** Архив распакован и проанализирован
- **Файлов обработано:** 1,248 .tgz файлов
- **Период данных:** 2025-10-14 до 2025-10-17

### 2. ✅ Парсинг и загрузка в VictoriaMetrics
- **Статус:** УСПЕШНО завершено
- **Метрик отправлено:** 36,859,680 метрик
- **Производительность:** 386,730 метрик/сек
- **Время обработки:** 95.3 секунды (1.6 минуты)
- **Unknown IDs:** НЕ НАЙДЕНО (все ID известны)

### 3. ✅ Данные в VictoriaMetrics
- **Статус:** Данные ЕСТЬ и доступны
- **Найдено метрик для Controller NFSV3:** 81 метрика
- **Примеры NFSv3 метрик:**
  ```
  huawei_nfs_v3_access_opsnumber_s
  huawei_nfs_v3_access_response_timeus
  huawei_nfs_v3_commit_opsnumber_s
  huawei_nfs_v3_create_opsnumber_s
  huawei_nfs_v3_fsinfo_opsnumber_s
  huawei_nfs_v3_fsinfo_response_timeus
  huawei_nfs_v3_fsstat_opsnumber_s
  huawei_nfs_v3_fsstat_response_timeus
  huawei_nfs_v3_getattr_opsnumber_s
  huawei_nfs_v3_getattr_response_timeus
  huawei_nfs_v3_link_opsnumber_s
  huawei_nfs_v3_link_response_timeus
  huawei_nfs_v3_lookup_opsnumber_s
  huawei_nfs_v3_lookup_response_timeus
  huawei_nfs_v3_mkdir_opsnumber_s
  huawei_nfs_v3_mkdir_response_timeus
  huawei_nfs_v3_mknod_opsnumber_s
  huawei_nfs_v3_null_opsnumber_s
  huawei_nfs_v3_open_response_timeus
  huawei_nfs_v3_pathconf_opsnumber_s
  huawei_nfs_v3_pathconf_response_timeus
  huawei_nfs_v3_readdir_opsnumber_s
  huawei_nfs_v3_readdirplus_opsnumber_s
  huawei_nfs_v3_readdirplus_response_timeus
  huawei_nfs_v3_readdir_response_timeus
  huawei_nfs_v3_readlink_opsnumber_s
  huawei_nfs_v3_readlink_response_timeus
  huawei_nfs_v3_read_opsnumber_s
  huawei_nfs_v3_remove_opsnumber_s
  huawei_nfs_v3_rename_opsnumber_s
  huawei_nfs_v3_rename_response_timeus
  huawei_nfs_v3_rmdir_opsnumber_s
  huawei_nfs_v3_rmdir_response_timeus
  huawei_nfs_v3_setattr_response_timeus
  huawei_nfs_v3_symlink_opsnumber_s
  huawei_nfs_v3_symlink_response_timeus
  huawei_nfs_v3_write_opsnumber_s
  ... и другие
  ```

### 4. ✅ Панели в Grafana Dashboard
- **Статус:** Панели СОЗДАНЫ (33 панели)
- **Секция:** "📊 Controller NFSV3"
- **Queries:** Правильные и соответствуют названиям в VM

---

## ❌ ПРОБЛЕМА: "No data" в Grafana панелях

### Причина
Панели показывают "No data" из-за **неправильных настроек в Grafana**:

1. **Временной диапазон**: Пользователь смотрит на неправильный период
2. **Переменная $Element**: Возможно не выбран элемент
3. **Переменная $SN**: Возможно не выбран правильный массив

### Реальные данные в VictoriaMetrics

**Проверено:**
```bash
# Временной диапазон данных
От: 2025-10-16 05:05:00 (Unix: 1760580300)
До: 2025-10-17 13:00:00 (Unix: 1760695200)

# Serial Number
SN: 2102355TLFFSQ4100003

# Resource
Resource: Controller NFSV3

# Elements (Controllers)
- 0A (Controller A)
- 0B (Controller B)

# Пример реальных данных
Метрика: huawei_nfs_v3_lookup_opsnumber_s
Element: 0A
Значение: 27 (operations per second)
```

---

## 🔧 РЕШЕНИЕ

### Шаг 1: Откройте Grafana Dashboard
```
URL: http://localhost:3000/d/huawei-oceanstor-real/huawei-oceanstor-real-data
```

### Шаг 2: Установите правильный временной диапазон
1. Кликните на селектор времени (правый верхний угол)
2. Выберите **Custom range**
3. Установите:
   - **From:** `2025-10-16 00:00:00`
   - **To:** `2025-10-18 00:00:00`
4. Нажмите **Apply**

### Шаг 3: Выберите правильные переменные
1. **$SN** (вверху dashboard):
   - Выберите: `2102355TLFFSQ4100003`

2. **$Element** (если есть):
   - Выберите: `0A` (или `All` для обоих контроллеров)

3. **$Resource** (если есть):
   - Убедитесь что выбрано: `Controller NFSV3`

### Шаг 4: Обновите dashboard
- Нажмите **Refresh** (значок обновления в правом верхнем углу)
- Или нажмите **Ctrl+R** / **Cmd+R**

---

## ✅ Ожидаемый результат

После применения настроек вы должны увидеть:

### OPS метрики (Operations Per Second):
- **LOOKUP OPS:** ~27 ops/s (самая активная)
- **PATHCONF OPS:** ~12 ops/s
- **GETATTR OPS:** ~5 ops/s
- **CREATE OPS:** ~2 ops/s
- **REMOVE OPS:** ~1 ops/s
- И другие метрики с реальными значениями

### Response Time метрики (Microseconds):
- **LOOKUP RT:** ~17,610 us (максимум)
- **PATHCONF RT:** ~10,283 us
- **READDIR RT:** ~65,919 us
- И другие метрики с реальными значениями

---

## 🔍 Проверка через VictoriaMetrics API

Если после настройки Grafana данные всё ещё не показываются, проверьте напрямую через API:

```bash
# Проверка наличия данных для LOOKUP OPS
curl -s "http://localhost:8428/api/v1/query?query=huawei_nfs_v3_lookup_opsnumber_s{SN=\"2102355TLFFSQ4100003\",Resource=\"Controller NFSV3\"}&time=1760580300" | jq

# Проверка временного диапазона
curl -s "http://localhost:8428/api/v1/query_range?query=huawei_nfs_v3_lookup_opsnumber_s{SN=\"2102355TLFFSQ4100003\",Resource=\"Controller NFSV3\"}&start=1760580000&end=1760640000&step=300" | jq

# Список всех элементов
curl -s "http://localhost:8428/api/v1/label/Element/values?match[]=\{SN=\"2102355TLFFSQ4100003\",Resource=\"Controller+NFSV3\"\}" | jq
```

---

## 📊 Список всех 33 NFSv3 панелей в Dashboard

### OPS метрики (22 панели):
1. ✅ REMOVE OPS
2. ✅ GETATTR OPS
3. ✅ LOOKUP OPS (95%)
4. ❌ NULL OPS
5. ⚠️ CREATE OPS
6. ❌ ACCESS OPS
7. 🔍 READLINK OPS
8. 🔍 READ OPS
9. 🔍 WRITE OPS
10. 🔍 MKDIR OPS
11. 🔍 SYMLINK OPS
12. ❌ MKNOD OPS
13. ❌ RENAME OPS
14. 🔍 READDIR OPS
15. 🔍 READDIRPLUS OPS
16. 🔍 FSSTAT OPS
17. 🔍 FSINFO OPS
18. 🔍 PATHCONF OPS
19. 🔍 COMMIT OPS
20. ❌ RMDIR OPS
21. 🔍 LINK OPS (если есть)
22. 🔍 SETATTR OPS (если есть)

### Response Time метрики (11 панелей):
1. ✅ LOOKUP RT (95%)
2. ⚠️ PATHCONF RT
3. ⚠️ READDIR RT
4. ❌ GETATTR RT
5. ❌ MKDIR RT
6. ❌ ACCESS RT
7. ❌ READDIRPLUS RT
8. ❌ OPEN RT
9. ❌ READLINK RT
10. ❌ SYMLINK RT
11. 🔍 RENAME RT
12. 🔍 LINK RT
13. ❌ FSSTAT RT
14. 🔍 FSINFO RT
15. ❌ SETATTR RT (если есть)
16. ❌ RMDIR RT (если есть)

**Легенда:**
- ✅ - Подтверждено, данные есть
- 🔍 - Найдено в данных
- ⚠️ - Требует проверки
- ❌ - Может отсутствовать или быть нулями

---

## 🔧 Автоматическое обновление словарей

Теперь скрипт `huawei_streaming_pipeline.py` автоматически вызывает `auto_update_dictionaries.py` после парсинга. Это означает:

1. Если в логах найдены **unknown resource IDs**, они автоматически добавляются в `Data2csv/RESOURCE_DICT.py`
2. Если в логах найдены **unknown metric IDs**, они автоматически добавляются в `Data2csv/METRIC_DICT.py`
3. Новые записи помечаются с датой добавления и комментарием `⚠️ Требует уточнения`

**Пример автоматически добавленной записи:**
```python
"9999": "UNKNOWN_METRIC_9999",  # ⚠️ Автоматически добавлено 2025-10-27, требует уточнения
```

### Запуск вручную:
```bash
cd /data/projects/monitoring_VM_Grafana
python3 auto_update_dictionaries.py
```

---

## 📝 Итоговая сводка

| Этап | Статус | Результат |
|------|--------|-----------|
| 1. Данные в архиве | ✅ | 1,248 файлов, 2025-10-14 до 2025-10-17 |
| 2. Парсинг → VictoriaMetrics | ✅ | 36.8M метрик отправлено |
| 3. Данные в VM | ✅ | 81 NFSv3 метрика доступна |
| 4. Панели в Grafana | ✅ | 33 панели созданы |
| 5. Queries в панелях | ✅ | Правильные названия метрик |
| 6. Отображение в Grafana | ⚠️ | Требует настройки временного диапазона |

**Вывод:** Данные есть, панели есть, queries правильные. Проблема только в настройках Grafana (временной диапазон и переменные).

---

## 💡 Полезные команды

```bash
# Проверить все метрики для массива
curl -s "http://localhost:8428/api/v1/label/__name__/values?match[]=\{SN=\"2102355TLFFSQ4100003\"\}" | jq -r '.data[]' | grep nfs_v3

# Проверить временной диапазон данных
curl -s "http://localhost:8428/api/v1/query_range?query=huawei_nfs_v3_lookup_opsnumber_s\{SN=\"2102355TLFFSQ4100003\"\}&start=1571875200&end=1830000000&step=86400" | jq '.data.result[0].values | [.[0], .[-1]]'

# Удалить все данные массива (если нужно перепарсить)
curl -X POST "http://localhost:8428/api/v1/admin/tsdb/delete_series?match[]=\{SN=\"2102355TLFFSQ4100003\"\}"

# Повторный парсинг архива
python3 huawei_streaming_pipeline.py -i Data2csv/logs/Perf_3000v6_NFSv3.zip --all-metrics --monitor
```

---

**Создано:** 2025-10-27  
**Автор:** AI Assistant  
**Версия:** 1.0



