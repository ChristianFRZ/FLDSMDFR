# services/common/tests

Pruebas del paquete `meloxo_common`: `test_auth.py`, `test_boundaries.py`, `test_breaker.py`, `test_errors.py`, `test_internal.py` (timeouts, reintentos y breaker), `test_latency.py`, `test_playback_queue.py`, `test_redis_client.py`, `test_revocation.py`, `test_security.py` y `test_track_events.py`. `conftest.py` fija las variables mínimas y desactiva Redis; las pruebas que lo necesitan usan `fakeredis`. No necesitan base de datos ni red.

```bash
cd services/common && pytest -q
```
