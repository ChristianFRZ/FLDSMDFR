# MELOXO · Rediseño según Figma y funciones nuevas

Fecha: 2026-10-31 · Estado: borrador para revisión

## 1. Intención

La interfaz actual (casetera de dos columnas, temas Lado A / Lado B) se sustituye por el
diseño de Figma "MELOXO · Tu casetera"
(`https://www.figma.com/design/cVr6xEoHkTZJyeDrngHxIL/Project-Sistemas-Distribuidos?node-id=39-2`).
El producto pasa a llamarse **MELOXO** en todo lo visible y estrena un logo propio inspirado
en la cultura mexicana y la música. Además, las funciones que el Figma muestra y la app no
tiene deben **funcionar de verdad**, con backend y base de datos, no solo verse.

Por qué: el usuario quiere que la app se parezca al modelo de Figma y que lo que se ve en
pantalla (avisos, favoritos, historial, colaboración) sea real.

## 2. Objetivos, no objetivos y anti‑objetivos

**Objetivos**

1. UI de `ui/` rehecha según el Figma: barra lateral + contenido + reproductor fijo abajo,
   tema oscuro oliva/mostaza.
2. `DESIGN.md` reescrito por completo para describir el nuevo sistema (sustituye al
   concepto de dos columnas y a los anti‑patrones que hoy prohíben esta distribución).
3. Logo **Sol‑carrete** integrado (barra lateral, pantalla de acceso, favicon).
4. Funciones nuevas con backend: historial, favoritos, seguir artistas, avisos,
   casetes colaborativos por enlace, portadas subidas, cola, aleatorio y repetir.
5. Se mantiene el concepto de casete: playlist = casete; "grabar" = agregar canción.

**No objetivos**

- Renombrar el repositorio, paquetes Python/npm, servicios de Docker, `AGENTS.md` o
  `docs/PRD.md` a MELOXO (el nombre solo cambia en lo visible; ver §4.1).
- Letras, selección de dispositivos y plan "Plus": se muestran **deshabilitados** con
  "Próximamente", sin backend.
- Tiempo real (SSE/WebSockets): los avisos se obtienen por consulta periódica.
- Tema claro: se elimina.

**Anti‑objetivos (sería un fracaso aunque "funcione")**

- Botones o secciones del Figma que parecen activos pero no hacen nada (fuera de los tres
  deshabilitados explícitos).
- Romper la regla de módulos (`tests/test_architecture.py`) para implementar las funciones
  nuevas.
- Colores escritos a mano en componentes en vez de tokens.
- Romper lo que ya funciona: streaming con Range, telemetría de reproducción, cabina de
  administrador, gestión de casetes.

## 3. Restricciones

- Arquitectura de `AGENTS.md`: monolito modular; un módulo solo usa a otro vía
  `service`/`schemas`; sin FK entre tablas de módulos distintos.
- Pila existente. **Sin dependencias nuevas** salvo necesidad concreta justificada
  (las imágenes se validan por bytes mágicos, sin Pillow).
- Migraciones nuevas en Alembic (`0005_…` en adelante), nunca editar las existentes.
- No tocar los cambios sin confirmar de `media/seed/` (son del usuario).
- Pruebas: pytest para el backend (vía Docker Compose), Vitest para el frontend;
  `ruff` y `vue-tsc` deben pasar.

## 4. Decisiones del usuario

### 4.1. Marca

- Nombre visible: **MELOXO**. Cambia en la UI, `<title>`, favicon, `DESIGN.md` y
  `README.md`. Todo lo demás conserva FLDSMDFR.
- Logo: concepto **A · Sol‑carrete**: el sol de la Piedra del Sol cuya ventana central
  es un carrete de casete (anillo con seis dientes). Minimalista, una tinta, mostaza sobre
  el fondo oscuro. Boceto aprobado: `docs/superpowers/specs/2026-10-31-meloxo-logo-boceto.svg`
  (geometría a afinar al integrarlo; ver §7.1).

### 4.2. Tema

Solo oscuro. Se eliminan `InterruptorLado.vue`, `useTheme.ts`, sus pruebas y el atributo
`data-lado`.

### 4.3. Navegación

Barra lateral con tres destinos:

| Destino | Contenido |
|---|---|
| **Página de inicio** (`/`) | Lo del Figma: saludo, más escuchadas, artistas más escuchados, Crear casete, Avisos, "Vuelve a lo que te gusta". |
| **Catálogo** (`/catalogo`) | Buscar en el catálogo, grabar canciones en un casete, seguir/dejar de seguir artistas. |
| **Streaming** (`/streaming`) | Panel técnico: cómo se transmite la canción actual y métricas del sistema. |

