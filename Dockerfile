# Multi-stage Dockerfile for HealthLink
# Optimized for Google Cloud Run deployment.
# Produces ONE image containing the FastAPI backend AND the built React frontend
# (FastAPI serves the SPA at "/" and the API at "/api/v1").

# ---- Frontend build stage (React via Vite) ----
FROM node:22-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci || npm install
COPY frontend/ ./
# Empty VITE_API_BASE -> the SPA calls relative "/api/..." (same origin as the
# backend), so no CORS and no backend URL needs to be baked in.
ENV VITE_API_BASE=""
RUN npm run build

# ---- Python build stage ----
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080 \
    HF_HOME=/app/hf_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/hf_cache \
    TOKENIZERS_PARALLELISM=false

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create app directory
WORKDIR /app

# Copy application code
COPY . .

# Copy the built React frontend from the frontend-builder stage so FastAPI can
# serve it at "/". (frontend/ source is excluded via .dockerignore; only the
# compiled dist is brought in here.)
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/hf_cache

# Pre-download the embedding model so it's baked into the image
# (avoids a HuggingFace download on every Cloud Run cold start).
RUN python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')"

# Create non-root user
RUN useradd -m -u 1000 healthlink && \
    chown -R healthlink:healthlink /app
USER healthlink

# Expose port (Cloud Run injects $PORT, defaulting to 8080)
EXPOSE 8080

# Health check (uses $PORT so it matches whatever Cloud Run assigns)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/v1/health || exit 1

# Run application. Shell form so ${PORT} is expanded at runtime; `exec` keeps
# uvicorn as PID 1 so it receives Cloud Run's SIGTERM for graceful shutdown.
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1