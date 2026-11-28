# modules/analytics

Agregados para gráficas, consulta de latencia y salud del sistema. Sus pruebas están en [`tests/modules/analytics/`](../../../tests/modules/analytics/README.md).

**Tablas:** `agg_cursor`, `agg_plays_hourly`, `agg_user_plays` y `request_metrics`.

**Lo que ofrece a otros módulos:** `refresh_aggregates`, `catch_up_aggregates` y `rebuild_aggregates`, en [`public.py`](public.py).

Además de los [archivos comunes](../README.md), [`aggregates.py`](aggregates.py) arma las tablas de resumen. Las consultas de las gráficas están en [`service.py`](service.py).

## Datos de otros servicios

Los nombres de pistas y artistas, las cuentas de catálogo, el crecimiento de usuarios y las inclusiones en playlists y casetes se piden por HTTP con [`clients/`](../../clients/README.md). Si el servicio no responde, la ruta devuelve `503`. Los eventos de reproducción se leen en proceso por `playback.public`.

## Agregados

Cada 2 s, `refresh_aggregates` lee los eventos nuevos con `events_since`, del módulo [`playback`](../playback/README.md), y los suma en `agg_plays_hourly` y `agg_user_plays`. Un bloqueo asesor evita que dos procesos hagan el mismo trabajo.

- **Eventos recientes:** un evento espera 1 s antes de sumarse. `seq` se asigna al insertar, no al confirmar la transacción, así que sin esa espera el cursor podría saltarse un evento que se confirmó tarde.
- **Género:** cada reproducción cuenta solo en el primer género de la pista, para no sumarla dos veces.
- **Horas:** se guardan en UTC. Las gráficas `plays` y `heatmap` reciben en `tz` la zona horaria del navegador.

## Caché de lectura

`GET /api/metrics/top`, `genres`, `plays` y `heatmap` se guardan 15 s en `redis-cache` (`AGGREGATE_TTL_SECONDS` en [`routes.py`](routes.py)), sin invalidación explícita: los agregados ya van hasta 30 s por detrás de las reproducciones, así que esos 15 s no cambian lo que se puede observar. El rol se comprueba antes de mirar la caché, y la clave lleva `scope`, `kind`, `limit`, `days`, `group`, `tz` y, en lecturas personales o de Compositor, el usuario. `top` no guarda una respuesta con etiquetas «No disponible» (pista que catálogo no conoce); un error `503` por catálogo caído tampoco se guarda. Sin `redis-cache` se consulta PostgreSQL como siempre.

## Latencia

La medición la hace `LatencyMiddleware` de `meloxo_common` (ver [`main.py`](../../main.py)). Esta tabla, `request_metrics`, solo se lee en `GET /api/metrics/latency`; quien la llena es la tarea de recolección de latencia, que no está en este paso del traslado.

## Privacidad

El Compositor ve agregados, sin identidades. Cada oyente ve únicamente sus propios datos, con `scope=me`.

## CSV

`GET /api/admin/reports/{name}.csv` exporta las gráficas de administración. Los valores que empiezan con `=`, `+`, `-`, `@`, tabulador o retorno de carro llevan un apóstrofo delante para que una hoja de cálculo no los ejecute como fórmula.
