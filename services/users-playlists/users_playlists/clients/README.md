# clients

Llamadas HTTP a otros servicios, con `InternalClient` de `meloxo_common` (conexión 1 s, lectura 1.5 s, hasta 2 reintentos con espera de 0.2 y 0.4 s solo en lecturas, y un circuit breaker por destino: tras 5 llamadas fallidas en 30 s falla al instante y prueba de nuevo a los 15 s). Si el otro servicio no responde, lanzan `UpstreamError` y la petición termina en `503`, salvo donde el módulo prefiere degradar (playlists, casetes y avisos).

| Archivo | Para qué sirve |
| --- | --- |
| [`catalog.py`](catalog.py) | `get_songs`, `get_artists`, `upcoming_for_artists`, `published_since`, `song_is_playable`, `songs_owned_by` y `missing_song`, contra `CATALOG_URL`. Piden los ids en lotes de 200 y unen las respuestas; los ids que catálogo no conoce no aparecen en el resultado |
