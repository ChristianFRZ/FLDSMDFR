# Pruebas

No necesitan base de datos: `users-playlists` se simula con `respx` en `http://users.test`.

| Archivo | Para qué sirve |
| --- | --- |
| [`conftest.py`](conftest.py) | Fija `JWT_SECRET` y `USERS_URL` (no `DATABASE_URL`), limpia la caché y da `client` y `make_token`. Incluye el fixture automático `fast_resilience` (sin espera entre reintentos y con los breakers cerrados) |
| [`fake_users.py`](fake_users.py) | `FakeUsers`: solo la ruta de estado de autenticación; permite simular caída (`down`) |
| [`test_auth_route.py`](test_auth_route.py) | `/auth`: 204, 401, 403, 503 y `/internal/health` |
| [`test_boundaries.py`](test_boundaries.py) | El servicio solo importa `meloxo_common` |
