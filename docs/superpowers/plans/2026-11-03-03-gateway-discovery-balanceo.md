# 03-gateway-discovery-balanceo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Directorio Consul con registro por latido, gateway propio con round-robin, tres réplicas del catálogo y balanceo del lado del cliente.

**Architecture:** Cada servicio Python lleva `app/shared/discovery.py` (registro TTL, latido, baja, consulta con caché, `RoundRobin`) y lo arranca en el `lifespan` de FastAPI. Los clientes de `app/clients/` resuelven por nombre lógico con ese módulo. `services/gateway/` es un FastAPI que reenvía en streaming a la instancia elegida. `web` queda solo con el SPA.

**Tech Stack:** Python 3.12, FastAPI, httpx, Consul 1.20 (`agent -dev`), Nginx, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-11-03-03-gateway-discovery-balanceo-design.md`

## Global Constraints

- Sin dependencias Python nuevas; imagen nueva solo `hashicorp/consul:1.20`.
- Variables: `FLDSMDFR_CONSUL_URL=http://discovery:8500`, `FLDSMDFR_SERVICE_NAME`, `FLDSMDFR_SERVICE_PORT=8000`, `FLDSMDFR_HEARTBEAT_S=3`, `FLDSMDFR_TTL_S=10`, `FLDSMDFR_DEREGISTER_AFTER=1m`, `FLDSMDFR_LB_CACHE_S=5`, `FLDSMDFR_DISCOVERY_ENABLED` (`true` en compose, `false` en pruebas).
- Id de instancia: `<servicio>-<hostname>`; cabecera `X-Instancia` con ese id; el gateway agrega `X-Gateway-Instancia`.
- Puertos publicados: solo `8000` (gateway) y `8500` (panel de Consul).
- Sin reintentos ni circuit breaker; errores remotos como en `02` (`503 service_unavailable`).
- Rutas públicas y respuestas de error idénticas a `02`.

## Review Focus

1. Varias cabeceras `Set-Cookie` y el `Content-Length`/`Transfer-Encoding` del audio a través del gateway → `test_multiple_set_cookie_preserved`, `test_range_passthrough_206` (Task 3).
2. Cliente que corta la descarga del audio a la mitad: el gateway debe cerrar la respuesta upstream sin fugar conexiones → cierre en `BackgroundTask`, revisión en vivo (Task 4).
3. Consul apagado al arrancar un servicio: el servicio arranca igual y reintenta registrarse en cada latido → `test_register_retries_when_directory_down` (Task 1).
4. Réplica muerta con caché vigente: la petición falla con `503` JSON, no 500 → `test_connect_error_503` (Task 3) y demo (Task 5).
5. Semilla de `users-playlists` con réplicas registradas → verificación en vivo del casete demo (Task 4).

---

### Task 1: Módulo de directorio en `catalog-streaming`

**Files:**
- Create: `services/catalog-streaming/app/shared/discovery.py`, `services/catalog-streaming/tests/fake_consul.py`, `services/catalog-streaming/tests/test_discovery.py`
- Modify: `services/catalog-streaming/app/config.py` (variables), `app/main.py` (`lifespan` + middleware `X-Instancia`), `scripts/entrypoint.sh` (solo arranca; migrar y sembrar pasan a `scripts/init.sh`)

**Interfaces — Produces:** las del spec (`register`, `deregister`, `instances`, `instance_id`, `RoundRobin.pick`, `NoInstances`) y `set_consul_transport(t)` para pruebas.

- [ ] **Step 1: Tests fallando** con un Consul falso (`FakeConsul`, FastAPI en memoria con `/v1/agent/service/register`, `/v1/agent/check/pass/{id}`, `/v1/agent/service/deregister/{id}`, `/v1/health/service/{name}`):
  `test_register_sends_ttl_check` (Name, ID `catalog-streaming-<host>`, `Check.TTL == "10s"`, `DeregisterCriticalServiceAfter == "1m"`), `test_heartbeat_passes_check`, `test_deregister_removes_instance`, `test_instances_only_passing_and_cached`, `test_round_robin_cycles`, `test_no_instances_raises`, `test_register_retries_when_directory_down`, `test_responses_carry_x_instancia`.
