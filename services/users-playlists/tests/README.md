# Pruebas

Corren contra un PostgreSQL real, en la base `users_playlists_test`, que se crea sola y se limpia entre pruebas. `catalog-streaming` se simula con `respx`; el hash de contraseñas es barato solo aquí.

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`conftest.py`](conftest.py) | Prepara la base, la app, los usuarios de prueba y los fixtures `fake_catalog`, `fake_redis` (fakeredis) y `relogin` (token nuevo tras una revocación). Incluye el fixture automático `fast_resilience` (sin espera entre reintentos y con los breakers cerrados) |
| [`fake_catalog.py`](fake_catalog.py) | `FakeCatalog`: las rutas `/internal/*` de catálogo en memoria; permite crear, ocultar y borrar canciones, simular caída (`down`) y lentitud (`delay`) y ver las llamadas recibidas |
| [`test_boundaries.py`](test_boundaries.py) | El servicio solo importa `meloxo_common` y los módulos pasan por `public.py` |
| [`test_catalog_client.py`](test_catalog_client.py) | Lotes de 200 ids, ids desconocidos y `UpstreamError` con catálogo caído |
| [`test_degraded.py`](test_degraded.py) | Playlist de 250 canciones, lectura degradada y pistas que catálogo ya no conoce |
| [`test_add_song.py`](test_add_song.py) | `503` con catálogo caído y sin retener la conexión de la base durante la llamada |
| [`test_internal_routes.py`](test_internal_routes.py) | Rutas `/internal/*`: estado de autenticación, auditoría, límites de ids, conteos y semilla de demo |
| [`modules/`](modules/README.md) | Pruebas de cada módulo |
