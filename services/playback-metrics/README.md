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

`DATABASE_URL` y `JWT_SECRET` (compartidas, ver [`meloxo_common`](../common/README.md)), `CATALOG_URL` (por defecto `http://catalog-streaming:8002`), `USERS_URL` (por defecto `http://users-playlists:8001`), `REDIS_URL` (la cola de reproducciones), `APP_VERSION` y `MEDIA_DIR`.

## Si un servicio cae

- **Guardar una reproducción:** las escrituras entran por catálogo, que las encola en Redis. Si este servicio está caído, los eventos esperan en el stream y se aplican al volver. El consumidor no consulta catálogo, así que se guardan aunque catálogo no responda.
- **Métricas y reportes:** `503` si necesitan datos de un servicio que no responde.
- **Sesiones:** el estado del usuario se guarda 30 s; si users-playlists cae, se usa el último conocido.

## Salud y latencia

`GET /api/admin/health` devuelve `{"services": [...]}` con `users-playlists`, `catalog-streaming`, `playback-metrics`, `database`, `jamendo` y `aggregates`. Cada servicio ajeno se consulta en su `GET /internal/health` (1.5 s, todos a la vez); si falla, aparece como `{"name": ..., "status": "down"}`. Este servicio responde en proceso.

La tarea periódica `volcar_latencia` (cada 30 s, `pull_latency` en `latency_pull.py`) pide `POST /internal/latency/drain` a users-playlists y a cada réplica de catalog-streaming (resuelve el nombre de `CATALOG_URL` por DNS y llama a cada IP; si no resuelve, usa el nombre tal cual), drena su propio registro y escribe los buckets en `request_metrics`. Como el drenaje incluye el minuto abierto, un mismo (módulo, minuto) puede llegar dos veces: se suman `count` y `errors` y `p50`/`p95` se ponderan por cantidad. Si un servicio o una réplica no responde no se escribe nada de ella, sus buckets esperan en su memoria y los de las demás se guardan igual.

## Rutas internas

No las publica nginx ni llevan autenticación.

| Ruta | Respuesta |
| --- | --- |
| `GET /internal/health` | `{"name": "playback-metrics", "status": "up"\|"down", "database_ms": float, "uptime_seconds": int}` (siempre 200) |
| `POST /internal/latency/drain` | Lista de buckets `{service, module, minute, count, errors, p50_ms, p95_ms}` |
| `POST /internal/demo/playbacks` | `204` |
| `POST /internal/demo/playbacks/clear` | `204` |
| `POST /internal/demo/aggregates/rebuild` | `204` |
| `POST /internal/demo/aggregates/catch-up` | `204` (vuelve cuando los agregados están al día) |

Cuerpo de `POST /internal/demo/playbacks`:

```json
{
  "plays": [{"user_id": "<uuid>", "song_id": "<uuid>", "listened_seconds": 90, "started_at": "2026-11-10T10:00:00Z"}],
  "duplicates": 3
}
```

`duplicates` es el contador de duplicados descartados que muestra la demo. Las reproducciones quedan marcadas como demo; `clear` borra solo esas y ese contador. Después de `clear` conviene llamar a `rebuild`.

## Preparar el entorno y probar

Desde la raíz del repositorio, con el `.venv` y PostgreSQL arriba (puerto 5433, `POSTGRES_PASSWORD` en `.env`):

```bash
cd services/playback-metrics
../../.venv/bin/pip install -e ../common -e '.[dev]'
../../.venv/bin/pytest -q
```

Las pruebas crean la base `playbacks_test`, aplican las migraciones de este servicio y la limpian entre pruebas.
