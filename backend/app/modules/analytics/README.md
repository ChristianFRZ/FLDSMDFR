# modules/analytics

Agregados para gráficas, latencia y salud del sistema. Sus pruebas están en [`tests/modules/analytics/`](../../../tests/modules/analytics/README.md).

**Tablas:** `agg_cursor`, `agg_plays_hourly`, `agg_user_plays` y `request_metrics`.

**Lo que ofrece a otros módulos:** `refresh_aggregates`, `catch_up_aggregates` y `rebuild_aggregates`, en [`public.py`](public.py).

Además de los [archivos comunes](../../README.md#qué-hay-en-un-módulo), [`aggregates.py`](aggregates.py) arma las tablas de resumen y [`latency.py`](latency.py) mide los tiempos de respuesta. Las consultas de las gráficas están en [`service.py`](service.py).

## Agregados

Cada 2 s, `refresh_aggregates` lee los eventos nuevos con `events_since`, del módulo [`playback`](../playback/README.md), y los suma en `agg_plays_hourly` y `agg_user_plays`. Un bloqueo asesor evita que dos procesos hagan el mismo trabajo.

- **Eventos recientes:** un evento espera 1 s antes de sumarse. `seq` se asigna al insertar, no al confirmar la transacción, así que sin esa espera el cursor podría saltarse un evento que se confirmó tarde.
- **Género:** cada reproducción cuenta solo en el primer género de la pista, para no sumarla dos veces.
- **Horas:** se guardan en UTC. Las gráficas `plays` y `heatmap` reciben en `tz` la zona horaria del navegador.

## Latencia

`LatencyMiddleware` mide el tiempo hasta el primer byte y agrupa los resultados por módulo. El streaming tiene su propio grupo. Cada 30 s, los minutos ya cerrados se guardan en `request_metrics`. Solo una respuesta 5xx cuenta como error.

## Privacidad

El Compositor ve agregados, sin identidades. Cada oyente ve únicamente sus propios datos, con `scope=me`.

## CSV

`GET /api/admin/reports/{name}.csv` exporta las gráficas de administración. Los valores que empiezan con `=`, `+`, `-`, `@`, tabulador o retorno de carro llevan un apóstrofo delante para que una hoja de cálculo no los ejecute como fórmula.