- [ ] **Step 2:** `docker compose --profile test run --rm tests-catalog pytest -q tests/test_discovery.py` → FAIL (módulo inexistente).
- [ ] **Step 3:** Implementar; el latido reintenta registrar si el `pass` devuelve 404 o falla la conexión.
- [ ] **Step 4:** Suite completa de catálogo → PASS; ruff limpio.
- [ ] **Step 5: Commit** `feat(catalog-streaming): registro con latido en Consul y X-Instancia`

### Task 2: Directorio y balanceo de cliente en `users-playlists` y `playback-metrics`

**Files:** copiar `discovery.py` y su prueba; modificar `config.py`, `main.py`, `app/clients/{http,catalog,users}.py`, `tests/conftest.py`, pruebas de clientes.

**Interfaces:**
- Consumes: Task 1.
- Produces: `http.call(service: str, method: str, path: str, **kwargs) -> httpx.Response`; `http.set_transport(service: str, transport | None)`.

- [ ] **Step 1: Tests fallando** `test_client_balances_between_instances` (dos instancias falsas registradas en `FakeConsul`, cuatro llamadas → dos y dos por `X-Instancia`) y `test_no_instances_is_503` en ambos servicios.
- [ ] **Step 2:** Implementar; `catalog_url`/`users_url` desaparecen de la configuración.
- [ ] **Step 3:** Suites `tests-users` y `tests-playback` → PASS; ruff limpio.
- [ ] **Step 4: Commit** `feat: clientes internos por nombre lógico con round-robin`

### Task 3: `services/gateway`

**Files:** `services/gateway/{Dockerfile,pyproject.toml}`, `app/{main,config,routes,proxy}.py`, `app/shared/{discovery,errors}.py`, `tests/`.

**Interfaces:** `routes.service_for(path: str) -> str | None` (`None` = `/internal` bloqueado), tabla del spec; `/api/health` propio.

- [ ] **Step 1: Tests fallando** (los diez del spec) con `FakeConsul` y servicios falsos ASGI.
- [ ] **Step 2:** Implementar proxy en streaming (`client.build_request(..., content=request.stream())`, `send(stream=True)`, `StreamingResponse` con cierre en `BackgroundTask`); quitar cabeceras hop-by-hop; límite 21 MB por `Content-Length`.
- [ ] **Step 3:** `docker compose --profile test run --rm tests-gateway` → PASS; ruff limpio.
- [ ] **Step 4: Commit** `feat(gateway): gateway propio con round-robin sobre Consul`

### Task 4: Compose, `web` solo SPA y verificación en vivo

**Files:** `docker-compose.yml` (`discovery`, `catalog-init`, `catalog-streaming` ×3, `gateway`, `tests-gateway`, variables), `web/nginx.conf`, `web/Dockerfile` (registro: script `web/register.sh` con `curl` en bucle).

- [ ] **Step 1:** `docker compose up --build -d` → `catalog-init` sale con 0 y los demás `healthy`.
- [ ] **Step 2: Verificar:** `curl localhost:8500/v1/health/service/catalog-streaming?passing=true` → 3; nueve `GET /api/songs` → tres valores distintos de `X-Instancia`; Range `206`; `/internal` `404`; subida 19 MB `201`; casete demo con 3 canciones; UI responde en `/`.
- [ ] **Step 3:** `cd ui && npm test && npm run build` → PASS.
- [ ] **Step 4: Commit** `feat: Consul, gateway y tres réplicas del catálogo en compose`

### Task 5: Demo y documentación

**Files:** `scripts/demo-03.sh`, `README.md`, `docs/PRD.md`, `AGENTS.md`, `services/README.md`.

- [ ] **Step 1:** `demo-03.sh`: lista instancias, 9 consultas con `X-Instancia`, `docker kill` de una réplica y consultas cada segundo con código HTTP hasta 20 s, luego `docker start`; después `docker stop` y la baja inmediata. Correrlo y guardar la salida real en el README.
- [ ] **Step 2:** README (qué cambió desde `02`, diagrama, tiempos, demo, qué queda fuera), PRD §6–§10, AGENTS (regla de directorio).
- [ ] **Step 3: Commit** `docs: README, PRD y demo de 03`
