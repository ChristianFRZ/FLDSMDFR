# MELOXO 03-gateway-balanceo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir el nginx de entrada en un gateway que valida el JWT y el rol por prefijo antes de enrutar, y poner dos réplicas de `catalog-streaming` con failover (F2.4).

**Architecture:** `edge` (nginx) llama con `auth_request` a un servicio nuevo `gateway-auth` (FastAPI, sin base de datos) que reutiliza `meloxo_common.auth`. La autenticación se activa a nivel de `server`, así que toda ruta nueva queda protegida salvo que se declare pública. Catálogo corre con dos contenedores bajo el mismo nombre DNS; nginx ya resuelve por DNS en cada petición y reintenta GET/HEAD con la otra dirección. `playback-metrics` pasa a drenar la latencia de cada réplica.

**Tech Stack:** Python 3.12, FastAPI, httpx, PyJWT, pytest, respx · nginx 1.27 · Docker Compose. Sin Redis (rama 04).

**Spec:** `docs/specs/2026-11-13-03-gateway-balanceo-design.md` (y `docs/prd.md`).

## Global Constraints

- Servicio nuevo: carpeta `services/gateway-auth`, paquete `gateway_auth`, puerto interno 8004, nombre de servicio compose `gateway-auth`. Solo importa `meloxo_common` de fuera de su paquete. Sin base de datos ni Redis.
- Reglas de rol por prefijo (PRD §12): `/api/admin/*` → `admin`; `/api/composer/*` → `composer` o `admin`; el resto autenticado → cualquier rol. `/api/composer-requests` **no** entra en `/api/composer/*`.
- Sin sesión (no pasan por `auth_request`): `POST /api/auth/register`, `/login`, `/refresh`, `/logout`; `GET /api/health`; la SPA; `GET /api/songs/{id}/stream` (ticket); `GET /api/media/*`. Cualquier otra ruta exige sesión.
- Respuestas del gateway: `401` con código `invalid_token` y `403` con código `forbidden`, ambos con `detail: {"source": "gateway"}`; validador caído → `503` con `upstream_unavailable`. Formato `{"error": {"code": str, "message": str, "detail": object|null}}`. Fallar cerrado.
- Los servicios siguen revalidando token, rol y propiedad: no se quita ninguna comprobación existente. Los servicios no leen todavía `X-User-Id` ni `X-User-Role`.
- nginx borra `X-User-Id` y `X-User-Role` del cliente y reenvía solo los del validador. `X-Required-Roles` lo fija nginx, nunca el cliente.
- Estado de cuenta: caché de 30 s (`AUTH_CACHE_SECONDS`), igual que en `02`. Sin lista de revocación.
- Failover: `proxy_next_upstream error timeout http_502 http_503`, `proxy_next_upstream_tries 2`, `proxy_connect_timeout 1s`, solo GET/HEAD (las escrituras no se reintentan). F2.4: a lo sumo 1 petición fallida.
- Réplicas: `catalog-streaming` con 2 contenedores por defecto. `users-playlists` y `playback-metrics` siguen con uno.
- Umbrales de F2.3 sin relajar (primer byte p95 < 500 ms con 50 clientes; `GET /api/songs` p95 < 300 ms). Si no se cumplen, se documenta en `docs/decisions/03-gateway-balanceo.md`.
- `restart: always` en `edge` y `gateway-auth`. Secretos solo en `.env`. Cada carpeta nueva lleva `README.md` en español. Código y rutas en inglés, interfaz en español.
- Commits pequeños en la rama `03-gateway-balanceo`, **sin `Co-Authored-By`** (regla del repositorio, vale más que cualquier otro texto de atribución) y sin `git push`. No tocar otros proyectos Docker de la máquina (`fldsmdfr-*`).

## Review Focus

