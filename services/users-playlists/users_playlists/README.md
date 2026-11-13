# users_playlists

Paquete de Python del servicio [`users-playlists`](../README.md).

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`main.py`](main.py) | `create_app()`: rutas de usuarios, playlists, favoritas, seguidos y casetes, y medición de latencia. En el arranque crea el primer administrador si `ADMIN_EMAIL` y `ADMIN_PASSWORD` están definidos. No tiene tareas periódicas |
| [`config.py`](config.py) | `Settings`, que extiende la configuración común con `CATALOG_URL`, los datos del primer administrador, `DEMO_PASSWORD` y los límites de casetes |
| [`auth.py`](auth.py) | `current_user` y `require_role`: el rol y el estado se leen de la base propia en cada petición, sin caché ni red |
| [`security.py`](security.py) | Hash argon2 de contraseñas, token de acceso y tokens opacos |
| [`clients/`](clients/README.md) | Llamadas HTTP a otros servicios |
| [`modules/`](modules/README.md) | Los módulos del servicio |
