# Decisiones de 04-resiliencia-concurrencia

Lo que se decidió durante la construcción sin preguntarlo al equipo, con lo que cuesta si fue un error, y lo que quedó pendiente. El diseño está en [`../specs/`](../specs/README.md) y el plan en [`../plans/`](../plans/README.md).

## Avisos al equipo

- **`POST /api/playbacks` cambia de contrato.** Ahora responde `202` con `{"playback_id": ...}`, sin `counted`, y lo atiende `catalog-streaming`, no `playback-metrics`. La interfaz no usaba esos campos. `PATCH .../progress` también responde `202`; un progreso de una reproducción ajena o inexistente ya no da `403`/`404`: el consumidor lo descarta y suma 1 a `events_discarded`.
- **Redis entra al stack.** Es un contenedor más (`redis`, con AOF y volumen `redisdata`) y una dependencia dura de `users-playlists`, `gateway-auth`, `catalog-streaming` y `playback-metrics` en Compose. Si Redis cae, la app sigue: las reproducciones dan `503` y el navegador reintenta, y la revocación vuelve a la caché de 30 s.
- **Cambiar un rol o suspender revoca la sesión al instante.** El token anterior da `401` en la siguiente petición y la persona debe volver a entrar (o renovar con su refresh token). Reactivar una cuenta no devuelve el token viejo: hay que entrar de nuevo. La interfaz ya trata el `401` renovando la sesión.
- **Quedan fuera, a propósito:** la saga con estados, la cola de mensajes muertos (rama 05), el circuit breaker de Jamendo y el estado de los breakers en la sección Salud.
- **Sin verificar:** el escenario 3 y `seed all` siguen necesitando `JAMENDO_CLIENT_ID`. Las pruebas de navegador de Playwright no se corrieron en esta rama.

## Decisiones

