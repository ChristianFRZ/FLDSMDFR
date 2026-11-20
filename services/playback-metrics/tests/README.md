# Pruebas

Corren contra un PostgreSQL real, en la base `playbacks_test`, que se crea sola y se limpia entre pruebas. `catalog-streaming` y `users-playlists` se simulan con `respx`.

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`conftest.py`](conftest.py) | Prepara la base, la app, los usuarios de prueba y los fixtures `fake_catalog` y `fake_users` |
| [`fake_catalog.py`](fake_catalog.py) | `FakeCatalog`: las rutas `/internal/*` de catálogo en memoria; permite crear y borrar pistas, simular caída (`down`) y ver las llamadas recibidas |
| [`fake_users.py`](fake_users.py) | `FakeUsers`: estado de autenticación, crecimiento, inclusiones y actividad de casetes; permite simular caída |
| [`test_boundaries.py`](test_boundaries.py) | El servicio solo importa `meloxo_common` y los módulos pasan por `public.py` |
| [`test_playback_resilience.py`](test_playback_resilience.py) | Reproducción guardada con catálogo caído, `404` si catálogo dice que no existe, `503` en métricas, lotes de inclusiones y caché de autenticación |
| [`modules/`](modules/README.md) | Pruebas de cada módulo |
