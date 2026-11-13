# meloxo_common

Paquete de Python con lo que comparten los tres servicios de MELOXO. Aquí no van reglas de negocio.

| Archivo | Para qué sirve |
| --- | --- |
| [`config.py`](meloxo_common/config.py) | `BaseServiceSettings`: `DATABASE_URL`, `JWT_SECRET`, `DISABLE_SCHEDULER`, `INTERNAL_TIMEOUT_SECONDS` y `AUTH_CACHE_SECONDS` |
| [`errors.py`](meloxo_common/errors.py) | `AppError` y el formato de error `{"error": {"code", "message", "detail"}}` |
| [`pagination.py`](meloxo_common/pagination.py) | Paginación de resultados |
| [`scheduler.py`](meloxo_common/scheduler.py) | Tareas periódicas dentro del proceso |
| [`security.py`](meloxo_common/security.py) | `encode_token` y `decode_token` (JWT). El hash de contraseñas queda en `users-playlists` |
| [`db.py`](meloxo_common/db.py) | `Base`, motor, `session_scope()`, `get_session()` y `load_models(package)` |
| [`internal.py`](meloxo_common/internal.py) | `InternalClient` para llamar a otro servicio (3 s, sin reintentos, lotes de 200 ids) y `UpstreamError` (503) |
| [`auth.py`](meloxo_common/auth.py) | `build_auth(fetch)`: `resolve_user`, `current_user` y `require_role`. Guarda rol y estado de cada usuario 30 s; si el origen cae usa el último estado guardado y, sin ninguno, responde 503 |
| [`latency.py`](meloxo_common/latency.py) | `LatencyRecorder` (tiempos por módulo y minuto en memoria), `LatencyMiddleware` e `internal_router`, que expone `POST /internal/latency/drain` para que `playback-metrics` recoja y vacíe los buckets |
| [`contracts.py`](meloxo_common/contracts.py) | Modelos de lo que viaja entre servicios |
| [`boundaries.py`](meloxo_common/boundaries.py) | Detector de imports prohibidos entre servicios y entre módulos |

## Uso

```bash
pip install -e 'services/common[dev]'
cd services/common && pytest -q
```

`find_violations(root, package, allowed)` recibe la carpeta del paquete de un servicio, su nombre y los paquetes de otros servicios que sí puede importar.
