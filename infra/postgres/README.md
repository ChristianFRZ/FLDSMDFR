# infra/postgres

Inicialización de PostgreSQL para los tres servicios.

`init.sh` lo ejecuta la imagen oficial de `postgres` una sola vez, cuando el volumen `pgdata` está vacío (se monta en `/docker-entrypoint-initdb.d`). Crea:

| Base | Rol (mismo nombre) | Servicio | Clave |
|---|---|---|---|
| `users_playlists` | `users_playlists` | users-playlists | `USERS_DB_PASSWORD` |
| `catalog` | `catalog` | catalog-streaming | `CATALOG_DB_PASSWORD` |
| `playbacks` | `playbacks` | playback-metrics | `PLAYBACKS_DB_PASSWORD` |

Cada rol es dueño de su base y de su esquema `public` (así alembic puede crear tablas). A `PUBLIC` se le quita `CONNECT`, que solo se concede al dueño: ningún servicio puede abrir la base de otro. En `catalog` se crea la extensión `pg_trgm`.

La base `meloxo` y su superusuario (`POSTGRES_PASSWORD`) siguen existiendo; las pruebas de cada servicio crean ahí sus bases `<servicio>_test`.

Si cambias `init.sh` o las claves con un volumen ya creado no se vuelve a ejecutar: hay que recrearlo con `docker compose down -v` (borra los datos).

Las pruebas de aislamiento están en [`../tests`](../tests/README.md).
