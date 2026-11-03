# catalog-streaming: catálogo, audio y portadas de canciones.
# Se construye desde la raíz del repo (necesita media/seed).
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY services/catalog-streaming/pyproject.toml services/catalog-streaming/alembic.ini ./
COPY services/catalog-streaming/app ./app
RUN pip install --no-cache-dir ".[dev]" && rm -rf build *.egg-info
COPY services/catalog-streaming/scripts ./scripts
COPY services/catalog-streaming/tests ./tests
COPY media/seed ./media/seed
RUN chmod +x /app/scripts/entrypoint.sh /app/scripts/init.sh

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
