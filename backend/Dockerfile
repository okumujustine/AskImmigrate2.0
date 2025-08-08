FROM python:3.10-slim

WORKDIR /app

# Install minimal system dependencies for ML workloads
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    WORKERS=4 \
    MAX_WORKERS=8 \
    TIMEOUT=60 \
    TRANSFORMERS_CACHE=/app/cache \
    SENTENCE_TRANSFORMERS_HOME=/app/cache

# Install PyTorch CPU-only first (smaller)
RUN pip install --no-cache-dir \
    torch==2.1.2+cpu torchvision==0.16.2+cpu torchaudio==2.1.2+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies  
COPY requirements.txt .
RUN pip install --no-cache-dir --no-deps sentence-transformers>=2.5.1
RUN grep -v "^torch\|^sentence-transformers\|^#\|^$" requirements.txt > requirements-filtered.txt && \
    pip install --no-cache-dir -r requirements-filtered.txt

# Create cache directory for models
RUN mkdir -p /app/cache

# Copy app source
COPY . .

# Set Python path so imports work correctly
ENV PYTHONPATH="/app:$PYTHONPATH"

# Pre-download the all-mpnet-base-v2 model during build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-mpnet-base-v2')"

# Create non-root user for security (Debian style)
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8088

# Optimized startup with resource limits for 8GB RAM/8vCPU server
CMD ["uvicorn", "code.api:app", \
     "--host", "0.0.0.0", \
     "--port", "8088", \
     "--workers", "4", \
     "--timeout-keep-alive", "5", \
     "--access-log"]
