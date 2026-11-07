# modules/playback

Eventos de reproducción, contadores e historial. Sus pruebas están en [`tests/modules/playback/`](../../../tests/modules/playback/README.md).

**Tablas:** `playback_events` y `playback_counters`.

**Lo que ofrece a otros módulos:** `events_since`, `duplicates_discarded` y `retention_for_songs`, en [`public.py`](public.py).

## Idempotencia

`POST /api/playbacks` inserta con `ON CONFLICT (playback_id) DO NOTHING`. Si no insertó nada, suma 1 a `duplicates_discarded` en la misma transacción. Responde `201` si el evento era nuevo y `200` si era un reenvío.

`PATCH /api/playbacks/{playback_id}/progress` solo aumenta `listened_seconds`: no cuenta como reproducción ni como duplicado. La gráfica de retención depende de ese dato.

El módulo [`analytics`](../analytics/README.md) lee estos eventos con `events_since`, nunca directamente de las tablas.
