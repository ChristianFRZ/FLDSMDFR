# Contexto de construcción: la raíz del repositorio (copia services/common).
FROM python:3.12-slim
RUN useradd --create-home meloxo
WORKDIR /app
COPY services/common /tmp/common
RUN pip install --no-cache-dir /tmp/common && rm -rf /tmp/common
COPY services/gateway-auth/pyproject.toml ./
COPY services/gateway-auth/gateway_auth ./gateway_auth
RUN pip install --no-cache-dir .
USER meloxo
EXPOSE 8004
CMD ["uvicorn", "gateway_auth.main:app", "--host", "0.0.0.0", "--port", "8004"]
