# Decisiones de 02-separacion

Lo que se decidió durante la construcción sin preguntarlo al equipo, con lo que cuesta si fue un error, y lo que quedó pendiente. El diseño está en [`../specs/`](../specs/README.md) y el plan en [`../plans/`](../plans/README.md).

## Avisos al equipo

- **Posible regresión al agregar a una playlist (por confirmar):** en la fase de preparación de la prueba de carga (50 clientes, `POST /api/playlists/{id}/songs`, 1000 peticiones) salió p50 de 780 ms y p95 de 1400 ms. El valor del monolito por fase se desconoce; solo se registró el p99 acumulado de toda su corrida, entre 240 y 390 ms. Con un solo usuario y sin otra carga, la misma ruta dio p50 26 ms y p95 29 ms (30 agregados seguidos), así que el salto HTTP a catalog-streaming por sí solo no explica los 780 ms; lo más probable (inferencia, no medido) es contención durante la preparación, cuando 50 clientes agregan sin pausa. Conviene medir esa fase por separado, en el monolito y aquí, antes de darla por buena.
- **`seed all`, la importación de Jamendo y el escenario 3 siguen sin verificar:** `JAMENDO_CLIENT_ID` está vacío en este entorno. Hay que correrlos con una llave real antes de cerrar la rama.
- **Umbrales de F2.3:** los tres se cumplieron; no hay ninguno sin cumplir.

## Decisiones

- **Tarea 1:** `services/common` reúne el estado de autenticación, el error `UpstreamError` y el cliente interno `InternalClient`, y el hash de contraseñas queda fuera de él — los tres servicios comparten lo primero y solo users-playlists usa lo segundo — costo si es error: mover un módulo.
- **Tarea 6:** el hash de contraseñas pasa al módulo `users` de users-playlists al separar `security.py` — el resto de `security.py` ya vive en common — costo si es error: un archivo más.
- **Tarea 4:** el ticket de streaming se valida localmente; si el estado de la cuenta se puede obtener (caché o users-playlists) y no está activa, se rechaza con 401; si users-playlists no responde y no hay estado guardado, se acepta el ticket firmado — el diseño manda que un ticket firmado sobreviva a la caída — costo si es error: una cuenta suspendida podría seguir un stream ya abierto mientras users-playlists esté caído.
- **Tarea 9:** playback-metrics expone también `GET /internal/health` — sin él el healthcheck de compose de la tarea 10 fallaba — costo si es error: quitar una ruta.
- **Tarea 14:** el `Dockerfile` raíz se borra — lo reemplazan `edge/` y el de cada servicio — costo si es error: ninguno.
- **Tarea 10:** el contexto de build de cada servicio es la raíz del repositorio (`context: .`, `dockerfile: services/<svc>/Dockerfile`) — los servicios copian `services/common` — costo si es error: imágenes algo más lentas de construir.
- **Tarea 10:** las pruebas de cada servicio crean su base `<svc>_test` con el superusuario `meloxo` en `localhost:5433` (con `POSTGRES_PASSWORD` de `.env`) — no hace falta otro rol — costo si es error: ninguno.
- **Tarea 10:** `USERS_DB_PASSWORD`, `CATALOG_DB_PASSWORD` y `PLAYBACKS_DB_PASSWORD` se agregan al `.env` local (ignorado por git) con valores aleatorios, nunca a archivos versionados — costo si es error: ninguno.
- **Tarea 10 y 15:** `docker compose down -v` borró el volumen de desarrollo del proyecto `meloxo` (el del monolito) y se volvió a sembrar — el dueño decidió re-sembrar y solo se tocó el proyecto `meloxo`, nunca `fldsmdfr-*` — costo si es error: datos locales de demo, que se regeneran con `seed`.
- **Tarea 13:** el escenario 3 distingue `PRECONDICIÓN NO CUMPLIDA` (código de salida 2, se comprueba antes de subir nada) de `FALLA`, y el bucle del README corre todos los escenarios sin `|| break` — sin datos de Jamendo el 3 detenía el bucle y no corrían del 4 al 8 — costo si es error: un código de salida más.
- **Tarea 15:** `seed all` no se pudo correr aquí porque `JAMENDO_CLIENT_ID` está vacío en `.env`; se usó `seed activity` (pistas locales y actividad) — sin llave no hay importación de Jamendo — costo si es error: la importación de Jamendo y el escenario 3 quedan sin verificar en esta rama (ver Resultados).
- **Tarea 14:** se perdió la cobertura de `test_pool.py` (6 pruebas de soltar la conexión antes de llamar a otro módulo) — la llamada entre dominios ahora es HTTP y ya no hay pool compartido que retener — costo si es error: una regresión por conexiones retenidas dentro de un servicio no tendría prueba.
- **Tarea 2:** con users-playlists caído, cada petición espera el timeout de 3 s antes de usar el estado de cuenta guardado — el cliente intenta refrescar en cada petición en vez de recordar la caída — costo si es error: latencia de 3 s en todas las rutas autenticadas de catalog-streaming y playback-metrics durante la caída; se arregla con un cortacircuitos.
- **Tarea 6:** `add_song` vuelve a leer la playlist tras la espera al catálogo y dependía de que `session.get` no devolviera un objeto en memoria (la sesión usa `expire_on_commit=False`) — en la revisión final se agregó `populate_existing=True` como defensa y una prueba que borra la playlist durante la espera y espera 404 (la prueba ya pasaba antes del cambio: fija el comportamiento, no la defensa) — costo si es error: ninguno conocido.
- **Tarea 3:** `drain` devuelve también el minuto abierto, así que playback-metrics hace upsert con promedio ponderado al volcar a `request_metrics`, como el monolito — así no se duplican minutos — costo si es error: métricas de latencia algo imprecisas en el minuto en curso.
- **Tarea 5:** `get_songs` y `get_artists` parten en lotes de 200 ids y unen los diccionarios, porque `InternalClient.get_ids` extiende listas y esas rutas devuelven dict — sin adaptar, el cliente fallaba — costo si es error: ajustar los clientes.

