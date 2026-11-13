# services

Los tres servicios de MELOXO y el paquete que comparten. Cada carpeta se instala, prueba y construye por separado (tiene su `pyproject.toml`; los servicios, además, `Dockerfile`, `alembic.ini` y `migrations/`).

| Carpeta | Qué es |
| --- | --- |
| [`common`](common) | Paquete `meloxo_common` con lo compartido (errores, JWT, configuración, cliente interno…). Sin reglas de negocio |
| [`users-playlists`](users-playlists) | Usuarios, sesiones, listas, favoritos, seguidores y administración (:8001) |
| [`catalog-streaming`](catalog-streaming) | Canciones, artistas, géneros, audio y subidas del compositor (:8002) |
| [`playback-metrics`](playback-metrics) | Reproducciones, métricas, salud y reportes (:8003) |

Ninguno publica puertos al exterior: se llega a ellos por [`edge`](../edge). Cada servicio tiene su propia base de datos (ver [`infra/postgres`](../infra/postgres)).
Detalles de cada uno en su README.
