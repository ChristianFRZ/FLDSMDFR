# MELOXO · Rediseño y funciones nuevas · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rehacer la UI según el Figma "MELOXO · Tu casetera" con el logo Sol‑carrete, y dar backend real a historial, favoritos, seguir artistas, avisos, casetes colaborativos por enlace, portadas, cola, aleatorio y repetir.

**Architecture:** Monolito modular FastAPI. Las funciones nuevas crecen en `catalog`, `playlists` y `playback`, y se crea el módulo `social` (favoritos, seguidos, avisos), que es el único que consume a varios módulos y lo hace siempre por su `service`. El frontend Vue 3 pasa a un layout con barra lateral + encabezado + vista + reproductor fijo, con un solo tema oscuro.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, Pydantic, PostgreSQL 16; Vue 3 + Vue Router + Vite + TypeScript, Vitest. Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-10-31-meloxo-rediseno-design.md` (leerlo antes de cada tarea). Figma: fileKey `cVr6xEoHkTZJyeDrngHxIL`, nodo `39:2`. Logo base: `docs/superpowers/specs/2026-10-31-meloxo-logo-boceto.svg`.

## Global Constraints

- Regla de módulos: un módulo solo importa `app.modules.<otro>.service` y `.schemas`; sin FK entre tablas de módulos distintos. `tests/test_architecture.py` no se modifica.
- Migraciones nuevas `0005_…` en adelante, una por tarea que toque tablas; nunca editar `0001`–`0004`. Cada modelo nuevo se registra en `app/db/models_registry.py`.
- Sin dependencias nuevas (ni Python ni npm). Iconos Lucide copiados como SVG en línea.
- Nombre visible "MELOXO" solo en UI, `<title>`, favicon, `DESIGN.md` y `README.md`. Paquetes, Docker, `AGENTS.md`, `docs/PRD.md` y variables `FLDSMDFR_*` no cambian de nombre.
- Solo tema oscuro. Todo color sale de un token `var(--…)` en `ui/src/styles/tokens.css`.
- Errores con las clases de `app/shared/errors.py` (formato `{"error": {"code","message"}}`), mensajes en español con la voz de `DESIGN.md`.
- Portadas: PNG/JPEG/WebP detectados por bytes mágicos, ≤ 2 MB (2 097 152 bytes), guardadas en `settings.media_dir / "covers" / {"songs"|"playlists"} / f"{id}.{ext}"`.
- Letras (`mic-2`), dispositivos (`monitor-speaker`) y plan "Plus": `aria-disabled="true"` y tooltip "Próximamente".
- No tocar los cambios sin confirmar de `media/seed/`.
- Pruebas backend: `docker compose --profile test run --rm tests pytest <ruta> -v`. Lint: `docker compose --profile test run --rm tests ruff check .`. Frontend: `cd ui && npm test && npm run build`.
- Commits pequeños, uno por tarea, terminados con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Enlace de invitación abierto por el dueño o un miembro existente**: 409 `already_member` y la UI muestra "Ya formas parte de este casete" y navega al casete, sin crear aviso. Prueba en Task 4 y Task 18.
2. **Portada que no es imagen (un .mp3 renombrado a .png) o de más de 2 MB**: 422 `invalid_image` / 413 `image_too_large`, la portada anterior se conserva intacta. Prueba en Task 1.
3. **Usuario sin sesión abre `/invitacion/:token`**: va a `/acceso?siguiente=/invitacion/<token>` y tras entrar se reclama la invitación. Prueba en Task 12.
4. **Canción desactivada por el admin que aparece en historial, favoritas o un aviso de lanzamiento**: se muestra como no disponible y no se reproduce; los avisos de lanzamiento de canciones inactivas no se listan. Pruebas en Task 5, 6 y 8.
5. **Colaborador expulsado que sigue con el casete abierto**: la siguiente escritura recibe 404 `playlist_not_found`, la UI avisa "Ya no tienes acceso a este casete", recarga la biblioteca y vuelve a Inicio. Prueba en Task 3 y Task 18.

---

## Fase A · Backend

### Task 1: Portadas de canciones

**Files:**
- Create: `app/shared/images.py`, `app/db/migrations/versions/0005_song_covers.py`, `tests/test_covers.py`
- Modify: `app/modules/catalog/{models,schemas,service,repository,router}.py`

**Interfaces:**
- Produces:
  - `app/shared/images.py`: `IMAGE_MAX_BYTES = 2_097_152`; `async def save_image(upload: UploadFile, dest_dir: Path, stem: str) -> str` (devuelve el nombre de archivo relativo `f"{stem}.{ext}"`, borra versiones previas `stem.*` con otra extensión; lanza `InvalidInput("…", code="invalid_image")` o `DomainError` 413 `image_too_large`); `def image_media_type(filename: str) -> str`.
  - `Song.cover_path: str | None`; `SongOut.has_cover: bool` (propiedad `Song.has_cover`).
  - `catalog.service.set_cover(session, song_id, upload) -> SongOut`; `catalog.service.get_cover_file(session, song_id) -> StreamFile`.
  - `PUT /api/songs/{id}/cover` (admin, multipart campo `file`) → `SongOut`; `GET /api/songs/{id}/cover` → imagen con `Cache-Control: private, max-age=86400` y `ETag` = `f'"{mtime_ns}-{size}"'`, 304 si coincide `If-None-Match`.
- Migración `0005_song_covers`: columna `songs.cover_path String nullable`; índice `ix_songs_lower_artist_created` sobre `(lower(artist), created_at)`.

- [ ] **Step 1: Pruebas que fallan** en `tests/test_covers.py`:
  - `test_admin_uploads_png_cover`: PUT con `b"\x89PNG\r\n\x1a\n" + b"0"*100` → 200 y `has_cover is True`; GET → 200, `content-type == "image/png"`, cuerpo idéntico.
  - `test_cover_etag_304`: segundo GET con `If-None-Match` del primero → 304.
  - `test_listener_cannot_upload_cover` → 403.
  - `test_fake_png_rejected_keeps_previous` (Review Focus 2): subir PNG válido, luego un WAV renombrado `x.png` → 422 `invalid_image`; GET sigue devolviendo el PNG original.
  - `test_oversized_cover_413`: 2 097 153 bytes con cabecera JPEG `b"\xff\xd8\xff"` → 413 `image_too_large`.
  - `test_replace_with_other_format_removes_old`: PNG y luego WebP (`b"RIFF"+b"\0"*4+b"WEBP"`) → en disco solo existe `<id>.webp`.
  - `test_cover_404_when_missing`: canción sin portada → 404 `cover_not_found`.
- [ ] **Step 2:** Correr `docker compose --profile test run --rm tests pytest tests/test_covers.py -v` → FAIL (404 de ruta).
- [ ] **Step 3:** Implementar `images.py` (lee en bloques hasta `IMAGE_MAX_BYTES+1`, escribe a archivo temporal en `dest_dir` y `os.replace` al final para conservar la anterior si falla), migración, modelo, esquemas, service y rutas. `UploadSizeGuard` solo vigila `POST /api/songs`, así que el límite de portadas lo impone `save_image`.
- [ ] **Step 4:** Correr las pruebas de cover + `tests/test_catalog_admin.py` + `tests/test_architecture.py` → PASS.
- [ ] **Step 5:** Commit `feat(catalog): portadas de canciones subidas por el admin`.

### Task 2: Portadas de casetes

**Files:**
- Create: `app/db/migrations/versions/0006_playlist_covers.py`
- Modify: `app/modules/playlists/{models,schemas,service,router}.py`; Test: `tests/test_playlist_covers.py`

**Interfaces:**
- Consumes: `save_image`, `image_media_type` (Task 1).
- Produces: `Playlist.cover_path`; `PlaylistSummary.has_cover: bool`, `PlaylistDetail.has_cover: bool`; `PUT /api/playlists/{id}/cover` (solo dueño), `GET /api/playlists/{id}/cover` (dueño o miembro tras Task 3; aquí solo dueño). Borrar el casete borra su archivo de portada.

- [ ] **Step 1:** Pruebas: `test_owner_uploads_cover` (200, `has_cover` en GET lista y detalle), `test_other_user_cover_404` (otro usuario → 404 `playlist_not_found` en PUT y GET), `test_delete_playlist_removes_cover_file`.
- [ ] **Step 2:** Correr → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Correr `tests/test_playlist_covers.py tests/test_playlists.py` → PASS.
- [ ] **Step 5:** Commit `feat(playlists): portada del casete`.

### Task 3: Miembros y permisos de casetes colaborativos

**Files:**
- Create: `app/db/migrations/versions/0007_playlist_members.py`, `tests/test_playlist_members.py`
- Modify: `app/modules/playlists/{models,repository,schemas,service,router}.py`

**Interfaces:**
- Produces:
  - Tabla `playlist_members(playlist_id FK playlists ON DELETE CASCADE, user_id Uuid, joined_at)`, PK compuesta; índice en `user_id`.
  - `PlaylistSummary.role: Literal["owner","collaborator"]`; `PlaylistDetail.role` igual y `PlaylistDetail.members: list[MemberOut]` con `MemberOut{user_id: UUID, name: str}` (nombre vía `users.service.get_user`; si falla, `"Alguien"`).
  - Service: `_get_readable(session, user_id, playlist_id, for_update=False) -> tuple[Playlist, Role]` (dueño o miembro; si no, `NotFound playlist_not_found`). `add_song`, `remove_song`, `reorder`, `get_playlist`, `GET cover` usan `_get_readable`. `rename_playlist`, `delete_playlist`, `PUT cover` siguen con `_get_owned`.
  - `list_playlists(session, user_id)` devuelve propios + donde es miembro, ordenados por `updated_at` desc.
  - `remove_member(session, actor_id, playlist_id, member_id) -> None`: el dueño quita a cualquiera; un miembro solo a sí mismo (salir); otro caso → `Forbidden`. Ruta `DELETE /api/playlists/{id}/members/{user_id}` → 204.
  - `add_member(session, playlist_id, user_id) -> None` (uso interno de Task 4).

- [ ] **Step 1:** Pruebas (insertar miembro con `playlists.service.add_member` directo):
  - `test_member_sees_playlist_in_list_as_collaborator`.
  - `test_member_can_add_remove_reorder`.
  - `test_member_cannot_rename_delete_or_upload_cover` → 404 en rename/delete (no se filtra existencia) y 404 en PUT cover.
  - `test_owner_removes_member_then_write_404` (Review Focus 5): tras DELETE miembro, `POST songs` del ex miembro → 404 `playlist_not_found`.
  - `test_member_leaves`; `test_member_cannot_remove_other_member` → 403.
  - `test_detail_lists_members_with_names`.
- [ ] **Step 2:** Correr → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Correr `tests/test_playlist_members.py tests/test_playlists.py tests/test_architecture.py` → PASS.
- [ ] **Step 5:** Commit `feat(playlists): casetes colaborativos (miembros y permisos)`.

### Task 4: Enlaces de invitación

**Files:**
- Create: `app/db/migrations/versions/0008_playlist_invites.py`, `tests/test_playlist_invites.py`
- Modify: `app/modules/playlists/{models,repository,schemas,service,router}.py`; Create router secundario `invites_router` en `app/modules/playlists/router.py` con prefijo `/api/invites`, incluido en `app/main.py`.

**Interfaces:**
- Consumes: `add_member` (Task 3).
- Produces:
  - Tablas `playlist_invites(token String(64) PK, playlist_id FK CASCADE, created_by Uuid, created_at, revoked_at nullable)` y `playlist_invite_claims(token FK CASCADE, user_id Uuid, status Enum('pending','accepted','ignored', name='invite_status'), claimed_at)`, PK `(token,user_id)`.
  - `POST /api/playlists/{id}/invites` (dueño) → 201 `InviteOut{token: str, url: str}` con `url = f"/invitacion/{token}"`, `token = secrets.token_urlsafe(24)`; revoca el token activo anterior.
  - `DELETE /api/playlists/{id}/invites` (dueño) → 204.
  - `POST /api/invites/{token}/claim` → 200 `ClaimOut{playlist_id, playlist_name, status}`; idempotente; token desconocido o revocado → 404 `invite_not_found`; dueño o miembro → 409 `already_member`.
  - `POST /api/invites/{token}/accept` → 200 `PlaylistSummary` (añade miembro); `POST /api/invites/{token}/ignore` → 204. Sin claim previo → 404 `invite_not_found`.
  - `playlists.service.pending_invites_for(session, user_id) -> list[PendingInviteOut]` con `PendingInviteOut{token, playlist_id, playlist_name, invited_by: UUID, claimed_at: datetime}` (solo `pending`, token no revocado).

- [ ] **Step 1:** Pruebas: `test_create_link_and_claim_creates_pending`, `test_claim_is_idempotent`, `test_accept_makes_member`, `test_ignore_removes_from_pending`, `test_new_link_revokes_old` (claim con el viejo → 404), `test_revoked_link_404`, `test_owner_claim_409_already_member` y `test_member_claim_409_already_member` (Review Focus 1), `test_non_owner_cannot_create_link` (404).
- [ ] **Step 2:** Correr → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Correr `tests/test_playlist_invites.py tests/test_architecture.py` → PASS.
- [ ] **Step 5:** Commit `feat(playlists): invitación a casetes por enlace`.

### Task 5: Historial y artistas más escuchados

**Files:**
- Create: `app/db/migrations/versions/0009_playback_user_index.py`, `tests/test_history.py`
- Modify: `app/modules/playback/{repository,schemas,service,router}.py`, `app/modules/catalog/{repository,service,schemas}.py`

**Interfaces:**
- Produces:
  - Índice `ix_playback_events_user_occurred (user_id, occurred_at DESC)`.
  - `catalog.service.count_active_by_artists(session, artists: Sequence[str]) -> dict[str, int]` (clave = artista normalizado `artist.strip().lower()`).
  - `catalog.service.normalize_artist(name: str) -> str` (mismo criterio en todo el proyecto).
  - `GET /api/me/history?limit=20&offset=0` (`limit` 1–50) → `HistoryPage{items: list[HistoryItemOut], total: int}`, `HistoryItemOut{song: SongOut, last_played_at: datetime, available: bool}`; una entrada por canción (la escucha más reciente), orden desc.
  - `GET /api/metrics/top-artists?limit=5` (1–20) → `list[TopArtistOut{artist: str, play_count: int, song_count: int, cover_song_id: UUID | None}]`. Se agregan los 500 `song_play_counts` mayores; `cover_song_id` = canción más escuchada del artista con portada, si no la más escuchada.

- [ ] **Step 1:** Pruebas: `test_history_dedupes_and_orders`, `test_history_is_per_user`, `test_history_marks_inactive_unavailable` (Review Focus 4: desactivar canción → `available is False`), `test_history_paginates`, `test_top_artists_aggregates_and_counts_songs`, `test_top_artists_prefers_song_with_cover`.
- [ ] **Step 2:** Correr → FAIL.
- [ ] **Step 3:** Implementar (playback llama a `catalog.service.get_songs_by_ids`; canción no encontrada se omite).
- [ ] **Step 4:** Correr `tests/test_history.py tests/test_playback.py tests/test_architecture.py` → PASS.
- [ ] **Step 5:** Commit `feat(playback): historial por usuario y artistas más escuchados`.

### Task 6: Módulo social · favoritos

**Files:**
- Create: `app/modules/social/{__init__,models,repository,schemas,service,router}.py`, `app/db/migrations/versions/0010_social.py`, `tests/test_favorites.py`
- Modify: `app/db/models_registry.py`, `app/main.py`

**Interfaces:**
- Produces:
  - Migración `0010_social` crea las tres tablas del módulo: `favorites(user_id, song_id, created_at)` PK `(user_id, song_id)`; `artist_follows(user_id, artist_key String(200), artist_name String(200), followed_at)` PK `(user_id, artist_key)`; `notification_reads(user_id, notification_id String(120), read_at)` PK `(user_id, notification_id)`.
  - Router `prefix="/api/me"`: `GET /favorites` → `FavoritesOut{songs: list[FavoriteSongOut], total_seconds: int}` con `FavoriteSongOut{song_id, title, artist, album, duration_seconds, has_cover, status: Literal["ok","unavailable"], added_at}` orden `added_at` desc; `PUT /favorites/{song_id}` → 204 (404 `song_not_found` si no existe o inactiva; idempotente); `DELETE /favorites/{song_id}` → 204 idempotente; `GET /favorites/ids` → `list[UUID]` (para pintar corazones).

- [ ] **Step 1:** Pruebas: `test_like_and_list`, `test_like_idempotent`, `test_unlike_idempotent`, `test_like_unknown_song_404`, `test_inactive_favorite_shown_unavailable` (Review Focus 4), `test_favorites_per_user`, `test_ids_endpoint`.
- [ ] **Step 2:** Correr → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Correr `tests/test_favorites.py tests/test_architecture.py` → PASS.
- [ ] **Step 5:** Commit `feat(social): favoritos`.

### Task 7: Seguir artistas

**Files:**
- Modify: `app/modules/social/{repository,schemas,service,router}.py`, `app/modules/catalog/{repository,service}.py`; Test: `tests/test_follows.py`

**Interfaces:**
- Consumes: `normalize_artist`, `count_active_by_artists` (Task 5).
- Produces:
  - `catalog.service.songs_by_artists_since(session, follows: Sequence[tuple[str, datetime]], not_before: datetime) -> list[SongOut]` — canciones activas cuyo artista normalizado coincide y `created_at > max(followed_at, not_before)`, orden `created_at` desc, máx. 50. `SongOut` gana `created_at: datetime`.
  - `catalog.service.latest_song_by_artists(session, artists) -> dict[str, SongOut]` (para imagen del artista).
  - `GET /api/me/follows` → `list[FollowOut{artist: str, followed_at, song_count: int, cover_song_id: UUID | None}]`; `PUT /api/me/follows/{artist}` → 204 (guarda `artist_name` con el formato de la canción más reciente; 404 `artist_not_found` si no hay canciones activas); `DELETE /api/me/follows/{artist}` → 204. `{artist}` llega URL‑codificado.

- [ ] **Step 1:** Pruebas: `test_follow_case_insensitive` (`"natalia LAFOURCADE "` sigue a "Natalia Lafourcade"), `test_follow_unknown_artist_404`, `test_unfollow_idempotent`, `test_follow_list_has_counts_and_cover`, `test_songs_by_artists_since_ignores_older_and_inactive`.
- [ ] **Step 2:** Correr → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Correr `tests/test_follows.py tests/test_architecture.py` → PASS.
- [ ] **Step 5:** Commit `feat(social): seguir artistas`.

### Task 8: Avisos

**Files:**
- Modify: `app/modules/social/{repository,schemas,service,router}.py`; Test: `tests/test_notifications.py`

**Interfaces:**
- Consumes: `songs_by_artists_since` (Task 7), `pending_invites_for` (Task 4), `users.service.get_user`.
- Produces:
  - `GET /api/me/notifications` → `NotificationsOut{items: list[NotificationOut], unread_count: int}`. `NotificationOut{id: str, type: Literal["release","invite"], created_at: datetime, read: bool, song: SongOut | None, invite: InviteNotice | None}`; `InviteNotice{token, playlist_id, playlist_name, inviter_name}`. Ids: `f"release:{song_id}"`, `f"invite:{token}"`. Lanzamientos de los últimos 30 días. Orden `created_at` desc (invitación usa `claimed_at`).
  - `POST /api/me/notifications/read` body `{ids: list[str]}` (máx. 100, cada uno ≤ 120 caracteres) → 204, idempotente.
  - Si catalog o playlists fallan, se omite esa fuente y se registra `logger.warning` (mismo patrón degradado de `playlists._detail`).

- [ ] **Step 1:** Pruebas: `test_release_notice_for_followed_artist` (seguir, luego admin sube canción → aparece no leída), `test_no_notice_for_song_before_follow`, `test_inactive_release_not_listed` (Review Focus 4), `test_invite_notice_after_claim_with_inviter_name`, `test_mark_read_updates_unread_count`, `test_accepted_invite_disappears`.
- [ ] **Step 2:** Correr → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Correr la suite completa `docker compose --profile test run --rm tests` y `ruff check .` → PASS.
- [ ] **Step 5:** Commit `feat(social): avisos de lanzamientos e invitaciones`.

---

## Fase B · Frontend

### Task 9: Sistema visual, logo y DESIGN.md

**Files:**
- Create: `ui/src/assets/logo-meloxo.svg`, `ui/src/components/LogoMeloxo.vue`, `ui/src/components/icons/Icono.vue`, `ui/public/favicon.svg`, `ui/public/favicon.ico`
- Modify: `ui/src/styles/tokens.css`, `ui/src/styles/base.css`, `ui/src/main.ts`, `ui/index.html`, `DESIGN.md` (reescrito)
- Delete: `ui/src/components/InterruptorLado.vue`, `ui/src/composables/useTheme.ts`, sus specs

**Interfaces:**
- Produces:
  - Tokens (nombres fijos que usan las demás tareas): `--bg`, `--surface` (tarjetas/bordes), `--surface-active` (`#6e6547` aprox.), `--accent` (mostaza `#d4ae35` aprox.), `--accent-strong`, `--on-accent`, `--ink` (texto principal mostaza claro), `--ink-muted` (`#a1893e` aprox.), `--rule`, `--danger`, `--focus`; más `--space-1..6`, `--radius-s|m|l|pill`, `--font-display`, `--font-body`, `--sidebar-width: 232px`, `--player-height: 96px`. Valores exactos desde Figma.
  - `<LogoMeloxo :size="number" :conTexto="boolean" />`.
  - `<Icono nombre="house|compass|radio|plus|disc-3|arrow-up-right|chevron-left|chevron-right|search|bell|music|arrow-right|audio-lines|ellipsis|heart|shuffle|skip-back|skip-forward|play|pause|repeat|repeat-1|mic-2|list-music|monitor-speaker|volume-2|volume-x|maximize-2|minimize-2|x|grip-vertical|link|log-out|user-plus|image" :tam="number" />` con `aria-hidden="true"`; los paths son copia de Lucide (licencia ISC, citar en comentario).

