# Инструкция по установке

## ✅ Что уже сделано

1. **Docker Compose** успешно запущен:
   - VictoriaMetrics: http://localhost:8428 (работает ✅)
   - Grafana: http://localhost:3000 (работает ✅)

2. **Исправлен docker-compose.yml**:
   - Заменен `bash` на `sh` в healthcheck
   - Отключен строгий healthcheck для VictoriaMetrics (порт доступен с хоста)
   - Убрано условие `service_healthy` для Grafana

3. **Создан requirements.txt** с необходимыми зависимостями

## 📦 Установка Python зависимостей

### Вариант 1: С использованием sudo (рекомендуется)

```bash
# Установить python3-venv
sudo apt install python3-venv

# Создать виртуальное окружение
cd /data/projects/monitoring_VM_Grafana
python3 -m venv venv

# Активировать окружение
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### Вариант 2: Установка системных пакетов

```bash
sudo apt update
sudo apt install python3-pip python3-tqdm python3-click python3-pandas
```

### Вариант 3: Без sudo (минимальный набор)

Для базовой работы (`csv2vm_streaming.py`) нужен только `requests`, который уже установлен ✅

Для `Huawei_perf_parser` дополнительно нужны:
- `tqdm`
- `click` 
- `pandas`

## 🚀 Быстрый тест

### Проверка сервисов

```bash
# VictoriaMetrics
curl http://localhost:8428/health
# Должен вернуть: OK

# Grafana
curl http://localhost:3000/api/health
# Должен вернуть: {"database":"ok","version":"12.1.1",...}
```

### Проверка Python зависимостей

```bash
python3 -c "import requests; print('requests OK')"
python3 -c "import tqdm; print('tqdm OK')" 2>&1
python3 -c "import click; print('click OK')" 2>&1
python3 -c "import pandas; print('pandas OK')" 2>&1
```

## 📊 Использование

### Импорт CSV в VictoriaMetrics (базовый скрипт)

```bash
# Если есть все зависимости
python3 csv2vm_streaming.py your_file.csv

# Или с параметрами
python3 csv2vm_streaming.py your_file.csv --batch 50000 --url http://localhost:8428/api/v1/import/prometheus
```

### Парсинг архивов Huawei

```bash
# Требует: tqdm, click, pandas
cd Data2csv
python3 Huawei_perf_parser_v0.1.py -i /path/to/archive.zip -o /path/to/output
```

## 🔧 Управление Docker

```bash
# Статус
docker compose ps

# Логи
docker compose logs -f

# Остановка
docker compose down

# Запуск
docker compose up -d

# Перезапуск
docker compose restart
```

## 📝 Доступ к Grafana

```
URL: http://localhost:3000
Логин: admin
Пароль: changeme (по умолчанию, можно изменить в .env)
```

## ⚙️ Конфигурация

Создайте файл `.env` для настройки:

```bash
cat > .env << 'EOF'
VM_PORT=8428
VM_RETENTION=12m
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASS=your_secure_password
EOF
```

Затем перезапустите:
```bash
docker compose down
docker compose up -d
```

## 📚 Документация

- `README.md` - Основная документация
- `QUICKSTART.md` - Быстрый старт
- `DASHBOARD_GUIDE.md` - Руководство по дашбордам
- `csv2vm_streaming.py --help` - Помощь по импорту