1. **Token de streaming usado como sesión:** un ticket de `stream-ticket` (lleva `scope`) enviado en `Authorization` debe dar `401`, nunca pasar (Tarea 1).
2. **Cabeceras de identidad falsificadas:** un cliente que envía `X-User-Id: <admin>` o `X-Required-Roles: ` no debe llegar así a ningún servicio ni vaciar la regla de rol (Tarea 3).
3. **Ruta nueva sin declarar:** una ruta pública agregada a un servicio sin tocar `nginx.conf` debe romper la prueba, no quedar abierta ni cerrada por accidente (Tarea 3).
4. **Una réplica no responde al drenar la latencia:** los buckets de la otra se guardan igual y los de la caída esperan en su memoria (Tarea 5).
5. **Validador caído o usuario inexistente:** `503` JSON con validador detenido; token de un usuario borrado da `401`, no `500` (Tareas 1 y 7).

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `services/gateway-auth/` (nuevo) | Validador de sesión y rol para `auth_request`: `gateway_auth/{config,auth,routes,main}.py`, `clients/users.py`, `tests/`, `Dockerfile`, `pyproject.toml`, `README.md` |
| `edge/nginx.conf` | `auth_request` a nivel de `server`, mapa de roles, rutas públicas, cabeceras de identidad, failover |
| `edge/errors/` | JSON estáticos `unauthorized.json` y `forbidden.json` junto a `upstream_unavailable.json` |
| `compose.yaml` | Servicio `gateway-auth`, `catalog-streaming` con 2 réplicas, `edge` depende de `gateway-auth` |
| `services/playback-metrics/playback_metrics/{clients/catalog.py,latency_pull.py}` | Drenar la latencia de cada réplica de catálogo |
| `demo/{common.py,scenario_2_failover.py}` | Escenario 2 y devolver catálogo a 2 réplicas |
| `edge/tests/{test_routes.py,test_stack.py}` | Reglas de auth y roles sin stack; gateway y F2.4 con stack |
| `docs/` y `README.md` | Decisiones, README por carpeta, CHANGELOG, índices |

---

### Task 1: Servicio `gateway-auth`

**Files:**
- Create: `services/gateway-auth/{pyproject.toml,Dockerfile,README.md}`, `services/gateway-auth/gateway_auth/{__init__,config,auth,routes,main}.py`, `services/gateway-auth/gateway_auth/clients/{__init__,users}.py`, `services/gateway-auth/tests/{__init__,conftest,test_auth_route,test_boundaries,README}.py|md`
- Modelo a seguir: `services/playback-metrics/` (misma forma de `pyproject.toml`, `Dockerfile` y `conftest.py`, sin la parte de base de datos) y `services/playback-metrics/tests/fake_users.py` para simular `users-playlists` con respx.

**Interfaces:**
- Consumes: `meloxo_common.auth.build_auth(fetch) -> Auth` (`Auth.resolve_user(token) -> CurrentUser(id, role)`), `meloxo_common.contracts.AuthState`, `meloxo_common.internal.InternalClient`, `meloxo_common.errors.{AppError, register_error_handlers}`.
- Produces: `GET /auth` (cabeceras de entrada `Authorization: Bearer <jwt>` y `X-Required-Roles: <rol[,rol]>` opcional) → `204` con `X-User-Id` y `X-User-Role`; `401 invalid_token`; `403 forbidden`; `503 upstream_unavailable`. `GET /internal/health` → `200 {"status": "up"}`. `create_app() -> FastAPI` y `app` en `gateway_auth.main`.

- [ ] **Step 1: Crear la rama y guardar spec y plan**

```bash
git checkout -b 03-gateway-balanceo
git add docs/specs docs/plans
git commit -m "docs: diseño y plan de 03-gateway-balanceo"
```

