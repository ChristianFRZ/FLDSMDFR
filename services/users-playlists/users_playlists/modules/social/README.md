# modules/social

Favoritas, seguidos, casetes, invitaciones y avisos. Sus pruebas están en [`tests/modules/social/`](../../../tests/modules/social/README.md).

**Tablas:** `favorites`, `follows`, `notices_seen`, `tapes`, `tape_members`, `tape_tracks`, `tape_invites` e `invite_claims` y `release_events`.

**Lo que ofrece a otros módulos:** `count_tape_inclusions`, `tape_activity` y `run_release_consumer`, en [`public.py`](public.py).

## Avisos

Los lanzamientos se leen de `release_events`, una tabla local que llena [`release_consumer.py`](release_consumer.py) con los mensajes de `track_published`; `local_releases` en `service.py` no llama a catálogo. Solo generan aviso las publicaciones de Compositores, y solo las posteriores al momento de seguir al artista y a la última marca de `notices_seen`. Las invitaciones pendientes se suman como antes.

`GET /api/notices` responde `degraded: false` aunque catálogo esté caído. Una fila cuyo `song` ya no valida como `SongSummary` se omite con un aviso en el log. La copia no cambia si catálogo oculta o edita la pista después de publicarla (ver [decisiones](../../../../../docs/decisions/05-mensajeria.md)).

### Consumidor de `track_published`

`consume_once` lee primero lo pendiente propio, luego lo pendiente de otros consumidores (`XAUTOCLAIM` tras 30 s) y al final lo nuevo, de 50 en 50, con el grupo `users-playlists`. Guarda cada evento con `ON CONFLICT DO NOTHING` sobre `song_id` y hace `XACK` solo después del commit, así que un evento repetido no cambia nada. Un mensaje inválido va de inmediato a `track_published:dlq` con su `reason` y `original_id`, y uno que ya se entregó más de `MAX_ATTEMPTS` (5) veces también. Si falla el guardado, el mensaje queda pendiente y se reintenta tras 1 s.

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
