# users_playlists

Paquete de Python del servicio [`users-playlists`](../README.md).

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`main.py`](main.py) | `create_app()`: rutas de usuarios, playlists, favoritas, seguidos y casetes, y medición de latencia. En el arranque crea el primer administrador si `ADMIN_EMAIL` y `ADMIN_PASSWORD` están definidos. No tiene tareas periódicas |
| [`internal_routes.py`](internal_routes.py) | Rutas `/internal/*` para otros servicios (ver tabla abajo) |
| [`config.py`](config.py) | `Settings`, que extiende la configuración común con `CATALOG_URL`, los datos del primer administrador, `DEMO_PASSWORD` y los límites de casetes |
| [`auth.py`](auth.py) | `current_user` y `require_role`: el rol y el estado se leen de la base propia en cada petición, sin caché ni red |
| [`security.py`](security.py) | Hash argon2 de contraseñas, token de acceso y tokens opacos |
| [`clients/`](clients/README.md) | Llamadas HTTP a otros servicios |
| [`modules/`](modules/README.md) | Los módulos del servicio |

## Rutas internas

Van bajo `/internal`, no llevan autenticación y nginx no las publica. Las listas de identificadores van separadas por comas y admiten 200 como máximo (más, o un id mal formado, dan `422`).

| Ruta | Respuesta |
| --- | --- |
| `GET /internal/users/{id}/auth-state` | `AuthState`; `404` con `{"error": {"code": "not_found"}}` si no existe |
| `GET /internal/users/display-names?ids=` | `{uuid: nombre}`; los ids que no existen no aparecen |
| `POST /internal/audit` | Cuerpo `AuditEntry`; `204` |
| `GET /internal/users/growth?days=` | `list[UserGrowthPoint]` (`days` por defecto 30) |
| `GET /internal/playlists/inclusions?song_ids=` | `{"count": n}`: playlists distintas que incluyen alguna de las pistas |
| `GET /internal/tapes/inclusions?song_ids=` | `{"count": n}`: casetes distintos |
| `GET /internal/tapes/activity` | `TapeActivity` |
| `GET /internal/health` | `{"name", "status", "database_ms", "uptime_seconds"}`; siempre `200`, con `status: "down"` si la base no responde |
| `POST /internal/latency/drain` | Cubos de latencia (de `meloxo_common`) |

Semilla de demostración (todo lo que crea queda marcado como demo):

| Ruta | Cuerpo | Respuesta |
| --- | --- | --- |
| `POST /internal/demo/users` | `{"users": [{"email", "display_name", "role", "created_at", "request_message"?}], "password"}` | `{"ids": {email: uuid}}` |
| `GET /internal/demo/users/ids` | | `{"ids": [uuid]}` (usuarios demo) |
| `POST /internal/demo/users/clear` | vacío | `204` |
| `POST /internal/demo/playlists` | `{"playlists": [{"owner_id", "name", "is_public", "song_ids": [uuid]}]}` | `204` |
| `POST /internal/demo/playlists/clear` | vacío | `204` |
| `POST /internal/demo/social` | `{"tapes": [{"creator_id", "title", "color", "member_ids": [uuid], "tracks": [{"song_id", "added_by", "dedication"?}]}], "favorites": [[user_id, song_id]], "follows": [[user_id, artist_id]]}`; los tres campos son opcionales | `204` |
| `POST /internal/demo/social/clear` | `{"user_ids": [uuid]}`: borra los casetes demo y los favoritos, seguidos y avisos vistos de esos usuarios | `204` |
