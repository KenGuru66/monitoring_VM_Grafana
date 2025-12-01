# Deployment Guide

Полное руководство по развертыванию системы мониторинга Huawei Storage Performance с нуля.

## 📁 Структура проекта

```
monitoring_VM_Grafana/
├── README.md                          # Главная документация
├── DEPLOYMENT.md                      # Это руководство
├── TROUBLESHOOTING_GRAFANA_DASHBOARDS.md
├── VICTORIAMETRICS_INTEGRATION.md
├── docker-compose.yml                 # Оркестрация Docker
├── env.example                        # Пример переменных окружения
├── requirements.txt                   # Python зависимости (локальный запуск)
│
├── api/                               # FastAPI Backend
│   ├── main.py                        # API endpoints
│   ├── Dockerfile
│   └── requirements.txt
│
├── web/                               # React Frontend
│   ├── src/
│   ├── Dockerfile
│   └── ...
│
├── parsers/                           # Все парсеры
│   ├── streaming_pipeline.py          # Streaming → VictoriaMetrics
│   ├── csv_wide_parser.py             # CSV wide format
│   ├── perfmonkey_parser.py           # Perfmonkey format
│   └── dictionaries/
│       ├── METRIC_DICT.py             # 743+ метрик
│       ├── RESOURCE_DICT.py           # 51+ ресурсов
│       └── METRIC_CONVERSION.py       # Конверсия единиц
│
├── tools/                             # Утилиты
│   ├── batch_import.py                # Массовый импорт
│   ├── victoriametrics_client.py      # VM API клиент
│   └── pdf_extractor/                 # Извлечение метрик из PDF
│
├── grafana/provisioning/              # Grafana dashboards
│   ├── dashboards/
│   │   ├── provider.yml
│   │   └── Huawei-OceanStor-Real-Data.json  # 808+ панелей
│   └── datasources/
│       └── victoriametrics.yml
│
├── test_data/                         # Тестовые данные
├── perfmonkey/                        # Perfmonkey (legacy)
└── tests/                             # Тесты
```

## 🎯 Системные требования

### Hardware
- **CPU:** Минимум 4 ядра, рекомендуется 8+ ядер
- **RAM:** Минимум 8GB, рекомендуется 16GB+
- **Disk:** 
  - System: 20GB для Docker images
  - Data: Зависит от объема данных (рекомендуется SSD)
  - Temp: ~2x размера загружаемых архивов

### Software
- **OS:** Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
- **Docker:** >= 20.10
- **Docker Compose:** >= 2.0
- **Ports:** 3000, 3001, 8000, 8428 должны быть свободны

## 🚀 Быстрый старт (5 минут)

### 1. Клонирование репозитория

```bash
git clone <repository-url> monitoring_VM_Grafana
cd monitoring_VM_Grafana
```

### 2. Настройка переменных окружения

```bash
cp env.example .env
nano .env  # Отредактируйте при необходимости
```

**Минимальная конфигурация `.env`:**
```bash
# Порты (по умолчанию)
VM_PORT=8428
GRAFANA_PORT=3000
API_PORT=8000
WEB_PORT=3001

# Grafana
GRAFANA_ADMIN_PASS=changeme

# Важно: замените localhost на IP сервера для внешнего доступа
GRAFANA_URL=http://YOUR_SERVER_IP:3000
VITE_API_URL=http://YOUR_SERVER_IP:8000
VITE_GRAFANA_URL=http://YOUR_SERVER_IP:3000
```

### 3. Создание директорий для данных

```bash
# На хост-системе создайте директории для persistent storage
sudo mkdir -p /data/vmdata /data/jobs /data/grafana
sudo chown -R $(id -u):$(id -g) /data/vmdata /data/jobs /data/grafana
```

### 4. Запуск

```bash
# Сборка и запуск всех сервисов
docker compose up -d

# Проверка статуса
docker compose ps
```

### 5. Проверка работоспособности

```bash
# API
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# VictoriaMetrics
curl http://localhost:8428/-/healthy
# Expected: OK

# Web UI - откройте в браузере
http://localhost:3001

# Grafana - откройте в браузере
http://localhost:3000  # admin / changeme
```

## 📦 Полное развертывание

### Установка Docker (если не установлен)

#### Ubuntu/Debian
```bash
# Обновление системы
sudo apt-get update && sudo apt-get upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker

# Установка Docker Compose
sudo apt-get install docker-compose-plugin -y
```

#### CentOS/RHEL
```bash
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y

sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### Настройка firewall

```bash
# Ubuntu (ufw)
sudo ufw allow 3001/tcp comment "Web UI"
sudo ufw allow 8000/tcp comment "API"
sudo ufw allow 3000/tcp comment "Grafana"
sudo ufw allow 8428/tcp comment "VictoriaMetrics"

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=3001/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=8428/tcp
sudo firewall-cmd --reload
```

### Полная конфигурация .env

```bash
# VictoriaMetrics
VM_PORT=8428
VM_RETENTION=6  # Месяцев хранения данных

# Grafana
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASS=your_secure_password
GRAFANA_URL=http://your-server-ip:3000

