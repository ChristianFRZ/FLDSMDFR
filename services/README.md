# services

Los servicios de MELOXO y el paquete que comparten. Cada carpeta se instala, prueba y construye por separado (tiene su `pyproject.toml`; los servicios, además, `Dockerfile`, `alembic.ini` y `migrations/`).

| Carpeta | Qué es |
| --- | --- |
| [`common`](common/README.md) | Paquete `meloxo_common` con lo compartido (errores, JWT, configuración, cliente interno…). Sin reglas de negocio |
| [`users-playlists`](users-playlists/README.md) | Usuarios, sesiones, listas, favoritos, seguidores y administración (:8001) |
| [`catalog-streaming`](catalog-streaming/README.md) | Canciones, artistas, géneros, audio y subidas del compositor (:8002) |
| [`playback-metrics`](playback-metrics/README.md) | Reproducciones, métricas, salud y reportes (:8003) |
| [`gateway-auth`](gateway-auth/README.md) | Valida sesión y rol para el `auth_request` de nginx; sin base de datos (:8004) |

Ninguno publica puertos al exterior: se llega a ellos por [`edge`](../edge/README.md). `catalog-streaming` corre con dos réplicas detrás de `edge`. Los tres servicios de negocio tienen su propia base de datos (ver [`infra/postgres`](../infra/postgres/README.md)). Detalles de cada uno en su README.
