# 🌐 Web Interface Overview

Modern web interface for Huawei Storage Performance Monitoring.

## Features

### ✨ User Interface
- 🎨 **Modern Design** - Beautiful gradient UI with glassmorphism effects
- 📁 **Drag & Drop** - Intuitive file upload (up to 10GB)
- 📊 **Real-time Progress** - Live progress bar with status updates
- 🔍 **Auto Detection** - Automatic serial number extraction from archives
- 🎯 **One-Click Access** - Direct link to Grafana dashboards
- 📱 **Responsive** - Works on desktop, tablet, and mobile

### 🔧 Technical Stack

**Frontend:**
- React 18.3 + TypeScript
- Vite 5.4 (fast builds)
- Lucide React (icons)
- Pure CSS (no heavy frameworks)

**Backend:**
- FastAPI 0.115 (async Python)
- Uvicorn (ASGI server)
- Background Tasks (threading)
- Swagger/OpenAPI docs

**Infrastructure:**
- Docker multi-stage builds
- Nginx (production web server)
- Docker Compose orchestration
- Network isolation

## API Endpoints

### POST `/api/upload`
Upload a .zip archive for processing.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@Storage_History_Performance.zip"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "serial_numbers": ["2102353TJWFSP3100020"],
  "message": "Upload successful, processing started"
}
```

### GET `/api/status/{job_id}`
Get processing status for a job.

**Request:**
```bash
curl "http://localhost:8000/api/status/550e8400-e29b-41d4-a716-446655440000"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 75,
  "message": "Importing CSV to VictoriaMetrics...",
  "serial_numbers": ["2102353TJWFSP3100020"],
  "grafana_url": "http://localhost:3000/d/huawei-storage",
  "created_at": "2025-10-06T12:00:00",
  "updated_at": "2025-10-06T12:05:30"
}
```

**Status values:**
- `pending` - Job queued, waiting to start
- `running` - Processing in progress
- `done` - Completed successfully
- `error` - Failed with error

### GET `/api/jobs`
List all jobs.

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "...",
      "status": "done",
      "progress": 100,
      ...
    }
  ],
  "total": 5
}
```

### DELETE `/api/job/{job_id}`
Delete a job record (does not stop running job).

## Environment Variables

### API Backend
```bash
VM_URL=http://victoriametrics:8428/api/v1/import/prometheus
GRAFANA_URL=http://localhost:3000
MAX_UPLOAD_SIZE=10737418240  # 10GB
```

### Web Frontend
```bash
VITE_API_URL=http://localhost:8000
VITE_GRAFANA_URL=http://localhost:3000
```

## Development

### Frontend Development

```bash
cd web

# Install dependencies
npm install

# Run dev server (hot reload)
npm run dev
# Access: http://localhost:3001

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend Development

```bash
cd api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server (hot reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Access API docs: http://localhost:8000/docs
```

### Full Stack Development

```bash
# Terminal 1: Backend
cd /data/projects/monitoring_VM_Grafana
python3 -m venv venv
source venv/bin/activate
pip install -r api/requirements.txt
uvicorn api.main:app --reload

# Terminal 2: Frontend
cd web
npm install
npm run dev

# Terminal 3: VictoriaMetrics & Grafana
docker-compose up victoriametrics grafana
```

## Production Build

```bash
# Build all services
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api web
```

## Architecture

### Request Flow

```
User uploads file → Web UI → API (/api/upload)
                                  ↓
                         Creates job_id
                                  ↓
                    Starts background task
                                  ↓
                    huawei_to_vm_pipeline.py
                                  ↓
                         Updates job status
                                  ↓
Web UI polls /api/status/{job_id} every 2s
                                  ↓
                    Shows progress 0-100%
                                  ↓
                    Job completes (done)
                                  ↓
            User clicks "Open in Grafana"
```

### File Processing Flow

```
1. Upload: .zip → /app/uploads/
2. Extract: .zip → .tgz files (temp)
3. Parse: .tgz → CSV (/app/Data2csv/output/)
4. Import: CSV → VictoriaMetrics (batch)
5. Cleanup: Delete .zip, .tgz, CSV
```

### Progress Tracking

Progress is estimated based on log output from pipeline:

| Log message | Progress |
|-------------|----------|
| "Парсинг" | 20% |
| "CSV файлов:" | 50% |
| "Импорт" | 60% |
| "PIPELINE ЗАВЕРШЁН" | 95% |
| Done | 100% |

## Security Considerations

### Current Implementation (Development)
- ✅ CORS: Allow all origins
- ✅ File type validation (.zip only)
- ✅ File size limit (10GB)
- ⚠️ No authentication
- ⚠️ No rate limiting
- ⚠️ Jobs stored in memory

### Production Recommendations
- 🔒 Add JWT authentication
- 🔒 Implement rate limiting
- 🔒 Use Redis for job storage
- 🔒 Restrict CORS to specific domains
- 🔒 Add HTTPS/SSL
- 🔒 Implement file scanning (antivirus)
- 🔒 Add user roles/permissions
- 🔒 Implement request logging

## Customization

### Change Grafana Dashboard URL

Edit `api/main.py`:

```python
# Line ~170
grafana_dashboard = f"{GRAFANA_URL}/d/YOUR_DASHBOARD_UID/your-dashboard-name"
```

### Change Upload Limits

Edit `docker-compose.yml`:

```yaml
api:
  environment:
    - MAX_UPLOAD_SIZE=21474836240  # 20GB
```

Also update nginx if using reverse proxy:

```nginx
client_max_body_size 20G;
```

### Add More API Endpoints

Edit `api/main.py`:

```python
@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics"""
    return {"cpu": ..., "memory": ...}
```

### Customize UI Theme

Edit `web/src/App.css`:

```css
.app {
  background: linear-gradient(135deg, #YOUR_COLOR1 0%, #YOUR_COLOR2 100%);
}
```

## Testing

### Manual Testing

```bash
# 1. Upload test file
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@test.zip"

# 2. Get job status
JOB_ID="..." # from step 1
curl "http://localhost:8000/api/status/$JOB_ID"

# 3. List all jobs
curl "http://localhost:8000/api/jobs"

# 4. Delete job
curl -X DELETE "http://localhost:8000/api/job/$JOB_ID"
```

### Load Testing

```bash
# Install apache bench
sudo apt-get install apache2-utils

# Test API endpoint
ab -n 100 -c 10 http://localhost:8000/
```

## Monitoring

### Application Logs

```bash
# API logs
docker-compose logs -f api

# Web server logs
docker-compose logs -f web

# Application log file
docker exec -it api tail -f /app/api.log
```

### System Metrics

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Network
docker network inspect monitoring_monitoring
```

## Common Issues

### Port already in use

```bash
# Change port in docker-compose.yml
services:
  web:
    ports:
      - "3002:80"  # Changed from 3001
```

### Build fails

```bash
# Clean rebuild
docker-compose down
docker system prune -a
docker-compose build --no-cache
docker-compose up -d
```

### API can't connect to VictoriaMetrics

```bash
# Check network
docker network inspect monitoring_monitoring

# Check VM is running
curl http://localhost:8428/health

# Check from inside API container
docker exec -it api curl http://victoriametrics:8428/health
```

---

**Happy coding! 💻**