## Pendientes menores

Servicios y common:

- `InternalClient`: una respuesta 2xx no JSON o 3xx lanza `ValueError` en vez de `UpstreamError`; el timeout de httpx es por fase; el timeout de cada cliente sale de `INTERNAL_TIMEOUT_SECONDS` (3 s por defecto), pero `compose.yaml` no lo pasa a los contenedores, así que solo cambia si se agrega ahí.
- el chequeo de fronteras (`boundaries`) ignora imports relativos, y `test_boundaries` con `{"meloxo_common"}` no tiene efecto real.
- `load_models` y `contracts` de common no tienen pruebas; `current_user` y `require_role` no se prueban por inyección de FastAPI.
- un `sub` mal formado da 500, como en el monolito.
- `AuthStateCache` con `ttl=0` acumula entradas y `UsersService.set_status` toca `_entries` (debería exponer `clear()`).
- si la auditoría pasa y el commit falla queda una entrada sin acción.
- los buckets de latencia se pierden si se pierde la respuesta del `drain` o si falla la escritura tras drenar.
- `ensure_artist` (`catalog_streaming/modules/catalog/composer.py`) hace una llamada HTTP a users-playlists con la transacción abierta: la primera subida de un Compositor nuevo da 503 si users-playlists está caída, y mientras espera retiene la conexión y el bloqueo de la fila.
- `hide_song` y `restore_song` (`publishing.py`) retienen la conexión de base de datos durante la llamada de auditoría a users-playlists.
- `compose.yaml` no pasa al contenedor `TAPE_MAX_TRACKS`, `COMPOSER_MAX_TRACKS`, `INTERNAL_TIMEOUT_SECONDS` y las demás variables con valor por defecto: cambiarlas en `.env` no tiene efecto sin agregarlas al `environment` del servicio.
- `since` mal formado da 500 (no 422); `limit/minimum` con default 0 en demo listenable; `except Exception` sin log en `/internal/health` ni prueba de la rama caída.
- `list_favorites` y `list_follows` dan 503 `upstream_unavailable` en vez de `catalog_unavailable`.
- `history` da 503 si catálogo cae (el monolito fallaba igual); se podría degradar con la pista en `None`.
- `inclusions` con más de 200 ids suma por lote (cota superior; solo importa si `COMPOSER_MAX_TRACKS` supera 200).
- `health._aggregates` llama `lag_seconds()` sin `try/except`: 500 posible con la BD arriba, contra F7.3.
- seed repetido sin `clear` da 500 por `IntegrityError` en vez de 409; `demo/social` no es atómico (un reintento debe llamar antes a `/clear`) y `growth days` no tiene límites; los campos demo no se validan (rol libre, `KeyError` → 500 si el catálogo no conoce la pista); el demo de playlists/social exige el catálogo sembrado antes.
- `test_metrics_return_503_when_catalog_down` tiene un nombre engañoso y `test_health_reports_db_and_jamendo` quedó con una aserción más débil.
- sin pruebas de: id mal formado, tope en `upcoming/published-since`, POST demo import, exactamente 200 ids, batching de `get_display_names`, auth-state 404 → `None`, `lifespan`.

