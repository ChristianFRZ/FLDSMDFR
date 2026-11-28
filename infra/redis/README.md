# infra/redis

Redis 7 del stack. No hay archivos de configuración propios: la imagen `redis:7-alpine` y sus opciones están en el servicio `redis` de [`compose.yaml`](../../compose.yaml).

| Qué | Cómo está |
| --- | --- |
| Persistencia | `--appendonly yes` (AOF, con `fsync` cada segundo) y el volumen `redisdata`. Reiniciar el contenedor no borra lo encolado; una caída brusca puede perder hasta 1 s |
| Red | Sin puerto publicado: solo lo alcanzan los servicios por `redis:6379`. Sin contraseña, igual que PostgreSQL dentro de la red de Compose |
| Dirección | `REDIS_URL` (por defecto `redis://redis:6379/0`). Vacía, desactiva Redis en ese servicio |
| Salud | `redis-cli ping` cada 3 s; `restart: always` |

## Qué guarda

- **Stream `playbacks`** y su grupo `playbacks`: la cola de reproducciones. `catalog-streaming` escribe (`XADD`) y `playback-metrics` lee (`XREADGROUP`) y acusa (`XACK`) después de guardar. Contrato en [`meloxo_common.playback_queue`](../../services/common/meloxo_common/playback_queue.py).
- **Claves `revoked_after:<user_id>`:** la hora de la última revocación de sesiones de esa persona, con vencimiento de 960 s. Las escribe `users-playlists` y las lee `meloxo_common.auth`.

## Límite del stream

El stream se recorta con `MAXLEN ~ 100000`: si `playback-metrics` pasa mucho tiempo caído y se encolan más de unos 100 000 eventos, **los más viejos se pierden**. Con la carga de la prueba (unas 7 reproducciones por segundo) eso son más de 4 horas.

## Mirar la cola

Con el stack arriba:

```bash
docker compose exec redis redis-cli XLEN playbacks               # eventos en el stream
docker compose exec redis redis-cli XPENDING playbacks playbacks # entregados y sin acusar
docker compose exec redis redis-cli XINFO GROUPS playbacks       # grupo, consumidores y pendientes
docker compose exec redis redis-cli --scan --pattern 'revoked_after:*'
```

Con `playback-metrics` detenido, `XLEN` sube con cada reproducción; al volver, baja el número de pendientes hasta 0. Las pruebas usan `fakeredis`, no este contenedor.

## `redis-cache`: la caché de lectura

Un segundo Redis, aparte, definido en el servicio `redis-cache` de [`compose.yaml`](../../compose.yaml). Todo lo de arriba habla de `redis`; la caché no comparte nada con él.

| Qué | Cómo está |
| --- | --- |
| Para qué | Caché de lectura del catálogo, de los agregados de las gráficas y del estado de cuenta. Se puede perder sin perder datos: PostgreSQL sigue siendo la fuente de verdad |
| Memoria | `--maxmemory 64mb` con `--maxmemory-policy allkeys-lru`: al llenarse desaloja lo menos usado |
| Persistencia | Ninguna (`--save ""`, `--appendonly no`, sin volumen). Reiniciarla la vacía |
| Dirección | `CACHE_REDIS_URL` (por defecto `redis://redis-cache:6379/0`). Vacía, desactiva la caché en ese servicio. Solo la reciben `catalog-streaming`, `playback-metrics` y `gateway-auth` |
| Arranque | Ningún servicio espera a que esté sana: si falta, se lee de PostgreSQL |

Por qué es una instancia aparte: el desalojo LRU de una instancia compartida podría expulsar el stream `track_published`, su cola de mensajes muertos, la cola de reproducciones o la revocación, que sí deben conservarse.

```bash
docker compose exec redis-cache redis-cli DBSIZE
docker compose exec redis-cache redis-cli --scan --pattern 'cache:*'
docker compose exec redis-cache redis-cli INFO stats | grep keyspace   # aciertos y fallos
```
