# clients

Llamadas HTTP a otros servicios, con `InternalClient` de `meloxo_common` (3 s de espera y sin reintentos). Si el otro servicio no responde, lanzan `UpstreamError` y la petición termina en `503`, salvo al guardar una reproducción, que se guarda igual.

| Archivo | Para qué sirve |
| --- | --- |
| [`catalog.py`](catalog.py) | `get_songs`, `get_artists`, `catalog_by_source`, `release_counts`, `jamendo_status`, `songs_owned_by` y `drain_latency_all`, contra `CATALOG_URL`. `drain_latency_all` resuelve el nombre por DNS (`resolve_replicas`) y drena la latencia de cada réplica; una que falla se omite. `get_songs` y `get_artists` piden en lotes de 200 y unen los diccionarios; los ids desconocidos no aparecen |
| [`users.py`](users.py) | `get_auth_state` (`404` es `None`), `user_growth`, `count_inclusions`, `count_tape_inclusions` y `tape_activity`, contra `USERS_URL` |

## Conteo de inclusiones con más de 200 pistas

Las rutas de inclusiones aceptan 200 ids como máximo. Con 200 o menos, una sola llamada da el conteo exacto de playlists (o casetes) distintos. Con más, el cliente suma los conteos de cada lote: una playlist con pistas de dos lotes cuenta dos veces. El resultado es una cota superior, nunca menor que el real. Un conteo exacto pediría una ruta que reciba los ids por cuerpo o que cuente por Compositor; queda como mejora.
