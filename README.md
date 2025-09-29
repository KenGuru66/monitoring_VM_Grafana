# OceanStor Monitoring с VictoriaMetrics и Grafana

Проект для мониторинга систем хранения данных Huawei OceanStor с использованием VictoriaMetrics и Grafana.

## 📋 Оглавление

- [Описание](#описание)
- [Архитектура](#архитектура)
- [Требования](#требования)
- [Быстрый старт](#быстрый-старт)
- [Утилита csv2vm.py](#утилита-csv2vmpy)
- [Работа с Grafana](#работа-с-grafana)
- [Примеры запросов](#примеры-запросов)
- [Troubleshooting](#troubleshooting)

## 📖 Описание

Система позволяет импортировать исторические данные из CSV/TSV файлов OceanStor в VictoriaMetrics и визуализировать их в Grafana.

### Что делает система:
- ✅ Автоматическое определение разделителя CSV (табуляция, точка с запятой, запятая)
- ✅ Преобразование метрик OceanStor в формат Prometheus
- ✅ Загрузка больших объемов данных (batch-режим)
- ✅ Хранение временных рядов в VictoriaMetrics
- ✅ Визуализация в Grafana с автоматическим форматированием времени

## 🏗️ Архитектура

```
CSV файлы → csv2vm.py → VictoriaMetrics (порт 8428) → Grafana (порт 3000)
   (OceanStor)              (импорт)        (хранение)       (визуализация)
```

## 🔧 Требования

### Системные требования:
- Linux (Ubuntu/Debian)
- Python 3.8+
- Docker и Docker Compose
- 2GB+ RAM
- 10GB+ свободного места на диске

### Python зависимости:
```bash
requests
tqdm
```

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd monitoring_VM_Grafana
```

### 2. Установка зависимостей
```bash
python3 -m venv venv
source venv/bin/activate
pip install requests tqdm
```

### 3. Запуск Docker-стека
```bash
# Создать .env файл с настройками
cat > .env << EOF
VM_PORT=8428
VM_RETENTION=12m
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASS=admin
EOF

# Запустить контейнеры
docker compose up -d
```

### 4. Проверка работы сервисов
```bash
# VictoriaMetrics
curl http://localhost:8428/health

# Grafana
curl http://localhost:3000/api/health
```

### 5. Импорт данных
```bash
source venv/bin/activate
python csv2vm.py your_data.csv
```

### 6. Открыть Grafana
Откройте браузер: http://localhost:3000
- Логин: `admin`
- Пароль: `admin` (или значение из `.env`)

## 📊 Утилита csv2vm.py

### Описание
Утилита для импорта CSV/TSV файлов из Huawei OceanStor в VictoriaMetrics.

### Формат входных данных

Файл должен содержать 6 колонок (разделители: табуляция, точка с запятой или запятая):

```
Controller;KV CPU Usage (%);0A;85;2025-09-22T00:05:00Z;1758488700.0
Controller;KV CPU Usage (%);0A;68;2025-09-22T00:06:00Z;1758488760.0
```

**Структура колонок:**
- Колонка 0: Тип лейбла (например, "Controller", "Disk", "Pool")
- Колонка 1: Название метрики (например, "KV CPU Usage (%)")
- Колонка 2: Значение лейбла (например, "0A", "0B")
- Колонка 3: Значение метрики (число)
- Колонка 4: Временная метка ISO-8601 (не используется)
- Колонка 5: **Unix timestamp в секундах** (используется)

### Формат выходных данных

Данные преобразуются в формат Prometheus:
```
huawei_kv_cpu_usage_percent{array="2102353TJWFSP3100020",controller="0A"} 85 1758488700000
```

**Особенности:**
- Префикс `huawei_` добавляется ко всем метрикам
- Пробелы заменяются на `_`
- Символ `%` заменяется на `percent`
- Специальные символы удаляются
- Timestamp конвертируется в миллисекунды

### Использование

#### Базовое использование
```bash
python csv2vm.py data.csv
```

#### С указанием URL VictoriaMetrics
```bash
python csv2vm.py data.csv --url http://victoriametrics:8428/api/v1/import/prometheus
```

#### С настройкой размера batch
```bash
python csv2vm.py data.csv --batch 5000
```

#### Полная команда с всеми параметрами
```bash
python csv2vm.py 2102353TJWFSP3100020.csv \
  --url http://localhost:8428/api/v1/import/prometheus \
  --batch 10000
```

### Параметры

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `file` | Путь к CSV/TSV файлу (обязательный) | - |
| `--url` | URL endpoint VictoriaMetrics | http://localhost:8428/api/v1/import/prometheus |
| `--batch` | Количество строк в одном запросе | 10000 |

### Примеры вывода

**Успешный импорт:**
```
upload: 100%|██████████| 1/1 [00:00<00:00,  4.75it/s]
✅ imported 5760 rows for array 2102353TJWFSP3100020
```

**Ошибка:**
```
❌ File not found: data.csv
❌ No valid data rows found
❌ batch 0: HTTP 400 - cannot parse timestamp
```

### Обработка больших файлов

Для файлов с миллионами строк:
1. Используйте больший batch размер: `--batch 50000`
2. Мониторьте память VictoriaMetrics
3. Проверяйте логи: `docker compose logs victoriametrics`

## 📈 Работа с Grafana

### Первый вход
1. Откройте http://localhost:3000
2. Логин: `admin`, пароль: `admin`
3. При необходимости смените пароль

### Создание дашборда

#### Шаг 1: Создать новый Dashboard
- Нажмите `+` → `Create Dashboard`
- Нажмите `Add visualization`

#### Шаг 2: Выбрать datasource
- Выберите `VictoriaMetrics`

#### Шаг 3: Написать запрос
```promql
huawei_kv_cpu_usage_percent{array="2102353TJWFSP3100020"}
```

#### Шаг 4: Настроить временной диапазон
- В правом верхнем углу выберите диапазон дат
- Пример: `2025-09-22 00:00:00` to `2025-09-24 23:59:59`

#### Шаг 5: Настроить визуализацию
- **Panel title**: "CPU Usage (%)"
- **Unit**: Percent (0-100)
- **Legend**: `{{controller}}`

### Настройка алертов

Создайте алерт для высокой загрузки CPU:

```promql
huawei_kv_cpu_usage_percent > 90
```

## 🔍 Примеры запросов

### Базовые запросы

**Текущее значение CPU:**
```promql
huawei_kv_cpu_usage_percent{array="2102353TJWFSP3100020"}
```

**Только контроллер 0A:**
```promql
huawei_kv_cpu_usage_percent{controller="0A"}
```

### Агрегации

**Средний CPU за последние 5 минут:**
```promql
avg_over_time(huawei_kv_cpu_usage_percent[5m])
```

**Максимальный CPU по всем контроллерам:**
```promql
max(huawei_kv_cpu_usage_percent) by (controller)
```

**Минимальный CPU за час:**
```promql
min_over_time(huawei_kv_cpu_usage_percent[1h])
```

### Продвинутые запросы

**Среднее значение по всем массивам:**
```promql
avg(huawei_kv_cpu_usage_percent) by (array)
```

**Разница между контроллерами:**
```promql
huawei_kv_cpu_usage_percent{controller="0A"} - huawei_kv_cpu_usage_percent{controller="0B"}
```

**Процент времени, когда CPU > 80%:**
```promql
count_over_time((huawei_kv_cpu_usage_percent > 80)[1h:1m]) / 60 * 100
```

## 🛠️ Troubleshooting

### Проблема: Метрики не отображаются в Grafana

**Решение 1:** Проверьте временной диапазон
```bash
# Узнайте диапазон timestamp в ваших данных
head -1 your_data.csv
# Установите правильный диапазон в Grafana
```

**Решение 2:** Проверьте наличие данных
```bash
curl "http://localhost:8428/api/v1/query?query=huawei_kv_cpu_usage_percent"
```

**Решение 3:** Проверьте логи VictoriaMetrics
```bash
docker compose logs victoriametrics | tail -50
```

### Проблема: Ошибка "cannot parse timestamp"

**Причина:** VictoriaMetrics не понимает формат времени

**Решение:** Скрипт автоматически использует колонку 5 (Unix timestamp). Проверьте, что в файле 6 колонок:
```bash
head -1 your_data.csv | awk -F';' '{print NF}'  # должно быть 6
```

### Проблема: Данные слишком старые/новые

**Симптом:** Логи VictoriaMetrics показывают "timestamp outside retention"

**Решение:** Увеличьте retention период:
```bash
# В docker-compose.yml или .env
VM_RETENTION=24m  # 24 месяца
docker compose up -d
```

### Проблема: Медленный импорт

**Решение 1:** Увеличьте batch размер
```bash
python csv2vm.py data.csv --batch 50000
```

**Решение 2:** Проверьте ресурсы Docker
```bash
docker stats
```

### Проблема: VictoriaMetrics не запускается

**Решение:** Проверьте порты и логи
```bash
# Проверить занятые порты
sudo netstat -tulpn | grep 8428

# Посмотреть логи
docker compose logs victoriametrics

# Пересоздать контейнеры
docker compose down -v
docker compose up -d
```

## 📁 Структура проекта

```
monitoring_VM_Grafana/
├── csv2vm.py                           # Утилита импорта
├── docker-compose.yml                  # Docker конфигурация
├── .env                                # Переменные окружения
├── README.md                           # Эта документация
├── venv/                               # Python виртуальное окружение
└── grafana/
    └── provisioning/
        ├── datasources/                # Настройки datasource
        └── dashboards/                 # Дашборды Grafana
```

## 🔐 Безопасность

1. **Измените пароль Grafana** после первого входа
2. **Используйте .env** для секретов (не коммитьте в git)
3. **Ограничьте доступ** к портам 3000 и 8428 файрволлом
4. **Регулярно обновляйте** Docker образы

```bash
# Обновление образов
docker compose pull
docker compose up -d
```

## 📝 Лицензия

MIT License

## 👥 Авторы

Система мониторинга OceanStor

## 🤝 Contributing

Pull requests приветствуются! Для серьезных изменений сначала откройте issue.

## 📞 Поддержка

При возникновении проблем:
1. Проверьте [Troubleshooting](#troubleshooting)
2. Изучите логи: `docker compose logs`
3. Создайте issue в репозитории