- [ ] **Step 1:** Cargar la skill `figma:figma-design-to-code` (o `/figma-design-to-code`), crear sesión Figma y llamar `get_design_context` sobre `39:2` y sus hijos `29:5`, `29:73`, `29:198`, `29:96`, `29:158`. Anotar colores exactos, familias, tamaños y radios.
- [ ] **Step 2:** Escribir `tokens.css` solo con el tema oscuro, `base.css` sin `data-lado`, fuentes en `main.ts` (retirar Caveat y su dependencia si ya no se usa; si las familias del Figma no son Fraunces/Figtree, sustituirlas por los paquetes `@fontsource` equivalentes: es el único cambio de dependencias permitido y debe justificarse en el commit).
- [ ] **Step 3:** Afinar el logo desde el boceto (corrección óptica, versión de 16 px sin dientes del carrete si se empastan), generar `favicon.svg`/`favicon.ico`, `LogoMeloxo.vue` con la palabra MELOXO en `--font-display` color `--accent` y el punto de marca.
- [ ] **Step 4:** `index.html`: `<title>MELOXO</title>`, descripción "MELOXO: tu casetera de música en streaming.", favicon; quitar `data-lado`.
- [ ] **Step 5:** Reescribir `DESIGN.md`: concepto (casetera MELOXO), distribución (barra lateral, encabezado, contenido, reproductor), tokens, tipografía, iconos, logo (construcción, tamaños mínimos, usos indebidos), componentes, estados vacíos/carga/error, accesibilidad (AA, foco visible, teclado, `prefers-reduced-motion`), tono, anti‑patrones nuevos (colores a mano, emojis como iconos, modales salvo borrar casete, botones del Figma sin función salvo los tres "Próximamente").
- [ ] **Step 6:** `cd ui && npm test && npm run build` → PASS (las specs eliminadas ya no corren).
- [ ] **Step 7:** Commit `feat(ui): sistema visual MELOXO, logo Sol-carrete y DESIGN.md`.

