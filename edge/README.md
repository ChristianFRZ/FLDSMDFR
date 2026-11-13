# edge

Puerta de entrada de MELOXO (puerto `8080`): un nginx que sirve la SPA del `frontend/` y reparte `/api/*` entre los tres servicios. Los servicios no publican puertos; solo `edge` es alcanzable desde fuera.

## Rutas

nginx elige el `location` con el prefijo más largo. Los prefijos que terminan en `/` evitan que `/api/composer` capture `/api/composer-requests`.

| Servicio | Prefijos |
|---|---|
| `users-playlists` (:8001) | `/api/auth/`, `/api/users/`, `/api/composer-requests`, `/api/admin/composer-requests`, `/api/admin/users`, `/api/admin/audit`, `/api/playlists`, `/api/favorites`, `/api/follows`, `/api/notices`, `/api/releases`, `/api/tapes` |
| `catalog-streaming` (:8002) | `/api/songs`, `/api/artists`, `/api/genres`, `/api/media/`, `/api/composer/`, `/api/admin/catalog`, `/api/admin/songs` |
| `playback-metrics` (:8003) | `/api/playbacks`, `/api/metrics`, `/api/admin/health`, `/api/admin/reports` |
| edge | `/internal/` responde 404; `/api/health` responde `{"status":"ok"}`; todo lo demás es la SPA (`try_files $uri /index.html`) |

## Audio y subidas

- `/api/songs/{id}/stream` y `/api/media/`: `proxy_buffering off`, `proxy_request_buffering off`, `proxy_read_timeout 3600s`, `Range` e `If-Range` reenviados y sin gzip.
- `/api/composer/` (MP3 de hasta 15 MB y portadas): `client_max_body_size 20m`. El resto de rutas admite 1 MB.

## Servicio caído

nginx resuelve los nombres en cada petición (`resolver 127.0.0.11`, el DNS de Docker, con `proxy_pass` por variable). Por eso arranca aunque un servicio esté caído y lo recupera cuando vuelve. Si un servicio no responde (502, 503 o 504), edge devuelve el JSON de error de la API (`edge/errors/upstream_unavailable.json`) con `Content-Type: application/json`:

```json
{"error":{"code":"upstream_unavailable","message":"Servicio no disponible","detail":null}}
```

## Pruebas

Ver [tests/README.md](tests/README.md).

```bash
.venv/bin/pytest edge/tests -q -m "not stack"
docker compose up -d --build && .venv/bin/pytest edge/tests -q -m stack
```
