# clients

Llamadas HTTP a otros servicios, con `InternalClient` de `meloxo_common` (3 s de espera y sin reintentos). Si el otro servicio no responde, lanzan `UpstreamError` y la petición termina en `503`.

| Archivo | Para qué sirve |
| --- | --- |
| [`users.py`](users.py) | `get_auth_state` (un `404` devuelve `None`), `get_display_names` (en lotes de 200) y `record_audit`, contra `USERS_URL` |