### Task 10: Clientes de API y tipos

**Files:**
- Modify: `ui/src/api/{types,songs,playlists,metrics}.ts`; Create: `ui/src/api/{me,invites}.ts`; Test: `ui/src/api/__tests__/me.spec.ts`

**Interfaces:**
- Produces (espejo exacto de los esquemas de Tasks 1–8): tipos `SongOut.has_cover`, `SongOut.created_at`, `PlaylistSummary.role|has_cover`, `PlaylistDetail.role|has_cover|members`, `MemberOut`, `InviteOut`, `ClaimOut`, `HistoryPage`, `HistoryItemOut`, `TopArtistOut`, `FavoritesOut`, `FavoriteSongOut`, `FollowOut`, `NotificationsOut`, `NotificationOut`, `InviteNotice`.
  - `songs.coverUrl(id: string): string`, `songs.uploadCover(id, file: File)`; `playlists.coverUrl`, `uploadCover`, `createInvite(id)`, `revokeInvite(id)`, `removeMember(id, userId)`; `invites.claim(token)`, `accept(token)`, `ignore(token)`; `me.history(limit, offset)`, `favorites()`, `favoriteIds()`, `like(songId)`, `unlike(songId)`, `follows()`, `follow(artist)`, `unfollow(artist)` (usar `encodeURIComponent`), `notifications()`, `markRead(ids)`; `metrics.topArtists(limit)`.
  - `request` acepta `FormData` como `body` sin forzar `Content-Type`.

