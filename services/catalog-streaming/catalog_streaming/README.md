# catalog_streaming

Paquete de Python del servicio [`catalog-streaming`](../README.md).

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`main.py`](main.py) | `create_app()`: rutas de catálogo y compositor, medición de latencia y las tareas periódicas `publicar_programadas` (30 s) y `refrescar_jamendo` (24 h) |
| [`config.py`](config.py) | `Settings`, que extiende la configuración común con `USERS_URL`, Jamendo, `MEDIA_DIR` y límites de subida |
| [`auth.py`](auth.py) | `auth`: usuario actual y roles, con el estado de `users-playlists` guardado 30 s |
| [`clients/`](clients/README.md) | Llamadas HTTP a otros servicios |
| [`modules/`](modules/README.md) | Los módulos del servicio |
