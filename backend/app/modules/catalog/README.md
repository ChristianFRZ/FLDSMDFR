# modules/catalog

Canciones, artistas, álbumes, importación, subidas y streaming. Sus pruebas están en [`tests/modules/catalog/`](../../../tests/modules/catalog/README.md).

**Tablas:** `artists`, `albums`, `songs`, `import_jobs` y `published_events`.

**Lo que ofrece a otros módulos:** `get_songs`, `get_artists`, `missing_song`, `song_is_playable`, `songs_owned_by`, `published_since`, `upcoming_for_artists`, `release_counts`, `catalog_by_source`, `jamendo_status`, `publish_due_tracks` y `refresh_metadata`, en [`public.py`](public.py).

Además de los [archivos comunes](../../README.md#qué-hay-en-un-módulo), este módulo tiene:

| Archivo | Para qué sirve |
| --- | --- |
| [`streaming.py`](streaming.py) | Entrega el audio |
| [`jamendo.py`](jamendo.py) | Cliente de la API de Jamendo |
| [`import_jobs.py`](import_jobs.py) | Importación por lotes |
| [`uploads.py`](uploads.py) | Validación y guardado de archivos |
| [`publishing.py`](publishing.py) | Publicación y moderación |
| [`composer.py`](composer.py), [`composer_routes.py`](composer_routes.py) | Reglas y rutas del Compositor |

## Streaming

`GET /api/songs/{id}/stream` admite `Range` y responde `206`. El elemento `<audio>` no puede enviar el encabezado `Authorization`, así que el navegador pide primero un ticket con `POST /api/songs/{id}/stream-ticket` y lo pasa en `?ticket=`. El ticket es un JWT de 1 hora ligado a la pista.

Las pistas de Jamendo pasan por un proxy que no escribe a disco, con un tiempo de espera de 3 s y un reintento. Con `JAMENDO_AUDIO_MODE=redirect`, la app redirige a la URL oficial en lugar de usar el proxy. La conexión a la base de datos se libera antes de empezar a transmitir.

Si la URL de audio guardada responde con un error 4xx, la app pide una nueva a Jamendo, la guarda y reintenta una vez. Así no importa si caduca el parámetro `from` de esas URL.

## Importación de Jamendo

`POST /api/admin/catalog/import` crea un trabajo y devuelve su `job_id`. El trabajo importa por páginas, es idempotente gracias a `jamendo_id` y guarda su avance, de modo que `POST /api/admin/catalog/import/{job_id}/resume` continúa donde falló. Respeta los límites de la API esperando 1, 2 y 4 s entre reintentos. El refresco diario solo actualiza los metadatos que cambiaron.

## Subidas

Solo se aceptan archivos MP3 de hasta 15 MB y portadas JPG o PNG de hasta 2 MB. El MP3 se comprueba leyendo el archivo; la portada, solo por sus primeros bytes. Cada Compositor puede tener hasta 20 pistas.

El archivo se escribe primero en `tmp/`, se valida y después se mueve con un nombre UUID. Las portadas son públicas en `/api/media/covers/...`; el audio nunca se sirve por esa ruta.

## Publicación programada

Cada 30 s, `publish_due_tracks` publica las pistas cuya fecha ya pasó. Usa `FOR UPDATE SKIP LOCKED` para que dos procesos no publiquen la misma pista.

`published_events` es el registro único de `track_published`, y ocultar o restaurar una pista no lo modifica. Al restaurar, un administrador devuelve la pista al estado que tenía, guardado en `status_before_hide`. Solo puede restaurar lo que ocultó un administrador.
