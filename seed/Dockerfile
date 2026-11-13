# Contexto de construcción: la raíz del repositorio.
FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home meloxo \
 && mkdir -p /media && chown meloxo /media
WORKDIR /app
COPY seed/pyproject.toml ./
RUN pip install --no-cache-dir "httpx>=0.27" "mutagen>=1.47"
COPY seed ./seed
USER meloxo
CMD ["python", "-m", "seed", "all"]
