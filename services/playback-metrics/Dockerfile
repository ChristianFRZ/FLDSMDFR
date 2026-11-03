# playback-metrics: eventos de reproducción, historial y métricas.
# Se construye desde la raíz del repo.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY services/playback-metrics/pyproject.toml services/playback-metrics/alembic.ini ./
COPY services/playback-metrics/app ./app
RUN pip install --no-cache-dir ".[dev]" && rm -rf build *.egg-info
COPY services/playback-metrics/tests ./tests

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
