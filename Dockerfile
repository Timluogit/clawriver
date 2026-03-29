FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-recommends curl && rm -rf /var/lib/apt/lists/*

ARG CACHE_BUST=0
COPY requirements-minimal.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements-minimal.txt

COPY app/ ./app/
COPY pyproject.toml .

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# cache bust 1774780696