- [ ] **Step 2: Escribir las pruebas que fallan** en `tests/test_auth_route.py` (cliente `httpx.AsyncClient` con `ASGITransport` sobre `create_app()`, `users-playlists` simulado con respx en `http://users.test`, `USERS_URL` y `JWT_SECRET` fijados en `conftest.py`; `DATABASE_URL` no se fija):
  - `test_valid_token_returns_204_with_identity_headers`: rol `listener`, sin `X-Required-Roles` → 204, `x-user-id` y `x-user-role == "listener"`.
  - `test_missing_or_malformed_authorization_is_401`: sin cabecera, `Basic x`, `Bearer basura` → 401 con `error.code == "invalid_token"`.
  - `test_expired_token_is_401`.
  - `test_suspended_user_is_401` (estado `suspended`) y `test_unknown_user_is_401` (el fake devuelve 404; no debe ser 500).
  - `test_stream_ticket_is_not_a_session`: token creado con `encode_token` y `scope="stream"` → 401.
  - `test_role_not_allowed_is_403`: `X-Required-Roles: admin` con `listener` → 403 `forbidden`; `composer,admin` con `composer` → 204; con `admin` → 204.
  - `test_empty_required_roles_means_any_role`.
  - `test_users_playlists_down_is_503`: el fake devuelve error de red y no hay estado en caché → 503 `upstream_unavailable`.
  - `test_health_needs_no_auth`.
  Y en `test_boundaries.py`: `find_violations(PACKAGE, "gateway_auth", {"meloxo_common"}) == []`.

- [ ] **Step 3: Ejecutar y comprobar que fallan**

Run: `cd services/gateway-auth && pip install -e ../common -e '.[dev]' && pytest -q`
Expected: FAIL (el paquete `gateway_auth` no existe).

- [ ] **Step 4: Implementar el servicio.**
  - `gateway_auth/config.py`: `Settings(BaseServiceSettings)` con `USERS_URL: str = "http://users-playlists:8001"`, `APP_VERSION: str = "03-gateway-balanceo"`, y `get_settings()` con `lru_cache`. Como `BaseServiceSettings.DATABASE_URL` es obligatorio y este servicio no tiene base, el módulo hace `os.environ.setdefault("DATABASE_URL", "unused://gateway-auth")` **antes** de importar nada de `meloxo_common.config` (decisión del constructor; documentarla en el README del servicio).
  - `gateway_auth/clients/users.py`: `get_auth_state(user_id: UUID) -> AuthState | None`, igual que el de `playback_metrics/clients/users.py` (404 → `None`).
  - `gateway_auth/auth.py`: `auth = build_auth(get_auth_state, ttl=get_settings().AUTH_CACHE_SECONDS)`.
  - `gateway_auth/routes.py`: `async def check(authorization: str | None = Header(None), x_required_roles: str | None = Header(None)) -> Response`; extrae el token de `Bearer`, llama `auth.resolve_user`, compara el rol con `x_required_roles` separado por comas (vacío o ausente = cualquier rol) y responde 204 con las cabeceras; `AppError` ya lo traduce `register_error_handlers`. Un `Authorization` sin esquema `Bearer` → `AppError(401, "invalid_token", ...)`. Un `sub` mal formado (UUID inválido) → 401, no 500. `GET /internal/health` aparte.
  - `gateway_auth/main.py`: `create_app()` con `register_error_handlers` y los dos routers; sin `lifespan` ni scheduler.
  - `Dockerfile` copiado de playback-metrics, sin alembic, `EXPOSE 8004`, `CMD uvicorn gateway_auth.main:app --host 0.0.0.0 --port 8004`.

- [ ] **Step 5: Ejecutar y comprobar que pasan**

Run: `cd services/gateway-auth && pytest -q`
Expected: todas PASS.

- [ ] **Step 6: Escribir `README.md` del servicio y de `tests/`** (qué hace, contrato de `/auth`, la nota de `DATABASE_URL`), y commit:

```bash
git add services/gateway-auth
git commit -m "feat: servicio gateway-auth que valida sesión y rol para auth_request"
```

---

### Task 2: Compose, réplicas de catálogo y demo a dos réplicas

**Files:**
- Modify: `compose.yaml`, `compose.demo.yaml` (solo si hace falta), `demo/common.py`, `demo/test_common.py`
- Test: `demo/test_common.py`

