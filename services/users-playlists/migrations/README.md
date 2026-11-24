# Migraciones

Migraciones de Alembic del servicio. Las pruebas aplican estas mismas migraciones, así que un esquema roto hace fallar las pruebas.

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`env.py`](env.py) | Conecta Alembic con los modelos de `users_playlists.modules` |
| [`script.py.mako`](script.py.mako) | Plantilla de los archivos nuevos |
| [`versions/`](versions/README.md) | Las migraciones, en orden |