- [ ] **Step 1:** Spec: `follow` codifica `"Calle 13/Residente"` como `/api/me/follows/Calle%2013%2FResidente`; `uploadCover` envía `FormData` con campo `file` y método `PUT`.
- [ ] **Step 2:** `npm test` → FAIL. **Step 3:** Implementar. **Step 4:** `npm test` → PASS.
- [ ] **Step 5:** Commit `feat(ui): clientes de API para las funciones nuevas`.

### Task 11: Reproductor: cola, aleatorio y repetir

**Files:**
- Modify: `ui/src/composables/usePlayer.ts`; Test: `ui/src/composables/__tests__/usePlayer.spec.ts`

**Interfaces:**
- Produces (añadidos a `usePlayer()`): `shuffle: Ref<boolean>`, `repeat: Ref<'off'|'all'|'one'>`, `toggleShuffle()`, `cycleRepeat()`, `enqueue(song: SongOut)`, `playNext(song: SongOut)`, `removeFromQueue(index: number)`, `moveInQueue(from: number, to: number)`, `upcoming: ComputedRef<SongOut[]>` (lo que sigue respetando aleatorio). Persistencia en `localStorage` claves `meloxo.shuffle` y `meloxo.repeat` con `try/catch`.
- Comportamiento: `repeat 'one'` al terminar la canción la reinicia; el botón "siguiente" sí avanza. `repeat 'all'` vuelve al inicio al acabar la cola. Aleatorio genera un orden barajado una vez (Fisher‑Yates) al activarse y al reemplazar la cola; desactivarlo regresa al orden original desde la canción actual.

