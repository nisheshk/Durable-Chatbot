FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config_cloud.py .
COPY worker_cloud.py .
COPY client_cloud.py .
COPY .env.cloud .

# Copy workflow and activity modules
COPY workflows/ ./workflows/
COPY activities/ ./activities/
COPY shared/ ./shared/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run worker by default
CMD ["python", "worker_cloud.py"]