# Pruebas de la semilla

[`test_seed.py`](test_seed.py) corre la [semilla](../README.md) con tamaños reducidos y los tres servicios simulados con `respx`: comprueba el orden de las llamadas, los cuerpos, el borrado, la contraseña, el informe y los mensajes de error. No necesita Docker ni base de datos.

`ffmpeg` solo existe en la imagen de Docker, así que los tonos se reemplazan por un MP3 mínimo en una carpeta temporal.

Corren desde la raíz del repositorio con el entorno virtual del proyecto:

```bash
.venv/bin/pytest seed/tests -q
```

[`pytest.ini`](pytest.ini) añade la raíz al `PYTHONPATH` y activa `asyncio_mode = auto`. La corrida real contra la pila se hace con `docker compose run --rm seed python -m seed all`.