- [ ] **Step 1:** Specs: `repeat one restarts on ended but next advances`, `repeat all wraps`, `shuffle with single song does not loop forever`, `shuffle covers every song exactly once`, `enqueue/playNext/remove/move`, `persists shuffle and repeat`, `localStorage throwing does not break`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat(ui): cola, aleatorio y repetir`.

### Task 12: Layout, rutas, barra lateral y encabezado

**Files:**
- Create: `ui/src/layouts/LayoutPrincipal.vue`, `ui/src/components/BarraLateral.vue`, `ui/src/components/EncabezadoSuperior.vue`, `ui/src/components/NavegacionMovil.vue`, `ui/src/components/TarjetaCabina.vue`
- Modify: `ui/src/App.vue`, `ui/src/router.ts`, `ui/src/views/AccesoView.vue`; Test: `ui/src/__tests__/router.spec.ts`, `ui/src/components/__tests__/EncabezadoSuperior.spec.ts`

**Interfaces:**
- Produces:
  - Rutas (todas con `meta.auth` salvo acceso; `/cabina` con `meta.admin`): `inicio /`, `catalogo /catalogo` (query `q`), `streaming /streaming`, `casete /casete/:id`, `favoritas /favoritas`, `historial /historial`, `biblioteca /biblioteca`, `invitacion /invitacion/:token`, `cabina /cabina`, `acceso /acceso` (query `siguiente`). Rutas con `meta.sinLayout: true`: `acceso`.
  - `LayoutPrincipal` con slots fijos: `BarraLateral` (≥ 900 px), `EncabezadoSuperior`, `<RouterView>`, `Reproductor` (Task 13, placeholder aquí), `NavegacionMovil` (< 900 px). El `<audio>` sigue en `App.vue`.
  - `BarraLateral`: logo, navegación (Inicio/Catálogo/Streaming con indicador activo), separador, `<Biblioteca />` (Task 16, placeholder aquí), `TarjetaCabina` solo si `isAdmin`.
  - `EncabezadoSuperior`: atrás/adelante (`router.back/forward`), búsqueda (Enter → `/catalogo?q=`), atajo Ctrl K/⌘K enfoca la búsqueda, etiqueta de rol "Administrador"/"Oyente", etiqueta "Plus" deshabilitada, campana (Task 14, placeholder), avatar con iniciales y menú "Cerrar sesión".
  - Guard: sin sesión → `{ name: 'acceso', query: { siguiente: to.fullPath } }`; tras login, `AccesoView` navega a `siguiente` si empieza por `/` y no por `//`.
