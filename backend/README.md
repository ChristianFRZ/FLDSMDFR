# Backend

El backend FastAPI de MELOXO corre en tres procesos: usuarios/playlists/social, catálogo/streaming y reproducción/analítica. Cada proceso tiene su propia base PostgreSQL. Necesita Python 3.11 o superior; la imagen de Docker usa 3.12.

| Carpeta | Contenido |
| --- | --- |
| [`app/`](app/README.md) | Código de la aplicación |
| [`migrations/`](migrations/README.md) | Migraciones de Alembic |
| [`seed/`](seed/README.md) | Datos de demo, que se cargan con un comando aparte |
| [`tests/`](tests/README.md) | Pruebas contra un PostgreSQL real |

Las dependencias están en [`pyproject.toml`](pyproject.toml) y la configuración de Alembic en [`alembic.ini`](alembic.ini).

## Preparar el entorno

Solo hace falta la primera vez. Corre esto dentro de `backend/`:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

También necesitas el archivo `.env` en la raíz del repositorio (se crea a partir de [`.env.example`](../.env.example)) y PostgreSQL en marcha. Desde la raíz, este comando lo levanta en el puerto 5433:

```bash
docker compose up -d postgres
```

## Comandos

Todos se corren dentro de `backend/`:

```bash
.venv/bin/pytest                                                    # todas las pruebas
.venv/bin/pytest tests/modules/social                               # las pruebas de un módulo
.venv/bin/alembic upgrade head                                      # aplica las migraciones del monolito local
.venv/bin/alembic revision --autogenerate --rev-id 0013 -m "tema"   # crea una migración nueva
```

En Compose, `migrate` aplica la cadena de cada dominio antes del arranque. El comando local de Alembic anterior usa la cadena del monolito para desarrollo y pruebas. [Migración de datos y propietarios](../docs/02-separacion.md).