- **Tarea 1:** `REDIS_URL` vacío desactiva Redis (`get_redis()` devuelve `None`) — así las pruebas corren sin Redis y cada pieza decide qué hacer sin él — costo si es error: una prueba que olvide fijar el cliente falso cae en la ruta «sin Redis».
- **Tarea 3:** `iat` es un decimal (`time.time()`), no un entero, y un token es inválido si `iat < revoked_after` — con segundos enteros, quien entra justo después de que un admin le cambia el rol, en el mismo segundo, quedaría rechazado — costo si es error: ninguno mientras emisor y validador compartan reloj (mismo host en Compose).
- **Tarea 3:** la lectura de la revocación espera 0.3 s como máximo y, tras un fallo, no vuelve a llamar a Redis durante 5 s — sin esto, un Redis colgado sumaría su espera a cada petición autenticada — costo si es error: hasta 5 s con la revocación apagada tras un fallo aislado.
- **Tarea 4:** tres pruebas existentes de `users-playlists` usaban el mismo token tras un cambio de rol o una suspensión; ahora usan un token nuevo (`relogin`) — es el comportamiento nuevo — costo si es error: ninguno.
- **Tarea 5:** el breaker vive en memoria de cada proceso, uno por cliente (URL destino), y cuenta la llamada ya reintentada como un fallo — con tres servicios y dos réplicas un estado compartido no aporta y obligaría a depender de Redis — costo si es error: cada réplica abre su breaker por su cuenta, así que con dos réplicas se necesitan hasta 10 llamadas fallidas para que ambas fallen rápido.
- **Tarea 5:** `INTERNAL_TIMEOUT_SECONDS` bajó de 3 s a 1.5 s y es solo la espera de lectura; la de conexión es fija de 1 s — lo piden los valores del PRD §11 — costo si es error: una llamada legítima de más de 1.5 s (por ejemplo, un lote grande de pistas) dará `503`.
- **Tarea 5:** solo `get` y `post(..., idempotent=True)` se reintentan; no se agregaron `put` ni `delete` a `InternalClient` porque nadie los usa — costo si es error: ninguno.
- **Tarea 6:** `consume_once` lee primero lo pendiente propio, luego lo pendiente de otros (`XAUTOCLAIM` tras 30 s) y al final lo nuevo, y se detiene ante un fallo transitorio — sin esto, tras un fallo un `progress` podía aplicarse antes que su `record` y descartarse — costo si es error: un fallo transitorio retrasa también los mensajes siguientes, no los pierde.
- **Tarea 6:** una entrega repetida (el consumidor cayó tras el commit y antes del `XACK`) suma 1 a `duplicates_discarded` aunque el cliente no reenviara nada — el contador no distingue el origen del duplicado — costo si es error: el contador sube de más tras una caída del consumidor.
- **Tarea 7:** `POST` y `PATCH` de `/api/playbacks` pasan a catálogo, y `GET /api/playbacks/history` se queda en `playback-metrics`; en nginx son `location = /api/playbacks` y `location ~ ^/api/playbacks/[^/]+/progress$` — el progreso exige que la reproducción exista, y por un solo stream con un solo consumidor el `PATCH` no se adelanta al `POST` — costo si es error: si el consumidor se vuelve más de uno, el orden entre `record` y `progress` de un mismo `playback_id` puede perderse.
- **Tarea 7:** catálogo espera 1 s al encolar y, si Redis no responde, devuelve `503` `upstream_unavailable` — el navegador ya guarda lo pendiente y reintenta — costo si es error: una reproducción puede tardar en llegar mientras Redis esté caído.
- **Tarea 7:** el registro de latencia de catálogo no cubre `/api/playbacks` — no se pidió y las métricas de latencia de reproducciones se miden hoy por otro camino — costo si es error: el módulo no aparece en las gráficas de latencia de catálogo.
- **Tarea 8:** al construir apareció que un token emitido justo después de un cambio de rol seguía viendo el rol viejo hasta 30 s, porque la caché de estado de cuenta no sabía de la revocación. `AuthStateCache.get` ahora descarta lo guardado antes de la revocación (`not_before`) — sin esto el objetivo «se ve en la siguiente petición» no se cumplía para quien vuelve a entrar — costo si es error: una consulta más a `users-playlists` por cada revocación.
- **Tarea 8:** el escenario 10 usa `docker compose pause` y no `stop` — con `stop` la conexión se rechaza al instante y no hay espera que el breaker evite; con `pause` la llamada aguarda el timeout de lectura — costo si es error: el escenario dura cerca de un minuto.
- **Revisión final:** el breaker se quedaba en medio abierto para siempre si la llamada de prueba terminaba cancelada o con un error que no es de HTTP; `InternalClient` ahora registra un fallo en ese caso — costo si es error: una llamada cancelada cuenta como fallo del destino.
- **Revisión final:** el consumidor guarda la reproducción con la hora en que se recibió (`received_at`) y no la de cuando se aplica — tras una caída de `playback-metrics`, lo escuchado durante ella aparecía como un pico al volver — costo si es error: ninguno.
- **Tarea 9:** no se corrió `docker compose down -v`, aunque el plan lo pedía — esta rama no cambia el esquema ni las migraciones, así que bastó `up --build -d` y se conservaron los datos — costo si es error: ninguno.

## Resultados de la verificación

Corrida del 2026-11-14 en la misma laptop de `02` y `03` (Intel i7-1165G7, 8 hilos, 15 GB de RAM, Linux), con el stack en `docker compose` local y `seed activity`. Todo corrió en ella; Jamendo quedó fuera.

### Pruebas

| Suite | Resultado |
| --- | --- |
| `meloxo_common` | 87 pasaron |
| `users-playlists` | 182 pasaron |
| `catalog-streaming` | 169 pasaron |
| `playback-metrics` | 110 pasaron |
| `gateway-auth` | 14 pasaron |
| `edge` (sin stack y con stack) | 115 pasaron |
| `demo/test_common.py` y `tests/` | 17 y 2 pasaron |
| Pruebas de `frontend/src/player` (Vitest) | 35 pasaron |

