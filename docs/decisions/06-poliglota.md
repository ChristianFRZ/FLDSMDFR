# Decisiones de 06-poliglota

Lo que se decidió durante la construcción sin preguntarlo al equipo, con lo que cuesta si fue un error, y lo que quedó pendiente. El diseño está en [`../specs/`](../specs/README.md) y el plan en [`../plans/`](../plans/README.md).

## Avisos al equipo

- **La caché es una instancia aparte.** `redis-cache` (`redis:7-alpine`, `--maxmemory 64mb`, `allkeys-lru`, sin persistencia ni volumen) no comparte nada con el `redis` durable, que sigue con AOF y sin límite de memoria. Una prueba de `infra/tests` fija las dos configuraciones y el escenario 13 comprueba que ningún stream cae en la caché ni ninguna clave de caché en el durable.
- **MongoDB quedó fuera**, por decisión del equipo. La bitácora de auditoría y los avisos siguen en PostgreSQL, y la regla de una base por servicio del PRD no cambió. El PRD solo anota que existe `redis-cache` y que la caché no es dueña de ningún dato.
- **Nada espera a la caché.** Ningún servicio la declara en `depends_on`. Sin `CACHE_REDIS_URL`, o con la caché caída o lenta, las lecturas van a PostgreSQL y responden igual; con la caché caída el costo es un timeout de 0,2 s cada 5 s, no uno por petición (escenario 13: 0,02 s por lectura).
- **Qué se guarda y cuánto.** Lista, detalle, artistas y géneros del catálogo: 300 s de respaldo y versión que sube al escribir. Agregados de las gráficas (`top`, `genres`, `plays`, `heatmap`): 15 s, sin invalidación explícita. Estado de cuenta: 30 s.
- **El estado de cuenta compartido también lo usan catálogo y `playback-metrics`**, no solo `gateway-auth`, porque los tres usan `AuthStateCache` con `ttl=30`. `users-playlists` usa `ttl=0` y no toca la caché. La clave `cache:auth:<user_id>` es la misma para todos: el estado sale de `users-playlists` y vale igual para cualquiera de ellos.
- **Un cambio de rol o una suspensión no tarda más que antes.** La revocación se consulta antes y manda sobre la caché compartida, y el estado que una réplica toma de ahí conserva su edad, así que no vive más de 30 s en total. El escenario 11 sigue pasando.
- **Quedan fuera, a propósito:** contadores de reproducciones, escrituras, tickets de streaming y rutas de administración; un panel de la caché y su tasa de aciertos en Salud; y los pendientes de la rama 05.
- **Sin verificar:** las pruebas de navegador (Playwright) y las de Vitest del frontend no se corrieron en esta rama, porque no toca la interfaz.

## Decisiones

- **Tarea 1:** `cached` devuelve el valor del `loader` tal cual en un fallo de caché y el JSON guardado en un acierto, y el valor se guarda con `jsonable_encoder` — así se guardan los dataclasses y los modelos que ya devolvían las rutas — costo si es error: un acierto y un fallo difieren en tipo (objeto contra diccionario), aunque FastAPI los serializa igual.
- **Tarea 1:** tras cualquier fallo de la caché se salta 5 s, también para escribir: un fallo en la lectura impide guardar después de cargar — costo si es error: la caché tarda hasta 5 s en volver a llenarse tras recuperarse.
- **Tarea 1:** con `versioned=True` la versión se lee una sola vez al inicio y se usa en la clave — una lectura que empezó antes de una escritura guarda su valor viejo bajo la versión vieja, que ya nadie consulta — costo si es error: ninguno visible; lo cubre `test_lectura_que_empezo_antes_del_bump_no_ensucia_la_version_nueva`.
- **Tarea 3:** crear una pista y `get_profile` no suben la versión del catálogo. El diseño §5 no los lista: una pista nueva nace como borrador o programada, que no se ve en las lecturas públicas, y un artista nuevo da 404, que no se guarda — costo si es error: una lectura cacheada tardaría hasta 300 s en cambiar.
- **Tarea 3:** `upsert_tracks` sube la versión una sola vez al terminar de guardar el lote (la importación de Jamendo y el refresco la usan), y solo si había pistas — costo si es error: durante una importación larga las lecturas pueden mostrar el catálogo anterior hasta terminarla o hasta los 300 s.
- **Tarea 4:** `top` no guarda una respuesta con alguna etiqueta «No disponible», es decir, una pista que catálogo no conoce — para que esa etiqueta no dure 15 s más cuando catálogo vuelva a conocerla — costo si es error: las lecturas de `top` con una pista borrada en los agregados nunca salen de la caché y siempre consultan PostgreSQL. Con catálogo caído `top` devuelve `503`, que tampoco se guarda.
- **Tarea 5:** una entrada compartida más vieja que el TTL se descarta aunque a Redis le quede vida (`age < ttl`), y la réplica que la toma hereda esa edad — sin esto el redondeo del TTL de Redis y la edad heredada podían sumar más de 30 s — costo si es error: ninguno visible.
- **Tarea 6:** `/api/metrics/top` no está en `locustfile.py`, que solo busca, abre listas y descarga audio. Se midió aparte, con 300 lecturas seguidas del administrador — costo si es error: esa cifra es de una sola persona y no de 50 clientes.
- **Revisión final (hecha por quien construyó, sin revisor independiente):** `bump` ya no respeta la ventana de salto de 5 s de las lecturas, porque saltárselo dejaba entradas viejas vivas hasta 300 s si la caché había fallado un instante antes de una escritura; y un valor corrupto o con otra forma en la caché, tanto en `cached` como en el estado de cuenta compartido, se trata como ausente en vez de lanzar una excepción. Cada uno tiene su prueba, vista fallar antes de corregir — costo si es error: un `bump` con la caché caída tarda hasta el timeout de conexión (0,2 s) en cada escritura del catálogo.

