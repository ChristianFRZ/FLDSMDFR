# web: proxy mínimo de 02-separacion. Compila el SPA de Vue y lo sirve con Nginx, que además
# reparte /api por prefijo hacia los tres servicios. Sin balanceo ni directorio (rama 03).
FROM node:22-alpine AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=ui /ui/dist /usr/share/nginx/html