### 4.4. Funciones con backend

| Función | Decisión |
|---|---|
| Historial | "Vuelve a lo que te gusta" muestra las escuchas recientes **del usuario**. |
| Favoritos | Corazón en el reproductor y en las filas. "Tus favoritas" aparece en la biblioteca como un casete especial (no se puede renombrar ni borrar ni invitar a él). |
| Seguir artistas | Botón en el Catálogo. La pestaña "Artistas" de la biblioteca lista los artistas seguidos. |
| Avisos | Campana con contador + panel "Avisos" en Inicio. Tipos: **nuevo lanzamiento** (canción nueva de un artista que sigues) e **invitación a casete**. Entrega por **consulta periódica** (~30 s). |
| Casetes colaborativos | El dueño genera un **enlace de invitación**. Quien lo abre (con sesión) recibe una invitación que acepta o ignora desde Avisos. Aceptada, puede grabar, quitar y reordenar canciones. |
| Portadas | **Solo subidas**: el admin sube la portada de cada canción; el dueño, la de su casete. Sin portada se muestra un marcador. |
| Cola, aleatorio, repetir | Funcionan en el reproductor (cola visible desde el icono `list-music`). |

### 4.5. Deshabilitados

Iconos de letras (`mic-2`), dispositivos (`monitor-speaker`) y la tarjeta/etiqueta del
plan "Plus": visibles, `aria-disabled="true"`, tooltip "Próximamente".

## 5. Decisiones mías (revisables)

- La etiqueta junto a la campana muestra el rol: "Administrador" u "Oyente".
- La tarjeta lateral "Cabina de grabación · Administrador" solo aparece a administradores
  y enlaza a `/cabina` (que se restyliza, no se rediseña su funcionalidad).
- "Artistas más escuchados" se agrega a partir de las escuchas por canción; la imagen del
  artista es la portada de su canción más escuchada.
- Ctrl K (⌘K en macOS) enfoca la búsqueda superior; la búsqueda lleva al Catálogo con
  la consulta.
- Flechas atrás/adelante = `router.back()` / `router.forward()`.
- Saludo según hora local: "Buenos días" (5–12), "Buenas tardes" (12–20),
  "Buenas noches"; usa el primer nombre de `user.name`.
- Pantalla completa (`maximize-2`): abre una vista "Sonando ahora" (portada grande,
  título, controles) usando la Fullscreen API; Esc la cierra.
- Clic en un casete de la biblioteca abre su vista de detalle `/casete/:id` (lista,
  reordenar, quitar, portada, invitar, renombrar, borrar). Ver §7.4.
- En pantallas < 900 px la barra lateral se convierte en barra de navegación inferior
  encima del reproductor compacto, y la biblioteca pasa a la vista `/biblioteca`.
- Los avisos de lanzamiento se calculan **al leerlos** (pull), no se escriben al subir
  la canción. Así catalog no depende del módulo de avisos. Ver §6.4.
- Desaparece la idea de "casete activo en la casetera". **Grabar** una canción (desde
  Catálogo, historial, más escuchadas o el menú `…`) abre un selector en línea con los
  casetes donde puedes escribir (propios + colaborativos); recuerda el último elegido.
- La ventanita con carretes girando se conserva como pieza del panel **Streaming**
  (giran mientras suena), no en Inicio.
- El admin sube la portada de una canción desde la Cabina: en el formulario de subida
  (opcional) y en la fila de la tabla de canciones (reemplazar).
- "N temas" en artistas = canciones activas de ese artista en el catálogo. La imagen de
  un artista en la pestaña "Artistas" es la portada de su canción más reciente.
- El aviso de invitación muestra el nombre de quien creó el enlace ("de Marta R.");
  `social` lo obtiene con `users.service.get_user`.
- "Crear casete" crea el casete en línea y navega a su detalle.

## 6. Backend

### 6.1. Módulos

Se agrega un módulo nuevo `app/modules/social/` (seguidos + avisos + favoritos). Los
existentes crecen:

| Módulo | Tablas nuevas / cambios | Expone (service) |
|---|---|---|
| catalog | `songs.cover_path` (nullable) | `set_cover`, `get_cover_file`, `songs_by_artists_since(artists, since)`, `get_songs_by_ids` (existente) |
| playlists | `playlists.cover_path`; `playlist_members(playlist_id FK, user_id, role, joined_at)`; `playlist_invites(token PK, playlist_id FK, created_by, created_at, revoked_at)`; `playlist_invite_claims(token FK, user_id, status pending/accepted/ignored, claimed_at)` | `pending_invites_for(user_id)`, `accept_invite`, `ignore_invite` |
| playback | (sin tablas) | `recent_for_user(user_id, limit)`, `top_artists(limit)` |
| social (nuevo) | `favorites(user_id, song_id, created_at)`; `artist_follows(user_id, artist_key, artist_name, followed_at)`; `notification_reads(user_id, notification_id, read_at)` | `is_favorite`, `list_favorites`, `followed_artists`, `notifications_for(user_id)` |

