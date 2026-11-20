# infra/tests

Pruebas de la infraestructura compartida.

- `test_db_isolation.py`: comprueba que cada servicio se conecta con su propio rol a su propia base y que los roles no pueden conectarse a las bases de los demás.

Necesitan PostgreSQL arriba (`docker compose up -d postgres`) y las claves `USERS_DB_PASSWORD`, `CATALOG_DB_PASSWORD` y `PLAYBACKS_DB_PASSWORD` en el `.env` de la raíz. Se ejecutan con el entorno virtual del repositorio (necesita `asyncpg`, `pytest` y `pytest-asyncio`):

```bash
.venv/bin/pytest infra/tests -q
```
