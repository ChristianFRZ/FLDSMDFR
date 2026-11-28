# Diseño · Rama `05-mensajeria`

Quinta rama de MELOXO. Complementa al PRD (`docs/prd.md`) y al [diseño de `04-resiliencia-concurrencia`](2026-11-14-04-resiliencia-concurrencia-design.md). Aquí se registra cómo el evento `track_published` viaja de catálogo a `users-playlists` sin que los avisos dependan de que catálogo responda.

Las decisiones marcadas **(equipo)** las tomó el usuario durante el diseño. Las marcadas **(constructor)** las propuso quien diseña y pueden corregirse.

## 1. Intención

Hoy los avisos de lanzamientos de `users-playlists` se calculan al leer: `notices()` le pide a catálogo, por HTTP, las pistas publicadas de los artistas seguidos. Si catálogo cae o su breaker está abierto, el usuario recibe los avisos sin lanzamientos y `degraded: true`.

Con esta rama, catálogo publica `track_published` en un stream de Redis cuando una pista se publica, y `users-playlists` lo guarda en su propia base. Los avisos de lanzamientos se leen de esa tabla local: catálogo caído deja de afectarlos, y un evento publicado mientras `users-playlists` estaba caído espera en el stream hasta que vuelva.

## 2. Objetivos

1. **Outbox en catálogo.** `published_events` gana una marca `relayed_at`. Un relevo periódico, con `SKIP LOCKED`, lee los eventos sin relevar, los publica con `XADD` a `track_published` y solo entonces marca `relayed_at`. Entrega al menos una vez.
2. **Consumidor en `users-playlists`.** Un grupo de consumidores sobre ese stream guarda cada evento en una tabla propia y hace `XACK` solo después del commit. Lo pendiente de un consumidor caído se reclama con `XAUTOCLAIM`.
3. **Consumo idempotente.** La clave primaria de la tabla local es `song_id`: un evento repetido no cambia nada.
4. **Mensajes muertos.** Un mensaje con formato inválido, o que falla `MAX_ATTEMPTS` veces, se copia a `track_published:dlq` con el motivo y se acusa. El contador de intentos sale de `XPENDING`.
5. **Avisos desde la tabla local.** `notices()` deja de llamar a catálogo para los lanzamientos. Sigue calculando lo mismo: pistas de artistas seguidos publicadas después de seguirlos y después de lo último visto.
6. **Verificación.** Un escenario nuevo en `demo/` (catálogo detenido: los avisos siguen completos) y pruebas de relevo, consumidor, idempotencia y DLQ.
7. Un `README.md` por carpeta nueva y actualización de los existentes, del README raíz, de `docs/ramas.md` y de `CHANGELOG.md`.

## 3. No objetivos y antiobjetivos

**No objetivos**

- Otros eventos (casete compartido, artista seguido, reproducción registrada): el siguiente paso, con este mismo mecanismo **(equipo)**.
- `GET /api/releases`: su parte «programadas» sigue necesitando a catálogo, así que no se toca.
- RabbitMQ y su panel **(equipo)**: se usa Redis Streams.
- Un evento `track_hidden` y la reconciliación de pistas ocultadas o editadas después de publicarse (ver §6).
- Panel del stream, o mostrarlo en Salud del admin.

**Antiobjetivos: si pasa esto, la rama falló aunque funcione**

- Que un lanzamiento se pierda por reiniciar Redis, catálogo o `users-playlists`.
- Que un lanzamiento aparezca dos veces en los avisos.
- Que un usuario deje de ver avisos que veía antes de la rama (las pistas ya publicadas deben llegar a la tabla local).
- Que publicar una pista falle o se retrase porque Redis esté caído: el relevo reintenta, la publicación no.
- Que cambie el comportamiento visible de los avisos sin estar en este documento.

## 4. Decisiones del equipo

| Tema | Decisión |
|---|---|
| Broker | **Redis Streams.** Ya corre en el stack desde la 04 y el PRD lo aprobó. |
| Alcance | **Solo `track_published`.** |
| Pistas ocultas o editadas después de publicarse | **Opción 1 (§6):** se acepta la diferencia y se documenta en las decisiones de la rama. `track_hidden` queda para una rama aparte. |

## 5. Decisiones del constructor

| Tema | Decisión | Razón |
|---|---|---|
| Outbox | Columna `relayed_at` (nullable) en `published_events`, con migración. No hay tabla nueva. | `published_events` ya se escribe en la misma transacción que el cambio de estado y ya es única por pista. |
| Relevo | Tarea periódica de `meloxo_common.scheduler`, cada 2 s, lotes de 100, `FOR UPDATE SKIP LOCKED`. Marca `relayed_at` después del `XADD`. | Seguro con las dos réplicas. Si el proceso muere entre el `XADD` y el commit, el evento se publica otra vez, y el consumidor es idempotente. |
| Eventos anteriores a la rama | No hay migración de datos: salen por el mismo relevo, porque su `relayed_at` es nulo. | Evita un camino especial y llena la tabla local con el historial. |
| Carga del evento | `song_id`, `artist_id`, `published_at` y un resumen de la pista (el mismo `SongSummary` que hoy devuelve `published_since`), armado al relevar. | Los avisos devuelven la pista completa; sin el resumen, `users-playlists` tendría que volver a llamar a catálogo. |
| Pista ya no publicada al relevar | Si al relevar la pista está oculta o borrada, se marca `relayed_at` sin publicar. | Evita avisar de algo que ya no se muestra. |
| Streams | `track_published` y `track_published:dlq`, con `MAXLEN ~ 100000`. Grupo `users-playlists`. Contrato en `meloxo_common`, como `playback_queue.py`. | Mismo patrón que la cola de reproducciones. |
| Tabla local | `release_events` en `users_playlists` (`song_id` PK, `artist_id`, `published_at`, `song` en `jsonb`), con índice en `(artist_id, published_at)`. | Consulta por artistas seguidos y fecha. |
| Reintentos | `MAX_ATTEMPTS = 5`, espera de 1 s entre vueltas, igual que el consumidor de reproducciones. | Cubre una caída breve de la base sin atascar el stream. |
| Redis caído | El relevo falla y reintenta; `notices()` solo lee Postgres. | Redis no está en el camino de lectura. |

## 6. Decidido: pistas ocultas o editadas

El equipo eligió el camino 1. Se conservan los tres caminos como registro.

**Pistas ocultas o editadas después de publicarse.** Hoy `published_since` consulta el estado actual de catálogo: una pista que un administrador oculta deja de aparecer en los avisos. Con la tabla local, la copia queda como estaba al publicarse, así que una pista ocultada seguiría apareciendo hasta que se cambie. Hay tres caminos:

1. **Aceptar la diferencia y documentarla.** Es lo más simple, pero es un cambio visible.
2. **Agregar `track_hidden` y `track_restored`** con el mismo mecanismo. Es lo correcto, pero amplía el alcance que fijaste.
3. **Filtrar al leer:** `users-playlists` consulta a catálogo solo para saber cuáles de las pistas locales siguen visibles y, si catálogo no responde, muestra la copia local. Los avisos nunca quedan vacíos, pero siguen dependiendo de catálogo en el camino feliz.

Elegido: el 1, con la diferencia anotada en `docs/decisions/05-mensajeria.md`. El 2 queda como trabajo futuro.

## 7. Lo que queda al constructor

Nombres de columnas y de índices, el formato exacto de los campos del mensaje, el texto de los avisos de log y cuántos mensajes lee cada vuelta del consumidor.
