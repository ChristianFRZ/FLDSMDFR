# Contexto de construcción: la raíz del repositorio (copia services/common).
FROM python:3.12-slim
RUN useradd --create-home meloxo
WORKDIR /app
COPY services/common /tmp/common
RUN pip install --no-cache-dir /tmp/common && rm -rf /tmp/common
COPY services/users-playlists/pyproject.toml services/users-playlists/alembic.ini ./
COPY services/users-playlists/users_playlists ./users_playlists
COPY services/users-playlists/migrations ./migrations
RUN pip install --no-cache-dir .
USER meloxo
EXPOSE 8001
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn users_playlists.main:app --host 0.0.0.0 --port 8001"]
