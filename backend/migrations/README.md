# Migraciones

Migraciones de Alembic. Las pruebas aplican estas mismas migraciones, así que un esquema roto hace fallar las pruebas.

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`env.py`](env.py) | Conecta Alembic con los modelos |
| [`script.py.mako`](script.py.mako) | Plantilla de los archivos nuevos |
| [`versions/`](versions/README.md) | Las migraciones, en orden |

Los comandos para aplicarlas y crear una nueva están en el [README del backend](../README.md#comandos).
