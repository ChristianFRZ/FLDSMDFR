# services/common/tests

Pruebas del paquete `meloxo_common`: `test_auth.py`, `test_boundaries.py`, `test_errors.py`, `test_internal.py`, `test_latency.py`, `test_redis_client.py` y `test_security.py`. `conftest.py` fija las variables mínimas y desactiva Redis; las pruebas que lo necesitan usan `fakeredis`. No necesitan base de datos ni red.

```bash
cd services/common && pytest -q
```
