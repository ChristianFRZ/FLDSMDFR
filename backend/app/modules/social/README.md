# modules/social

Favoritas, seguidos, casetes, invitaciones y avisos. Sus pruebas están en [`tests/modules/social/`](../../../tests/modules/social/README.md).

**Tablas:** `favorites`, `follows`, `notices_seen`, `tapes`, `tape_members`, `tape_tracks`, `tape_invites` e `invite_claims`.

**Lo que ofrece a otros módulos:** `count_tape_inclusions` y `tape_activity`, en [`public.py`](public.py).

## Avisos

Se calculan al leer, sin bus de eventos: cruzan los artistas seguidos con `published_since`, del módulo [`catalog`](../catalog/README.md). Solo generan aviso las publicaciones de Compositores, y solo las posteriores al momento de seguir al artista y a la última marca de `notices_seen`.

Si el catálogo falla, `GET /api/notices` responde `200` con `degraded: true`.

## Casetes

[`tapes.py`](tapes.py) guarda las reglas y [`tape_routes.py`](tape_routes.py) las rutas. Toda escritura que dependa de un límite bloquea primero la fila del casete con `SELECT ... FOR UPDATE`. Así, dos miembros nunca pueden ocupar a la vez la pista 12 ni la plaza 8.

- **Orden:** `tapes.version` aumenta cuando cambian las pistas. Reordenar con una versión vieja responde `409`.
- **Lados:** dependen solo de la posición. Las posiciones de la primera mitad de `TAPE_MAX_TRACKS` son el Lado A y las demás, el Lado B.
- **Pista oculta o borrada:** conserva su lugar y su dedicatoria gracias a `metadata_cache`, y aparece con `available: false`.

## Invitaciones

Solo se entra por enlace; no hay búsqueda de personas. El token se guarda como hash, por eso se muestra una sola vez, al crearlo.

Abrir el enlace crea una invitación pendiente. La lista de pendientes no puede devolver el token, así que la pantalla de Inicio acepta o descarta cada invitación con `POST /api/tapes/claims/{invite_id}/join` y `POST /api/tapes/claims/{invite_id}/dismiss`.

| Situación | Respuesta |
| --- | --- |
| Enlace revocado o caducado | `410` |
| Enlace sin usos restantes, o casete sin plazas | `409` |
| Ya eres miembro | `200` con `joined: false`, sin gastar un uso |
