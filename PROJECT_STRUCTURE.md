# Project Structure

Detailed structure of the Huawei Storage Performance Monitoring project.

## 📂 Root Directory

```
monitoring_VM_Grafana/
├── README.md                     # Main documentation
├── SCRIPTS.md                    # Detailed script documentation
├── DEPLOYMENT.md                 # Deployment guide
├── PROJECT_STRUCTURE.md          # This file
├── docker-compose.yml            # Docker orchestration
├── .env                          # Environment variables (gitignored)
├── env.example                   # Environment template
├── requirements.txt              # Python dependencies
└── huawei_streaming_pipeline.py  # Main streaming pipeline script
```

## 🔧 API Backend (`/api`)

FastAPI-based REST API server.

```
api/
├── main.py                       # Main API application
│   ├── Upload endpoints          # File upload & processing
│   ├── Job management            # Status tracking
│   ├── Arrays management         # VictoriaMetrics operations
│   ├── CSV files management      # File download & cleanup
│   └── Background tasks          # Async processing
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container build
└── .dockerignore                 # Docker ignore patterns
```

**Key Functions:**
- `upload_file()` - Handle ZIP uploads
- `run_pipeline_sync()` - Execute Grafana streaming
- `run_csv_parser_sync()` - Execute CSV wide parser
- `run_perfmonkey_parser_sync()` - Execute perfmonkey parser
- `gzip_csv_files()` - Multi-threaded compression
- `cleanup_old_jobs()` - Auto-cleanup (24h TTL)

## 🌐 Web Frontend (`/web`)

React-based single-page application.

```
web/
├── src/
│   ├── App.tsx                   # Main application component
│   ├── Home.tsx                  # Home page (arrays & CSV jobs)
│   ├── Upload.tsx                # Upload page (file upload & processing)
│   ├── App.css                   # Styles
│   └── main.tsx                  # Entry point
├── public/                       # Static assets
├── index.html                    # HTML template
├── package.json                  # Node.js dependencies
├── vite.config.ts                # Vite configuration
├── tsconfig.json                 # TypeScript configuration
├── Dockerfile                    # Container build
└── nginx.conf                    # Nginx configuration
```

**Components:**
- `App.tsx` - Routing & navigation
- `Home.tsx` - VictoriaMetrics arrays & CSV jobs display
- `Upload.tsx` - Drag & drop upload, mode selection, progress tracking

## 📊 CSV Parsers

### Wide Format Parser (`/Data2csv`)

Exports data in wide CSV format (semicolon-delimited).

```
Data2csv/
├── Huawei_perf_parser_v0.2_parallel.py  # Main parser script
├── METRIC_DICT.py                       # Metric ID → Name mapping
├── RESOURCE_DICT.py                     # Resource ID → Type mapping
└── output/                              # Output directory (gitignored)
```

**Output:**
- One CSV file per array: `{SerialNumber}.csv`
- Format: `Resource;Metric;Element;Value;Timestamp;UnixTime`

### Perfmonkey Format Parser (`/perfmonkey`)

Exports data in perfmonkey-compatible wide format (comma-delimited).

```
perfmonkey/
└── perf_zip2csv_wide.py          # Main parser script
```

**Output:**
8 CSV files per job (one per resource type):
- `cpu_output.csv.gz` - Controller metrics
- `disk_output.csv.gz` - Disk (RAID Group) metrics
- `lun_output.csv.gz` - LUN metrics
- `host_output.csv.gz` - Host metrics
- `fcp_output.csv.gz` - FC Port metrics
- `pool_output.csv.gz` - Storage Pool metrics
- `disk_domain_output.csv.gz` - Disk Domain metrics
- `fc_repl_link_output.csv.gz` - FC Replication Link metrics

## 📈 Grafana Configuration (`/grafana`)

Pre-configured Grafana dashboards and datasources.

```
grafana/
├── dashboards/
│   └── huawei-oceanstor-real.json       # Main performance dashboard
├── datasources/
│   └── victoriametrics.yml              # VictoriaMetrics datasource
└── grafana.ini                          # Grafana configuration (optional)
```

**Auto-provisioning:**
- Datasources loaded from `/etc/grafana/provisioning/datasources/`
- Dashboards loaded from `/etc/grafana/provisioning/dashboards/`

## 🧪 Tests (`/tests`)

Test files for parsers and API.

```
tests/
├── test_parser.py                # Parser unit tests
└── sample_data/                  # Test archives
```

## 🐋 Docker Configuration

### docker-compose.yml

Defines 4 services:

1. **web** - Nginx + React frontend (port 8080)
2. **api** - FastAPI backend (port 8000)
3. **victoriametrics** - Time-series database (port 8428)
4. **grafana** - Visualization (port 3000)

