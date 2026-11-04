# 04-resiliencia Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Timeouts, un reintento en otra réplica, circuit breaker hecho a mano, degradación con copias en favoritas e historial, y estado de los circuitos en la Cabina.

**Architecture:**
- `app/shared/circuit.py` (copia en `users-playlists` y `playback-metrics`) implementa el circuito.
- `app/clients/http.py` lo envuelve junto con el timeout y el reintento.
- Favoritas y eventos de reproducción guardan copias de la canción y responden `degraded` cuando el cliente levanta `RemoteUnavailable`.
- El gateway reintenta en otra instancia si no pudo conectar.
- La UI agrega el estado "Sin actualizar" y la tarjeta `EstadoCircuitos`.

**Tech Stack:** Python 3.12, FastAPI, httpx, SQLAlchemy async, Alembic, Vue 3 + Vitest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-11-03-04-resiliencia-design.md`

## Global Constraints

- Sin dependencias nuevas, ni Python ni npm.
- Variables y valores por omisión:

  | Variable | Valor | Dónde |
  |---|---|---|
  | `FLDSMDFR_CALL_TIMEOUT_S` | `1.5` | clientes |
  | `FLDSMDFR_RETRIES` | `1` | clientes y gateway |
  | `FLDSMDFR_CB_FAILURES` | `5` | clientes |
  | `FLDSMDFR_CB_OPEN_S` | `10` | clientes |
  | `FLDSMDFR_UPSTREAM_CONNECT_S` | `1.5` | gateway |
  | `FLDSMDFR_UPSTREAM_READ_S` | `30` | gateway |

- Espera antes del reintento: aleatoria entre 100 y 300 ms.
- Estados del circuito en la API: `closed` | `open` | `half_open`. En la UI: "Cerrado", "Abierto", "Semiabierto".
- Línea de log en cada transición: `circuito <source>→<target>: <antes> → <después> (<motivo>)`. Los estados van en español: cerrado, abierto, semiabierto.
- Rutas públicas existentes sin cambios. Rutas nuevas:
  - `GET /api/admin/circuits` (`users-playlists`);
  - `GET /api/metrics/circuits` (`playback-metrics`).
- Un `4xx` remoto no se reintenta ni cuenta para el circuito. Un `404` → `NotFound`; otro `4xx` → `503`, como hoy.
- Texto de UI: "Sin actualizar", "Canción no disponible" y "Sin datos de <servicio>". Aviso de lista degradada: "El catálogo no responde; mostramos los últimos datos guardados."

## Review Focus

1. **Semiabierto bajo concurrencia:** dos peticiones simultáneas con el circuito vencido. Solo una llega al servicio y la otra recibe `503` al instante → `test_half_open_allows_single_probe` (Task 1).
2. **Un `POST` o una subida en el gateway con la primera instancia muerta:** jamás se reintenta, y el cuerpo no se consume dos veces → `test_post_not_retried_on_connect_error` (Task 3).
3. **Lectura degradada que intenta escribir la copia y falla el commit:** la respuesta sigue siendo `200` → `test_snapshot_write_failure_still_200` (Task 2).
4. **Panel con un servicio caído:** la tarjeta muestra "Sin datos de playback-metrics" y la otra mitad sigue refrescándose → `EstadoCircuitos.spec.ts` "una mitad falla" (Task 4).
5. **Respuesta lenta pero válida (2–5 s) por el gateway:** no se corta, porque el límite de 1.5 s es solo para conectar → `test_slow_response_not_cut` (Task 3).

---

### Task 1: Circuito, timeout y reintento en los clientes

**Files:**
- Create: `services/users-playlists/app/shared/circuit.py` y una copia idéntica en `services/playback-metrics/app/shared/circuit.py`.
- Create: `tests/test_circuit.py` y `tests/test_client_resilience.py` en ambos servicios.
- Modify: `app/clients/http.py` y `app/config.py` en ambos servicios.

**Interfaces — Produces:**
- `CircuitOpen(Exception)`.
- `CircuitBreaker(source, target, failures, open_s, clock=time.monotonic)` con `before_call()`, `record_success()`, `record_failure()`, `snapshot() -> dict`, `state`.
  - `snapshot()` devuelve las claves `source`, `target`, `state`, `consecutive_failures`, `since` (ISO 8601 UTC) y `retry_in_s` (`float | None`).
- En `http.py`:
  - `breakers() -> list[CircuitBreaker]`;
  - `reset_breakers()`;
  - `call(service, method, path, **kwargs)` con la misma firma que hoy.
- `source` = `settings.service_name`.

- [ ] **Step 1: Tests fallando**, con un reloj falso (`clock=lambda: now[0]`):
  - `test_circuit.py`:
    - `test_opens_after_threshold`: 5 × `record_failure()` → `state == "open"`.
    - `test_success_resets_count`: 4 fallas, 1 éxito y 4 fallas → sigue `closed`.
    - `test_open_rejects`: `before_call()` levanta `CircuitOpen`.
    - `test_half_open_after_open_s`: avanzar el reloj 10 s → `state == "half_open"`.
    - `test_half_open_allows_single_probe`: el primer `before_call()` pasa y el segundo levanta `CircuitOpen`.
    - `test_probe_success_closes`.
    - `test_probe_failure_reopens`: `retry_in_s == 10`.
    - `test_snapshot_fields`.
    - `test_transition_logged`: con `caplog`, la línea `circuito users-playlists→catalog-streaming: cerrado → abierto (5 fallas seguidas)`.
  - `test_client_resilience.py`, con `FakeConsul` y dos instancias en `set_network_transport`:
    - `test_timeout_retries_other_instance`: la primera instancia duerme más que el timeout → la respuesta llega de la segunda.
    - `test_5xx_retried_and_counted_once`.
    - `test_4xx_not_retried_not_counted`.
    - `test_open_circuit_does_not_call`: un contador en el remoto falso queda igual.
    - `test_no_instances_counts_as_failure`.
- [ ] **Step 2:** `docker compose --profile test run --rm tests-users pytest -q tests/test_circuit.py tests/test_client_resilience.py` → FAIL (`ModuleNotFoundError: app.shared.circuit`). Igual en `tests-playback`.
- [ ] **Step 3: Implementar.**
  - El estado semiabierto guarda una bandera de "prueba en curso".
  - `call`: `before_call` → intento con `httpx.Timeout(settings.call_timeout_s)` → si falla de forma reintentable y quedan reintentos, otra instancia distinta, elegida entre las de `discovery.instances()` excluyendo la usada; si no hay otra, la misma → `record_success` / `record_failure` una sola vez.
  - `CircuitOpen` → `RemoteUnavailable(service)`.
  - Las pruebas existentes de clientes llaman a `reset_breakers()` en su fixture.
- [ ] **Step 4:** Suites completas de `tests-users` y `tests-playback` → PASS. Ruff limpio.
- [ ] **Step 5: Commit** `feat: circuit breaker, timeout y reintento en los clientes internos`

### Task 2: Copias, degradación y endpoints de circuitos

**Files:**
- `users-playlists`:
  - migración `0011_favorite_snapshots.py`;
  - `modules/social/{models,repository,service,schemas,router}.py`;
  - `modules/users/router.py` o un `admin_router.py` nuevo para `/api/admin/circuits`;
  - pruebas `tests/test_favorites_degraded.py` y `tests/test_circuits_endpoint.py`.
- `playback-metrics`:
  - migración `0012_playback_snapshots.py`;
  - `modules/playback/{models,repository,service,schemas,router}.py`;
  - pruebas `tests/test_history_degraded.py`, `tests/test_summary_degraded.py` y `tests/test_circuits_endpoint.py`.

**Interfaces:**
- **Consumes:** Task 1 (`http.breakers()`, `RemoteUnavailable`).
- **Produces** (contratos del spec, Meta 4–5 y 7):
  - `FavoriteSongOut.status: ok|degraded|unavailable`, `FavoritesOut.degraded: bool`;
  - `HistoryItemOut.status`, `HistoryPage.degraded`;
  - `MetricsSummary.total_songs: int | None`, `total_users: int | None`, `degraded: bool`;
  - `CircuitsOut {instance: str, circuits: list[CircuitOut]}`.

- [ ] **Step 1: Tests fallando.**
  - `test_like_stores_snapshot`.
  - `test_favorites_degraded_uses_snapshot`: `catalog_down` → `200`, `status == "degraded"`, `degraded is True` y el título copiado.
  - `test_old_row_without_snapshot`: "Canción no disponible", artista `""`, duración 0.
  - `test_read_refreshes_snapshot`: el catálogo cambia el título → la fila queda actualizada.
  - `test_snapshot_write_failure_still_200`.
  - `test_total_seconds_includes_degraded`.
  - Equivalentes para el historial:
    - `test_history_degraded_nested_song_defaults`: `is_active false`, `has_cover false`, `created_at == last_played_at`, `size_bytes 0`, `mime_type ""`, `available false`.
    - `test_history_omits_missing_when_catalog_up`.
  - `test_summary_users_down_null`.
  - `test_summary_catalog_down_null`.
  - `test_circuits_listener_403`, `test_circuits_admin_shape` y `test_circuits_anonymous_401`, en ambos servicios.
- [ ] **Step 2:** Correr las pruebas nuevas → FAIL (columnas, campos y rutas inexistentes).
- [ ] **Step 3: Implementar.**
  - Columnas opcionales `title_snapshot`, `artist_snapshot`, `album_snapshot` y `duration_snapshot`.
  - Las escrituras guardan la copia que devuelve `catalog.get_song`.
  - Las lecturas capturan `RemoteUnavailable` y arman la respuesta desde las copias.
  - La copia que se refresca al leer va en un `commit` explícito dentro de `try`, con `logger.warning` si falla.
- [ ] **Step 4:** Suites completas → PASS. Ruff limpio. `alembic upgrade head` en la base `_test` lo hace el conftest existente.
- [ ] **Step 5: Commit** `feat: copias en favoritas e historial, resumen degradado y estado de circuitos`

### Task 3: Gateway, límites y reintento si no conecta

**Files:** `services/gateway/app/{config,proxy}.py`, `services/gateway/tests/test_gateway_resilience.py`.

**Interfaces:**
- **Consumes:** —.
- **Produces:** `proxy.forward` con la misma firma que hoy.

- [ ] **Step 1: Tests fallando.**
  - `test_get_retried_on_connect_error`: dos instancias, la primera ausente en `Network` → `200` desde la segunda.
  - `test_post_not_retried_on_connect_error` → `503`, y la segunda instancia no recibe nada.
  - `test_5xx_not_retried`: el remoto devuelve `500` → `500`, una sola llamada.
  - `test_connect_timeout_retried`: un transporte que levanta `httpx.ConnectTimeout`.
  - `test_slow_response_not_cut`: el remoto tarda 2 s con `UPSTREAM_CONNECT_S=1.5` → `200`.
  - `test_client_timeouts_configured`: `proxy._http().timeout` tiene `connect == 1.5`, `read == 30` y `write == 30`.
- [ ] **Step 2:** `docker compose --profile test run --rm tests-gateway pytest -q tests/test_gateway_resilience.py` → FAIL.
- [ ] **Step 3: Implementar.**
  - `httpx.Timeout(connect=…, read=…, write=…, pool=5)`.
  - Ante `ConnectError` o `ConnectTimeout` en `GET` o `HEAD`, otra instancia distinta tras la espera aleatoria. Cualquier otro error → `Unavailable` como hoy.
- [ ] **Step 4:** Suite del gateway → PASS. Ruff limpio.
- [ ] **Step 5: Commit** `feat(gateway): límite de conexión y reintento en otra réplica si no conecta`

### Task 4: UI, estado "Sin actualizar", avisos y tarjeta de circuitos

**Files:**
- Create: `ui/src/components/EstadoCircuitos.vue` y `ui/src/components/__tests__/EstadoCircuitos.spec.ts`.
- Modify:
  - `ui/src/api/{types,metrics,users}.ts`, con `circuitosUsuarios()` y `circuitosMetricas()`;
  - `ui/src/composables/canciones.ts`;
  - `ui/src/components/FilaCancion.vue`;
  - `ui/src/views/{FavoritasView,HistorialView,InicioView,CaseteView,CabinaView}.vue`;
  - `ui/src/components/ResumenMetricas.vue`;
  - `DESIGN.md` §7: estado "Sin actualizar" y tarjeta "Resiliencia".

**Interfaces:**
- **Consumes:** los contratos de Task 2.
- **Produces:** `FilaCancion` con la prop `estado?: 'ok' | 'degraded' | 'unavailable'`. Reemplaza el uso de `disponible`, que se conserva derivado para no romper a quien lo usa.

- [ ] **Step 1: Tests fallando (Vitest).**
  - `FilaCancion` con `estado="degraded"`: muestra "Sin actualizar", el botón está deshabilitado y tiene la clase `fila--sin-actualizar`.
  - `FavoritasView` y `HistorialView` con `degraded: true`: muestran el aviso con el texto de Global Constraints.
  - `CaseteView`: una fila `degraded` ya no se puede reproducir.
  - `ResumenMetricas` con `total_users: null` → "—" y "sin datos".
  - `EstadoCircuitos`:
    - muestra los tres estados en español y "vuelve a probar en 7 s";
    - "una mitad falla" → "Sin datos de playback-metrics" y la otra mitad presente;
    - el refresco cada 2 s usa temporizadores falsos y se detiene en `unmount` y con `document.hidden`.
- [ ] **Step 2:** `cd ui && npm test` → FAIL.
- [ ] **Step 3: Implementar** según el spec, Metas 7–8 y `DESIGN.md`. El indicador de estado no puede depender solo del color: lleva texto e icono.
- [ ] **Step 4:** `cd ui && npm test && npm run build` → PASS. La salida de cada comando se lee por separado.
- [ ] **Step 5: Commit** `feat(ui): estado sin actualizar, avisos degradados y circuitos en la Cabina`

### Task 5: Compose, demo, verificación en vivo y documentación

**Files:**
- `docker-compose.yml`: las variables nuevas en `x-directorio` o en un ancla `x-resiliencia`.
- `scripts/demo-04.sh`.
- `README.md`, `docs/PRD.md` (§6, §7, §9 y "por qué no hay saga"), `AGENTS.md` (regla de resiliencia) y `services/README.md`.

- [ ] **Step 1:** `docker compose up --build -d` → todos `healthy` y `catalog-init` con `Exited (0)`.
- [ ] **Step 2: `demo-04.sh`.**
  1. Nueve `GET /api/songs` con tiempos.
  2. `docker kill` de una réplica, seguido de 15 s de consultas → **ningún `503`** y ninguna mayor a 2 s.
  3. `docker compose stop catalog-streaming` (las tres) y luego:
     - consultas a favoritas → `200` con `degraded`;
     - el endpoint de circuitos pasa a `open`, y después de abierto las respuestas tardan menos de 100 ms;
     - las transiciones tomadas de `docker logs fldsmdfr-users-playlists-1`.
  4. `docker compose start catalog-streaming` → `half_open` → `closed`.

  Correr la demo y guardar la salida real.
- [ ] **Step 3: Verificación en la UI** con la Cabina abierta durante el paso 3: la tarjeta cambia de estado, y favoritas e historial muestran "Sin actualizar" y el aviso.
- [ ] **Step 4: Documentación**, con la salida real en el README.
- [ ] **Step 5: Commit** `docs: README, PRD y demo de 04`
