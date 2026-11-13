# Pruebas

Corren contra un PostgreSQL real, en la base `catalog_test`, que se crea sola y se limpia entre pruebas. Jamendo y `users-playlists` se simulan con `respx`.

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`conftest.py`](conftest.py) | Prepara la base, la app y el fixture `users_service`, que simula `auth-state`, `display-names` y `audit` de `users-playlists` |
| [`media.py`](media.py) | Crea MP3, JPG y PNG mínimos |
| [`test_boundaries.py`](test_boundaries.py) | El servicio solo importa `meloxo_common` y los módulos pasan por `public.py` |
| [`test_audit_down.py`](test_audit_down.py) | Con la auditoría caída, ocultar, restaurar e importar responden `503` sin cambiar nada |
| [`test_ensure_artist_race.py`](test_ensure_artist_race.py) | Diez primeras llamadas a la vez de un mismo Compositor crean un solo artista |
| [`modules/`](modules/README.md) | Pruebas de cada módulo |
