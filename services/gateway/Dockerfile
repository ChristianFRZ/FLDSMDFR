# gateway: la única puerta. Reparte por prefijo y en round-robin entre las instancias vivas
# que anuncia el directorio (Consul). Se construye desde la raíz del repo.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY services/gateway/pyproject.toml ./
COPY services/gateway/app ./app
RUN pip install --no-cache-dir ".[dev]" && rm -rf build *.egg-info
COPY services/gateway/tests ./tests

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
