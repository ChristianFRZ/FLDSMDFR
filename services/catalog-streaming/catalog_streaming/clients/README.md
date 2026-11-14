# clients

Llamadas HTTP a otros servicios, con `InternalClient` de `meloxo_common` (conexión 1 s, lectura 1.5 s, hasta 2 reintentos con espera de 0.2 y 0.4 s solo en lecturas, y un circuit breaker por destino: tras 5 llamadas fallidas en 30 s falla al instante y prueba de nuevo a los 15 s). Si el otro servicio no responde, lanzan `UpstreamError` y la petición termina en `503`.

| Archivo | Para qué sirve |
| --- | --- |
| [`users.py`](users.py) | `get_auth_state` (un `404` devuelve `None`), `get_display_names` (en lotes de 200) y `record_audit`, contra `USERS_URL` |
