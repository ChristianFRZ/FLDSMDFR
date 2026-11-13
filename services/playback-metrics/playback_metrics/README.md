# playback_metrics

Paquete de Python del servicio [`playback-metrics`](../README.md).

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`main.py`](main.py) | `create_app()` (puerto 8003): rutas de reproducciones y métricas, medición de latencia y la tarea periódica `actualizar_agregados` (cada 2 s). Aún no tiene rutas `/internal/*` |
| [`config.py`](config.py) | `Settings`, que extiende la configuración común con `CATALOG_URL`, `USERS_URL`, `APP_VERSION` y `MEDIA_DIR` |
| [`auth.py`](auth.py) | `current_user` y `require_role`: el rol y el estado se piden a users-playlists, con caché de 30 s |
| [`clients/`](clients/README.md) | Llamadas HTTP a catálogo y usuarios |
| [`modules/`](modules/README.md) | Los módulos del servicio |