Servicios y common (cierre de tareas 4, 9 y 10, verificadas en el código):

- los `main.py` de los servicios no corren alembic; lo hacen las imágenes con el `CMD` del Dockerfile (`alembic upgrade head && uvicorn ...`), así que arrancarlos a mano exige migrar antes.
- `playback_metrics/modules/analytics/routes.py` quedó con imports sin uso tras reescribir health (`time`, `text`, `UpstreamError`, `lag_seconds`, `jamendo_status`).
- el middleware de latencia de common no tiene prueba de respuesta en streaming ni de doble conteo.
- `.dockerignore` no excluye `frontend/` entero (por ejemplo `frontend/e2e`), que entra al contexto de build aunque los servicios no lo usen. `**/dist` sí queda fuera.

Infraestructura y edge:

- compose usa `${VAR}` sin `${VAR:?}`: en un clon sin `.env` avisa en vez de fallar claro.
- las contraseñas se ven en la lista de procesos del contenedor de init (`psql -v`).
- el parser de `.env` del test no quita comillas; no hay política `restart:`.
- `depends_on: service_healthy` del edge impide que `compose up` lo arranque si playback-metrics está caído (considerar `service_started`).
- sin prueba negativa del resolvedor de rutas; prefijos sin barra final aceptan `/api/songsXYZ` (según la tabla del diseño); sin cabeceras de caché para assets e `index.html`.
- aserciones débiles en `test_stack` (accept-ranges, Content-Range, nombre de contenedor fijo); sin prueba real de cuerpos de 16/21 MB; `len(ROUTES)>70` es un número mágico.
- `client.test.ts` no ejercita `usePlaybackReporter`: el reintento de reproducciones solo se verificó leyendo código.
- `Health.test.tsx` no asserta la tarjeta "Caído".

Semilla y demo:

- `test_seed` no verifica que `POST /catalog/import` ocurra antes de users; los mocks respx aceptan cualquier cuerpo; el test de determinismo solo compara `listened_seconds`.
- el Dockerfile de seed duplica la lista de dependencias de `seed/pyproject.toml`; los fallos que no son `SeedError` imprimen traceback.
- `wait_up`, `wait_edge` y `wait_metrics` solo capturan `OSError`; `SERVICE` en `scenario_1` sombrea `common.SERVICE`; `Api.at()` sin uso.
- confirmar que no quedan filas `source='jamendo'` temporales en catalog tras el escenario 3.
- el escenario 8 vence pistas con SQL (heredado de la rama 01): no prueba que las dos réplicas consultaran a la vez.

Documentación y pruebas de documentación:

- `test_readmes` llama `git ls-files` por carpeta (lento a futuro) y falla con `FileNotFoundError` si no hay git.
- `backend/.venv` y otros ignorados del usuario quedan en disco sin tocar.

## Resultados de la verificación

Corrida del 2026-11-12 en la misma laptop de la corrida del monolito (Intel i7-1165G7, 8 hilos, 15 GB de RAM, Linux), sobre un stack recién reconstruido con `docker compose down -v && docker compose up -d --build` y `docker compose run --rm seed python -m seed activity` (no `seed all`, ver arriba). Locust, nginx, los tres servicios y PostgreSQL corrieron en ella; Jamendo quedó fuera de la carga.

### Prueba de carga (F2.3)

`locust -f demo/locustfile.py --headless -u 50 -r 10 -t 2m --host http://localhost:8080`: 5461 peticiones y 0 fallos (el monolito, el 2026-11-06: 5576 y 0).

