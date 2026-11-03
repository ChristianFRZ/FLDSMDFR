# Servicios

Cada carpeta es un servicio FastAPI autónomo: su `Dockerfile`, su `pyproject.toml`, su base de datos, su cadena de migraciones y sus pruebas. Ninguno importa código de otro; lo que necesitan se piden por HTTP a la API interna (`/internal/...`) del dueño del dato.

| Servicio | Módulos | Base | Expone en `/internal` | Llama a |
|---|---|---|---|---|
| [`gateway/`](gateway) | — (prefijo → servicio en `app/routes.py`, reenvío en `app/proxy.py`) | — | — (bloquea `/internal` con `404`) | todos, por round-robin |
| [`users-playlists/`](users-playlists) | `users`, `playlists`, `social` | `users_playlists` | `GET /users/count` | `catalog-streaming` |
| [`catalog-streaming/`](catalog-streaming) (×3 réplicas) | `catalog` | `catalog` | canciones por id, lote, conteo y búsqueda exacta; conteos, última canción y lanzamientos por artista | — |
| [`playback-metrics/`](playback-metrics) | `playback` | `playback` | — | `catalog-streaming`, `users-playlists` |

Los clientes HTTP viven en `app/clients/` de quien consume y conservan el nombre y el tipo de retorno de la función que se importaba en el monolito. Fallas remotas: `404` → el mismo `NotFound`; sin conexión o `5xx` → `503 service_unavailable`.

**Directorio (desde `03`).** Cada servicio, incluido el gateway, lleva su copia de `app/shared/discovery.py`. Al arrancar se registra en Consul (`discovery:8500`) con id `<servicio>-<hostname>` y check TTL, manda latido cada 3 s y se da de baja al apagarse. Los clientes no tienen URLs: `http.call("catalog-streaming", ...)` pide las instancias vivas (caché de 5 s) y elige una en round-robin; sin instancias → `503`. Cada respuesta lleva `X-Instancia`.

Pruebas: `docker compose --profile test run --rm tests-catalog | tests-users | tests-playback | tests-gateway`.