### Volumes

```yaml
volumes:
  vm_data:          # VictoriaMetrics data
  grafana_data:     # Grafana configuration
  jobs_data:        # CSV output files
```

### Networks

```yaml
networks:
  monitoring:       # Internal network for services
```

## 📋 Data Flow

### Mode 1: Grafana (Streaming)

```
1. User uploads ZIP via Web UI
2. API saves to /app/uploads/
3. Extract serial numbers
4. Background task starts:
   └─> huawei_streaming_pipeline.py
       ├─> Extract .tgz files
       ├─> Parse binary format
       ├─> Convert to Prometheus format
       ├─> Stream batches to VictoriaMetrics
       └─> Complete (cleanup temp files)
5. User opens Grafana dashboard
```

### Mode 2: CSV Wide Format

```
1. User uploads ZIP via Web UI
2. API saves to /app/uploads/
3. Background task starts:
   └─> Huawei_perf_parser_v0.2_parallel.py
       ├─> Extract .tgz files
       ├─> Parse binary format
       ├─> Generate CSV (semicolon-delimited)
       └─> Save to /app/jobs/{job_id}/
4. Multi-threaded compression:
   └─> gzip_csv_files()
       ├─> ThreadPoolExecutor (16 threads)
       └─> Create .csv.gz files
5. User downloads files from Web UI
```

### Mode 3: CSV Perfmonkey Format

```
1. User uploads ZIP via Web UI
2. API saves to /app/uploads/
3. Background task starts:
   └─> perf_zip2csv_wide.py
       ├─> Extract .tgz files
       ├─> Parse binary format
       ├─> Generate 8 CSV files (wide format)
       ├─> Sort and renumber
       └─> Save to /app/jobs/{job_id}/
4. Multi-threaded compression:
   └─> gzip_csv_files()
5. User downloads files from Web UI
```

## 🔄 Background Processes

### Periodic Cleanup (api/main.py)

```python
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_cleanup())

async def periodic_cleanup():
    while True:
        await asyncio.sleep(3600)  # Every hour
        cleanup_old_jobs()         # Remove jobs > JOB_TTL_HOURS
```

### Job Lifecycle

```
1. Upload Complete → Job Created (status: pending)
2. Processing Started (status: running, progress: 0-100%)
3. Processing Complete:
   ├─> Grafana: status=done, grafana_url set
   └─> CSV: status=done, files list populated
4. Auto-cleanup after 24h (configurable)
```

## 📁 Temporary Directories

Created and cleaned automatically:

```
temp/                             # Parser temp files
temp_zip_extract/                 # ZIP extraction
temp_streaming_extract/           # Streaming pipeline temp
uploads/                          # Uploaded archives (auto-delete after processing)
```

## 🔐 Sensitive Files (gitignored)

```
.env                              # Environment variables
uploads/*                         # Uploaded archives
Data2csv/output/*                 # CSV outputs
*.log                             # Log files
api.log                           # API logs
streaming_pipeline.log            # Pipeline logs
```

## 🚀 Entry Points

### Development

```bash
# Backend
cd api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd web && npm run dev

# VictoriaMetrics
./victoria-metrics-prod -retentionPeriod=12

# Grafana
grafana-server --config=/etc/grafana/grafana.ini
```

### Production (Docker)

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Restart specific service
docker compose restart api
```

## 📊 Monitoring & Logs

### Application Logs

```bash
# API logs
docker compose logs -f api

# Streaming pipeline logs
docker exec monitoring_vm_grafana-api-1 tail -f /app/streaming_pipeline.log

# Parser logs
docker exec monitoring_vm_grafana-api-1 tail -f /app/log/process_perf_files.log
```

### System Health

```bash
# API health
curl http://localhost:8000/health

# VictoriaMetrics health
curl http://localhost:8428/-/healthy

# Check metrics count
curl "http://localhost:8428/api/v1/label/__name__/values" | jq
```

## 🔧 Configuration Files

```
.env                              # Environment variables (from env.example)
docker-compose.yml                # Docker orchestration
web/nginx.conf                    # Web server config
grafana/grafana.ini               # Grafana settings
api/main.py                       # API settings (UPLOAD_DIR, WORK_DIR, etc.)
```

## 📚 Documentation Files

```
README.md                         # Main documentation & quick start
SCRIPTS.md                        # Detailed script documentation
DEPLOYMENT.md                     # Deployment & operations guide
PROJECT_STRUCTURE.md              # This file
```

---

**Last Updated:** 2025-10-09  
**Version:** 2.0.0

