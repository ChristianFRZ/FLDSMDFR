# edge/errors

`upstream_unavailable.json` es el cuerpo que nginx devuelve cuando un servicio responde 502, 503 o 504 (formato de error de la API, `Content-Type: application/json`). La imagen de `edge` lo copia a `/etc/nginx/errors` y [`nginx.conf`](../nginx.conf) lo usa en `error_page`. Más en el [README de `edge`](../README.md).
