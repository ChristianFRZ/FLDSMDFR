# Pruebas

Corren contra un PostgreSQL real, en la base `catalog_test`, que se crea sola y se limpia entre pruebas. Jamendo y `users-playlists` se simulan con `respx`.

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`conftest.py`](conftest.py) | Prepara la base, la app, el fixture `fake_redis` (fakeredis) y el fixture `users_service`, que simula `auth-state`, `display-names` y `audit` de `users-playlists`. Incluye el fixture automático `fast_resilience` (sin espera entre reintentos y con los breakers cerrados) |
| [`test_playback_ingest.py`](test_playback_ingest.py) | Las escrituras de `/api/playbacks`: encolan y responden `202`, `401` sin sesión, `404` si la pista no existe, `422` con segundos inválidos, la identidad sale del token y `503` rápido con Redis caído, colgado o desactivado |
| [`media.py`](media.py) | Crea MP3, JPG y PNG mínimos |
| [`test_boundaries.py`](test_boundaries.py) | El servicio solo importa `meloxo_common` y los módulos pasan por `public.py` |
| [`test_audit_down.py`](test_audit_down.py) | Con la auditoría caída, ocultar, restaurar e importar responden `503` sin cambiar nada |
| [`test_ensure_artist_race.py`](test_ensure_artist_race.py) | Diez primeras llamadas a la vez de un mismo Compositor crean un solo artista |
| [`test_stream_ticket_users_down.py`](test_stream_ticket_users_down.py) | El ticket firmado sigue valiendo con `users-playlists` caído; una cuenta suspendida se rechaza si el estado se puede obtener |
| [`modules/`](modules/README.md) | Pruebas de cada módulo |
