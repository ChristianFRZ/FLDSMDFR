# catalog_streaming

Paquete de Python del servicio [`catalog-streaming`](../README.md).

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`main.py`](main.py) | `create_app()`: rutas de catálogo y compositor, medición de latencia y las tareas periódicas `publicar_programadas` (30 s) y `refrescar_jamendo` (24 h) |
| [`internal_routes.py`](internal_routes.py) | Rutas `/internal/*` para otros servicios (ver tabla abajo) |
| [`config.py`](config.py) | `Settings`, que extiende la configuración común con `USERS_URL`, Jamendo, `MEDIA_DIR` y límites de subida |
| [`auth.py`](auth.py) | `auth`: usuario actual y roles, con el estado de `users-playlists` guardado 30 s |
| [`clients/`](clients/README.md) | Llamadas HTTP a otros servicios |
| [`modules/`](modules/README.md) | Los módulos del servicio |

## Rutas internas

Van bajo `/internal`, no llevan autenticación y nginx no las publica. Las listas de identificadores van separadas por comas y admiten 200 como máximo (más, o un id mal formado, dan `422`).

| Ruta | Respuesta |
| --- | --- |
| `GET /internal/songs?ids=` y `GET /internal/artists?ids=` | `{uuid: SongSummary}` / `{uuid: ArtistSummary}`; los ids que no existen no aparecen |
| `GET /internal/songs/{id}/playable` | `{"playable": bool}` (solo `published`) |
| `GET /internal/artists/upcoming?artist_ids=` | `list[UpcomingRelease]` |
| `GET /internal/artists/published-since?artist_ids=&since=` | `list[PublishedRelease]`; `since` ISO 8601 o vacío; sin Jamendo |
| `GET /internal/owners/{user_id}/songs` | `list[UUID]` |
| `GET /internal/catalog/by-source` | `{"local": n, "jamendo": n}` |
| `GET /internal/catalog/release-counts?owner_id=` | `ReleaseCounts` |
| `GET /internal/jamendo-status` | `{"status": str}` |
| `GET /internal/health` | `{"name", "status", "database_ms", "uptime_seconds"}`; siempre `200`, con `status: "down"` si la base no responde |
| `POST /internal/latency/drain` | Cubos de latencia (de `meloxo_common`) |

Semilla de demostración:

| Ruta | Petición | Respuesta |
| --- | --- | --- |
| `POST /internal/demo/catalog` | `{"composers": [{"user_id", "name", "bio", "tracks": [{"title", "genre", "audio_path", "duration", "status", "publish_at", "published_at"}]}]}` | `204` |
| `POST /internal/demo/catalog/clear` | vacía | `204` |
| `POST /internal/demo/catalog/import` | `{"genres": [str], "per_genre": int}`; llama a Jamendo y espera a que termine | `{"status", "imported", "error"}` |
| `GET /internal/demo/catalog/import-done?genres=a,b&minimum=n` | | `{"done": bool}` |
| `GET /internal/demo/catalog/listenable?limit=n` | | `[{"id", "artist_id", "duration", "source"}]` |
