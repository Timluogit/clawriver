FROM python:3.12-slim AS builder

WORKDIR /build

# System deps for building native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements-prod.txt

# ---- Runtime ----
FROM python:3.12-slim

LABEL maintainer="ClawRiver"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

# Create non-root user (compatible with slim image)
RUN addgroup --system app && adduser --system --ingroup app --home ${APP_HOME} --shell /sbin/nologin app

WORKDIR ${APP_HOME}

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY pyproject.toml .
COPY scripts/ ./scripts/
COPY clawriver/ ./clawriver/
COPY clawriver_mcp/ ./clawriver_mcp/
COPY skills/ ./skills/

RUN mkdir -p /app/data /app/logs && chown -R app:app ${APP_HOME}

USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
