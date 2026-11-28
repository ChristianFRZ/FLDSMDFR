# catalog-streaming

Servicio de catálogo y streaming de MELOXO. Es el módulo `catalog` del monolito, separado en su propio proceso (puerto 8002) y con su propia base de datos. No tiene tabla de usuarios: pregunta el rol y el estado de cada persona a `users-playlists` y guarda la respuesta 30 s.

| Carpeta o archivo | Para qué sirve |
| --- | --- |
| [`catalog_streaming/`](catalog_streaming/README.md) | Código del servicio |
| [`migrations/`](migrations/README.md) | Migraciones de Alembic, numeradas desde `0001` |
| [`tests/`](tests/README.md) | Pruebas contra PostgreSQL real; `users-playlists` se simula con `respx` |
| [`alembic.ini`](alembic.ini) | Configuración de Alembic |
| [`pyproject.toml`](pyproject.toml) | Dependencias y configuración de `pytest` |

## Variables

`DATABASE_URL` y `JWT_SECRET` (compartidas, ver [`meloxo_common`](../common/README.md)), `USERS_URL` (por defecto `http://users-playlists:8001`), `REDIS_URL` (la cola de reproducciones y el stream `track_published`), `MEDIA_DIR`, `JAMENDO_CLIENT_ID`, `JAMENDO_API_URL`, `JAMENDO_AUDIO_MODE`, `COMPOSER_MAX_TRACKS`, `UPLOAD_MAX_MP3_MB`, `UPLOAD_MAX_COVER_MB` y `UPLOAD_MAX_MINUTES`.

## Preparar el entorno y probar

Desde la raíz del repositorio, con el `.venv` y PostgreSQL arriba (puerto 5433, `POSTGRES_PASSWORD` en `.env`):

```bash
cd services/catalog-streaming
../../.venv/bin/pip install -e ../common -e '.[dev]'
../../.venv/bin/pytest -q
```

Las pruebas crean la base `catalog_test`, aplican las migraciones de este servicio y la limpian entre pruebas.
