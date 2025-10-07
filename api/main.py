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
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
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
OUTPUT_DIR = Path("/app/Data2csv/output")
VM_URL = os.getenv("VM_URL", "http://victoriametrics:8428")
VM_IMPORT_URL = os.getenv("VM_IMPORT_URL", "http://victoriametrics:8428/api/v1/import/prometheus")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024 * 1024))
JOB_TIMEOUT = int(os.getenv("JOB_TIMEOUT", 86400))  # 24 hours default

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Job storage
jobs: Dict[str, dict] = {}
upload_progress: Dict[str, dict] = {}

# Thread pool
executor = ThreadPoolExecutor(max_workers=4)


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


def extract_serial_numbers(zip_path: Path) -> list[str]:
    """Extract serial numbers from .tgz filenames inside ZIP archive."""
    serial_numbers = set()
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for filename in zip_ref.namelist():
                matches = re.findall(r"_SN_([0-9A-Z]+)_SP\d+", filename)
                if matches:
                    serial_numbers.add(matches[0])
        
        return sorted(list(serial_numbers))
    except Exception as e:
        logger.error(f"Error extracting serial numbers: {e}")
        return []


def run_pipeline_sync(job_id: str, zip_path: Path):
    """Run the Huawei processing pipeline synchronously."""
    import subprocess
    
    start_time = time.time()
    process = None
    
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["progress"] = 10
        jobs[job_id]["message"] = "Starting pipeline..."
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        jobs[job_id]["start_time"] = start_time
        
        cmd = [
            "python3",
            "/app/huawei_streaming_pipeline.py",
            "-i", str(zip_path),
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
            jobs[job_id]["status"] = "done"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["message"] = "Processing completed successfully!"
            
            sn_list = jobs[job_id]["serial_numbers"]
            if sn_list:
                grafana_dashboard = f"{GRAFANA_URL}/d/huawei-oceanstor-real/huawei-oceanstor-real-data"
                jobs[job_id]["grafana_url"] = grafana_dashboard
            
            logger.info(f"Job {job_id}: Completed successfully")
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["progress"] = 0
            jobs[job_id]["message"] = "Pipeline failed"
            jobs[job_id]["error"] = f"Process exited with code {return_code}"
            logger.error(f"Job {job_id}: Failed with return code {return_code}")
        
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        try:
            zip_path.unlink()
            logger.info(f"Job {job_id}: Cleaned up uploaded file {zip_path}")
        except Exception as e:
            logger.warning(f"Job {job_id}: Failed to cleanup {zip_path}: {e}")
            
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
            if zip_path.exists():
                zip_path.unlink()
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
            if zip_path.exists():
                zip_path.unlink()
        except:
            pass


async def run_pipeline_async(job_id: str, zip_path: Path):
    """Async wrapper to run pipeline in thread pool."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, run_pipeline_sync, job_id, zip_path)


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
    file: UploadFile = File(...)
):
    """Upload ZIP archive with chunked progress tracking."""
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")
    
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
            "filename": file.filename
        }
        
        background_tasks.add_task(run_pipeline_async, job_id, upload_path)
        
        return {
            "job_id": job_id,
            "serial_numbers": serial_numbers,
            "upload_size": total_size,
            "upload_time": elapsed_total,
            "upload_speed": avg_speed,
            "message": "Upload successful, processing started"
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
    """Get list of all imported arrays (serial numbers) from VictoriaMetrics."""
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
        
        if response.status_code == 200:
            data = response.json()
            arrays = data.get("data", [])
            return {
                "arrays": sorted(arrays),
                "total": len(arrays)
            }
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch arrays from VictoriaMetrics")
    
    except Exception as e:
        logger.error(f"Error fetching arrays: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch arrays: {str(e)}")


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


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    """Delete job record."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    del jobs[job_id]
    return {"message": f"Job {job_id} deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
