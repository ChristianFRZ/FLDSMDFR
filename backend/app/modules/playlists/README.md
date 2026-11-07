# modules/playlists

Playlists y sus pistas. Sus pruebas están en [`tests/modules/playlists/`](../../../tests/modules/playlists/README.md).

**Tablas:** `playlists` y `playlist_songs`.

**Lo que ofrece a otros módulos:** `count_inclusions`, en [`public.py`](public.py).

## Degradación elegante

Cada fila de `playlist_songs` guarda en `metadata_cache` los datos de la pista. Ese campo se escribe al agregar la pista y se actualiza al leerla, si el [catálogo](../catalog/README.md) responde.

Si el catálogo falla, leer una lista responde `200` con `degraded: true` y los datos guardados. Agregar pistas responde `503`, porque no se puede validar la canción.

Una pista oculta o borrada sigue en la lista con `available: false`, para que quien la guardó vea que ya no está disponible.
