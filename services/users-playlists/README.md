# users-playlists

Servicio de usuarios y playlists de MELOXO (puerto 8001), con su propia base de datos. Reúne los módulos `users`, `playlists` y `social` del monolito. No tiene tabla de canciones: pregunta a `catalog-streaming` por HTTP y guarda en cada fila una copia de los metadatos para seguir mostrándola si el catálogo cae.

| Carpeta o archivo | Para qué sirve |
| --- | --- |
| [`users_playlists/`](users_playlists/README.md) | Código del servicio |
| [`migrations/`](migrations/README.md) | Migraciones de Alembic, numeradas desde `0001` |
| [`tests/`](tests/README.md) | Pruebas contra PostgreSQL real; `catalog-streaming` se simula con `respx` |
| [`alembic.ini`](alembic.ini) | Configuración de Alembic |
| [`pyproject.toml`](pyproject.toml) | Dependencias y configuración de `pytest` |

## Variables

`DATABASE_URL` y `JWT_SECRET` (compartidas, ver [`meloxo_common`](../common/README.md)), `CATALOG_URL` (por defecto `http://catalog-streaming:8002`), `REDIS_URL` (el stream `track_published`), `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `DEMO_PASSWORD`, `TAPE_MAX_TRACKS` (12) y `TAPE_MAX_MEMBERS` (8).

## Preparar el entorno y probar

Desde la raíz del repositorio, con el `.venv` y PostgreSQL arriba (puerto 5433, `POSTGRES_PASSWORD` en `.env`):

```bash
cd services/users-playlists
../../.venv/bin/pip install -e ../common -e '.[dev]'
../../.venv/bin/pytest -q
```

Las pruebas crean la base `users_playlists_test`, aplican las migraciones de este servicio y la limpian entre pruebas.
