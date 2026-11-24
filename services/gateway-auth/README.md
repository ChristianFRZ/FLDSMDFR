# gateway-auth

Servicio pequeño (puerto 8004) que nginx consulta con `auth_request` antes de dejar pasar una petición protegida: valida la sesión y, si hace falta, el rol. No tiene base de datos; el rol y el estado del usuario se piden a `users-playlists` (`/internal/users/{id}/auth-state`) con la caché de 30 s de `meloxo_common.auth`.

## Contrato

`GET /auth`

| Cabecera de entrada | Significado |
| --- | --- |
| `Authorization: Bearer <jwt>` | La sesión. Obligatoria |
| `X-Required-Roles: rol[,rol]` | Roles permitidos. Ausente o vacía: cualquier rol |

| Respuesta | Cuándo |
| --- | --- |
| `204` con `X-User-Id` y `X-User-Role` | Sesión válida y rol permitido |
| `401 invalid_token` | Sin cabecera, esquema distinto de `Bearer`, token inválido o vencido, ticket de streaming, `sub` mal formado, usuario inexistente o suspendido |
| `403 forbidden` | El rol del usuario no está en `X-Required-Roles` |
| `503 upstream_unavailable` | `users-playlists` no responde y no hay estado en caché |

`GET /internal/health` responde `200 {"status": "up"}` sin autenticación.

## `DATABASE_URL`

`BaseServiceSettings` exige `DATABASE_URL`, pero este servicio no usa base de datos. Por eso [`config.py`](gateway_auth/config.py) hace `os.environ.setdefault("DATABASE_URL", "unused://gateway-auth")` antes de importar `meloxo_common.config`. No hace falta definirla en compose.

## Estructura

| Archivo | Para qué sirve |
| --- | --- |
| [`gateway_auth/main.py`](gateway_auth/main.py) | `create_app()` y `app` |
| [`gateway_auth/routes.py`](gateway_auth/routes.py) | `/auth` y `/internal/health` |
| [`gateway_auth/auth.py`](gateway_auth/auth.py) | `auth`, construido con `build_auth` |
| [`gateway_auth/config.py`](gateway_auth/config.py) | `Settings` (`USERS_URL`, `APP_VERSION`) |
| [`gateway_auth/clients/users.py`](gateway_auth/clients/users.py) | Llamada a `users-playlists` |
| [`tests/`](tests/README.md) | Pruebas, sin base de datos |
| `Dockerfile` | Contexto de construcción: la raíz del repositorio |

Pruebas: `cd services/gateway-auth && pip install -e ../common -e '.[dev]' && pytest -q`.
