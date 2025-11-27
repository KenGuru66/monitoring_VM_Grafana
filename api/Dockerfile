FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt

# Copy application code
COPY api/main.py /app/api/main.py
COPY huawei_streaming_pipeline.py /app/huawei_streaming_pipeline.py
COPY Data2csv /app/Data2csv
COPY perfmonkey /app/perfmonkey

# Create necessary directories
RUN mkdir -p /app/uploads /app/Data2csv/output /app/log

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

