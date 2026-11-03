# Servicios

Cada carpeta es un servicio FastAPI autónomo: su `Dockerfile`, su `pyproject.toml`, su base de datos, su cadena de migraciones y sus pruebas. Ninguno importa código de otro; lo que necesitan se piden por HTTP a la API interna (`/internal/...`) del dueño del dato.

| Servicio | Módulos | Base | Expone en `/internal` | Llama a |
|---|---|---|---|---|
| [`users-playlists/`](users-playlists) | `users`, `playlists`, `social` | `users_playlists` | `GET /users/count` | `catalog-streaming` |
| [`catalog-streaming/`](catalog-streaming) | `catalog` | `catalog` | canciones por id, lote, conteo y búsqueda exacta; conteos, última canción y lanzamientos por artista | — |
| [`playback-metrics/`](playback-metrics) | `playback` | `playback` | — | `catalog-streaming`, `users-playlists` |

Los clientes HTTP viven en `app/clients/` de quien consume y conservan el nombre y el tipo de retorno de la función que se importaba en el monolito. Fallas remotas: `404` → el mismo `NotFound`; sin conexión o `5xx` → `503 service_unavailable`.

Pruebas: `docker compose --profile test run --rm tests-catalog | tests-users | tests-playback`.
