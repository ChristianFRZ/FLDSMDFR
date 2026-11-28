# Decisiones de 05-mensajeria

Lo que se decidió durante la construcción sin preguntarlo al equipo, con lo que cuesta si fue un error, y lo que quedó pendiente. El diseño está en [`../specs/`](../specs/README.md) y el plan en [`../plans/`](../plans/README.md).

## Avisos al equipo

- **Los avisos de lanzamientos ya no dependen de catálogo.** `GET /api/notices` lee la tabla local `release_events` de `users-playlists`. Con catálogo caído responde `degraded: false` y con los lanzamientos; antes devolvía `degraded: true` y sin ellos. `GET /api/releases` no cambia: su parte «programadas» sigue necesitando a catálogo y se sigue degradando.
- **Diferencia aceptada con las pistas ocultas.** Es el camino 1 del [diseño §6](../specs/2026-11-14-05-mensajeria-design.md#6-decidido-pistas-ocultas-o-editadas), que el equipo eligió. La copia local queda como estaba al publicarse: si un administrador oculta o edita una pista después, el aviso ya guardado sigue apareciendo con los datos de entonces. Lo pide una prueba (`test_hidden_after_publish_still_listed`). La solución completa son los eventos `track_hidden` y `track_restored` con este mismo mecanismo, y queda para una rama aparte.
- **Un stream y una tabla más.** Redis guarda `track_published` y `track_published:dlq` (recortados a unos 100 000 mensajes cada uno), y `users-playlists` tiene una tabla nueva, `release_events`. Catálogo gana la columna `published_events.relayed_at`. Hay dos migraciones nuevas: `0005_published_relayed` de catálogo y `0006_release_events` de `users-playlists`.
- **El historial se publica solo.** Las filas de `published_events` que existían antes de la rama quedan con `relayed_at` nulo y el relevo las publica, así que la tabla local se llena con lo ya publicado y nadie pierde avisos. Solo generan fila las pistas locales que siguen publicadas.
- **Quedan fuera, a propósito:** otros eventos (casete compartido, artista seguido, reproducción registrada), RabbitMQ, un panel del stream y mostrarlo en Salud.
- **Sin verificar:** las pruebas de navegador (Playwright) y las de Vitest del frontend no se corrieron en esta rama, porque no toca la interfaz.

## Decisiones

- **Tarea 1:** el evento lleva el resumen completo de la pista (`song`, el `SongSummary` como JSON) y `from_fields` rechaza un mensaje cuyo `song.id` no sea el `song_id` — así `users-playlists` no vuelve a llamar a catálogo y un mensaje a medias no entra a la tabla — costo si es error: el mensaje pesa más y cada cambio del `SongSummary` toca el contrato.
- **Tarea 2:** `relay_published_events` marca `relayed_at` dentro de la misma transacción que el `XADD`, con `SKIP LOCKED` y lotes de 100 cada 2 s — es seguro con las dos réplicas, y si Redis falla la transacción se revierte y el siguiente ciclo reintenta — costo si es error: si el proceso muere entre el `XADD` y el commit, el evento se publica dos veces (el consumidor lo tolera).
- **Tarea 2:** una pista de Jamendo, oculta o borrada al relevar solo se marca, sin publicar. Esto agrega `source == "local"` al diseño §5 — es lo que ya hace `published_since` y evita avisar de importaciones — costo si es error: ninguno visible, es lo que ya pasaba.
- **Tarea 2:** sin `REDIS_URL` el relevo lanza `RuntimeError` en vez de marcar los eventos — si marcara sin publicar, los lanzamientos se perderían — costo si es error: con Redis desactivado el planificador registra un error cada 2 s.
- **Tarea 3:** `consume_once` lee primero lo pendiente propio, luego lo pendiente de otros consumidores (`XAUTOCLAIM` tras 30 s) y al final lo nuevo; ante un fallo transitorio espera 1 s y se detiene sin leer lo siguiente — igual que el consumidor de reproducciones — costo si es error: un fallo retrasa también a los mensajes siguientes, no los pierde.
- **Tarea 3:** el mensaje va a la cola de mensajes muertos cuando `XPENDING` indica más de `MAX_ATTEMPTS` (5) entregas, es decir, cuando ya se intentó cinco veces, y un mensaje inválido va a ella de inmediato — la copia lleva `reason` y `original_id` y se acusa para que no atasque el stream — costo si es error: un mensaje que falló solo por una caída larga de la base acaba en la DLQ y hay que reinyectarlo a mano.
- **Tarea 3:** la tabla `release_events` usa `song_id` como clave primaria y el guardado es `ON CONFLICT DO NOTHING` — un evento repetido no cambia nada — costo si es error: si una pista se republicara con otros datos, la fila no se actualizaría.
- **Tarea 4:** `notices()` conserva la regla de siempre (publicadas después de seguir al artista y después de lo último visto) pero sobre `local_releases`; una fila cuyo `song` ya no valida como `SongSummary` se omite con un aviso en el log — una fila rota no debe tirar todos los avisos — costo si es error: una pista con datos malformados desaparece de los avisos sin que el usuario lo note.
- **Tarea 4:** `degraded` en los avisos queda fijo en `false` y el campo se conserva — la interfaz ya lo lee — costo si es error: ninguno.
- **Tarea 5:** el escenario 12 deja un mensaje inválido en `track_published:dlq` en cada corrida — es lo que comprueba — costo si es error: la DLQ crece con las corridas de demostración.

## Resultados de la verificación

Corrida del 2026-11-14 en la misma laptop de `02` a `04` (Intel i7-1165G7, 8 hilos, 15 GB de RAM, Linux), con el stack en `docker compose` local reconstruido con `docker compose up -d --build`. Jamendo no se tocó.

### Pruebas

| Suite | Resultado |
| --- | --- |
| `meloxo_common` | 98 pasaron (87 en `04`) |
| `users-playlists` | 195 pasaron (182) |
| `catalog-streaming` | 176 pasaron (169) |
| `playback-metrics` | 110 pasaron |
| `gateway-auth` | 14 pasaron |
| `edge` sin stack | 101 pasaron (14 más con stack, no se repitieron) |
| `demo/test_common.py` | 17 pasaron |
| `seed/tests` | 18 pasaron |
| `infra/tests` | 7 pasaron |
| `tests/` | 2 pasaron |

### Escenarios

Los escenarios 1 a 8, 10, 11 y 12 pasaron contra el stack, todos con código `0`. El 9 es la prueba de carga y no se corrió.

El escenario 12 comprueba tres cosas: con catálogo detenido los avisos ya guardados siguen completos y sin `degraded`; con `users-playlists` detenido el lanzamiento espera en el stream y el aviso aparece al volver; y un mensaje inválido va a `track_published:dlq` sin atascar a los siguientes.

### Historial tras reconstruir el stack

| Medición | Resultado |
| --- | --- |
| `published_events` en catálogo | 132 eventos, 0 con `relayed_at` nulo |
| `release_events` en `users-playlists` | 101 filas: las pistas locales publicadas, sin las de Jamendo ni las ocultas |
| Mensajes en `track_published:dlq` | 4, los que dejan las corridas del escenario 12 |

## Pendientes

- `track_hidden` y `track_restored`, para que una pista ocultada deje de aparecer en los avisos ya guardados.
- Otros eventos de dominio (casete compartido, artista seguido, reproducción registrada) sobre el mismo mecanismo.
- Una forma de revisar y reinyectar lo que cae en `track_published:dlq` (hoy solo con `redis-cli`) y su lugar en la sección Salud del admin.
- `APP_VERSION` de `playback-metrics` y `gateway-auth` sigue en `04-resiliencia-concurrencia`: esta rama no la cambió.
