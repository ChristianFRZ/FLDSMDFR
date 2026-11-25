# Versiones

Los archivos de migración, en orden. No edites uno que ya se aplicó en otra máquina: crea uno nuevo.

| Migración | Qué hace |
| --- | --- |
| `0001_playback` | Tablas `playback_events` y `playback_counters` |
| `0002_analytics` | Tablas `agg_cursor`, `agg_plays_hourly`, `agg_user_plays` y `request_metrics` |

Son las migraciones `0007` y `0010` del monolito, renumeradas desde `0001`.
