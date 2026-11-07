FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home meloxo \
 && mkdir -p /media && chown meloxo /media
WORKDIR /app
COPY backend/pyproject.toml backend/alembic.ini ./
COPY backend/app ./app
COPY backend/seed ./seed
COPY backend/migrations ./migrations
RUN pip install --no-cache-dir .
COPY --from=web /web/dist ./static
ENV STATIC_DIR=/app/static MEDIA_DIR=/media
USER meloxo
EXPOSE 8080
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8080"]
