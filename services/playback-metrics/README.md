# playback-metrics

Servicio de reproducciones y métricas de MELOXO (puerto 8003), con su propia base de datos. Reúne los módulos `playback` y `analytics` del monolito. No guarda pistas ni usuarios: pide los metadatos a `catalog-streaming` y el estado de cada sesión a `users-playlists`, por HTTP.

| Carpeta o archivo | Para qué sirve |
| --- | --- |
| [`playback_metrics/`](playback_metrics/README.md) | Código del servicio |
| [`migrations/`](migrations/README.md) | Migraciones de Alembic, numeradas desde `0001` |
| [`tests/`](tests/README.md) | Pruebas contra PostgreSQL real; los otros servicios se simulan con `respx` |
| [`alembic.ini`](alembic.ini) | Configuración de Alembic |
| [`pyproject.toml`](pyproject.toml) | Dependencias y configuración de `pytest` |

## Variables

`DATABASE_URL` y `JWT_SECRET` (compartidas, ver [`meloxo_common`](../common/README.md)), `CATALOG_URL` (por defecto `http://catalog-streaming:8002`), `USERS_URL` (por defecto `http://users-playlists:8001`), `APP_VERSION` y `MEDIA_DIR`.

## Si un servicio cae

- **Guardar una reproducción:** se guarda aunque catálogo no responda. Solo un «no existe» explícito de catálogo da `404`.
- **Métricas y reportes:** `503` si necesitan datos de un servicio que no responde.
- **Sesiones:** el estado del usuario se guarda 30 s; si users-playlists cae, se usa el último conocido.

## Pendiente (Tarea 9)

Las rutas `/internal/*`, la salud agregada de todos los servicios y la recolección de latencia. `GET /api/admin/health` sigue como en el monolito, con Jamendo en `down` si catálogo no responde. El volcado de latencia a `request_metrics` aún no existe aquí.

## Preparar el entorno y probar

Desde la raíz del repositorio, con el `.venv` y PostgreSQL arriba (puerto 5433, `POSTGRES_PASSWORD` en `.env`):

```bash
cd services/playback-metrics
../../.venv/bin/pip install -e ../common -e '.[dev]'
../../.venv/bin/pytest -q
```

Las pruebas crean la base `playbacks_test`, aplican las migraciones de este servicio y la limpian entre pruebas.
