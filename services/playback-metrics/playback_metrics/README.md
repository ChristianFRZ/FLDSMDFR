# playback_metrics

Paquete de Python del servicio [`playback-metrics`](../README.md).

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`main.py`](main.py) | `create_app()` (puerto 8003): rutas de reproducciones y métricas, medición de latencia y las tareas periódicas `actualizar_agregados` (cada 2 s) y `volcar_latencia` (cada 30 s) |
| [`internal_routes.py`](internal_routes.py) | `/internal/health` y las rutas de la semilla de demo |
| [`health.py`](health.py) | Salud agregada de los tres servicios, base de datos, Jamendo y agregados |
| [`latency_pull.py`](latency_pull.py) | Drena la latencia de cada servicio y la guarda en `request_metrics` |
| [`config.py`](config.py) | `Settings`, que extiende la configuración común con `CATALOG_URL`, `USERS_URL`, `APP_VERSION` y `MEDIA_DIR` |
| [`auth.py`](auth.py) | `current_user` y `require_role`: el rol y el estado se piden a users-playlists, con caché de 30 s |
| [`clients/`](clients/README.md) | Llamadas HTTP a catálogo y usuarios |
| [`modules/`](modules/README.md) | Los módulos del servicio |