# API
API_PORT=8000
MAX_UPLOAD_SIZE=10737418240  # 10GB в байтах
JOB_TIMEOUT=86400            # 24 часа
JOB_TTL_HOURS=24             # Автоочистка jobs через 24 часа
WORKER_CONCURRENCY=4

# Web UI
WEB_PORT=3001
VITE_API_URL=http://your-server-ip:8000
VITE_GRAFANA_URL=http://your-server-ip:3000
```

## 🔧 Использование

### Web UI (http://localhost:3001)

1. **Home Page:**
   - Список массивов в VictoriaMetrics
   - Data Collection Interval для каждого массива
   - Прямые ссылки в Grafana с автоматическим временным диапазоном
   - Управление CSV jobs

2. **Upload Page:**
   - Drag & Drop загрузка ZIP архивов
   - Выбор режима обработки:
     - **Parse → Grafana** - streaming в VictoriaMetrics
     - **Parse → CSV (Wide)** - экспорт в широком формате
     - **Parse → CSV (Perfmonkey)** - формат perfmonkey

### Grafana (http://localhost:3000)

- 16 секций с 808+ панелями
- Поддержка всех типов ресурсов Huawei
- Автоматическая адаптация интервала запросов

### Batch Import (CLI)

```bash
# Массовый импорт из директории
python3 tools/batch_import.py /path/to/logs/

# С пропуском уже импортированных
python3 tools/batch_import.py /path/to/logs/ --skip-existing

# Dry-run режим
python3 tools/batch_import.py /path/to/logs/ --dry-run
```

### Локальный запуск парсеров

```bash
# Установка зависимостей
pip install -r requirements.txt

# Streaming pipeline
python3 parsers/streaming_pipeline.py -i archive.zip --vm-url http://localhost:8428/api/v1/import/prometheus

# CSV wide format
python3 parsers/csv_wide_parser.py -i archive.zip -o ./output --all-metrics

# Perfmonkey format
python3 parsers/perfmonkey_parser.py archive.zip -o ./output
```

## 📊 Мониторинг и обслуживание

### Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f api
docker compose logs -f victoriametrics
docker compose logs -f grafana
```

### Перезапуск сервисов

```bash
# Перезапуск всех
docker compose restart

# Перезапуск конкретного
docker compose restart api
```

### Обновление

```bash
cd monitoring_VM_Grafana
git pull
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Backup данных

```bash
# VictoriaMetrics данные
tar -czf vm_backup_$(date +%Y%m%d).tar.gz /data/vmdata

# Grafana данные
tar -czf grafana_backup_$(date +%Y%m%d).tar.gz /data/grafana

# CSV jobs
tar -czf jobs_backup_$(date +%Y%m%d).tar.gz /data/jobs
```

### Очистка

```bash
# Удаление неиспользуемых Docker образов
docker image prune -a -f

# Удаление старых volumes
docker volume prune -f

# Очистка CSV jobs через API
curl -X DELETE http://localhost:8000/api/files/<job_id>
```

## 🔒 Безопасность (Production)

### 1. Смена пароля Grafana

```bash
docker compose exec grafana grafana-cli admin reset-admin-password <новый_пароль>
```

### 2. Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name monitoring.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name monitoring.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/monitoring.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monitoring.yourdomain.com/privkey.pem;

    # Web UI
    location / {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_read_timeout 600s;
        client_max_body_size 20G;
    }

    # Grafana
    location /grafana/ {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host $host;
    }
}
```

### 3. Systemd service

```bash
# /etc/systemd/system/monitoring.service
[Unit]
Description=Huawei Storage Monitoring
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/monitoring_VM_Grafana
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable monitoring.service
sudo systemctl start monitoring.service
```

## 🚨 Troubleshooting

### Container не запускается

```bash
docker compose logs <service_name>
sudo netstat -tulpn | grep -E '3000|3001|8000|8428'
docker compose down && docker compose up -d
```

### Нет места на диске

```bash
df -h
docker system df
docker system prune -a --volumes -f
```

### Данные не появляются в Grafana

1. Проверьте что данные импортированы в VictoriaMetrics:
   ```bash
   curl "http://localhost:8428/api/v1/label/SN/values"
   ```

2. Проверьте временной диапазон в Grafana (должен соответствовать данным)

3. См. `TROUBLESHOOTING_GRAFANA_DASHBOARDS.md`

## ✅ Checklist развертывания

- [ ] Docker и Docker Compose установлены
- [ ] Директории `/data/vmdata`, `/data/jobs`, `/data/grafana` созданы
- [ ] Файл `.env` настроен с правильным IP сервера
- [ ] `docker compose up -d` выполнен успешно
- [ ] `docker compose ps` показывает все сервисы running
- [ ] Health checks пройдены (API, VM, Web, Grafana)
- [ ] Пароль Grafana изменён
- [ ] Firewall настроен
- [ ] (Production) Reverse proxy и SSL настроены
- [ ] (Production) Systemd service создан

## 🔗 Полезные ссылки

- **VictoriaMetrics:** https://docs.victoriametrics.com/
- **Grafana:** https://grafana.com/docs/
- **Docker:** https://docs.docker.com/
- **FastAPI:** https://fastapi.tiangolo.com/
