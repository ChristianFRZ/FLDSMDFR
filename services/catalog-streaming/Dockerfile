# Contexto de construcción: la raíz del repositorio (copia services/common).
FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home meloxo \
 && mkdir -p /media && chown meloxo /media
WORKDIR /app
COPY services/common /tmp/common
RUN pip install --no-cache-dir /tmp/common && rm -rf /tmp/common
COPY services/catalog-streaming/pyproject.toml services/catalog-streaming/alembic.ini ./
COPY services/catalog-streaming/catalog_streaming ./catalog_streaming
COPY services/catalog-streaming/migrations ./migrations
RUN pip install --no-cache-dir .
USER meloxo
EXPOSE 8002
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn catalog_streaming.main:app --host 0.0.0.0 --port 8002"]
