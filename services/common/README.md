# meloxo_common

Paquete de Python con lo que comparten los tres servicios de MELOXO. Aquí no van reglas de negocio.

| Archivo | Para qué sirve |
| --- | --- |
| [`config.py`](meloxo_common/config.py) | `BaseServiceSettings`: `DATABASE_URL`, `JWT_SECRET`, `DISABLE_SCHEDULER`, `INTERNAL_TIMEOUT_SECONDS`, `AUTH_CACHE_SECONDS` y `REDIS_URL` |
| [`errors.py`](meloxo_common/errors.py) | `AppError` y el formato de error `{"error": {"code", "message", "detail"}}` |
| [`pagination.py`](meloxo_common/pagination.py) | Paginación de resultados |
| [`scheduler.py`](meloxo_common/scheduler.py) | Tareas periódicas dentro del proceso |
| [`security.py`](meloxo_common/security.py) | `encode_token` (agrega `iat`) y `decode_token` (JWT). El hash de contraseñas queda en `users-playlists` |
| [`db.py`](meloxo_common/db.py) | `Base`, motor, `session_scope()`, `get_session()` y `load_models(package)` |
| [`internal.py`](meloxo_common/internal.py) | `InternalClient` para llamar a otro servicio (conexión 1 s, lectura 1.5 s, 2 reintentos con 0.2 y 0.4 s solo en `get` y en `post(..., idempotent=True)`, un `CircuitBreaker` por cliente, lotes de 200 ids) y `UpstreamError` (503; con el breaker abierto lleva `detail: "circuit_open"`). `reset_all_breakers()` y `RETRY_DELAYS` sirven para las pruebas |
| [`auth.py`](meloxo_common/auth.py) | `build_auth(fetch)`: `resolve_user`, `current_user` y `require_role`. Guarda rol y estado de cada usuario 30 s; si el origen cae usa el último estado guardado y, sin ninguno, responde 503 |
| [`latency.py`](meloxo_common/latency.py) | `LatencyRecorder` (tiempos por módulo y minuto en memoria), `LatencyMiddleware` e `internal_router`, que expone `POST /internal/latency/drain` para que `playback-metrics` recoja y vacíe los buckets |
| [`breaker.py`](meloxo_common/breaker.py) | `CircuitBreaker`: abre tras 5 llamadas fallidas en 30 s, pasa a medio abierto a los 15 s y deja pasar una sola llamada de prueba |
| [`revocation.py`](meloxo_common/revocation.py) | `revoke(user_id)` y `revoked_after(user_id)`: clave `revoked_after:<user_id>` en Redis con TTL de 960 s. `auth.py` rechaza el token cuyo `iat` es anterior. `auth.py` además descarta lo que la caché de estado guardó antes de la revocación, para que el token nuevo traiga el rol nuevo al instante. Si Redis falla o tarda más de 0.3 s, se ignora y manda la caché de 30 s |
| [`cache.py`](meloxo_common/cache.py) | Caché de lectura en un Redis aparte (`CACHE_REDIS_URL`, con LRU y sin persistencia). `cached(namespace, params, ttl, loader, versioned=, should_store=)` devuelve lo guardado o carga y guarda; `bump(namespace)` sube la versión que invalida lo versionado; `get_json` y `set_json` son la lectura y escritura sueltas. Nunca lanza por culpa de Redis: sin URL, con la caché caída o tras un timeout (0.2 s lectura, 0.3 s escritura) se llama al origen y se salta la caché 5 s |
| [`playback_queue.py`](meloxo_common/playback_queue.py) | El contrato de la cola de reproducciones: stream `playbacks`, `QueuedEvent`, `to_fields`/`from_fields`, `enqueue` y `ensure_group` |
| [`track_events.py`](meloxo_common/track_events.py) | El contrato de `track_published`: streams `track_published` y `track_published:dlq`, grupo `users-playlists`, `MAX_ATTEMPTS` (5), `TrackPublished`, `to_fields`/`from_fields` (lanza `ValueError` con el motivo), `enqueue`, `ensure_group` y `send_to_dlq` |
| [`redis_client.py`](meloxo_common/redis_client.py) | `get_redis()`: cliente de Redis compartido (`REDIS_URL`; vacío devuelve `None`) y `override_redis()` para las pruebas |
| [`contracts.py`](meloxo_common/contracts.py) | Modelos de lo que viaja entre servicios |
| [`boundaries.py`](meloxo_common/boundaries.py) | Detector de imports prohibidos entre servicios y entre módulos |

## Uso

```bash
pip install -e 'services/common[dev]'
cd services/common && pytest -q
```

`find_violations(root, package, allowed)` recibe la carpeta del paquete de un servicio, su nombre y los paquetes de otros servicios que sí puede importar. Si esa carpeta tiene `modules/`, cada subcarpeta de `modules/` es un módulo y lo demás (`config.py`, `clients/`, `auth.py`…) es código del servicio que cualquier módulo puede importar.