Todas las referencias entre módulos son UUID/strings sin FK. `artist_key` = nombre del
artista normalizado (minúsculas, sin espacios extremos), igual que la comparación que ya
usa catalog.

### 6.2. Endpoints nuevos (prefijo `/api` existente)

| Método y ruta | Quién | Qué |
|---|---|---|
| `PUT /songs/{id}/cover` | admin | Sube portada (multipart). PNG/JPEG/WebP por bytes mágicos, ≤ 2 MB. |
| `GET /songs/{id}/cover` | autenticado | Sirve la portada (404 si no tiene). Caché `max-age` + `ETag`. |
| `PUT /playlists/{id}/cover`, `GET /playlists/{id}/cover` | dueño / miembro | Igual que arriba. |
| `POST /playlists/{id}/invites` | dueño | Crea enlace; responde `{token, url}`. Un token activo por casete; crear otro revoca el anterior. |
| `DELETE /playlists/{id}/invites` | dueño | Revoca el enlace. |
| `POST /invites/{token}/claim` | autenticado | Registra la invitación pendiente para el usuario. Idempotente. El dueño o un miembro recibe 409. |
| `POST /invites/{token}/accept`, `POST /invites/{token}/ignore` | invitado | Cambia el estado. |
| `DELETE /playlists/{id}/members/{user_id}` | dueño, o el propio miembro | Quita a un colaborador / salir del casete. |
| `GET /me/history?limit=` | autenticado | Canciones escuchadas recientemente, sin duplicados, la más reciente primero. |
| `GET /metrics/top-artists?limit=` | autenticado | Artistas más escuchados con escuchas, nº de temas y canción representativa. |
| `GET/PUT/DELETE /me/favorites[/{song_id}]` | autenticado | Listar, marcar, desmarcar (idempotentes). |
| `GET/PUT/DELETE /me/follows[/{artist}]` | autenticado | Listar, seguir y dejar de seguir artistas. |
| `GET /me/notifications` | autenticado | Avisos `{id, type, created_at, read, ...}` + `unread_count`. |
| `POST /me/notifications/read` | autenticado | Marca como leídos los ids enviados. |

`GET /playlists` devuelve los casetes propios **y** aquellos donde el usuario es miembro,
con `role: owner|collaborator`. Los permisos de escritura de canciones pasan de "dueño" a
"dueño o colaborador"; renombrar, borrar, portada e invitar siguen siendo del dueño.

### 6.3. Favoritos como casete

`GET /me/favorites` devuelve la misma forma que el detalle de un casete (lista de
canciones con disponibilidad) para que la UI lo trate igual. No es una fila de
`playlists`.

### 6.4. Avisos

`social.service.notifications_for(user)` arma la lista al vuelo:

- **Lanzamientos:** `catalog.service.songs_by_artists_since(followed, since=followed_at)`;
  id = `release:<song_id>`. Solo las de los últimos 30 días.
- **Invitaciones:** `playlists.service.pending_invites_for(user)`; id = `invite:<token>`.

El estado "leído" vive en `notification_reads`. El contador de la campana = no leídos.
Abrir el panel marca como leídos los visibles. Aceptar/Ignorar llama a los endpoints de
invitación; la invitación desaparece de la lista.

Se elige pull porque encaja con la consulta periódica y deja a catalog y playlists sin
conocer el módulo social (más fácil de separar en servicios, PRD §6).

### 6.5. Almacenamiento de portadas

En el volumen de medios existente (`settings.media_dir`), bajo
`covers/songs/<id>.<ext>` y `covers/playlists/<id>.<ext>`, para no añadir volúmenes a
Docker Compose (decisión mía). Al reemplazar se borra el archivo anterior. Las rutas no se
exponen al cliente.

## 7. Frontend

### 7.1. Sistema visual (base del nuevo `DESIGN.md`)

- Paleta muestreada del Figma (exportar valores exactos con `get_design_context` al
  implementar): fondo `#3b3932`, superficie activa `#6e6547`, mostaza `#d4ae35`/`#caa735`,
  texto mostaza atenuado `#a1893e`, bordes en mostaza con baja opacidad. Todo como tokens en
  `tokens.css`, contraste AA verificado.