**Interfaces:**
- Consumes: imagen de `gateway-auth` (Tarea 1).
- Produces: servicio `gateway-auth` en la red; `catalog-streaming` con `deploy.replicas: 2`; constante `REPLICAS = 2` en `demo/common.py`, que usan `restore_catalog` y `demo_stack`.

- [ ] **Step 1: Escribir la prueba que falla** en `demo/test_common.py`: `restore_catalog` (con `run_compose` simulado, como las pruebas que ya existen) invoca `up -d --no-build --scale catalog-streaming=2 catalog-streaming`, y `demo_stack()` sin argumento usa `REPLICAS`. Run: `pytest demo/test_common.py -q` → FAIL.

- [ ] **Step 2: Implementar en `demo/common.py`** `REPLICAS = 2`; `restore_catalog` escala a `REPLICAS` (no a 1) y el docstring lo dice. `demo_stack(replicas: int = REPLICAS)`. Revisar los escenarios 3 y 8 por si dependen del valor por defecto de 1 (ver `grep -n "demo_stack(" demo/*.py`).

- [ ] **Step 3: Modificar `compose.yaml`**: agregar `gateway-auth` (build `services/gateway-auth/Dockerfile`, `JWT_SECRET` con el mismo `${JWT_SECRET:?...}` de los demás, `USERS_URL: http://users-playlists:8001`, `restart: always`, `depends_on: users-playlists: service_healthy`, healthcheck contra `http://localhost:8004/internal/health` con el mismo patrón `python -c urllib` de los otros). En `catalog-streaming` agregar `deploy: {replicas: 2}`. En `edge`: `restart: always` y `depends_on` también de `gateway-auth: service_healthy`.

- [ ] **Step 4: Verificar**

Run: `docker compose config -q && docker compose up -d --build && docker compose ps`
Expected: `catalog-streaming` aparece dos veces y todo `healthy`; `pytest demo/test_common.py -q` pasa.

- [ ] **Step 5: Commit**

```bash
git add compose.yaml demo/common.py demo/test_common.py
git commit -m "feat: gateway-auth en compose y catálogo con dos réplicas por defecto"
```

---

### Task 3: nginx valida sesión y rol

**Files:**
- Modify: `edge/nginx.conf`, `edge/tests/test_routes.py`
- Create: `edge/errors/unauthorized.json`, `edge/errors/forbidden.json`
- Modify: `edge/Dockerfile` solo si `COPY edge/errors` no cubre los nuevos archivos (debería).

**Interfaces:**
- Consumes: `GET /auth` de `gateway-auth` en `http://gateway-auth:8004` (Tarea 1).
- Produces: variables nginx `$required_roles` (del `map`), `$auth_user_id` y `$auth_user_role`; todo `location` de `/api/` protegido salvo los que llevan `auth_request off;`.

- [ ] **Step 1: Escribir las pruebas que fallan** en `edge/tests/test_routes.py` (reutilizan `blocks()` y `resolve()`):
  - `test_auth_request_is_on_by_default`: el bloque `server` declara `auth_request /_auth;`.
  - `test_public_locations_are_exactly_the_documented_ones`: el conjunto de rutas cuyo `location` tiene `auth_request off;` es `{/api/auth/ (4 rutas), /api/health, /api/songs/{id}/stream, /api/media/, /}`; la SPA y el 404 JSON de `/api/` cuentan como públicos.
  - `test_public_set_matches_the_services` (**Review Focus 3**): para cada ruta de `public_routes()` cuyo OpenAPI **no** declara `security`, más la del stream, el `location` resuelto tiene `auth_request off;`; para todas las demás, no. Una ruta pública nueva sin tocar `nginx.conf` falla. Si aparece una discrepancia real con el código, resolverla con el builder y anotarla en decisiones.
  - `test_role_map`: `/api/admin/users` → `admin`; `/api/composer/tracks` → `composer,admin`; `/api/composer-requests/mine` → vacío; `/api/playlists` → vacío (se evalúa el `map` con la misma regla de regex que nginx).
  - `test_identity_headers_are_always_set_by_the_gateway` (**Review Focus 2**): todo `location` que hace `proxy_pass`, ya sea porque hereda los `proxy_set_header` del `server` o porque los repite, termina con `X-User-Id $auth_user_id` y `X-User-Role $auth_user_role`; `X-Required-Roles` solo aparece en el bloque `/_auth`.
  - `test_auth_failures_return_json`: `error_page 401` y `403` apuntan a los JSON estáticos, `error_page 500 =503` al de `upstream_unavailable`; los tres archivos son JSON válido con el código y `detail.source == "gateway"` en 401 y 403.
  Run: `cd edge/tests && pytest -q -m "not stack"` → FAIL.

