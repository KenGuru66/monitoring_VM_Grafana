#!/usr/bin/env python3
"""
FastAPI Backend for Huawei Performance Data Processing
Provides endpoints for uploading ZIP archives and tracking processing status.
"""

import os
import sys
import asyncio
import logging
import uuid
import time
import re
import zipfile
import json
import gzip
import shutil
from pathlib import Path

# Поддержка .7z архивов
try:
    import py7zr
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests

# Add parent directory to path to import pipeline
sys.path.insert(0, '/app')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/api.log', mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Huawei Performance Data API",
    description="Upload and process Huawei storage performance logs",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = Path("/app/uploads")
OUTPUT_DIR = Path("/app/output")
WORK_DIR = Path(os.getenv("WORK_DIR", "/app/jobs"))  # Job output directory
VM_URL = os.getenv("VM_URL", "http://victoriametrics:8428")
VM_IMPORT_URL = os.getenv("VM_IMPORT_URL", "http://victoriametrics:8428/api/v1/import/prometheus")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024 * 1024))
JOB_TIMEOUT = int(os.getenv("JOB_TIMEOUT", 86400))  # 24 hours default
JOB_TTL_HOURS = int(os.getenv("JOB_TTL_HOURS", 24))  # Auto-cleanup after 24 hours

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
WORK_DIR.mkdir(parents=True, exist_ok=True)

# Job storage
jobs: Dict[str, dict] = {}
upload_progress: Dict[str, dict] = {}

# Thread pool
executor = ThreadPoolExecutor(max_workers=4)


# Background cleanup task
async def periodic_cleanup():
    """Periodically cleanup old job directories."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            cleanup_old_jobs()
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting periodic cleanup task...")
    asyncio.create_task(periodic_cleanup())
    logger.info("Application startup complete")


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    serial_numbers: list[str] = []
    grafana_url: Optional[str] = None
    created_at: str
    updated_at: str
    error: Optional[str] = None


def extract_serial_numbers(archive_path: Path) -> list[str]:
    """Extract serial numbers from .tgz filenames inside ZIP or 7Z archive."""
    serial_numbers = set()
    suffix = archive_path.suffix.lower()
    
    try:
        file_list = []
        
        if suffix == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
        elif suffix == '.7z' and PY7ZR_AVAILABLE:
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                file_list = archive.getnames()
        
        for filename in file_list:
            matches = re.findall(r"_SN_([0-9A-Z]+)_SP\d+", filename)
            if matches:
                serial_numbers.add(matches[0])
        
        # Fallback: извлечение SN из имени архива (формат Data_Model_Timestamp_SN.7z)
        if not serial_numbers:
            match = re.search(r"_(21[0-9A-Z]{18,})\.(zip|7z)$", archive_path.name, re.IGNORECASE)
            if match:
                serial_numbers.add(match.group(1))
        
        return sorted(list(serial_numbers))
    except Exception as e:
        logger.error(f"Error extracting serial numbers: {e}")
        return []


def extract_perf_zip_from_7z(archive_path: Path, temp_dir: Path) -> Optional[Path]:
    """
    Извлекает Perf ZIP файл из .7z архива.
    
    Структура внутри .7z:
    DataCollect/History_Performance_Data/<IP>/(<IP>)..._Perf_*.zip
    
    Args:
        archive_path: Путь к .7z архиву
        temp_dir: Временная директория для извлечения
        
    Returns:
        Путь к извлечённому .zip файлу или None
    """
    if not PY7ZR_AVAILABLE:
        logger.error("❌ py7zr не установлен! Установите: pip install py7zr")
        return None
    
    try:
        with py7zr.SevenZipFile(archive_path, mode='r') as archive:
            all_names = archive.getnames()
            
            # Ищем файлы с паттерном *_Perf_*.zip в History_Performance_Data
            perf_zip_files = [
                name for name in all_names 
                if '_Perf_' in name and name.endswith('.zip') and 'History_Performance_Data' in name
            ]
            
            if not perf_zip_files:
                logger.warning(f"⚠️  Perf ZIP файлы не найдены внутри {archive_path.name}")
                return None
            
            if len(perf_zip_files) > 1:
                logger.info(f"📦 Найдено {len(perf_zip_files)} Perf ZIP файлов, используем первый")
            
            perf_zip_name = perf_zip_files[0]
            logger.info(f"📦 Извлекаю: {perf_zip_name}")
            
            # Извлекаем только нужный файл
            archive.extract(temp_dir, targets=[perf_zip_name])
            
            extracted_path = temp_dir / perf_zip_name
            if extracted_path.exists():
                return extracted_path
            else:
                logger.error(f"❌ Файл не найден после извлечения: {extracted_path}")
                return None
                
    except Exception as e:
        logger.error(f"❌ Ошибка при извлечении из .7z: {e}")
        return None


def gzip_single_file(csv_file: Path) -> dict:
    """Gzip a single CSV file (for parallel processing)."""
    try:
        gz_file = csv_file.with_suffix('.csv.gz')
        
        with open(csv_file, 'rb') as f_in:
            with gzip.open(gz_file, 'wb', compresslevel=6) as f_out:  # compresslevel=6 for speed
                shutil.copyfileobj(f_in, f_out)
        
        # Remove original CSV
        csv_file.unlink()
        
        size_mb = gz_file.stat().st_size / (1024**2)
        return {
            'success': True,
            'file': csv_file.name,
            'gz_file': gz_file.name,
            'size_mb': size_mb
        }
    except Exception as e:
        return {
            'success': False,
            'file': csv_file.name,
            'error': str(e)
        }


def gzip_csv_files(directory: Path):
    """Gzip all CSV files in directory using multiple threads."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    csv_files = list(directory.glob("*.csv"))
    
    if not csv_files:
        logger.info(f"No CSV files to compress in {directory}")
        return
    
    logger.info(f"Compressing {len(csv_files)} CSV files using parallel threads...")
    
    # Use multiple threads for parallel compression (I/O bound operation)
    max_workers = min(16, os.cpu_count() or 4)
    logger.info(f"Using {max_workers} compression threads")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(gzip_single_file, csv_file) for csv_file in csv_files]
        
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            if result['success']:
                logger.info(f"  [{completed}/{len(csv_files)}] ✓ {result['file']} -> {result['gz_file']} ({result['size_mb']:.2f} MB)")
            else:
                logger.error(f"  [{completed}/{len(csv_files)}] ✗ Failed: {result['file']}: {result['error']}")
    
    logger.info(f"✅ Compression complete: {len(csv_files)} files")


