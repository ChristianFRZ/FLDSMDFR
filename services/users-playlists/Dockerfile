# users-playlists: usuarios, casetes y social. Emite los JWT de sesión.
# Se construye desde la raíz del repo (necesita media/seed).
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY services/users-playlists/pyproject.toml services/users-playlists/alembic.ini ./
COPY services/users-playlists/app ./app
RUN pip install --no-cache-dir ".[dev]" && rm -rf build *.egg-info
COPY services/users-playlists/scripts ./scripts
COPY services/users-playlists/tests ./tests
COPY media/seed ./media/seed
RUN chmod +x /app/scripts/entrypoint.sh

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