- [ ] **Step 2: Implementar en `edge/nginx.conf`**:
  - `map $uri $required_roles` en `http`: `~^/api/admin/` → `admin`; `~^/api/composer/` → `"composer,admin"`; `default ""`.
  - En `server`: `auth_request /_auth;`, `auth_request_set $auth_user_id $upstream_http_x_user_id;`, `auth_request_set $auth_user_role $upstream_http_x_user_role;`, y `proxy_set_header X-User-Id $auth_user_id;` / `X-User-Role $auth_user_role;` junto a los demás (un valor vacío hace que nginx no envíe la cabecera, lo que descarta la del cliente en las rutas públicas).
  - `location = /_auth { internal; set $upstream http://gateway-auth:8004; proxy_pass $upstream/auth; proxy_pass_request_body off; proxy_set_header Content-Length ""; proxy_set_header Authorization $http_authorization; proxy_set_header X-Required-Roles $required_roles; proxy_connect_timeout 1s; proxy_read_timeout 2s; }`
  - `error_page 401 /errors/unauthorized.json; error_page 403 /errors/forbidden.json; error_page 500 =503 /errors/upstream_unavailable.json;` (mantener el `502 503 504` existente) y sus `location internal` con `alias`.
  - `auth_request off;` en los `location` públicos: `/api/auth/` (solo `register`, `login`, `refresh`, `logout`: separar en locations exactas si `/api/auth/` abarca más rutas), `= /api/health`, el `location` regex del stream, `/api/media/`, el 404 JSON de `/api/` y `/`.
  - En los dos `location` de audio que repiten los `proxy_set_header`, repetir también `X-User-Id` y `X-User-Role`.
  - Crear `edge/errors/unauthorized.json` y `forbidden.json` con el formato de errores de la API.

- [ ] **Step 3: Ejecutar y comprobar que pasan**

Run: `cd edge/tests && pytest -q -m "not stack"`
Expected: PASS, incluidas las pruebas de enrutamiento que ya existían.

- [ ] **Step 4: Verificar nginx con el stack**

Run: `docker compose up -d --build edge && curl -s -o /dev/null -w "%{http_code}\n" localhost:8080/api/songs && curl -s -o /dev/null -w "%{http_code}\n" localhost:8080/api/health`
Expected: `401` y `200`.

- [ ] **Step 5: Commit**

```bash
git add edge
git commit -m "feat: el gateway valida sesión y rol por prefijo antes de enrutar"
```

---

### Task 4: Failover hacia la réplica sana

**Files:**
- Modify: `edge/nginx.conf`, `edge/tests/test_routes.py`

**Interfaces:**
- Consumes: `catalog-streaming` con dos direcciones DNS (Tarea 2).
- Produces: todo `location` que hace `proxy_pass` a `catalog-streaming:8002` reintenta GET/HEAD con la otra dirección.

- [ ] **Step 1: Escribir la prueba que falla** `test_catalog_locations_fail_over` en `edge/tests/test_routes.py`: cada `location` cuyo `owner()` es `catalog-streaming` (heredando del `server` si no lo repite) tiene `proxy_next_upstream error timeout http_502 http_503`, `proxy_next_upstream_tries 2` y `proxy_connect_timeout 1s`; ninguno incluye `non_idempotent`. Run → FAIL.

