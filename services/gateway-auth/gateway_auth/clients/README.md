# clients

Llamadas HTTP a otros servicios, con `InternalClient` de `meloxo_common`.

| Archivo | Para qué sirve |
| --- | --- |
| [`users.py`](users.py) | `get_auth_state`: pide `/internal/users/{id}/auth-state` a `USERS_URL`. Un `404` es `None` (el usuario no existe); si users-playlists no responde, el error sube y `gateway-auth` contesta `503` salvo que haya estado en caché |
