# Decisiones de 03-gateway-balanceo

Lo que se decidió durante la construcción sin preguntarlo al equipo, con lo que cuesta si fue un error, y lo que quedó pendiente. El diseño está en [`../specs/`](../specs/README.md) y el plan en [`../plans/`](../plans/README.md).

## Avisos al equipo

- **Dos diferencias con el PRD.** (1) La lista de revocación en Redis (cerrar sesión o suspender y que el gateway lo vea al instante) pasa a la rama `04`: aquí un cambio de rol o una suspensión tarda hasta 30 s en verse en el gateway. (2) El control de salud de las réplicas es solo pasivo: nginx de código abierto no sondea, así que una réplica caída se descubre cuando una petición falla y se reintenta con la otra. El sondeo activo requeriría nginx Plus u otro balanceador.
- **Un ascenso a Compositor tarda hasta 30 s en verse.** La caché de estado de cuenta de 30 s (`AUTH_CACHE_SECONDS`) ahora se nota en el borde: un usuario recién promovido recibe `403` del gateway en `/api/composer/*` hasta que vence. Las demos y pruebas que promueven y suben enseguida tardan unos 30 s más; `new_composer` sondea hasta que la ruta deja de dar `403`. Lo mismo vale para una suspensión: la cuenta sigue entrando hasta 30 s.
- **`proxy_connect_timeout` bajó de 3 s a 1 s y vale para todos los servicios**, no solo para catálogo. Un servicio que tarde más de 1 s en aceptar la conexión dará 502/503 en vez de esperar.
- **`seed all`, la importación de Jamendo y el escenario 3 siguen sin verificar:** `JAMENDO_CLIENT_ID` está vacío en este entorno y el escenario 3 sale con código 2 (`PRECONDICIÓN NO CUMPLIDA`), igual que en `02`. Hay que correrlos con una llave real antes de cerrar la rama.
- **Umbrales de F2.3 y F2.4:** se cumplen; ver [Resultados](#resultados-de-la-verificación).
- **El aviso de `02` sobre agregar a una playlist sigue sin confirmar:** la fase de preparación dio otra vez p50 de 760 ms y p95 de 1400 ms al agregar (50 clientes, 1000 peticiones). No cambió con el gateway.

## Decisiones

- **Tarea 1:** `gateway-auth` hace `os.environ.setdefault("DATABASE_URL", "unused://gateway-auth")` en `config.py`, antes de importar `meloxo_common.config` — `BaseServiceSettings` exige `DATABASE_URL` aunque el servicio no tenga base de datos, y así no hace falta ni pasarla en compose ni cambiar `meloxo_common` — costo si es error: quitar el valor y hacer opcional la variable en common.
- **Tarea 1:** un `sub` mal formado (no UUID) responde `401`, y `/docs` y `/openapi.json` están desactivados — evita un 500 como el de `02` y no expone documentación en un servicio que solo habla con nginx — costo si es error: una línea.
- **Tarea 2:** `catalog-streaming` se escala con `deploy.replicas: 2` en `compose.yaml`, `edge` pasa a `restart: always` y depende de `gateway-auth` sano — las dos réplicas salen del mismo servicio y el DNS de Docker devuelve ambas direcciones — costo si es error: ninguno; volver a una réplica es un cambio de número.
- **Tarea 3:** `/_auth` usa una variable propia, `$auth_upstream`, en vez de `$upstream` — una subpetición comparte variables con la petición principal, y con el texto del diseño toda petición protegida terminaba en `gateway-auth` (`GET /api/users/me` daba el 404 de FastAPI). Lo detectó la verificación en vivo, no las pruebas estáticas; ahora hay una prueba — costo si es error: ninguno, es una corrección.
- **Tarea 3:** el rol exigido se calcula en la petición principal, con `if ($uri != /_auth) { set $auth_required_roles $required_roles; }`, y `/_auth` lo envía como `X-Required-Roles` — dentro de la subpetición `$uri` vale `/_auth`, así que el `map $uri $required_roles` siempre daba vacío y el gateway no exigía el rol (los `403` que se veían venían de los servicios, con `detail: null`). El `map` se conserva; el `if` se salta en la subpetición y el valor de la principal llega intacto — costo si es error: una regresión silenciosa de permisos; la prueba `test_required_roles_are_computed_from_the_main_request_uri` la cubre.
- **Tarea 3:** `error_page 500 =503` — cuando `gateway-auth` no responde, `auth_request` da 500 y el cliente debe ver `503 upstream_unavailable` en JSON, como con cualquier servicio caído — costo si es error: un 500 propio de nginx también se verá como 503.
- **Tarea 3:** `/_auth` vacía `X-User-Id` y `X-User-Role` hacia `gateway-auth`, y las rutas sin sesión no envían esas cabeceras — la identidad solo la fija el gateway; una cabecera falsa del cliente nunca llega a un servicio — costo si es error: ninguno.
- **Tarea 3:** las rutas sin sesión son `/api/auth/` (register, login, refresh, logout), `/api/health`, el stream con su ticket y `/api/media/`; la prueba `test_public_set_matches_the_services` las compara con las rutas sin `security` de los servicios y **no encontró discrepancias** — costo si es error: una ruta pública nueva sin `auth_request off` queda protegida, que es el lado seguro.
- **Tarea 3:** el ticket de streaming no sirve como sesión: `gateway-auth` lo rechaza con `401` — el ticket solo vale en la ruta de stream, que valida catálogo — costo si es error: ninguno.
- **Tarea 3:** se corrigió `demo/common.new_composer` para que sondee `GET /api/composer/tracks` (máximo 40 s) hasta que deje de dar `403`, y solo reintenta `403`; cualquier otro estado falla enseguida — la prueba de `Range` con stack fallaba por la caché de 30 s tras promover — costo si es error: esperas de hasta 30 s en demos.
- **Tarea 4:** failover con `proxy_next_upstream error timeout http_502 http_503`, `proxy_next_upstream_tries 2` y `proxy_connect_timeout 1s`, sin `non_idempotent` — solo `GET` y `HEAD` se reintentan; una escritura que falla a medias nunca se repite — costo si es error: una escritura que cae justo al detenerse una réplica da 502 al cliente en vez de reintentarse.
- **Tarea 5:** `playback-metrics` resuelve las direcciones de todas las réplicas de catálogo (`resolve_replicas`) y drena la latencia de cada una (`drain_latency_all`) — con un nombre DNS por servicio, un solo `drain` solo vería una réplica y perdería los buckets de la otra — costo si es error: métricas de latencia incompletas en el catálogo.
- **Tarea 5:** la respuesta de cada réplica se valida por separado; una réplica con respuesta inválida o caída se registra y se omite, y las demás siguen — una réplica mala no debe tumbar el volcado de las sanas — costo si es error: los buckets de una réplica con respuesta mala se pierden.
- **Tarea 5:** se mantiene un cliente por dirección y, tras cada resolución, se cierran y se descartan los de direcciones que ya no existen (evicción) — al recrear réplicas cambian las IP y los clientes viejos se acumularían — costo si es error: fuga de clientes HTTP.
- **Tarea 6:** el escenario 2 corre 20 peticiones por segundo durante 15 s, detiene una réplica y cuenta solo el tráfico posterior a la caída; al final siempre restaura las dos réplicas y espera a que ambas estén sanas — así un fallo no deja el stack a medias — costo si es error: ninguno.
- **Tarea 8:** `demo.common.wait_edge` ahora sondea con una sesión de administrador y exige cinco `200` seguidos. Antes daba por buena una réplica con un `401` sin token, y con el gateway delante ese `401` ya no lo da el catálogo: lo da nginx sin llegar a él. El escenario 8 falló en su limpieza (`DELETE` con 502 contra las direcciones viejas, que nginx tiene en caché hasta 10 s) — costo si es error: los escenarios que recrean catálogo podrían volver a dar falsos "listo".
- **Tarea 8:** `APP_VERSION` de `playback-metrics` pasa a `03-gateway-balanceo` — es lo que muestra la sección de Salud — costo si es error: una cadena.

## Resultados de la verificación

Corrida del 2026-11-13 en la misma laptop de `02` (Intel i7-1165G7, 8 hilos, 15 GB de RAM, Linux), con el stack en `docker compose` local (proyecto `meloxo`) y `seed activity`: Locust, nginx, `gateway-auth`, los servicios, las dos réplicas de catálogo y PostgreSQL corrieron en ella; Jamendo quedó fuera.

### Prueba de carga (F2.3)

`locust -f demo/locustfile.py --headless -u 50 -r 10 -t 2m --host http://localhost:8080`: 5438 peticiones y 0 fallos (en `02`: 5461 y 0).

| Medida | p50 | p95 | Objetivo p95 | `02` p50 / p95 | Resultado |
| --- | --- | --- | --- | --- | --- |
| Primer byte de audio | 9 ms | 21 ms | < 500 ms | 9 / 20 ms | cumple |
| `GET /api/songs` | 15 ms | 34 ms | < 300 ms | 12 / 26 ms | cumple |
| `GET /api/playlists/{id}` | 36 ms | 94 ms | < 200 ms | 31 / 55 ms | cumple |

Los tres umbrales se cumplen; no hizo falta el primer ajuste (la caché de 30 s de `gateway-auth` ya estaba) ni se tocó el locustfile. Lo que suma el salto de `auth_request`: unos 3 ms en el p50 y 8 ms en el p95 de `GET /api/songs`, y 5 ms y 39 ms en `GET /api/playlists/{id}`; el audio casi no cambia porque el stream no pasa por el validador. Otras filas: `POST /api/playbacks` 23 / 55 ms, `POST stream-ticket` 12 / 32 ms, `preparar: agregar` 760 ms / 1400 ms. La diferencia en el p95 de las playlists es de una sola corrida; no se repitió ni se separó el efecto del validador de la variación normal.

### Failover (F2.4)

| Medición | Resultado |
| --- | --- |
| [`scenario_2_failover.py`](../../demo/scenario_2_failover.py), primera corrida de la verificación | 0 fallidas de 293 peticiones; las últimas 50 dan `200`; la réplica restante recibió tráfico; las 2 réplicas volvieron |
| Mismo escenario, corridas de la tarea 6 | 0 de 262 y 0 de 201 |
| [`test_stack.py::test_replica_failover_loses_at_most_one_request`](../../edge/tests/test_stack.py) | pasa (a lo sumo 1 fallida de 120, y las últimas 40 en `200`) |
| Medición de la tarea 4, a mano | 0 fallos de 40 `GET /api/songs` con una réplica detenida |

F2.4 se cumple con el umbral de a lo sumo una petición perdida.

### Pruebas

| Suite | Resultado |
| --- | --- |
| `services/common` | 43 passed in 1.08s |
| `services/users-playlists` | 174 passed in 39.58s |
| `services/catalog-streaming` | 158 passed in 23.38s |
| `services/playback-metrics` | 105 passed in 9.93s |
| `services/gateway-auth` | 14 passed in 0.19s |
| `edge/tests` (con stack) | 113 passed in 61.61s |
| `edge/tests -m stack` | 13 passed in 57.18s |
| `demo` | 11 passed in 0.04s |
| `npm test` (frontend) | 32 files, 144 tests passed |

### Escenarios de demo

```
demo/scenario_1_metrics_down.py -> 0
demo/scenario_2_failover.py -> 0
demo/scenario_3_jamendo_down.py -> 2
demo/scenario_4_idempotency.py -> 0
demo/scenario_5_tape_full.py -> 0
demo/scenario_6_last_admin.py -> 0
demo/scenario_7_permissions.py -> 0
demo/scenario_8_double_publish.py -> 0
```

El 3 sale con 2 (`PRECONDICIÓN NO CUMPLIDA`, sin pistas de Jamendo). El 8 falló en la primera pasada por `wait_edge` (ver la decisión de la tarea 8) y pasó tras el arreglo; se volvieron a correr 1, 2 y 3 con el arreglo. El 7 pasa con el gateway delante.

## Pendientes menores

Servicios y gateway:

- `gateway-auth`: `routes.py` captura `KeyError` y `ValueError` de forma amplia al resolver el usuario; el `conftest` toca `auth._cache` directamente.
- `error_page 500 =503` enmascara también los 500 propios de nginx.
- La prueba del rol en `test_routes` es textual: comprueba el texto del `if`, no su efecto; el efecto lo cubre `test_stack`.
- `proxy_connect_timeout 1s` aplica a todos los servicios (aceptado por el plan); el failover real lo prueba `test_stack`, la prueba estática solo mira el texto.
- `playback-metrics`: la clave de la caché de clientes es la dirección y no distingue un cambio de puerto o esquema de `CATALOG_URL`; el orden de imports en `clients/catalog.py` y el docstring de `_remote` están por pulir; el README de `clients/` no menciona la evicción.
- `wait_composer_role` (`demo/common.py`) no atrapa los errores de conexión de `api.call`.

Demo y pruebas:

- `restore_catalog` menciona "(dos)" en su docstring aunque el número sale de `REPLICAS`; `wait_healthy` espera 60 s fijos.
- En `test_stack.py`: el `finally` de `test_gateway_auth_down_is_503` puede tapar el error original, hay un fixture de oyente sin uso y la prueba de `Range` está duplicada (`test_range_requests_through_edge` y `test_range_still_works_through_the_gateway`).
- Siguen los pendientes de `02` que no tocó esta rama (ver [`02-separacion.md`](02-separacion.md#pendientes-menores)); en particular, el escenario 8 vence las pistas con SQL y no prueba que las dos réplicas consultaran a la vez.