- Se elimina `CaseteraView.vue` en esta tarea (su contenido se redistribuye en Tasks 15–18); `inicio` apunta a `InicioView.vue` placeholder.

- [ ] **Step 1:** Specs: `guard redirects to acceso with siguiente` (Review Focus 3), `acceso ignores external siguiente` (`//evil.com` → `/`), `ctrl+k focuses search`, `meta+k focuses search`, `enter navigates to catalogo with q`, `role label shows Oyente for listener`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar; restilizar `AccesoView` con `LogoMeloxo`. **Step 4:** `npm test && npm run build` → PASS.
- [ ] **Step 5:** Commit `feat(ui): layout MELOXO con barra lateral y encabezado`.

### Task 13: Barra del reproductor y vista "Sonando ahora"

**Files:**
- Create: `ui/src/components/Reproductor.vue`, `ui/src/components/PanelCola.vue`, `ui/src/components/SonandoAhora.vue`, `ui/src/components/Portada.vue`, `ui/src/composables/useFavoritos.ts`
- Modify: `ui/src/components/BarraProgreso.vue` (estilo), retirar `ControlesReproductor.vue`; Tests: `ui/src/components/__tests__/Reproductor.spec.ts`, `ui/src/composables/__tests__/useFavoritos.spec.ts`

**Interfaces:**
- Consumes: Task 10 (`me.like/unlike/favoriteIds`, `coverUrl`), Task 11.
- Produces:
  - `<Portada :src="string|null" :titulo="string" :tam="number" />`: imagen con `loading="lazy"`; sin `src` o con error de carga muestra marcador con iniciales sobre `--surface-active`.
  - `useFavoritos()` singleton: `ids: Ref<Set<string>>`, `cargar()`, `esFavorita(id): boolean`, `alternar(songId: string): Promise<void>` (optimista, revierte y avisa en error), `version: Ref<number>` (sube en cada cambio para que "Tus favoritas" recargue).
  - `Reproductor`: portada + título + artista + corazón; transporte (aleatorio, anterior, play/pausa, siguiente, repetir con icono `repeat-1` en modo una); `BarraProgreso`; herramientas: `mic-2` y `monitor-speaker` deshabilitados ("Próximamente"), `list-music` abre `PanelCola`, volumen (icono `volume-x` en 0, clic silencia/restaura), `maximize-2` abre `SonandoAhora` con `requestFullscreen` (si falla, se muestra igual como capa fija); Esc o `minimize-2` cierra.
  - Atajos: barra espaciadora play/pausa cuando el foco no está en un campo de texto.

- [ ] **Step 1:** Specs: `heart toggles optimistically and reverts on error`, `disabled tools are aria-disabled with Próximamente`, `repeat icon reflects mode`, `queue panel lists upcoming and removes`, `space toggles unless typing`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS + build.
- [ ] **Step 5:** Commit `feat(ui): reproductor MELOXO con cola, favoritos y pantalla completa`.

### Task 14: Avisos (campana y panel)

**Files:**
- Create: `ui/src/composables/useNotificaciones.ts`, `ui/src/components/Campana.vue`, `ui/src/components/PanelAvisos.vue`, `ui/src/components/TarjetaAviso.vue`; Test: `ui/src/composables/__tests__/useNotificaciones.spec.ts`, `ui/src/components/__tests__/PanelAvisos.spec.ts`

**Interfaces:**
- Consumes: `me.notifications/markRead`, `invites.accept/ignore`, `useCasetes().cargar`.
- Produces: `useNotificaciones()` singleton: `items`, `noLeidos: ComputedRef<number>`, `iniciar()` / `detener()` (sondeo cada `30_000` ms solo con `document.visibilityState === 'visible'`; consulta inmediata en `visibilitychange` a visible; se detiene al cerrar sesión), `marcarLeidos(ids)`, `aceptar(token)`, `ignorar(token)` (quitan la tarjeta, recargan casetes, avisan con `useAvisos`). Errores de red del sondeo no muestran aviso (se reintenta en el siguiente ciclo).
  - `TarjetaAviso`: lanzamiento → icono `audio-lines`, "NUEVO LANZAMIENTO", hace X, "Artista · «Título»", texto, acción "Escuchar ahora" (reproduce). Invitación → avatar con iniciales, "INVITACIÓN A CASETE", "«Casete» · de Nombre", texto, botones Aceptar / Ignorar. Tiempo relativo con `Intl.RelativeTimeFormat('es')`.
  - `Campana` muestra contador si `noLeidos > 0`; al abrirse muestra `PanelAvisos` en un popover y marca como leídos los visibles.

