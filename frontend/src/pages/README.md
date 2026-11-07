# Pantallas

Una pantalla por ruta. Las rutas van en inglés y el texto, en español. La lista completa de rutas está en [`App.tsx`](../App.tsx).

| Archivo | Ruta | Para qué sirve |
| --- | --- | --- |
| [`Home.tsx`](Home.tsx) | `/` | Inicio: casetes, invitaciones pendientes y lanzamientos |
| [`Search.tsx`](Search.tsx) | `/search` | Buscar en el catálogo |
| [`Library.tsx`](Library.tsx) | `/library` | Casetes, playlists y artistas que sigues |
| [`Favorites.tsx`](Favorites.tsx) | `/favorites` | Canciones favoritas |
| [`History.tsx`](History.tsx) | `/history` | Historial de lo escuchado |
| [`Stats.tsx`](Stats.tsx) | `/stats` | Estadísticas propias |
| [`Profile.tsx`](Profile.tsx) | `/profile` | Cuenta y solicitud para ser Compositor |
| [`Playlist.tsx`](Playlist.tsx) | `/playlists/:id` | Una playlist |
| [`Artist.tsx`](Artist.tsx) | `/artists/:id` | Un artista |
| [`TapeCreate.tsx`](TapeCreate.tsx) | `/tapes/new` | Crear un casete |
| [`TapeDetail.tsx`](TapeDetail.tsx) | `/tapes/:id` | Un casete: lados, dedicatorias y orden |
| [`TapeInvite.tsx`](TapeInvite.tsx) | `/invite/:token` | Abrir un enlace de invitación |
| [`Login.tsx`](Login.tsx), [`Register.tsx`](Register.tsx) | `/login`, `/register` | Iniciar sesión y registrarse, con [`AuthForm.tsx`](AuthForm.tsx) como base |
| [`NotFound.tsx`](NotFound.tsx) | Cualquier otra | Página no encontrada |

Un casete se puede reordenar arrastrando las pistas o con los botones de subir y bajar, que son la opción para teclado. Si otra persona cambió el casete, el servidor responde `409` y la pantalla se recarga.

## Subcarpetas

- [`composer/`](composer/README.md): pantallas del Compositor.
- [`admin/`](admin/README.md): pantallas del Administrador.
