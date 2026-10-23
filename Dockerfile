FROM python:3.13-slim

WORKDIR /app

# Instalar dependencias del sistema mínimas necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requerimientos y realizar instalación
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente y assets
COPY . .

# Exponer el puerto del monolito
EXPOSE 8000

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV FLDSMDFR_HOST=0.0.0.0
ENV FLDSMDFR_PORT=8000

# Inicializar DB y correr servidor Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
