# Etapa 1: compila el SPA de Vue (ui/dist).
FROM node:22-alpine AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

# Etapa 2: monolito FastAPI que sirve la API y el SPA compilado.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY scripts ./scripts
COPY media/seed ./media/seed
RUN pip install --no-cache-dir ".[dev]"

# Settings.ui_dist_dir = "ui/dist", relativo a WORKDIR /app.
COPY --from=ui /ui/dist ./ui/dist

RUN chmod +x /app/scripts/entrypoint.sh

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