def get_job_files(job_id: str) -> List[dict]:
    """Get list of output files for a job."""
    job_dir = WORK_DIR / job_id
    
    if not job_dir.exists():
        return []
    
    files = []
    for file_path in sorted(job_dir.glob("*.csv.gz")):
        stat = file_path.stat()
        files.append({
            "name": file_path.name,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 ** 2), 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "url": f"/api/file/{job_id}/{file_path.name}"
        })
    
    return files


def cleanup_old_jobs():
    """Remove job directories older than JOB_TTL_HOURS."""
    if not WORK_DIR.exists():
        return
    
    cutoff_time = time.time() - (JOB_TTL_HOURS * 3600)
    removed_count = 0
    
    for job_dir in WORK_DIR.iterdir():
        if not job_dir.is_dir():
            continue
        
        try:
            # Check if directory is old enough
            dir_mtime = job_dir.stat().st_mtime
            if dir_mtime < cutoff_time:
                shutil.rmtree(job_dir)
                removed_count += 1
                logger.info(f"Cleaned up old job directory: {job_dir.name}")
        except Exception as e:
            logger.error(f"Failed to cleanup {job_dir}: {e}")
    
    if removed_count > 0:
        logger.info(f"Cleanup complete: removed {removed_count} old job directories")


def run_csv_parser_sync(job_id: str, archive_path: Path):
    """Run Huawei CSV parser (wide format) - parsers/csv_wide_parser.py
    
    Поддерживает .zip и .7z архивы. Для .7z извлекает вложенный Perf ZIP.
    """
    import subprocess
    
    start_time = time.time()
    process = None
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    temp_7z_dir = None
    actual_input_path = archive_path
    
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["progress"] = 5
        jobs[job_id]["message"] = "Preparing archive..."
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Для .7z архивов: извлекаем вложенный Perf ZIP
        if archive_path.suffix.lower() == '.7z':
            jobs[job_id]["message"] = "Extracting Perf ZIP from .7z archive..."
            jobs[job_id]["updated_at"] = datetime.now().isoformat()
            
            temp_7z_dir = WORK_DIR / f"temp_7z_{job_id}"
            temp_7z_dir.mkdir(parents=True, exist_ok=True)
            
            extracted_zip = extract_perf_zip_from_7z(archive_path, temp_7z_dir)
            if not extracted_zip:
                raise ValueError("Failed to extract Perf ZIP from .7z archive")
            
            actual_input_path = extracted_zip
            logger.info(f"Job {job_id}: Extracted Perf ZIP: {extracted_zip}")
        
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "Starting CSV parser (wide format)..."
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        cmd = [
            "python3",
            "/app/parsers/csv_wide_parser.py",
            "-i", str(actual_input_path),
            "-o", str(job_dir),
            "--all-metrics"
        ]
        
        logger.info(f"Job {job_id}: Running CSV parser: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            elapsed = time.time() - start_time
            if elapsed > JOB_TIMEOUT:
                logger.error(f"Job {job_id}: Timeout exceeded")
                process.kill()
                raise TimeoutError(f"Job timeout after {JOB_TIMEOUT} seconds")
            
            line = line.strip()
            if line:
                logger.info(f"Job {job_id}: {line}")
                
                # Update progress based on output
                if "Processing array" in line:
                    jobs[job_id]["progress"] = 30
                elif "Successfully processed" in line:
                    jobs[job_id]["progress"] = 60
                elif "Process End" in line:
                    jobs[job_id]["progress"] = 80
                
                jobs[job_id]["message"] = line[:200]
                jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        return_code = process.wait(timeout=30)
        
        if return_code == 0:
            # Compress CSV files
            jobs[job_id]["progress"] = 85
            jobs[job_id]["message"] = "Compressing CSV files..."
            jobs[job_id]["updated_at"] = datetime.now().isoformat()
            
            gzip_csv_files(job_dir)
            
            jobs[job_id]["status"] = "done"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["message"] = "CSV files ready for download!"
            jobs[job_id]["files"] = get_job_files(job_id)
            
            logger.info(f"Job {job_id}: CSV parser completed successfully")
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = f"Parser failed with code {return_code}"
            logger.error(f"Job {job_id}: Parser failed with code {return_code}")
        
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
            
    except Exception as e:
        if process and process.poll() is None:
            process.kill()
        
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        logger.error(f"Job {job_id}: Error: {e}", exc_info=True)
    
    finally:
        # Cleanup: временная директория для .7z
        if temp_7z_dir and temp_7z_dir.exists():
            try:
                shutil.rmtree(temp_7z_dir)
                logger.debug(f"Job {job_id}: Cleaned up temp 7z directory")
            except Exception as e:
                logger.warning(f"Job {job_id}: Failed to cleanup temp 7z dir: {e}")
        
        # Cleanup uploaded archive
        try:
            if archive_path.exists():
                archive_path.unlink()
                logger.info(f"Job {job_id}: Cleaned up uploaded file {archive_path}")
        except Exception as e:
            logger.warning(f"Job {job_id}: Failed to cleanup {archive_path}: {e}")


def run_perfmonkey_parser_sync(job_id: str, archive_path: Path):
    """Run perfmonkey CSV parser - parsers/perfmonkey_parser.py
    
    Поддерживает .zip и .7z архивы. Для .7z извлекает вложенный Perf ZIP.
    """
    import subprocess
    
    start_time = time.time()
    process = None
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    temp_7z_dir = None
    actual_input_path = archive_path
    
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["progress"] = 5
        jobs[job_id]["message"] = "Preparing archive..."
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Для .7z архивов: извлекаем вложенный Perf ZIP
        if archive_path.suffix.lower() == '.7z':
            jobs[job_id]["message"] = "Extracting Perf ZIP from .7z archive..."
            jobs[job_id]["updated_at"] = datetime.now().isoformat()
            
            temp_7z_dir = WORK_DIR / f"temp_7z_{job_id}"
            temp_7z_dir.mkdir(parents=True, exist_ok=True)
            
            extracted_zip = extract_perf_zip_from_7z(archive_path, temp_7z_dir)
            if not extracted_zip:
                raise ValueError("Failed to extract Perf ZIP from .7z archive")
            
            actual_input_path = extracted_zip
            logger.info(f"Job {job_id}: Extracted Perf ZIP: {extracted_zip}")
        
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "Starting perfmonkey parser..."
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        cmd = [
            "python3",
            "/app/parsers/perfmonkey_parser.py",
            str(actual_input_path),
            "-o", str(job_dir),
            "--workers", "30"
        ]
        
        logger.info(f"Job {job_id}: Running perfmonkey parser: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            elapsed = time.time() - start_time
            if elapsed > JOB_TIMEOUT:
                logger.error(f"Job {job_id}: Timeout exceeded")
                process.kill()
                raise TimeoutError(f"Job timeout after {JOB_TIMEOUT} seconds")
            
            line = line.strip()
            if line:
                logger.info(f"Job {job_id}: {line}")
                
                # Update progress
                if "Processing" in line:
                    jobs[job_id]["progress"] = 40
                elif "Sorting" in line:
                    jobs[job_id]["progress"] = 70
                elif "Complete" in line:
                    jobs[job_id]["progress"] = 80
                
                jobs[job_id]["message"] = line[:200]
                jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        return_code = process.wait(timeout=30)
        
        if return_code == 0:
            # Compress CSV files
            jobs[job_id]["progress"] = 85
            jobs[job_id]["message"] = "Compressing CSV files..."
            jobs[job_id]["updated_at"] = datetime.now().isoformat()
            
            gzip_csv_files(job_dir)
            
            jobs[job_id]["status"] = "done"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["message"] = "CSV files ready for download!"
            jobs[job_id]["files"] = get_job_files(job_id)
            
            logger.info(f"Job {job_id}: Perfmonkey parser completed successfully")
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = f"Parser failed with code {return_code}"
            logger.error(f"Job {job_id}: Parser failed with code {return_code}")
        
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
            
    except Exception as e:
        if process and process.poll() is None:
            process.kill()
        
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        logger.error(f"Job {job_id}: Error: {e}", exc_info=True)
    
    finally:
        # Cleanup: временная директория для .7z
        if temp_7z_dir and temp_7z_dir.exists():
            try:
                shutil.rmtree(temp_7z_dir)
                logger.debug(f"Job {job_id}: Cleaned up temp 7z directory")
            except Exception as e:
                logger.warning(f"Job {job_id}: Failed to cleanup temp 7z dir: {e}")
        
        # Cleanup uploaded archive
        try:
            if archive_path.exists():
                archive_path.unlink()
                logger.info(f"Job {job_id}: Cleaned up uploaded file {archive_path}")
        except Exception as e:
            logger.warning(f"Job {job_id}: Failed to cleanup {archive_path}: {e}")


def run_pipeline_sync(job_id: str, archive_path: Path):
    """Run the Huawei processing pipeline synchronously.
    
    Поддерживает .zip и .7z архивы - streaming_pipeline.py умеет работать с обоими форматами.
    """
    import subprocess
    
    start_time = time.time()
    process = None
    
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "Starting pipeline..."
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        jobs[job_id]["start_time"] = start_time
        
        # streaming_pipeline.py поддерживает и .zip, и .7z
        cmd = [
            "python3",
            "/app/parsers/streaming_pipeline.py",
            "-i", str(archive_path),
            "--vm-url", VM_IMPORT_URL,
            "--batch-size", "50000",
            "--all-metrics"
        ]
        
        logger.info(f"Job {job_id}: Running command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        progress_markers = {
            "Processing TGZ files": 20,
            "Worker": 50,
            "metrics in": 70,
            "STREAMING PIPELINE COMPLETED": 95
        }
        
        for line in process.stdout:
            elapsed = time.time() - start_time
            if elapsed > JOB_TIMEOUT:
                logger.error(f"Job {job_id}: Timeout exceeded ({JOB_TIMEOUT}s)")
                process.kill()
                raise TimeoutError(f"Job timeout after {JOB_TIMEOUT} seconds")
            
            line = line.strip()
            if line:
                logger.info(f"Job {job_id}: {line}")
                
                for marker, progress in progress_markers.items():
                    if marker in line:
                        jobs[job_id]["progress"] = progress
                        jobs[job_id]["message"] = line[:200]
                        jobs[job_id]["updated_at"] = datetime.now().isoformat()
                        break
        
        return_code = process.wait(timeout=30)
        
        if return_code == 0:
            # НЕ устанавливаем status="done" сразу! Сначала получаем grafana_url,
            # потому что frontend прекращает polling когда видит status="done"
            jobs[job_id]["progress"] = 95
            jobs[job_id]["message"] = "Generating Grafana link..."
            
            sn_list = jobs[job_id]["serial_numbers"]
            if sn_list:
                # Формируем ссылку на Grafana с временным диапазоном данных
                grafana_dashboard = f"{GRAFANA_URL}/d/huawei-oceanstor-real/huawei-oceanstor-real-data"
                sn = sn_list[0]  # Берём первый SN
                grafana_url = f"{grafana_dashboard}?var-SN={sn}"
                
                # Получаем временной диапазон данных из VictoriaMetrics
                time_from = None
                time_to = None
                scrape_interval = "5s"  # default
                
                try:
                    import time as time_module
                    from urllib.parse import urlencode
                    
                    # Используем export API для получения реального временного диапазона
                    # Читаем несколько серий чтобы найти min/max по всем данным
                    export_url = f"{VM_URL}/api/v1/export"
                    export_data = {
                        "match[]": f'{{SN="{sn}"}}'
                    }
                    export_response = requests.post(export_url, data=export_data, timeout=30, stream=True)
                    
                    series_count = 0
                    max_series = 100  # Читаем до 100 серий
                    
                    if export_response.status_code == 200:
                        for line in export_response.iter_lines(decode_unicode=True):
                            if line and not line.startswith("remoteAddr"):
                                import json
                                try:
                                    data = json.loads(line)
                                    timestamps = data.get("timestamps", [])
                                    if timestamps:
                                        # Находим min/max по всем сериям
                                        series_min = min(timestamps)
                                        series_max = max(timestamps)
                                        if time_from is None or series_min < time_from:
                                            time_from = series_min
                                        if time_to is None or series_max > time_to:
                                            time_to = series_max
                                        series_count += 1
                                        if series_count >= max_series:
                                            break
                                except json.JSONDecodeError:
                                    continue
                        export_response.close()
                        logger.info(f"Job {job_id}: Time range {time_from} - {time_to} (from {series_count} series)")
                    else:
                        logger.warning(f"Job {job_id}: Export API returned {export_response.status_code}")
                    
                    # Получаем scrape_interval из series (POST для правильного кодирования)
                    series_url = f"{VM_URL}/api/v1/series"
                    series_data = {
                        "match[]": f'{{SN="{sn}"}}',
                        "start": "0"
                    }
                    series_response = requests.post(series_url, data=series_data, timeout=10)
                    if series_response.status_code == 200:
                        series_data = series_response.json()
                        series_list = series_data.get("data", [])
                        if series_list and len(series_list) > 0:
                            interval_sec = series_list[0].get("scrape_interval")
                            if interval_sec:
                                interval_sec = int(interval_sec)
                                if interval_sec < 60:
                                    scrape_interval = f"{interval_sec}s"
                                elif interval_sec < 3600:
                                    scrape_interval = f"{interval_sec // 60}m"
                                else:
                                    scrape_interval = f"{interval_sec // 3600}h"
                                    
                except Exception as e:
                    logger.warning(f"Job {job_id}: Failed to get time range: {e}")
                
                # Добавляем var-min_interval
                grafana_url += f"&var-min_interval={scrape_interval}"
                
                # Добавляем временной диапазон если нашли
                if time_from and time_to:
                    grafana_url += f"&from={time_from}&to={time_to}"
                
                # Добавляем стандартные параметры (без лишних Q1-Q4 переменных)
                grafana_url += "&orgId=1&timezone=browser&var-Resource=$__all&var-Element=$__all"
                jobs[job_id]["grafana_url"] = grafana_url
            
            # Теперь устанавливаем status="done" ПОСЛЕ того как grafana_url готов
            # Это важно потому что frontend прекращает polling когда видит done
            jobs[job_id]["status"] = "done"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["message"] = "Processing completed successfully!"
            logger.info(f"Job {job_id}: Completed successfully")
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["progress"] = 0
            jobs[job_id]["message"] = "Pipeline failed"
            jobs[job_id]["error"] = f"Process exited with code {return_code}"
            logger.error(f"Job {job_id}: Failed with return code {return_code}")
        
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        try:
            archive_path.unlink()
            logger.info(f"Job {job_id}: Cleaned up uploaded file {archive_path}")
        except Exception as e:
            logger.warning(f"Job {job_id}: Failed to cleanup {archive_path}: {e}")
            
    except TimeoutError as e:
        if process and process.poll() is None:
            process.kill()
        
        jobs[job_id]["status"] = "error"
        jobs[job_id]["progress"] = 0
        jobs[job_id]["message"] = f"Job timeout after {JOB_TIMEOUT} seconds"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        logger.error(f"Job {job_id}: Timeout: {e}")
        
        try:
            if archive_path.exists():
                archive_path.unlink()
        except:
            pass
            
    except Exception as e:
        if process and process.poll() is None:
            process.kill()
            
        jobs[job_id]["status"] = "error"
        jobs[job_id]["progress"] = 0
        jobs[job_id]["message"] = "Fatal error during processing"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        logger.error(f"Job {job_id}: Fatal error: {e}", exc_info=True)
        
        try:
            if archive_path.exists():
                archive_path.unlink()
        except:
            pass


async def run_pipeline_async(job_id: str, archive_path: Path):
    """Async wrapper to run pipeline in thread pool."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, run_pipeline_sync, job_id, archive_path)


async def run_csv_parser_async(job_id: str, archive_path: Path):
    """Async wrapper to run CSV parser in thread pool."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, run_csv_parser_sync, job_id, archive_path)


async def run_perfmonkey_parser_async(job_id: str, archive_path: Path):
    """Async wrapper to run perfmonkey parser in thread pool."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, run_perfmonkey_parser_sync, job_id, archive_path)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Huawei Performance Data API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}


@app.post("/api/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target: str = Form("grafana")  # grafana | csv | perfmonkey
):
    """Upload ZIP or 7Z archive with chunked progress tracking.
    
    Args:
        file: ZIP or 7Z archive with .tgz files
        target: Processing target - 'grafana', 'csv' (wide format), or 'perfmonkey' (perfmonkey format)
    """
    
    # Validate target
    if target not in ["grafana", "csv", "perfmonkey"]:
        raise HTTPException(status_code=400, detail="Invalid target. Must be 'grafana', 'csv', or 'perfmonkey'")
    
    # Поддержка .zip и .7z архивов
    filename_lower = file.filename.lower()
    if not (filename_lower.endswith('.zip') or filename_lower.endswith('.7z')):
        raise HTTPException(status_code=400, detail="Only .zip and .7z files are allowed")
    
    # Проверка доступности py7zr для .7z файлов
    if filename_lower.endswith('.7z') and not PY7ZR_AVAILABLE:
        raise HTTPException(status_code=400, detail=".7z support not available. Please install py7zr or use .zip files.")
    
    job_id = str(uuid.uuid4())
    upload_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    
    try:
        upload_progress[job_id] = {
            "uploaded": 0,
            "total": 0,
            "speed": 0,
            "status": "uploading"
        }
        
        chunk_size = 1024 * 1024  # 1MB
        total_size = 0
        start_time = time.time()
        
        with open(upload_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                f.write(chunk)
                total_size += len(chunk)
                
                elapsed = time.time() - start_time
                speed = (total_size / (1024**2)) / elapsed if elapsed > 0 else 0
                
                upload_progress[job_id] = {
                    "uploaded": total_size,
                    "total": total_size,
                    "speed": speed,
                    "status": "uploading"
                }
                
                if total_size > MAX_UPLOAD_SIZE:
                    f.close()
                    upload_path.unlink()
                    del upload_progress[job_id]
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Max size: {MAX_UPLOAD_SIZE / (1024**3):.1f} GB"
                    )
        
        upload_progress[job_id]["status"] = "complete"
        elapsed_total = time.time() - start_time
        avg_speed = (total_size / (1024**2)) / elapsed_total if elapsed_total > 0 else 0
        
        logger.info(f"Job {job_id}: Uploaded {file.filename} ({total_size / (1024**2):.2f} MB in {elapsed_total:.1f}s @ {avg_speed:.1f} MB/s)")
        
        serial_numbers = extract_serial_numbers(upload_path)
        
        jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": 0,
            "message": "File uploaded, waiting to start...",
            "serial_numbers": serial_numbers,
            "grafana_url": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "error": None,
            "filename": file.filename,
            "target": target,
            "files": []
        }
        
        # Start appropriate background task based on target
        if target == "grafana":
            background_tasks.add_task(run_pipeline_async, job_id, upload_path)
            message_suffix = "processing started (VictoriaMetrics)"
        elif target == "csv":
            background_tasks.add_task(run_csv_parser_async, job_id, upload_path)
            message_suffix = "processing started (CSV wide format)"
        elif target == "perfmonkey":
            background_tasks.add_task(run_perfmonkey_parser_async, job_id, upload_path)
            message_suffix = "processing started (CSV perfmonkey format)"
        
        return {
            "job_id": job_id,
            "serial_numbers": serial_numbers,
            "target": target,
            "upload_size": total_size,
            "upload_time": elapsed_total,
            "upload_speed": avg_speed,
            "message": f"Upload successful, {message_suffix}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        if upload_path.exists():
            upload_path.unlink()
        if job_id in upload_progress:
            del upload_progress[job_id]
        if job_id in jobs:
            del jobs[job_id]
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/upload/progress/{job_id}")
async def get_upload_progress(job_id: str):
    """Get upload progress for streaming."""
    if job_id not in upload_progress:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    return upload_progress[job_id]


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get processing status for a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs."""
    return {
        "jobs": list(jobs.values()),
        "total": len(jobs)
    }


@app.get("/api/arrays")
async def list_arrays():
    """Get list of all imported arrays (serial numbers) from VictoriaMetrics with metadata."""
    try:
        # Query VictoriaMetrics for unique SN labels
        # IMPORTANT: Specify time range to get ALL data (not just recent)
        # VictoriaMetrics requires a valid Unix timestamp (not "0")
        # Using 2020-01-01 as start time to capture all Huawei data
        url = f"{VM_URL}/api/v1/label/SN/values"
        params = {
            "start": "1577836800",  # 2020-01-01 00:00:00 UTC
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch arrays from VictoriaMetrics")
        
        data = response.json()
        arrays = data.get("data", [])
        
        # Get scrape_interval for all arrays in ONE batch request
        import time
        end_time = int(time.time())
        start_time = end_time - (365 * 24 * 60 * 60)
        
        # Build scrape_interval map from single series query
        scrape_intervals = {}
        try:
            series_url = f"{VM_URL}/api/v1/series"
            series_data_req = {
                "match[]": '{SN=~".+"}',  # All series with SN label
                "start": str(start_time)
            }
            series_response = requests.post(series_url, data=series_data_req, timeout=30)
            
            if series_response.status_code == 200:
                series_data = series_response.json()
                for item in series_data.get("data", []):
                    sn = item.get("SN")
                    if sn and sn not in scrape_intervals:
                        interval_sec = item.get("scrape_interval")
                        if interval_sec:
                            interval_sec = int(interval_sec)
                            if interval_sec < 60:
                                scrape_intervals[sn] = f"{interval_sec}s"
                            elif interval_sec < 3600:
                                scrape_intervals[sn] = f"{interval_sec // 60}m"
                            else:
                                scrape_intervals[sn] = f"{interval_sec // 3600}h"
        except Exception as e:
            logger.warning(f"Failed to get scrape intervals: {e}")
        
        # Build metadata list (time_from/time_to are fetched on-demand)
        arrays_with_metadata = []
        for sn in sorted(arrays):
            arrays_with_metadata.append({
                "sn": sn,
                "scrape_interval": scrape_intervals.get(sn),
                "time_from": None,
                "time_to": None
            })
        
        # Return both old format (for compatibility) and new format
        return {
            "arrays": sorted(arrays),  # Legacy format (list of strings)
            "arrays_metadata": arrays_with_metadata,  # New format with metadata
            "total": len(arrays)
        }
    
    except Exception as e:
        logger.error(f"Error fetching arrays: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch arrays: {str(e)}")


@app.get("/api/array/{sn}/timerange")
async def get_array_timerange(sn: str):
    """Get time range for a specific array (on-demand, may take a few seconds)."""
    try:
        export_url = f"{VM_URL}/api/v1/export"
        export_data = {
            "match[]": f'{{SN="{sn}"}}'
            # НЕ используем max_rows_per_line чтобы получить все серии
        }
        export_response = requests.post(export_url, data=export_data, timeout=30, stream=True)
        
        time_from = None
        time_to = None
        series_count = 0
        max_series = 100  # Читаем до 100 серий для определения диапазона
        
        if export_response.status_code == 200:
            for line in export_response.iter_lines(decode_unicode=True):
                if line and not line.startswith("remoteAddr"):
                    try:
                        import json
                        data = json.loads(line)
                        timestamps = data.get("timestamps", [])
                        if timestamps:
                            # Находим min/max по всем сериям
                            series_min = min(timestamps)
                            series_max = max(timestamps)
                            if time_from is None or series_min < time_from:
                                time_from = series_min
                            if time_to is None or series_max > time_to:
                                time_to = series_max
                            series_count += 1
                            if series_count >= max_series:
                                break
                    except:
                        continue
            export_response.close()
        
        logger.info(f"Timerange for {sn}: {time_from} - {time_to} (from {series_count} series)")
        
        return {
            "sn": sn,
            "time_from": time_from,
            "time_to": time_to
        }
    except Exception as e:
        logger.error(f"Error getting timerange for {sn}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/csv-jobs")
async def list_csv_jobs():
    """Get list of all CSV processing jobs with their files."""
    csv_jobs = []
    
    # Filter only CSV and perfmonkey jobs
    for job_id, job_data in jobs.items():
        if job_data.get("target") in ["csv", "perfmonkey"]:
            files = get_job_files(job_id)
            
            # Determine serial numbers from filenames if not in job_data
            serial_numbers = job_data.get("serial_numbers", [])
            if not serial_numbers and files:
                # Try to extract from filenames (e.g., "2102354JMX1****00016.csv.gz")
                for f in files:
                    match = re.search(r"([0-9A-Z]{20,})", f["name"])
                    if match and match.group(1) not in serial_numbers:
                        serial_numbers.append(match.group(1))
            
            csv_jobs.append({
                "job_id": job_id,
                "target": job_data.get("target"),
                "target_label": "CSV Wide" if job_data.get("target") == "csv" else "CSV Perfmonkey",
                "serial_numbers": serial_numbers,
                "status": job_data.get("status"),
                "created_at": job_data.get("created_at"),
                "updated_at": job_data.get("updated_at"),
                "filename": job_data.get("filename", ""),
                "files": files,
                "total_files": len(files),
                "total_size_mb": round(sum(f["size"] for f in files) / (1024**2), 2)
            })
    
    # Sort by creation time (newest first)
    csv_jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "csv_jobs": csv_jobs,
        "total": len(csv_jobs)
    }


@app.delete("/api/arrays/{sn}")
async def delete_array(sn: str):
    """Delete all metrics for a specific array (serial number)."""
    try:
        # Delete series from VictoriaMetrics
        url = f"{VM_URL}/api/v1/admin/tsdb/delete_series"
        params = {"match[]": f'{{SN="{sn}"}}'}
        
        response = requests.post(url, params=params, timeout=30)
        
        if response.status_code in (200, 204):
            # Force merge to free up space
            merge_url = f"{VM_URL}/internal/force_merge"
            try:
                requests.post(merge_url, timeout=30)
            except:
                pass  # Non-critical
            
            logger.info(f"Deleted array {sn} from VictoriaMetrics")
            return {
                "status": "ok",
                "message": f"Array {sn} deleted successfully",
                "sn": sn
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to delete array: {response.text}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting array {sn}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete array: {str(e)}")


@app.delete("/api/arrays")
async def delete_all_arrays():
    """Delete ALL metrics from VictoriaMetrics."""
    try:
        # Delete all series
        url = f"{VM_URL}/api/v1/admin/tsdb/delete_series"
        params = {"match[]": "{__name__=~\".+\"}"}  # Match all metrics
        
        response = requests.post(url, params=params, timeout=60)
        
        if response.status_code in (200, 204):
            # Force merge
            merge_url = f"{VM_URL}/internal/force_merge"
            try:
                requests.post(merge_url, timeout=60)
            except:
                pass
            
            logger.info("Deleted all arrays from VictoriaMetrics")
            return {
                "status": "ok",
                "message": "All arrays deleted successfully"
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Failed to delete all arrays: {response.text}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting all arrays: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete all arrays: {str(e)}")


@app.get("/api/files/{job_id}")
async def get_job_files_endpoint(job_id: str):
    """Get list of output files for a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    files = get_job_files(job_id)
    
    return {
        "job_id": job_id,
        "files": files,
        "total": len(files),
        "total_size": sum(f["size"] for f in files),
        "total_size_mb": round(sum(f["size"] for f in files) / (1024 ** 2), 2)
    }


@app.get("/api/file/{job_id}/{filename}")
async def download_file(job_id: str, filename: str, request: Request):
    """Download a specific output file with HTTP Range support for resumable downloads."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_dir = WORK_DIR / job_id
    file_path = job_dir / filename
    
    # Security check: ensure filename doesn't contain path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    if filename.endswith('.csv.gz'):
        media_type = "application/gzip"
    elif filename.endswith('.csv'):
        media_type = "text/csv"
    else:
        media_type = "application/octet-stream"
    
    # FileResponse automatically handles Range requests
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@app.delete("/api/files/{job_id}")
async def delete_job_files(job_id: str):
    """Delete all output files for a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_dir = WORK_DIR / job_id
    
    if not job_dir.exists():
        return {"message": "No files to delete", "job_id": job_id}
    
    try:
        deleted_count = len(list(job_dir.glob("*.csv.gz")))
        shutil.rmtree(job_dir)
        
        # Update job status
        jobs[job_id]["files"] = []
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"Deleted {deleted_count} files for job {job_id}")
        
        return {
            "message": f"Deleted {deleted_count} files",
            "job_id": job_id,
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error deleting files for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete files: {str(e)}")


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    """Delete job record and associated files."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete files if they exist
    job_dir = WORK_DIR / job_id
    if job_dir.exists():
        try:
            shutil.rmtree(job_dir)
            logger.info(f"Deleted files for job {job_id}")
        except Exception as e:
            logger.warning(f"Failed to delete files for job {job_id}: {e}")
    
    del jobs[job_id]
    return {"message": f"Job {job_id} deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
