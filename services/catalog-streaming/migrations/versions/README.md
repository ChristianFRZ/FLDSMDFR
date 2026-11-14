# Versiones

Los archivos de migración, en orden. No edites uno que ya se aplicó en otra máquina: crea uno nuevo.

| Migración | Qué hace |
| --- | --- |
| `0001_catalog` | Extensión `pg_trgm` y tablas `artists`, `albums` y `songs` (con `owner_user_id` único) |
| `0002_catalog_jobs` | Tabla `import_jobs` |
| `0003_catalog_publishing` | Tabla `published_events` |
| `0004_status_before_hide` | Columna `songs.status_before_hide` |
| `0005_published_relayed` | Columna `published_events.relayed_at` (nula: el evento aún no se publicó en Redis) |

Las cuatro primeras son las migraciones `0003`, `0004`, `0005` y `0011` del monolito, renumeradas desde `0001`; la `0005` es nueva de la rama `05-mensajeria`.
