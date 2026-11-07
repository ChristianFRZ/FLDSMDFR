# Backend

La aplicación FastAPI de MELOXO: un solo proceso con seis módulos y una base de datos PostgreSQL. Necesita Python 3.11 o superior; la imagen de Docker usa 3.12.

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
.venv/bin/alembic upgrade head                                      # aplica las migraciones
.venv/bin/alembic revision --autogenerate --rev-id 0012 -m "tema"   # crea una migración nueva
```

Las migraciones usan el `DATABASE_URL` de `.env`. En Docker no hay que correrlas a mano, porque el contenedor las aplica al arrancar. El número de `--rev-id` debe ser el siguiente al de la última migración de [`migrations/versions/`](migrations/versions/README.md).
