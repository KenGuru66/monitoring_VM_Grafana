# Deployment Guide

Руководство по развертыванию системы мониторинга Huawei Storage Performance.

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
- **Ports:** 8000, 8080, 3000, 8428 должны быть свободны

## 📦 Подготовка сервера

### 1. Установка Docker

#### Ubuntu/Debian
```bash
# Обновление системы
sudo apt-get update
sudo apt-get upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo apt-get install docker-compose-plugin -y
```

#### CentOS/RHEL
```bash
# Установка Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y

# Запуск Docker
sudo systemctl start docker
sudo systemctl enable docker

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
```

### 2. Настройка firewall

```bash
# Ubuntu (ufw)
sudo ufw allow 8080/tcp comment "Web UI"
sudo ufw allow 8000/tcp comment "API"
sudo ufw allow 3000/tcp comment "Grafana"

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --reload
```

### 3. Настройка хранилища

```bash
# Создание директорий для данных
sudo mkdir -p /data/monitoring/{vm_data,jobs_data,grafana}
sudo chown -R $(id -u):$(id -g) /data/monitoring

# Опционально: монтирование отдельного диска
# sudo mkfs.ext4 /dev/sdb
# sudo mount /dev/sdb /data/monitoring
# echo "/dev/sdb /data/monitoring ext4 defaults 0 0" | sudo tee -a /etc/fstab
```

## 🚀 Развертывание

### Шаг 1: Клонирование репозитория

```bash
cd /opt
sudo git clone <repository-url> monitoring_VM_Grafana
cd monitoring_VM_Grafana
sudo chown -R $USER:$USER .
```

### Шаг 2: Конфигурация

```bash
# Копирование примера конфигурации
cp env.example .env

# Редактирование конфигурации
nano .env
```

**Важные параметры .env:**

```bash
# VictoriaMetrics URLs
VM_URL=http://victoriametrics:8428
VM_IMPORT_URL=http://victoriametrics:8428/api/v1/import/prometheus

# Grafana URL (внешний адрес)
GRAFANA_URL=http://your-server-ip:3000

# Размер загружаемых файлов (в байтах)
MAX_UPLOAD_SIZE=21474836480  # 20GB

# Таймауты
JOB_TIMEOUT=86400      # 24 часа
JOB_TTL_HOURS=24       # Автоудаление jobs через 24 часа

# Рабочая директория для CSV файлов
WORK_DIR=/app/jobs
```

### Шаг 3: Настройка docker-compose.yml

Если нужно изменить пути к данным:

```yaml
volumes:
  vm_data:
    driver: local
    driver_opts:
      type: none
      device: /data/monitoring/vm_data
      o: bind

  jobs_data:
    driver: local
    driver_opts:
      type: none
      device: /data/monitoring/jobs_data
      o: bind

  grafana_data:
    driver: local
    driver_opts:
      type: none
      device: /data/monitoring/grafana
      o: bind
```

### Шаг 4: Запуск

```bash
# Сборка образов
docker compose build

# Запуск сервисов
docker compose up -d

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f
```

### Шаг 5: Проверка работоспособности

```bash
# API health check
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# VictoriaMetrics health
curl http://localhost:8428/-/healthy
# Expected: OK

# Web UI
curl -I http://localhost:8080
# Expected: HTTP/1.1 200 OK

# Grafana
curl -I http://localhost:3000
# Expected: HTTP/1.1 200 OK
```

## 🔒 Настройка безопасности

### 1. Grafana Security

```bash
# Изменение дефолтного пароля
docker compose exec grafana grafana-cli admin reset-admin-password <новый_пароль>

# Или через UI:
# 1. Войти в Grafana (http://localhost:3000)
# 2. admin / admin
# 3. Сменить пароль при первом входе
```

### 2. Reverse Proxy (Nginx)

Создайте файл `/etc/nginx/sites-available/monitoring`:

```nginx
server {
    listen 80;
    server_name monitoring.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name monitoring.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/monitoring.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monitoring.yourdomain.com/privkey.pem;

    # Web UI
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Increase timeouts for large uploads
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        client_max_body_size 20G;
    }

    # Grafana
    location /grafana/ {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Активация:
```bash
sudo ln -s /etc/nginx/sites-available/monitoring /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Firewall для Production