- [ ] **Step 2: Implementar**: poner `proxy_next_upstream`, `proxy_next_upstream_tries` y `proxy_connect_timeout 1s` en el `server` (los demás servicios solo tienen una dirección, así que no cambia nada para ellos) y repetirlos en los `location` de catálogo que reescriben `proxy_set_header` solo si nginx no los hereda (`proxy_*` sí se hereda: no hace falta repetirlos). Nota para el builder: `proxy_connect_timeout 3s` actual pasa a `1s`.

- [ ] **Step 3: Ejecutar y comprobar**

Run: `cd edge/tests && pytest -q -m "not stack"`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add edge
git commit -m "feat: el gateway reintenta GET y HEAD de catálogo con la réplica sana"
```

---

### Task 5: `playback-metrics` drena la latencia de cada réplica

**Files:**
- Modify: `services/playback-metrics/playback_metrics/clients/catalog.py`, `services/playback-metrics/playback_metrics/latency_pull.py`
- Test: `services/playback-metrics/tests/test_latency_pull.py`, `services/playback-metrics/tests/fake_catalog.py`

**Interfaces:**
- Consumes: `POST /internal/latency/drain` de cada réplica (existente).
- Produces: en `clients/catalog.py`: `async def resolve_replicas() -> list[str]` (direcciones IP que devuelve el DNS para el host de `CATALOG_URL`; si el host ya es una IP o falla la resolución, `[host]`) y `async def drain_latency_all() -> list[dict]` (una llamada a `http://<ip>:<puerto>/internal/latency/drain` por réplica; une las listas; una réplica que falla se omite con un aviso y no pierde las demás). `pull_latency` usa `drain_latency_all` en lugar de `drain_latency`.

- [ ] **Step 1: Escribir las pruebas que fallan** en `test_latency_pull.py` (la resolución se simula con `monkeypatch.setattr(catalog, "resolve_replicas", ...)` y respx atiende `http://10.0.0.1:8002` y `http://10.0.0.2:8002`; extender `FakeCatalog` para registrar esas dos direcciones):
  - `test_pull_latency_drains_every_replica`: dos réplicas con buckets distintos → ambos se guardan en `request_metrics`.
  - `test_one_replica_down_keeps_the_other_buckets` (**Review Focus 4**): la segunda lanza error de red → se guardan los de la primera, sin excepción.
  - `test_single_name_still_works`: `resolve_replicas` devuelve un solo valor y el comportamiento previo se conserva (las pruebas existentes siguen pasando).
  - `test_resolve_replicas_returns_the_literal_ip` y `test_resolve_replicas_falls_back_to_the_host_on_dns_error`.
  Run: `cd services/playback-metrics && pytest tests/test_latency_pull.py -q` → FAIL.

- [ ] **Step 2: Implementar** `resolve_replicas` con `asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)` (ordenado y sin repetidos) y `drain_latency_all` con un `InternalClient` por dirección (reutilizar la forma de `_catalog()`; cerrarlos o cachearlos por dirección).

- [ ] **Step 3: Ejecutar y comprobar que pasan**

Run: `cd services/playback-metrics && pytest -q`
Expected: toda la suite PASS.

- [ ] **Step 4: Commit**

```bash
git add services/playback-metrics
git commit -m "feat: playback-metrics drena la latencia de cada réplica de catálogo"
```

---

### Task 6: Escenario 2 de `/demo` (F2.4)

**Files:**
- Create: `demo/scenario_2_failover.py`
- Modify: `demo/README.md`, `demo/test_common.py` si se agrega un auxiliar a `common.py`

**Interfaces:**
- Consumes: `common.{Api, admin, new_user, check, run, compose, COMPOSE, wait_edge, SERVICE, REPLICAS}`.
- Produces: script ejecutable `python3 demo/scenario_2_failover.py` que imprime `PASA`/`FALLA`.