### Escenarios

Los escenarios 1, 2, 4, 5, 6, 7, 8, 10 y 11 pasaron contra el stack. El 3 no se corrió (falta una llave de Jamendo) y el 9 es la prueba de carga.

| Medición | Resultado |
| --- | --- |
| Escenario 1 | Con `playback-metrics` detenido, 3 reproducciones responden `202`; al volver se aplican las 3, sin duplicar la reenviada |
| Escenario 4 | 100 reenvíos: todos `202`, 1 reproducción y `duplicates_discarded` +99 |
| Escenario 10 | La primera llamada con catálogo congelado tarda 5.1 s (1.5 s de lectura y 2 reintentos); tras 5 llamadas lentas el breaker abre y responde en 17 ms; a los 15 s se cierra |
| Escenario 11 | Cambio de rol: el token anterior da `401` en 0.04 s (antes, hasta 30 s); suspensión: `401` en 0.03 s y la cuenta no puede volver a entrar |
| Redis reiniciado con 20 eventos pendientes (`playback-metrics` detenido) | Se aplican exactamente los 20 |

### F3.4: evento visible en ≤ 5 s

Diez mediciones desde el `POST` hasta ver la reproducción en `GET /api/playbacks/history`: mediana de 0.033 s y máximo de 0.07 s. Cumple.

### Prueba de carga (F2.3)

`locust -f demo/locustfile.py --headless -u 50 -r 10 -t 2m --host http://localhost:8080`: 5283 peticiones y 0 fallos (en `03`: 5438 y 0).

| Medida | p50 | p95 | Objetivo p95 | `03` p50 / p95 | Resultado |
| --- | --- | --- | --- | --- | --- |
| Primer byte de audio | 9 ms | 22 ms | < 500 ms | 9 / 21 ms | cumple |
| `GET /api/songs` | 15 ms | 35 ms | < 300 ms | 15 / 34 ms | cumple |
| `GET /api/playlists/{id}` | 35 ms | 82 ms | < 200 ms | 36 / 94 ms | cumple |
| `POST /api/playbacks` (ahora encola) | 13 ms | 26 ms | — | — | — |

La carga con la cola no empeoró los tiempos de `03`. La fase de preparación al agregar a una playlist sigue en p50 de 880 ms y p95 de 1500 ms, como en `02` y `03`; no cambió con esta rama.

## Pendientes

- Hallazgos menores de la revisión final que no se arreglaron: la hora de la caché de estado se toma después del `fetch` (carrera de milisegundos), el ticket de streaming no consulta la revocación (una cuenta suspendida sigue abriendo audio hasta 30 s), un mensaje que falla siempre con algo que no es `ValueError` bloquea la cola, reactivar no invalida el estado «suspendido» guardado, el nombre del consumidor es fijo (hay que cambiarlo si `playback-metrics` pasa a más de una réplica), el `lifespan` no espera las tareas ni cierra el cliente de Redis, `redis>=5.0` sin tope y respuestas leídas por posición, y gateway-auth no tiene prueba propia de revocación.
- Correr el escenario 3 y `seed all` con una `JAMENDO_CLIENT_ID` real, y las pruebas de Playwright.
- Si el consumidor de reproducciones pasa a ser más de uno, fijar el orden entre `record` y `progress` de un mismo `playback_id` (hoy lo da tener un solo consumidor).
- `MAXLEN ~ 100000` recorta lo más viejo si `playback-metrics` pasa mucho tiempo caído; con unas 7 reproducciones por segundo en la carga, eso son más de 4 horas.
- Circuit breaker para las llamadas de catálogo a Jamendo y estado de los breakers en la sección Salud.
- Cola de mensajes muertos para lo que hoy solo se descarta con un aviso (rama 05).
