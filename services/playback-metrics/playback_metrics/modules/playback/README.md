# modules/playback

Eventos de reproducción, contadores e historial. Sus pruebas están en [`tests/modules/playback/`](../../../tests/modules/playback/README.md).

**Tablas:** `playback_events` y `playback_counters`.

**Lo que ofrece a otros módulos:** `events_since`, `duplicates_discarded` y `retention_for_songs`, en [`public.py`](public.py).

## Idempotencia

Las escrituras ya no llegan por HTTP a este servicio: entran por `catalog-streaming`, que las encola, y las aplica el consumidor (más abajo). `service.apply_event` inserta con `ON CONFLICT (playback_id) DO NOTHING`; si no insertó nada, suma 1 a `duplicates_discarded` en la misma transacción. Un `progress` solo aumenta `listened_seconds`: no cuenta como reproducción ni como duplicado. La gráfica de retención depende de ese dato.

El módulo [`analytics`](../analytics/README.md) lee estos eventos con `events_since`, nunca directamente de las tablas.

## Catálogo caído

El historial (`GET /api/playbacks/history`) necesita catálogo para mostrar los datos de cada pista y responde `503` si no está. Guardar reproducciones no lo necesita: lo validó quien encoló.

## Cola de reproducciones

[`consumer.py`](consumer.py) lee el stream `playbacks` de Redis con el grupo `playbacks` ([contrato en `meloxo_common.playback_queue`](../../../../common/meloxo_common/playback_queue.py)) y aplica cada evento con `service.apply_event`, que inserta con `ON CONFLICT DO NOTHING` (`record`) o sube `listened_seconds` con `greatest` (`progress`). El `XACK` va después del commit.

- Orden: primero se leen los pendientes del propio consumidor, luego los de otros que llevan más de 30 s (`XAUTOCLAIM`) y al final los nuevos. Si un mensaje falla por algo transitorio, la vuelta se detiene: así un `progress` no se aplica antes que su `record`.
- Un mensaje inválido se acusa, se descarta con un aviso y suma 1 a `events_discarded` en `playback_counters`. Lo mismo un `progress` de una reproducción que no existe o es de otra persona.
- Una entrega repetida (el consumidor cayó tras el commit y antes del `XACK`) no cuenta dos veces: el `playback_id` ya existe.
- El consumidor no consulta catálogo: quien encola ya validó la pista.
- Arranca con la aplicación (`main.py`), salvo con `DISABLE_SCHEDULER`, y no hace nada si `REDIS_URL` está vacío.