- [ ] **Step 1:** Specs (con `vi.useFakeTimers`): `polls every 30s while visible`, `pauses when hidden and refreshes on visible`, `network error is silent`, `accept removes card and reloads casetes`, `opening bell marks visible as read`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat(ui): avisos con consulta periódica`.

### Task 15: Página de inicio e historial

**Files:**
- Create/replace: `ui/src/views/InicioView.vue`, `ui/src/views/HistorialView.vue`, `ui/src/components/SeccionMasEscuchadas.vue`, `ui/src/components/SeccionArtistas.vue`, `ui/src/components/FilaCancion.vue`, `ui/src/components/MenuCancion.vue`, `ui/src/composables/saludo.ts`
- Retirar: `PanelTop.vue` (su lógica pasa a `SeccionMasEscuchadas`); Test: `ui/src/composables/__tests__/saludo.spec.ts`, `ui/src/components/__tests__/FilaCancion.spec.ts`

**Interfaces:**
- Consumes: `metrics.top`, `metrics.topArtists`, `me.history`, `useNotificaciones`, `SelectorGrabar` (Task 16).
- Produces:
  - `saludo(fecha: Date, nombre: string): string` → `"Buenos días, Alex."` (5:00–11:59), `"Buenas tardes, Alex."` (12:00–19:59), `"Buenas noches, Alex."`; usa la primera palabra de `nombre`; nombre vacío → sin coma ni nombre.
  - `<FilaCancion :cancion :sonando :disponible @reproducir />` con portada, título, artista, `audio-lines` si suena, duración `m:ss`, botón `ellipsis` que abre `MenuCancion` (Grabar en casete…, Añadir a favoritas/Quitar, Añadir a la cola, Reproducir a continuación). No disponible: atenuada, sin reproducir, texto "No disponible".
  - Inicio: antetítulo "TU CASETERA DIARIA", saludo, tres columnas (Canciones más escuchadas, Artistas más escuchados, Crear casete + Avisos con badge), "Vuelve a lo que te gusta" con 6 elementos en 3 columnas y "Ver todo" → `/historial` (paginado de 20, botón "Cargar más"). Estados vacíos: "Aún no escuchas nada. Empieza en el Catálogo." con enlace.

- [ ] **Step 1:** Specs: `saludo` en 4:59, 5:00, 11:59, 12:00, 19:59, 20:00 y nombre vacío; `FilaCancion unavailable does not emit reproducir`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS + build.
- [ ] **Step 5:** Commit `feat(ui): página de inicio e historial`.

### Task 16: Biblioteca y selector para grabar

**Files:**
- Create: `ui/src/components/Biblioteca.vue`, `ui/src/components/SelectorGrabar.vue`, `ui/src/composables/useSeguidos.ts`, `ui/src/views/BibliotecaView.vue`
- Modify: `ui/src/composables/useCasetes.ts` (sin "casete activo"; añade `crear(nombre): Promise<PlaylistSummary>`, `grabar(caseteId: string, songId: string): Promise<void>`, `ultimoDestino: Ref<string|null>` persistido en `localStorage` `meloxo.ultimoCasete`); retirar `EstanteCasetes.vue`, `BotonGrabar.vue`; Tests: `ui/src/composables/__tests__/useCasetes.spec.ts` (actualizar), `ui/src/components/__tests__/SelectorGrabar.spec.ts`

**Interfaces:**
- Produces:
  - `useSeguidos()` singleton: `artistas: Ref<FollowOut[]>`, `cargar()`, `sigue(artist): boolean` (comparación `trim().toLowerCase()`), `alternar(artist)`.
  - `Biblioteca`: cabecera "TUS CASETES" + botón `plus` (crea en línea: campo de nombre, Enter crea y navega a `/casete/:id`, Esc cancela); pestañas "Casetes"/"Artistas" (patrón tabs ARIA con flechas); Casetes = "Tus favoritas" (→ `/favoritas`, detalle "Casete · N canciones") + casetes (detalle "Casete · N canciones" o "Casete · Colaborativo"); Artistas = seguidos con portada y "N temas" (clic → `/catalogo?q=<artista>`).
  - `<SelectorGrabar :songId @grabado />`: popover con los casetes donde `role` es owner o collaborator, el último destino primero y marcado; opción "Nuevo casete…" en línea. Errores 409 duplicada → "Esa canción ya está en «X»."

- [ ] **Step 1:** Specs: `selector lists writable casetes with last destination first`, `duplicate shows friendly message`, `create inline navigates`, `tabs keyboard navigation`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat(ui): biblioteca con casetes y artistas seguidos`.

### Task 17: Catálogo

**Files:**
- Create: `ui/src/views/CatalogoView.vue`
- Modify/retirar: `PanelCatalogo.vue` (reutilizar `useBusqueda`; mover su spec a `CatalogoView.spec.ts`)

**Interfaces:**
- Consumes: `useBusqueda`, `FilaCancion`, `SelectorGrabar`, `useSeguidos`.
- Produces: vista con campo de búsqueda sincronizado con `?q=`, resultados paginados con `FilaCancion` y botón "Grabar"; agrupación por artista visible en resultados con botón "Seguir"/"Siguiendo" (`aria-pressed`). Estado vacío, cargando y error.

- [ ] **Step 1:** Specs: `reads q from route`, `follow button toggles aria-pressed`, `empty state message`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS.
- [ ] **Step 5:** Commit `feat(ui): vista de catálogo`.

