# 🚀 Deployment Guide

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                   USER BROWSER                          │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│           WEB UI (React + Vite + Nginx)                 │
│              localhost:3001                             │
│  • Drag & Drop Upload                                   │
│  • Progress Bar                                         │
│  • Real-time Status                                     │
└────────────┬────────────────────────────────────────────┘
             │ HTTP REST API
             ▼
┌─────────────────────────────────────────────────────────┐
│           API (FastAPI)                                 │
│              localhost:8000                             │
│  • POST /api/upload                                     │
│  • GET  /api/status/{job_id}                           │
│  • GET  /api/jobs                                       │
│  • Background Tasks (threading)                         │
└────────────┬────────────────────────────────────────────┘
             │ Executes
             ▼
┌─────────────────────────────────────────────────────────┐
│      huawei_to_vm_pipeline.py                           │
│  1. Parse .tgz → CSV (parallel)                        │
│  2. Import CSV → VictoriaMetrics (parallel)            │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│         VictoriaMetrics TSDB                            │
│              localhost:8428                             │
│  • Time-series database                                │
│  • Prometheus-compatible                               │
│  • 6 months retention                                  │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│              Grafana                                    │
│              localhost:3000                             │
│  • Visualization                                       │
│  • Dashboards                                          │
│  • Auto-provisioned datasource                         │
└─────────────────────────────────────────────────────────┘
```

## Docker Services

### 1. VictoriaMetrics
- **Image**: `victoriametrics/victoria-metrics:v1.99.0`
- **Port**: 8428
- **Volume**: `/data/vmdata` (persistent storage)
- **Retention**: 6 months (configurable)

### 2. Grafana
- **Image**: `grafana/grafana:12.1.1`
- **Port**: 3000
- **Volume**: `grafana_data` (persistent storage)
- **Default credentials**: admin / changeme

### 3. API (FastAPI)
- **Build**: `./api/Dockerfile`
- **Port**: 8000
- **Volumes**:
  - `./uploads` - temporary file uploads
  - `./Data2csv` - parser code
- **Environment**:
  - `VM_URL` - VictoriaMetrics endpoint
  - `GRAFANA_URL` - Grafana URL for links

### 4. Web (React + Nginx)
- **Build**: `./web/Dockerfile` (multi-stage)
- **Port**: 3001 (nginx on port 80)
- **Build args**:
  - `VITE_API_URL` - API endpoint
  - `VITE_GRAFANA_URL` - Grafana URL

## Deployment Steps

### Development

```bash
# 1. Build and start services
docker-compose up -d --build

# 2. Watch logs
docker-compose logs -f api web

# 3. Access services
# - Web UI: http://localhost:3001
# - API Docs: http://localhost:8000/docs
# - Grafana: http://localhost:3000
```

### Production

1. **Configure environment variables**

```bash
cp env.example .env
nano .env
```

2. **Update docker-compose.yml for production**

```yaml
# Example production settings
services:
  api:
    restart: always
    environment:
      - VM_URL=http://victoriametrics:8428/api/v1/import/prometheus
      - GRAFANA_URL=https://grafana.yourcompany.com
      - MAX_UPLOAD_SIZE=21474836480  # 20GB
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

  web:
    restart: always
    build:
      args:
        - VITE_API_URL=https://api.yourcompany.com
        - VITE_GRAFANA_URL=https://grafana.yourcompany.com
```

3. **Add reverse proxy (nginx/traefik)**

```nginx
# Example nginx config
upstream api {
    server localhost:8000;
}

upstream web {
    server localhost:3001;
}

server {
    listen 443 ssl http2;
    server_name monitoring.yourcompany.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://web;
        proxy_set_header Host $host;
    }

    location /api/ {
        proxy_pass http://api;
        proxy_set_header Host $host;
        
        # Large file uploads
        client_max_body_size 20G;
        proxy_request_buffering off;
    }
}
```

4. **Security hardening**

```yaml
# api/main.py - Update CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://monitoring.yourcompany.com"],  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

5. **Monitoring and backups**

```bash
# Backup VictoriaMetrics data
tar -czf vmdata-backup-$(date +%Y%m%d).tar.gz /data/vmdata

# Backup Grafana dashboards
docker exec grafana grafana-cli admin export-all /var/lib/grafana/backups
```

## Scaling

### Horizontal scaling (multiple workers)

For large deployments, consider:

1. **Use Redis for job queue** (instead of in-memory dict)
2. **Deploy multiple API instances** behind load balancer
3. **Use Celery workers** for background processing
4. **Separate storage** for uploads (S3, NFS)

### Vertical scaling

Increase resources for API service:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 16G
```

## Maintenance

### Update services

```bash
# Pull latest images
docker-compose pull

# Rebuild custom images
docker-compose build --pull

# Restart services
docker-compose up -d
```

### Clean up

```bash
# Remove old uploads (older than 7 days)
find /data/projects/monitoring_VM_Grafana/uploads -name "*.zip" -mtime +7 -delete

# Clean Docker cache
docker system prune -a
```

### Monitor disk usage

```bash
# Check VictoriaMetrics data size
du -sh /data/vmdata

# Check Grafana data size
du -sh /data/grafana
```

## Troubleshooting

### High memory usage

```bash
# Check container stats
docker stats

# Restart API if needed
docker-compose restart api
```

### Slow processing

1. Check CPU/memory availability
2. Reduce workers in pipeline: `--workers 4`
3. Increase batch size: `--batch-size 100000`

### Database issues

```bash
# Check VictoriaMetrics health
curl http://localhost:8428/health

# Force merge (after data deletion)
curl -X POST http://localhost:8428/internal/force_merge
```

---

**Ready for production! 🚀**