## Resultados de la verificación

Corrida del 2026-11-14 en la misma laptop de `02` a `05` (Intel i7-1165G7, 8 hilos, 15 GB de RAM, Linux), con el stack en `docker compose` local reconstruido con `docker compose up -d --build`. Jamendo no se tocó.

### Pruebas

| Suite | Resultado |
| --- | --- |
| `meloxo_common` | 133 pasaron (98 en `05`) |
| `users-playlists` | 195 pasaron |
| `catalog-streaming` | 194 pasaron (176) |
| `playback-metrics` | 122 pasaron (110) |
| `gateway-auth` | 14 pasaron |
| `edge` sin stack | 101 pasaron |
| `demo/test_common.py` | 17 pasaron |
| `seed/tests` | 18 pasaron |
| `infra/tests` | 11 pasaron (7) |
| `tests/` | 2 pasaron |

### Escenarios

Los escenarios 1 a 8 y 10 a 13 pasaron contra el stack, todos con código `0`; el 9 es la prueba de carga. El 13 comprueba tres cosas: una lectura llena la caché y ocultar una pista la quita de la siguiente lectura sin esperar al TTL; con `redis-cache` detenido las lecturas dan lo mismo y al volver se vuelven a guardar; y el stream `track_published` del Redis durable no cambia ni recibe claves de caché.

### Prueba de carga

50 clientes durante 2 minutos, sin y con `redis-cache`, con los mismos parámetros y sin tocar nada más. Sin caché: 5373 peticiones y 0 fallos. Con caché: 5203 peticiones y 0 fallos. Entre paréntesis, sin caché.

| Medida | p50 | p95 |
| --- | --- | --- |
| `GET /api/songs` | 13 ms (38) | 28 ms (70) |
| `GET /api/playlists/{id}` | 37 ms (37) | 68 ms (86) |
| Primer byte de audio | 9 ms (9) | 16 ms (21) |

Con la caché, `redis-cache` terminó con 1368 aciertos, 1189 fallos y 0 claves desalojadas. Los fallos incluyen las lecturas de versión y de estado de cuenta, no solo de la lista. Las cifras de playlists y audio no cambian porque esas rutas no se cachean: la diferencia entre corridas es ruido.

Lecturas seguidas del administrador, 300 por ruta, sin y con caché (entre paréntesis, sin):

| Ruta | p50 | p95 |
| --- | --- | --- |
| `/api/metrics/top?days=30` | 7,1 ms (31,6) | 9,6 ms (42,4) |
| `/api/metrics/genres?days=30` | 7,3 ms (20,3) | 10,2 ms (29,9) |
| `/api/songs?size=20` | 10,0 ms (27,5) | 13,8 ms (37,5) |

Conviene decir dos cosas al presentarlos. La búsqueda de Locust usa solo seis palabras distintas, así que casi todas sus lecturas son aciertos: con consultas más variadas la mejora sería menor. Y el `GET /api/songs` sin caché de esta corrida (38 ms de mediana) es más lento que el de la rama `03` (15 ms); no se investigó por qué, y la comparación válida es la de esta tabla, con las dos corridas en las mismas condiciones.

## Pendientes

- Caché de otras lecturas (`GET /api/playlists/{id}`, historial) y de contadores, que quedaron fuera.
- La tasa de aciertos de la caché en la sección Salud del admin: hoy solo se ve con `redis-cli INFO stats`.
- `track_hidden` y `track_restored`, y una forma de revisar y reinyectar lo que cae en `track_published:dlq`, heredados de la rama `05`.
- `redis-cache` no tiene contraseña y ahora guarda roles de cuenta, como el Redis durable no tenía clave para la revocación. Solo lo alcanzan los contenedores de la red de Compose, que ya comparten `JWT_SECRET`; si algún día la red deja de ser de confianza, hay que ponerle contraseña a los dos Redis.
- Con la caché vacía tras un reinicio, todas las lecturas van a PostgreSQL a la vez; no hay protección contra esa estampida porque con este volumen no hizo falta.