- Tipografía: serif para títulos (saludo, "Vuelve a lo que te gusta", marca) y sans para
  el resto, según el Figma. Confirmar familias con `get_design_context`; si coinciden con
  Fraunces y Figtree se reutilizan. Caveat se retira si deja de usarse.
- Iconos: SVG en línea con estilo Lucide (los nombres del Figma son de Lucide). Se copian
  como componentes, sin agregar la dependencia.
- Logo: `ui/src/assets/logo-meloxo.svg` + componente `LogoMeloxo.vue`; favicon SVG y
  `favicon.ico` en `ui/public/`. Afinar la geometría del boceto (corrección óptica, versión
  pequeña) al integrarlo.

### 7.2. Estructura

`App.vue` pasa a un *layout* con `BarraLateral`, `EncabezadoSuperior` (historial,
búsqueda, rol, campana, avatar con menú "Cerrar sesión"), `<RouterView>` y
`Reproductor`. La vista de acceso (`/acceso`) no usa el layout.

Rutas: `/`, `/catalogo`, `/streaming`, `/casete/:id`, `/favoritas`, `/invitacion/:token`
(reclama y redirige a Inicio con el aviso visible), `/biblioteca` (solo móvil),
`/cabina` (admin), `/acceso`.

### 7.3. Reutilización

Se conserva la lógica de `usePlayer`, `useCasetes`, `useBusqueda`, `useSession`,
`usePlaybackTelemetry`, `useAvisos` y `api/*`, ampliándola. Los componentes visuales se
reescriben o adaptan; `BarraProgreso` mantiene el dibujo de fragmentos almacenados.
`ResumenMetricas` y `PanelTop` se reutilizan en Streaming/Inicio con el nuevo estilo.

### 7.4. Detalles de comportamiento

- Biblioteca: pestañas "Casetes" / "Artistas". Casetes = favoritas + propios +
  colaborativos (marcados con "Colaborativo"). Detalle bajo el nombre:
  "Casete · N canciones" o "Casete · Creado por ti".
- "+" de la biblioteca y "Crear casete" crean el casete en línea (sin modal).
- "Vuelve a lo que te gusta": 6 últimas; "Ver todo" abre el historial completo
  (paginado). La fila que suena se resalta con la superficie activa y el icono
  `audio-lines`. El menú `…` ofrece: grabar en casete, favorito, añadir a la cola.
- Cola: panel lateral derecho que se abre con `list-music`. Reordenar y quitar. Aleatorio y
  repetir (apagado / todo / una) se recuerdan en `localStorage`.
- Avisos: consulta cada 30 s solo con la pestaña visible (`visibilitychange`); también al
  volver a la pestaña.
- Estados vacíos, de carga y de error en cada sección, en la voz de `DESIGN.md`.

## 8. Pruebas

- Backend: pruebas pytest por endpoint nuevo (felices, permisos, validaciones de imagen,
  idempotencia, invitación revocada, colaborador sin permisos de dueño), y
  `test_architecture.py` en verde sin modificarla.
- Frontend: Vitest para los composables nuevos (cola/aleatorio/repetir, avisos con
  sondeo, favoritos) y los componentes con lógica (biblioteca, panel de avisos).
- Verificación manual con `docker compose up --build` siguiendo el flujo del Figma.

## 9. Documentación

- `DESIGN.md` reescrito (concepto, distribución, tokens, tipografía, componentes, logo,
  accesibilidad, tono, anti‑patrones nuevos).
- `README.md`: nombre MELOXO y funciones nuevas.
- `AGENTS.md` §1.1 y `docs/PRD.md` §6–7: añadir el módulo `social` y los datos nuevos
  (regla 11: la arquitectura cambia). El nombre del proyecto en estos dos archivos no
  cambia.

## 10. Riesgos

- **Tamaño:** es un cambio grande; se hará por fases (backend por función, luego UI) con
  commits pequeños.
- **Avisos al vuelo:** si un usuario sigue muchos artistas, la consulta crece; se limita a
  30 días y se indexa `songs(lower(artist), created_at)`.
- **Enlaces de invitación:** cualquiera con el enlace puede pedir unirse; el dueño puede
  revocar el enlace y quitar miembros.
- **Pérdida del tema claro:** decisión explícita del usuario.

## 11. Queda a criterio del implementador

Nombres internos de componentes y composables, el detalle de paginación, la forma exacta de
los esquemas Pydantic, el texto de microcopias siguiendo el tono de `DESIGN.md`, y el
orden de las fases del plan.
