# gateway_auth

Código del servicio [`gateway-auth`](../README.md).

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| [`main.py`](main.py) | `create_app()` y `app`; sin `/docs` ni `/openapi.json` |
| [`routes.py`](routes.py) | `GET /auth`, que valida el JWT y el rol para el `auth_request` de nginx, y `GET /internal/health` |
| [`auth.py`](auth.py) | `auth`, construido con `build_auth` de `meloxo_common`: el rol y el estado de la cuenta se piden a users-playlists y se guardan `AUTH_CACHE_SECONDS` (30 s) |
| [`config.py`](config.py) | `Settings` (`USERS_URL`, `APP_VERSION`); rellena `DATABASE_URL` con un valor que no se usa |
| [`clients/`](clients/README.md) | Llamada a users-playlists |
