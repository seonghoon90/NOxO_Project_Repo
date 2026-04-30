# syntax=docker/dockerfile:1.6

# ===== Stage 1: builder =====
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
 && rm -rf /var/lib/apt/lists/*
COPY apps/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===== Stage 2: dev =====
FROM python:3.11-slim AS dev
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Seoul \
    PYTHONPATH=/app/apps/backend:/app
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata curl \
 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--reload", \
     "--reload-dir", "/app/apps/backend/app", \
     "--reload-dir", "/app/digital_twin"]

# ===== Stage 3: prod =====
FROM python:3.11-slim AS prod
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Seoul \
    PYTHONPATH=/app/apps/backend:/app
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd -r app && useradd -r -g app -d /app app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=app:app apps/backend ./apps/backend
COPY --chown=app:app digital_twin ./digital_twin
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
