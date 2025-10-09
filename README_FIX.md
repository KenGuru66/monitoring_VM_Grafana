# 🔧 CSV Mode UI Fix Applied

## ✅ Problem Solved

**Issue:** UI показывал кнопку "Open in Grafana" для CSV режимов вместо таблицы файлов.

**Status:** 🟢 **ИСПРАВЛЕНО** - код обновлён, требуется пересборка контейнеров.

## 🚀 Применить исправление (2 минуты)

```bash
cd /data/projects/monitoring_VM_Grafana

# Пересобрать контейнеры
./rebuild.sh

# Очистить кэш браузера: Ctrl+Shift+R

# Протестировать
./test_csv_mode.sh test.zip
```

## 📋 Что изменилось

### ✅ Backend (API)
```python
# Добавлено в GET /api/file/{job_id}/{filename}
headers={
    "Accept-Ranges": "bytes",              # Поддержка докачки
    "Content-Disposition": f'attachment...' # Правильное имя файла
}
```

### ✅ Frontend (Web UI)
```tsx
// Теперь кнопки отображаются правильно
{jobStatus.target === 'grafana' && (
  <OpenInGrafanaButton />  // Только для Grafana
)}

{(jobStatus.target === 'csv' || jobStatus.target === 'perfmonkey') && (
  <FilesTable />  // Таблица файлов для CSV
)}
```

### ✅ Новые возможности
- HTTP Range support для больших файлов (докачка)
- Правильные Content-Type заголовки
- Индикатор загрузки при сжатии файлов
- Улучшенные сообщения об ошибках

## 🧪 Проверка результата

### Автоматический тест
```bash
./test_csv_mode.sh /path/to/test.zip
```

### Ручная проверка

1. **Откройте:** `http://localhost:3001`
2. **Загрузите** ZIP архив
3. **Выберите:** "Parse → CSV (Wide)"
4. **Дождитесь завершения**

**Ожидаемый результат:**
```
✅ НЕТ кнопки "Open in Grafana"
✅ Появляется таблица файлов
✅ Каждый файл можно скачать
✅ Файлы корректно распаковываются
```

## 📊 Сравнение До/После

### ❌ До исправления (НЕПРАВИЛЬНО)
```
[CSV режим завершён]
┌─────────────────────────┐
│                         │
│  [🟠 Open in Grafana]   │  ← ОШИБКА!
│                         │
└─────────────────────────┘
```

### ✅ После исправления (ПРАВИЛЬНО)
```
[CSV режим завершён]
┌─────────────────────────────────────────┐
│ 📁 Generated Files (5)                  │
│ ┌─────────────────────────────────────┐ │
│ │ Filename      │ Size  │ Download    │ │
│ ├─────────────────────────────────────┤ │
│ │ cpu_output... │ 12 MB │ [⬇ Download]│ │
│ │ disk_output...│  8 MB │ [⬇ Download]│ │
│ └─────────────────────────────────────┘ │
│  [🗑️ Delete All Files]                  │
└─────────────────────────────────────────┘
```

## 🔍 Детали изменений

### Файлы изменены
```
api/main.py              (+15 строк)   - HTTP Range support
web/src/Upload.tsx       (+10 строк)   - Условное отображение кнопок
web/src/App.css          (+25 строк)   - Стили индикатора загрузки
```

### Новые файлы
```
rebuild.sh               - Скрипт пересборки
test_csv_mode.sh         - Автотест
FIX_CSV_UI.md           - Эта инструкция
REBUILD_GUIDE.md        - Подробный гайд
CHANGELOG.md            - История изменений
```

## ⚡ Быстрые команды

```bash
# Пересобрать всё
./rebuild.sh

# Тест
./test_csv_mode.sh test.zip

# Логи
docker-compose logs -f api

# Статус
docker-compose ps
```

## 🎯 Проверочный список

После пересборки проверьте:

- [ ] API здоров: `curl http://localhost:8000/health`
- [ ] Web UI загружается: `http://localhost:3001`
- [ ] Загрузка с `target=csv` работает
- [ ] Кнопка Grafana НЕ появляется для CSV
- [ ] Таблица файлов появляется ≤30 сек
- [ ] Скачивание работает
- [ ] Файлы распаковываются
- [ ] Режим Grafana работает отдельно

## 🔧 Устранение проблем

### Всё ещё видна кнопка Grafana?

```bash
# Очистить кэш браузера
Ctrl+Shift+R (или Cmd+Shift+R на Mac)

# Пересобрать веб-контейнер
docker-compose build --no-cache web
docker-compose restart web
```

### Таблица файлов пуста?

```bash
# Проверить статус job
JOB_ID="ваш-job-id"
curl http://localhost:8000/api/status/$JOB_ID

# Проверить файлы на диске
docker exec huawei-api ls -lh /app/jobs/$JOB_ID/

# Логи
docker-compose logs api | grep ERROR
```

### Скачивание не работает?

```bash
# Тест через curl
curl -I http://localhost:8000/api/file/$JOB_ID/cpu_output.csv.gz

# Должны быть заголовки:
# Accept-Ranges: bytes
# Content-Disposition: attachment; filename="cpu_output.csv.gz"
```

## 📚 Дополнительная документация

- **FIX_CSV_UI.md** - Эта инструкция (краткая)
- **REBUILD_GUIDE.md** - Подробный гайд по пересборке
- **CHANGELOG.md** - История версий
- **FEATURE_MULTI_MODE.md** - Полная документация

## ⏱️ Время выполнения

```
┌──────────────────┬──────┬─────────────────────┐
│ Шаг              │ Время│ Действие            │
├──────────────────┼──────┼─────────────────────┤
│ Остановка        │  30s │ docker-compose down │
│ Сборка API       │ 2min │ build --no-cache    │
│ Сборка Web       │ 1min │ build --no-cache    │
│ Запуск           │  30s │ docker-compose up   │
│ Проверка         │  10s │ curl health         │
├──────────────────┼──────┼─────────────────────┤
│ ИТОГО            │ ~5min│ Готово к работе     │
└──────────────────┴──────┴─────────────────────┘
```

## ✅ Критерии успеха

Всё работает, если:

1. ✅ `target=csv` → показывает таблицу файлов
2. ✅ `target=csv` → НЕТ кнопки Grafana
3. ✅ Файлы скачиваются через браузер
4. ✅ Файлы - валидные .csv.gz архивы
5. ✅ `target=grafana` → показывает кнопку Grafana
6. ✅ HTTP Range работает (докачка)
7. ✅ Кнопка Delete удаляет файлы

## 🎉 Готово!

После выполнения `./rebuild.sh` всё должно работать корректно.

При любых проблемах смотрите:
- Логи: `docker-compose logs api web`
- Статус: `docker-compose ps`
- Детали: `REBUILD_GUIDE.md`

---

**Версия:** 2.0.1  
**Дата:** 9 октября 2025  
**Статус:** ✅ Готово к применению


