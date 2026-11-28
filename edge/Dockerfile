# Contexto de construcción: la raíz del repositorio.
FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine AS nginx
COPY --from=web /web/dist /usr/share/nginx/html
COPY edge/nginx.conf /etc/nginx/nginx.conf
COPY edge/errors /etc/nginx/errors
EXPOSE 80
