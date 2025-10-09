# Deployment Guide - Multi-Mode Processing

## Quick Start

### 1. Prepare Host Directories

```bash
# Create required directories
sudo mkdir -p /data/jobs /data/vmdata /data/grafana
sudo chown -R 1000:1000 /data/jobs /data/vmdata /data/grafana
```

### 2. Update Environment Variables (Optional)

Create or update `.env` file:

```bash
# Job processing
JOB_TTL_HOURS=24          # Auto-cleanup after 24 hours
MAX_UPLOAD_SIZE=10737418240  # 10GB

# VictoriaMetrics
VM_PORT=8428
VM_RETENTION=6            # months

# Grafana
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASS=changeme

# API
API_PORT=8000

# Web UI
WEB_PORT=3001
```

### 3. Build and Start Services

```bash
# Build containers
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### 4. Verify Services

```bash
# API health check
curl http://localhost:8000/health

# VictoriaMetrics
curl http://localhost:8428/health

# Grafana
curl http://localhost:3000/api/health

# Web UI
curl http://localhost:3001
```

## Upgrade from Previous Version

### 1. Stop Services

```bash
docker-compose down
```

### 2. Backup Data (Optional but Recommended)

```bash
# Backup VictoriaMetrics data
sudo tar -czf vmdata-backup-$(date +%Y%m%d).tar.gz /data/vmdata

# Backup Grafana data
sudo tar -czf grafana-backup-$(date +%Y%m%d).tar.gz /data/grafana
```

### 3. Create Jobs Directory

```bash
sudo mkdir -p /data/jobs
sudo chown -R 1000:1000 /data/jobs
```

### 4. Update Configuration Files

Replace:
- `api/main.py` - Updated API with multi-mode support
- `web/src/Upload.tsx` - Updated frontend
- `web/src/App.css` - New styles
- `docker-compose.yml` - New volumes and environment

### 5. Rebuild and Start

```bash
# Rebuild API container (includes new dependencies)
docker-compose build api

# Rebuild web container (includes new UI)
docker-compose build web

# Start all services
docker-compose up -d
```

### 6. Verify Upgrade

```bash
# Check API version
curl http://localhost:8000/ | jq '.version'
# Should show: "2.0.0"

# Test new upload endpoint
curl -X POST \
  -F "file=@test.zip" \
  -F "target=csv" \
  http://localhost:8000/api/upload
```

## Service Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Host System                      │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ /data/jobs  │  │ /data/vmdata│  │/data/grafana│ │
│  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘ │
│         │                │                │         │
└─────────┼────────────────┼────────────────┼─────────┘
          │                │                │
          │                │                │
┌─────────┼────────────────┼────────────────┼─────────┐
│         │  Docker Network (monitoring)    │         │
│         │                │                │         │
│    ┌────▼────┐     ┌────▼────┐      ┌───▼────┐    │
│    │   API   │────▶│   VM    │◀─────│ Grafana│    │
│    │  :8000  │     │  :8428  │      │  :3000 │    │
│    └────▲────┘     └─────────┘      └────────┘    │
│         │                                          │
│    ┌────┴────┐                                     │
│    │   Web   │                                     │
│    │  :3001  │                                     │
│    └─────────┘                                     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Port Mapping

| Service | Internal Port | Host Port | Purpose |
|---------|--------------|-----------|---------|
| API | 8000 | 8000 | REST API |
| Web | 80 | 3001 | Frontend UI |
| Grafana | 3000 | 3000 | Dashboards |
| VictoriaMetrics | 8428 | 8428 | Time-series DB |

## Volume Mapping

| Host Path | Container Path | Purpose | Size Estimate |
|-----------|---------------|---------|---------------|
| /data/jobs | /app/jobs | CSV output files | ~50GB per job |
| /data/vmdata | /vmdata | VM time-series data | ~100GB+ |
| /data/grafana | /var/lib/grafana | Grafana config/dashboards | ~1GB |
| ./uploads | /app/uploads | Temporary uploads | ~10GB |
| ./Data2csv | /app/Data2csv | CSV parser (wide) | Read-only |
| ./perfmonkey | /app/perfmonkey | CSV parser (perfmonkey) | Read-only |

## Resource Requirements

### Minimum
- CPU: 4 cores
- RAM: 8GB
- Disk: 100GB SSD
- Network: 100Mbps

### Recommended
- CPU: 16+ cores
- RAM: 32GB+
- Disk: 500GB+ NVMe SSD
- Network: 1Gbps

### For Large Workloads (500GB+ archives)
- CPU: 32+ cores
- RAM: 64GB+
- Disk: 2TB+ NVMe SSD (RAID 0 or ZFS for /data/jobs)
- Network: 10Gbps

## Monitoring

### Docker Logs

```bash
# API logs
docker logs -f huawei-api

# Web logs
docker logs -f huawei-web

# VictoriaMetrics logs
docker logs -f huawei-victoriametrics