```bash
# Закрыть прямой доступ к портам (если используется Nginx)
sudo ufw deny 8080
sudo ufw deny 8000
sudo ufw deny 3000
sudo ufw deny 8428

# Разрешить только Nginx
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

## 📊 Мониторинг системы

### Создание systemd service для автозапуска

```bash
# Создать файл /etc/systemd/system/monitoring.service
sudo nano /etc/systemd/system/monitoring.service
```

Содержимое:
```ini
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
sudo systemctl status monitoring.service
```

### Logrotate для Docker логов

```bash
# Создать файл /etc/logrotate.d/docker-monitoring
sudo nano /etc/logrotate.d/docker-monitoring
```

Содержимое:
```
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=50M
    missingok
    delaycompress
    copytruncate
}
```

## 🔧 Обслуживание

### Обновление приложения

```bash
cd /opt/monitoring_VM_Grafana

# Остановка сервисов
docker compose down

# Обновление кода
git pull

# Пересборка
docker compose build --no-cache

# Запуск
docker compose up -d

# Проверка
docker compose ps
docker compose logs -f
```

### Backup данных

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/monitoring"
DATE=$(date +%Y%m%d_%H%M%S)

# Создание директории
mkdir -p $BACKUP_DIR

# Backup VictoriaMetrics
docker compose exec victoriametrics /victoria-metrics-prod -snapshotCreateURL=http://localhost:8428/snapshot/create
docker cp monitoring_vm_grafana-victoriametrics-1:/victoria-metrics-data/snapshots $BACKUP_DIR/vm_$DATE

# Backup Grafana
docker cp monitoring_vm_grafana-grafana-1:/var/lib/grafana $BACKUP_DIR/grafana_$DATE

# Backup CSV jobs
tar -czf $BACKUP_DIR/jobs_$DATE.tar.gz /data/monitoring/jobs_data

# Очистка старых backup'ов (старше 30 дней)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -type d -mtime +30 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR"
```

Настройка cron:
```bash
# Ежедневный backup в 2:00
0 2 * * * /opt/monitoring_VM_Grafana/backup.sh >> /var/log/monitoring_backup.log 2>&1
```

### Очистка дискового пространства

```bash
# Удаление неиспользуемых Docker образов
docker image prune -a -f

# Удаление старых volumes
docker volume prune -f

# Очистка старых CSV jobs (автоматически через 24 часа)
# Или вручную через Web UI: Home → CSV Jobs → Delete Files
```

## 🚨 Troubleshooting

### Проблема: Container не запускается

```bash
# Проверка логов
docker compose logs <service_name>

# Проверка конфликтов портов
sudo netstat -tulpn | grep -E '8000|8080|3000|8428'

# Очистка и перезапуск
docker compose down
docker compose up -d
```

### Проблема: Нет места на диске

```bash
# Проверка использования
df -h
docker system df

# Очистка
docker system prune -a --volumes -f

# Удаление старых CSV jobs
curl -X DELETE http://localhost:8000/api/files/<job_id>
```

### Проблема: Slow performance

```bash
# Увеличить ресурсы Docker (в /etc/docker/daemon.json)
{
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}

# Перезапуск Docker
sudo systemctl restart docker
docker compose up -d
```

## 📝 Checklist развертывания

- [ ] Сервер соответствует системным требованиям
- [ ] Docker и Docker Compose установлены
- [ ] Firewall настроен
- [ ] Директории для данных созданы
- [ ] Файл .env сконфигурирован
- [ ] docker-compose.yml настроен (если нужно)
- [ ] Сервисы запущены (`docker compose up -d`)
- [ ] Health checks пройдены
- [ ] Grafana пароль изменен
- [ ] Reverse proxy настроен (production)
- [ ] SSL сертификаты установлены (production)
- [ ] Systemd service создан
- [ ] Backup настроен
- [ ] Logrotate настроен
- [ ] Мониторинг системы настроен

## 🔗 Полезные ссылки

- Docker Documentation: https://docs.docker.com/
- VictoriaMetrics: https://docs.victoriametrics.com/
- Grafana: https://grafana.com/docs/
- FastAPI: https://fastapi.tiangolo.com/

