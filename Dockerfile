# syntax=docker/dockerfile:1
# ---- Python RAG service image ----
# Slim base keeps the image small enough for a free-tier EC2 instance.
FROM python:3.11-slim

# Don't write .pyc files; flush stdout/stderr immediately for live logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps: build tools occasionally needed by faiss/numpy wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so this layer is cached across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source.
COPY app ./app

# Persisted data (FAISS index, uploads) and logs live on a mounted volume.
RUN mkdir -p data/uploads logs

EXPOSE 8000

# Container healthcheck hits the liveness endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Run the ASGI server, binding to all interfaces inside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
