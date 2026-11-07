# Pruebas de la semilla

[`test_seed.py`](test_seed.py) corre la [semilla](../../seed/README.md) con tamaños reducidos, Jamendo simulado y un PostgreSQL real.

`ffmpeg` solo existe en la imagen de Docker, así que aquí los tonos se reemplazan por un MP3 mínimo. La corrida real se comprueba con `docker compose exec app python -m seed all`.
