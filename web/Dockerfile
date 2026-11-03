# web: compila el SPA de Vue y lo sirve con Nginx. En 03 queda detrás del gateway y se registra
# en el directorio como cualquier otro servicio (web/register.sh).
FROM node:22-alpine AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

FROM nginx:1.27-alpine
RUN apk add --no-cache curl
COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY web/register.sh /register.sh
COPY --from=ui /ui/dist /usr/share/nginx/html
RUN chmod +x /register.sh
ENTRYPOINT ["/register.sh"]
