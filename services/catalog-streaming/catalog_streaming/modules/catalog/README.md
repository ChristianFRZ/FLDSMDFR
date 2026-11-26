# modules/catalog

Canciones, artistas, álbumes, importación, subidas y streaming. Sus pruebas están en [`tests/modules/catalog/`](../../../tests/modules/catalog/README.md).

**Tablas:** `artists`, `albums`, `songs`, `import_jobs` y `published_events`.

**Lo que ofrece a otros módulos (la interfaz HTTP llega en la tarea siguiente):** `get_songs`, `get_artists`, `missing_song`, `song_is_playable`, `songs_owned_by`, `published_since`, `upcoming_for_artists`, `release_counts`, `catalog_by_source`, `jamendo_status`, `publish_due_tracks`, `relay_published_events` y `refresh_metadata`, en [`public.py`](public.py).

Estos son los archivos del módulo:

| Archivo | Para qué sirve |
| --- | --- |
| `models.py`, `schemas.py`, `service.py`, `routes.py` | Tablas, esquemas, reglas y rutas de `/api/songs`, `/api/artists` y `/api/admin` |
| [`streaming.py`](streaming.py) | Entrega el audio |
| [`jamendo.py`](jamendo.py) | Cliente de la API de Jamendo |
| [`import_jobs.py`](import_jobs.py) | Importación por lotes |
| [`uploads.py`](uploads.py) | Validación y guardado de archivos |
| [`publishing.py`](publishing.py) | Publicación y moderación |
| [`outbox.py`](outbox.py) | `relay_published_events`: publica en Redis los `track_published` pendientes |
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

## Relevo de `track_published`

Cada 2 s, `relay_published_events` toma hasta 100 filas de `published_events` con `relayed_at` nulo (`FOR UPDATE SKIP LOCKED`, así que las dos réplicas no se pisan), publica cada una con `XADD` en el stream `track_published` y marca `relayed_at` en la misma transacción. Si Redis falla, la transacción se revierte y el siguiente ciclo reintenta; si el proceso cae entre el `XADD` y el commit, el evento sale dos veces y el consumidor lo tolera. La pista de Jamendo, oculta o borrada solo se marca, sin publicar. Las filas anteriores a la rama también salen por este camino. El contrato del mensaje está en [`track_events.py`](../../../../common/meloxo_common/track_events.py).

## Auditoría y usuarios

Este módulo no tiene tabla de usuarios. El rol y el estado vienen de `users-playlists` con la caché de 30 s de `meloxo_common.auth`, y los nombres de los Compositores se piden con [`clients/users.py`](../../clients/users.py). Ocultar, restaurar e importar registran la auditoría **antes** de confirmar: si `users-playlists` no responde, la acción termina en `503` y la pista conserva su estado (en la importación no queda ningún trabajo).

Cada Compositor tiene un solo artista: `ensure_artist` inserta con `ON CONFLICT DO NOTHING` sobre `owner_user_id` único y luego lo lee, así que dos primeras peticiones a la vez no fallan.