# Grafana logs
docker logs -f huawei-grafana
```

### Disk Usage

```bash
# Monitor jobs directory
du -sh /data/jobs/*

# Monitor VM data
du -sh /data/vmdata

# Find old jobs (manual cleanup if needed)
find /data/jobs -type d -mtime +1 -ls
```

### API Endpoints for Monitoring

```bash
# Health check
curl http://localhost:8000/health

# List all jobs
curl http://localhost:8000/api/jobs

# List imported arrays
curl http://localhost:8000/api/arrays
```

## Troubleshooting

### Issue: Cannot create /data/jobs directory

**Cause:** Permission denied

**Solution:**
```bash
sudo mkdir -p /data/jobs
sudo chown -R $(id -u):$(id -g) /data/jobs
```

### Issue: API container fails to start

**Cause:** Port 8000 already in use

**Solution:**
```bash
# Check what's using port 8000
sudo lsof -i :8000

# Change port in .env
echo "API_PORT=8001" >> .env

# Restart
docker-compose up -d api
```

### Issue: Files not downloading

**Cause:** Missing volume mount or wrong permissions

**Solution:**
```bash
# Check volume mount
docker inspect huawei-api | jq '.[0].Mounts'

# Fix permissions
sudo chown -R 1000:1000 /data/jobs

# Restart API
docker-compose restart api
```

### Issue: Out of disk space

**Cause:** Too many old jobs

**Solution:**
```bash
# Manual cleanup (deletes jobs older than 1 day)
find /data/jobs -type d -mtime +1 -exec rm -rf {} +

# Or reduce TTL
echo "JOB_TTL_HOURS=12" >> .env
docker-compose restart api
```

### Issue: CSV generation stuck

**Cause:** Not enough workers or memory

**Solution:**
```bash
# Check container resources
docker stats huawei-api

# Increase memory limit in docker-compose.yml
# Under api service:
#   deploy:
#     resources:
#       limits:
#         memory: 16G

# Restart
docker-compose up -d api
```

## Backup and Restore

### Backup

```bash
#!/bin/bash
BACKUP_DIR="/backup/huawei-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup VictoriaMetrics data
sudo tar -czf $BACKUP_DIR/vmdata.tar.gz /data/vmdata

# Backup Grafana
sudo tar -czf $BACKUP_DIR/grafana.tar.gz /data/grafana

# Backup current jobs (optional, since they auto-expire)
sudo tar -czf $BACKUP_DIR/jobs.tar.gz /data/jobs

# Backup config
cp docker-compose.yml $BACKUP_DIR/
cp .env $BACKUP_DIR/
```

### Restore

```bash
#!/bin/bash
BACKUP_DIR="/backup/huawei-20251009"

# Stop services
docker-compose down

# Restore VictoriaMetrics
sudo tar -xzf $BACKUP_DIR/vmdata.tar.gz -C /

# Restore Grafana
sudo tar -xzf $BACKUP_DIR/grafana.tar.gz -C /

# Fix permissions
sudo chown -R 1000:1000 /data/vmdata /data/grafana

# Start services
docker-compose up -d
```

## Security Considerations

### 1. Change Default Passwords

```bash
# Update Grafana admin password
echo "GRAFANA_ADMIN_PASS=YourStrongPassword123!" >> .env
docker-compose restart grafana
```

### 2. Firewall Rules

```bash
# Allow only local access
sudo ufw allow from 127.0.0.1 to any port 8000
sudo ufw allow from 127.0.0.1 to any port 8428

# Allow Grafana from specific subnet
sudo ufw allow from 192.168.1.0/24 to any port 3000
```

### 3. File Upload Size Limits

```bash
# Limit max upload size (10GB default)
echo "MAX_UPLOAD_SIZE=5368709120" >> .env  # 5GB
docker-compose restart api
```

### 4. Job Cleanup

```bash
# Reduce retention to 12 hours
echo "JOB_TTL_HOURS=12" >> .env
docker-compose restart api
```

## Maintenance

### Regular Tasks

**Daily:**
- Check disk space: `df -h /data`
- Check logs for errors: `docker logs huawei-api | grep ERROR`

**Weekly:**
- Review job count: `ls -1 /data/jobs | wc -l`
- Check VM retention: Check Grafana dashboards

**Monthly:**
- Backup VictoriaMetrics data
- Update containers: `docker-compose pull && docker-compose up -d`

### Updates

```bash
# Update containers
docker-compose pull

# Recreate with new images
docker-compose up -d

# Cleanup old images
docker image prune -a
```

## Performance Tuning

### 1. Increase API Workers

Edit `docker-compose.yml`:
```yaml
services:
  api:
    environment:
      - WORKER_CONCURRENCY=8  # Increase from 4
```

### 2. VictoriaMetrics Optimization

```yaml
services:
  victoriametrics:
    command:
      - --storageDataPath=/vmdata
      - --retentionPeriod=6
      - -memory.allowedPercent=90  # Increase from 80
      - -insert.maxQueueDuration=120s  # Increase from 60s
```

### 3. Faster Disk I/O

```bash
# Use tmpfs for uploads (RAM disk)
# Add to docker-compose.yml under api service:
#   tmpfs:
#     - /app/uploads:size=10G

# Or use faster storage
sudo mount -t tmpfs -o size=20G tmpfs /data/jobs
```

---

**Version:** 2.0.0  
**Last Updated:** October 9, 2025


