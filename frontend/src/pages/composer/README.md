# Pantallas del Compositor

Pantallas para quien publica música. Están bajo `/composer` y solo las ve el rol Compositor. El permiso real lo revisa el backend.

| Archivo | Ruta | Para qué sirve |
| --- | --- | --- |
| [`Tracks.tsx`](Tracks.tsx) | `/composer` | Lista de pistas con su estado. Permite publicar, ocultar y eliminar |
| [`TrackEdit.tsx`](TrackEdit.tsx) | `/composer/tracks/:id` | Editar los datos de una pista y reprogramarla |
| [`TrackForm.tsx`](TrackForm.tsx) | `/composer/new` | Subir una pista, con validación previa y progreso |
| [`Albums.tsx`](Albums.tsx) | `/composer/albums` | Crear y ver álbumes y EP |
| [`Profile.tsx`](Profile.tsx) | `/composer/profile` | Nombre artístico, biografía, foto y enlaces |
| [`Stats.tsx`](Stats.tsx) | `/composer/stats` | Reproducciones, retención, lanzamientos y conteo de inclusiones |
| [`Request.tsx`](Request.tsx) | Dentro de `/profile` | Solicitud de un Oyente para ser Compositor |

Las inclusiones solo muestran un conteo: nunca quién agregó la pista ni en qué casete está.