- [ ] **Step 1: Escribir el escenario** con `run("Escenario 2: cae una réplica de catálogo", scenario)`: crea un oyente; lanza en un hilo una carga de `GET /api/songs` a ~20 peticiones por segundo por el 8080 durante unos 15 s contando códigos; a los 3 s detiene una réplica (`docker stop` del id que da `compose(COMPOSE, "ps", "-q", SERVICE)`); `check` de que `fallidas <= 1`, de que las últimas 50 peticiones dan `200` y de que la otra réplica recibió tráfico; en `finally`, vuelve a `REPLICAS` con `restore_catalog()`. Antes de detener, comprobar que ambas réplicas atienden (los conteos de `docker compose logs --since` por contenedor son mayores que 0), y si no, imprimir `PRECONDICIÓN NO CUMPLIDA` y salir con código 2 como el escenario 3.

- [ ] **Step 2: Ejecutar**

Run: `python3 demo/scenario_2_failover.py`
Expected: `PASA` y `docker compose ps` muestra de nuevo las dos réplicas sanas.

- [ ] **Step 3: Documentar** el escenario en la tabla de `demo/README.md` (quitar la frase «El escenario 2 llega en una rama posterior»; el 2 detiene una réplica y siempre la restaura) y commit:

```bash
git add demo
git commit -m "feat: escenario 2 de failover de catálogo (F2.4)"
```

---

### Task 7: Pruebas con stack del gateway y de F2.4

**Files:**
- Modify: `edge/tests/test_stack.py`

**Interfaces:**
- Consumes: helpers existentes de `test_stack.py` (`raw_get`, `docker`, `wait_healthy`, fixtures `admin_api` y `track`) y `common.{new_user, new_composer}`.
- Produces: pruebas marcadas `stack`.

- [ ] **Step 1: Escribir las pruebas** (todas `pytest.mark.stack`):
  - `test_no_token_is_401_from_the_gateway`: `GET /api/songs` sin token → 401 con `error.detail == {"source": "gateway"}`.
  - `test_listener_gets_403_from_the_gateway_on_admin_and_composer`: oyente en `/api/admin/audit` y en `/api/composer/tracks` → 403 con `detail.source == "gateway"`; un compositor en `/api/admin/audit` también.
  - `test_composer_reaches_composer_routes` y `test_admin_reaches_admin_routes`: pasan el gateway (no 401/403 del gateway).
  - `test_stream_ticket_is_rejected_as_a_session` (**Review Focus 1**): el ticket en `Authorization` a `GET /api/playlists` → 401.
  - `test_fake_identity_headers_do_not_grant_access`: con `X-User-Id` y `X-User-Role: admin` falsos y sin token → 401; con token de oyente → sigue 403 en `/api/admin/audit`.
  - `test_gateway_auth_down_is_503` (**Review Focus 5**): `docker stop` de `gateway-auth`, `GET /api/songs` con token → 503 `upstream_unavailable`; las rutas públicas (`/api/health`, el stream con ticket) siguen respondiendo; `finally`: `docker start` y `wait_healthy`.
  - `test_range_still_works_through_the_gateway`: `bytes=0-1023` da 206 y `Content-Range`.
  - `test_replica_failover_loses_at_most_one_request` (F2.4): ráfaga secuencial de `GET /api/songs`; a mitad se detiene una réplica; fallidas `<= 1`; `finally`: restaurar con `restore_catalog()`.
  - Corregir `METRICS_CONTAINER`/nombres fijos si el escalado cambió los nombres de contenedor (`meloxo-catalog-streaming-1` y `-2`).

- [ ] **Step 2: Ejecutar**

Run: `docker compose up -d --build && pytest edge/tests/test_stack.py -q`
Expected: todas PASS. Si `test_replica_failover_loses_at_most_one_request` mide más de 1 fallo, revisar primero `proxy_connect_timeout` y el `valid=` del `resolver` (Riesgos del diseño) antes de tocar la lógica.

- [ ] **Step 3: Commit**

```bash
git add edge/tests/test_stack.py
git commit -m "test: pruebas del gateway y del failover con el stack levantado"
```

---

### Task 8: Verificación completa, carga y documentación