### Task 18: Detalle de casete, favoritas e invitación

**Files:**
- Create: `ui/src/views/CaseteView.vue`, `ui/src/views/FavoritasView.vue`, `ui/src/views/InvitacionView.vue`, `ui/src/components/CompartirCasete.vue`
- Modify/retirar: `ListaCasete.vue`, `CaseteActivo.vue` (reutilizar la lógica de reordenar/quitar en `CaseteView`); Tests: `ui/src/views/__tests__/CaseteView.spec.ts`, `ui/src/views/__tests__/InvitacionView.spec.ts`

**Interfaces:**
- Produces:
  - `CaseteView`: portada (dueño puede cambiarla con input de archivo `accept="image/png,image/jpeg,image/webp"`), nombre (dueño renombra en línea), "Reproducir todo", lista reordenable (arrastrar + botones de teclado), quitar, miembros, `CompartirCasete` (dueño: generar/copiar enlace absoluto `location.origin + url`, revocar; quitar miembros), "Salir del casete" (colaborador), "Borrar casete" con confirmación (dueño). Ante 404 `playlist_not_found` en cualquier acción: aviso "Ya no tienes acceso a este casete.", recarga casetes y navega a Inicio (Review Focus 5).
  - `FavoritasView`: misma presentación sin edición de nombre/portada/compartir; recarga cuando cambia `useFavoritos().version`.
  - `InvitacionView`: llama `invites.claim(token)`; éxito → navega a Inicio y abre avisos; 409 `already_member` → aviso "Ya formas parte de este casete." y navega a `/casete/:id` (Review Focus 1); 404 → "Este enlace ya no es válido." y navega a Inicio.

- [ ] **Step 1:** Specs: `404 on write shows lost access and goes home`, `invitation already_member navigates to casete`, `invalid invitation shows message`, `copy link uses absolute url`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS + build.
- [ ] **Step 5:** Commit `feat(ui): detalle de casete, favoritas e invitaciones`.

### Task 19: Panel Streaming

**Files:**
- Create: `ui/src/views/StreamingView.vue`, `ui/src/components/VentanaCarretes.vue`
- Modify/retirar: `ResumenMetricas.vue` (restilizar y reutilizar); Test: `ui/src/components/__tests__/VentanaCarretes.spec.ts`

**Interfaces:**
- Consumes: `usePlayer` (`current`, `buffered`, `duration`, `currentTime`, `isPlaying`), `SongOut.size_bytes: int` y `SongOut.mime_type: str` (se añaden en esta tarea al esquema backend y a `types.ts`, con la prueba `test_song_out_exposes_size_and_mime` en `tests/test_catalog_stream.py`), `metrics.summary`.
- Produces: `VentanaCarretes` (carretes giran con `isPlaying`, quietos con `prefers-reduced-motion`); tarjetas: formato (`mime_type`), tamaño, bitrate estimado `size_bytes*8/duration` kbps, porcentaje descargado (suma de `buffered`), número de fragmentos, barra con los fragmentos; explicación breve de HTTP Range; `ResumenMetricas`. Sin canción: estado vacío "Pon una canción para ver cómo llega a tu casetera."

- [ ] **Step 1:** Spec: `reels stop when paused and with reduced motion`; función pura `bitrateKbps(size, seconds)` con `(0, x) → null`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS + build.
- [ ] **Step 5:** Commit `feat(ui): panel técnico de streaming`.

### Task 20: Cabina con portadas

**Files:**
- Modify: `ui/src/views/CabinaView.vue`, `ui/src/components/{FormularioSubida,TablaCanciones,GestionUsuarios}.vue`; Test: `ui/src/components/__tests__/FormularioSubida.spec.ts`

**Interfaces:**
- Consumes: `songs.uploadCover`, `Portada`.
- Produces: restyle MELOXO; `FormularioSubida` con campo opcional "Portada" (tras crear la canción sube la portada; si la portada falla, la canción queda creada y se avisa "La canción se subió, pero la portada no. Inténtalo desde la tabla."); `TablaCanciones` muestra miniatura y acción "Cambiar portada".

- [ ] **Step 1:** Specs: `uploads cover after song`, `cover failure keeps song and warns`.
- [ ] **Step 2:** FAIL. **Step 3:** Implementar. **Step 4:** PASS + build.
- [ ] **Step 5:** Commit `feat(ui): cabina con portadas`.

### Task 21: Documentación, limpieza y verificación final

**Files:**
- Modify: `README.md`, `AGENTS.md` (§1.1: módulos `users, catalog, playlists, playback, social`), `docs/PRD.md` (§6–7: módulo `social`, tablas nuevas y su dueño)
- Delete: componentes y specs sin referencias (comprobar con `grep -r "<Nombre>" ui/src`)

- [ ] **Step 1:** `grep -rn "data-lado\|useTheme\|InterruptorLado\|CaseteraView\|Lado A" ui/src DESIGN.md README.md` → sin resultados.
- [ ] **Step 2:** Actualizar docs; README con nombre MELOXO, funciones nuevas y capturas opcionales.
- [ ] **Step 3:** Ejecutar y anotar resultados reales: `docker compose --profile test run --rm tests`, `docker compose --profile test run --rm tests ruff check .`, `cd ui && npm test && npm run build`.
- [ ] **Step 4:** `docker compose up --build` y recorrer: registro, Inicio, Catálogo (seguir, grabar), favorito, cola/aleatorio/repetir, admin sube canción con portada de un artista seguido → aviso en ≤ 30 s, invitación por enlace entre dos usuarios (aceptar e ignorar), Streaming, pantalla completa, móvil 375 px. Comparar Inicio con la captura del Figma.
- [ ] **Step 5:** Commit `docs: MELOXO en README, AGENTS y PRD`.
