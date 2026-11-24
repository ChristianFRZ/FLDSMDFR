# Contexto de construcción: la raíz del repositorio (copia services/common).
FROM python:3.12-slim
RUN useradd --create-home meloxo
WORKDIR /app
COPY services/common /tmp/common
RUN pip install --no-cache-dir /tmp/common && rm -rf /tmp/common
COPY services/playback-metrics/pyproject.toml services/playback-metrics/alembic.ini ./
COPY services/playback-metrics/playback_metrics ./playback_metrics
COPY services/playback-metrics/migrations ./migrations
RUN pip install --no-cache-dir .
USER meloxo
EXPOSE 8003
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn playback_metrics.main:app --host 0.0.0.0 --port 8003"]