**Files:**
- Create: `docs/decisions/03-gateway-balanceo.md`
- Modify: `README.md`, `edge/README.md`, `services/README.md`, `demo/README.md`, `docs/decisions/README.md`, `docs/plans/README.md`, `docs/specs/README.md` (ya tiene su fila), `CHANGELOG.md`, `compose` o `.env.example` si existe y falta alguna variable

- [ ] **Step 1: Suites completas**

Run: `for d in services/common services/users-playlists services/catalog-streaming services/playback-metrics services/gateway-auth; do (cd $d && pytest -q) || break; done; pytest edge/tests -q; (cd frontend && npm test -- --run)`
Expected: todo PASS.

- [ ] **Step 2: Escenarios 1 a 8**

Run: `for f in demo/scenario_*.py; do python3 "$f"; echo "$f -> código $?"; done`
Expected: `PASA` en todos, salvo el 3 que puede dar código 2 sin llave de Jamendo (se anota igual que en `02`). Los escenarios 7 y 8 deben dar los mismos códigos de antes, ahora con el gateway delante y las dos réplicas reales.

- [ ] **Step 3: Carga (F2.3)**: repetir la prueba de 50 clientes de `demo/locustfile.py` como se describe en `demo/README.md` y anotar primer byte p95 y `GET /api/songs` p95, con cuánto suma el salto de `auth_request`. Si pasa de los umbrales, aplicar el primer ajuste del diseño (caché de 30 s de `gateway-auth`) y volver a medir; la caché en nginx solo si no basta y anotando el costo en la ventana de suspensión.

- [ ] **Step 4: Documentar**: `docs/decisions/03-gateway-balanceo.md` con el formato de `02-separacion.md` (avisos al equipo, decisiones por tarea con su costo si fueron un error, pendientes menores): mínimo las dos diferencias con el PRD (revocación a la rama 04, control de salud pasivo), la resolución de `DATABASE_URL` en `gateway-auth`, los resultados de F2.3 y F2.4, y cualquier discrepancia que haya salido de `test_public_set_matches_the_services`. En `README.md`: nueva arquitectura (gateway-auth, réplicas), tabla de criterios con F2.4 «Cumple» enlazando a `scenario_2_failover.py` y `test_stack.py`, y «Lo que sigue» sin la rama 03. `edge/README.md`: cómo funciona `auth_request`, el mapa de roles, las rutas públicas y el failover. `CHANGELOG.md` y los índices de `docs/`.

- [ ] **Step 5: Verificar enlaces y rutas de la documentación** con la skill `repo-docs` (comprobar cada dato contra el código) y commit:

```bash
git add -A
git commit -m "docs: README, decisiones y CHANGELOG de 03-gateway-balanceo"
```

---

## Autorrevisión

- **Cobertura del diseño:** objetivos 1-3 (Tareas 1 y 3), 4 (Tareas 2 y 4), 5 (Tareas 6 y 7), 6 (el navegador no cambia: Tareas 3 y 8, paso 2), 7 (Tarea 8). Decisiones del constructor: validador y cabeceras (Tareas 1 y 3), rutas sin sesión (Tarea 3), estado de cuenta 30 s (Tarea 1), caída del validador (Tareas 3 y 7), réplicas (Tarea 2), reparto y failover (Tarea 4), streaming con `Range` (Tarea 7), métricas de latencia (Tarea 5), importación y publicaciones programadas (sin cambios; los comprueban el escenario 8 y la suite de catálogo en la Tarea 8), escenario 2 (Tarea 6). Riesgos del diseño: latencia (Tarea 8, paso 3), reintento en vuelo (Tarea 7, paso 2).
- **Consistencia de nombres:** `gateway-auth`/`gateway_auth`, puerto 8004, `REPLICAS`, `resolve_replicas`, `drain_latency_all`, `$required_roles`, `$auth_user_id`, `$auth_user_role` se usan igual en todas las tareas.
- **Fuera de este plan por decisión del diseño:** Redis, lista de revocación, circuit breaker, sondeo activo de salud.
