# edge/errors

Cuerpos JSON (formato de error de la API, `Content-Type: application/json`) que nginx devuelve con `error_page`:

- `upstream_unavailable.json`: un servicio responde 502, 503 o 504, o `gateway-auth` no responde (`auth_request` lo convierte en 500 y nginx lo devuelve como 503).
- `unauthorized.json`: 401 del gateway, sin sesión o con un token inválido.
- `forbidden.json`: 403 del gateway, rol insuficiente para el prefijo.

Los dos últimos llevan `detail.source = "gateway"` para distinguirlos de un 401/403 del servicio. La imagen de `edge` copia la carpeta a `/etc/nginx/errors` y [`nginx.conf`](../nginx.conf) la usa en `error_page`. Más en el [README de `edge`](../README.md).