| Medida | p50 | p95 | Objetivo p95 | Monolito p50 / p95 | Resultado |
| --- | --- | --- | --- | --- | --- |
| Primer byte de audio | 9 ms | 20 ms | < 500 ms | 12 / 39 ms | cumple |
| `GET /api/songs` | 12 ms | 26 ms | < 300 ms | 36 / 71 ms | cumple |
| `GET /api/playlists/{id}` | 31 ms | 55 ms | < 200 ms | 27 / 66 ms | cumple |

Los tres umbrales se cumplen; no se tocó el locustfile ni se relajó ningún umbral. Otras filas de la corrida: `POST /api/playbacks` 20 / 47 ms, `POST stream-ticket` 10 / 23 ms.

Diferencias con el monolito:

- Catálogo y audio salen más rápidos que en el monolito; la causa no se midió (inferencia: probablemente cada servicio atiende solo su parte). `GET /api/playlists/{id}` tiene p50 de 31 ms contra 27 ms; probablemente (inferencia, no medido) porque es la ruta con salto extra, ya que users-playlists pide canciones a catalog-streaming por HTTP, aunque el p95 igual bajó.
- Todas las peticiones pasan ahora por nginx y la validación de cuenta consulta a users-playlists (con caché), saltos que el monolito no tenía.
- La fase de preparación es más lenta que la de uso: `preparar: agregar` tuvo p50 de 780 ms y p95 de 1400 ms (1000 peticiones). Medición aparte, un usuario y sin otra carga, 30 `POST /api/playlists/{id}/songs` seguidos por el edge: p50 26 ms, p95 29 ms, máximo 41 ms (script temporal fuera del repositorio; la playlist se borró al terminar, respuesta 204). Eso muestra que el salto HTTP cuesta decenas de milisegundos, no cientos; no muestra la causa de los 780 ms, que probablemente es contención con 50 clientes agregando sin pausa (inferencia, no medido). No es un criterio de F2.3. La cifra del monolito para esa fase no se registró, así que no se compara; ver Avisos al equipo. Los percentiles de Locust son acumulados y mezclan las dos fases.
- Siguen sin ser 50 conexiones de audio abiertas todo el tiempo (ver `demo/README.md`).

### Pruebas

| Suite | Resultado |
| --- | --- |
| `services/common` | 39 passed in 1.12s |
| `services/users-playlists` | 172 passed in 37.86s |
| `services/catalog-streaming` | 158 passed in 23.79s |
| `services/playback-metrics` | 98 passed in 9.34s |
| `seed/tests` | 18 passed in 7.88s |
| `edge/tests -m "not stack"` | 90 passed, 4 deselected in 2.63s |
| `edge/tests -m stack` | 4 passed, 90 deselected in 10.28s |
| `infra/tests` | 7 passed in 0.20s |
| `demo/test_common.py` | 3 passed in 0.02s |
| `tests/test_readmes.py` | 2 passed in 0.23s |
| `npm test` (frontend) | 32 files, 144 tests passed |
| `npm run build` (frontend) | built in 4.18s (aviso de chunks mayores de 500 kB) |

### Escenarios de demo

```
demo/scenario_1_metrics_down.py -> 0
demo/scenario_3_jamendo_down.py -> 2
demo/scenario_4_idempotency.py -> 0
demo/scenario_5_tape_full.py -> 0
demo/scenario_6_last_admin.py -> 0
demo/scenario_7_permissions.py -> 0
demo/scenario_8_double_publish.py -> 0
```

El 3 sale con 2 (`PRECONDICIÓN NO CUMPLIDA`): no hay pistas de Jamendo porque `JAMENDO_CLIENT_ID` está vacío. Queda sin verificar en esta rama, igual que `seed all`; con la llave hay que correr ambos antes de dar por cerrada la separación.

### `git grep -nE "JAMENDO_CLIENT_ID=.+"`

Tres coincidencias, ninguna es una llave real: `docs/decisions/01-monolito.md:63` (texto de la decisión sobre este mismo comando), `docs/plans/2026-11-05-01-monolito.md:823` (el comando de verificación del plan) y `docs/plans/2026-11-12-02-separacion.md:422` (el comando en el paso 4 de esta tarea). Son ejemplos de comando, no valores.
