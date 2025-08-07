# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for PyTorch + sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    curl \
    libopenblas-dev \
    libomp-dev \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Optional: use precompiled torch wheels to reduce build time
ENV PIP_NO_CACHE_DIR=1

# Create virtual environment and install Python dependencies
COPY requirements.txt .
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    /venv/bin/pip install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /venv /venv

# Use virtualenv as the Python environment
ENV PATH="/venv/bin:$PATH"

# Copy app source
COPY backend ./backend

WORKDIR /app

# CMD ["uvicorn", "backend.code.api:app", "--host", "0.0.0.0", "--port", "8088"]
# # Expose the required port for FastAPI or your app
EXPOSE 8088

# Set the entrypoint or command to run the script when the container starts
CMD ["python -m backend.code.embed_documents && uvicorn backend.code.main:app --host 0.0.0.0 --port 8088"]
