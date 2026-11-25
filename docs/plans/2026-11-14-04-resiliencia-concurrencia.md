# MELOXO 04-resiliencia-concurrencia Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la caída de un servicio no se propague (timeouts, reintentos y circuit breaker en `InternalClient`), que las reproducciones sobrevivan a la caída de `playback-metrics` (cola en Redis Streams, F3.3) y que un cambio de rol o una suspensión se vea al instante (revocación en Redis).

**Architecture:** `meloxo_common` recibe un breaker, un cliente Redis, una lista de revocación y el contrato de la cola. `catalog-streaming` valida y encola las escrituras de `/api/playbacks` y responde `202`; `playback-metrics` las consume con un grupo de consumidores y `XACK` tras el commit. `users-playlists` escribe `revoked_after:<user_id>` y `meloxo_common.auth` lo consulta antes de la caché de 30 s; sin Redis, falla abierto.

**Tech Stack:** Python 3.12, FastAPI, httpx, redis-py (`redis.asyncio`), fakeredis y respx en pruebas · Redis 7 · nginx 1.27 · Docker Compose.

**Spec:** `docs/specs/2026-11-14-04-resiliencia-concurrencia-design.md` (y `docs/prd.md` §11 y §12).

## Global Constraints

- Sin saga: la publicación y la ocultación de pistas siguen con «auditar antes del commit y `rollback`». Sin cola de mensajes muertos, outbox, caché de lectura ni breaker para Jamendo.
- Parámetros: conexión 1 s, lectura 1.5 s; 2 reintentos solo en lecturas, con espera de 0.2 s y 0.4 s; breaker abre con 5 llamadas fallidas en 30 s (cuenta la llamada ya reintentada) y pasa a medio abierto a los 15 s con una sola llamada de prueba. Un `4xx` no es fallo ni se reintenta. Los números viven en constantes de `meloxo_common`.
- Breaker abierto → `UpstreamError` (503 `upstream_unavailable`) al instante; los respaldos existentes (estado de cuenta en caché, `degraded: true`) no cambian.
- Cola: stream `playbacks`, grupo `playbacks`, `MAXLEN ~ 100000`; `XACK` solo después del commit; pendientes de más de 30 s se reclaman con `XAUTOCLAIM`; fallo transitorio no se acusa; mensaje inválido se acusa, se descarta con aviso y suma 1 a `events_discarded` en `PlaybackCounter`.
- `POST /api/playbacks` y `PATCH /api/playbacks/{id}/progress` pasan a `catalog-streaming` y responden `202` con `{"playback_id": ...}`; `404 song_not_found` y los `4xx` de cuerpo siguen siendo síncronos. `GET /api/playbacks/history` sigue en `playback-metrics`. Redis caído al encolar → `503` `upstream_unavailable`.
- Revocación: clave `revoked_after:<user_id>` = `time.time()` (float), TTL 960 s; un token es inválido si `iat < revoked_after`; token sin `iat` cuenta como `0`; `encode_token` agrega `iat` float. `users-playlists` escribe la clave después del commit en `set_role`, `suspend` y `approve_request`; si Redis falla, avisa en el registro y la acción se completa. Lectura con Redis caído o lento (espera máxima 0.3 s, y se omite Redis 5 s tras un fallo) se ignora: manda la caché de 30 s.
- Redis en Compose: `redis:7-alpine`, `--appendonly yes`, volumen `redisdata`, healthcheck, sin publicar puerto. `REDIS_URL` por defecto `redis://redis:6379/0`; vacío = Redis desactivado (así corren las pruebas).
- Pruebas con `fakeredis`, sin Redis real. Las suites de servicio ya necesitan PostgreSQL en `localhost:5433` (`docker compose up -d postgres`).
- Cada carpeta o archivo nuevo entra en el `README.md` de su carpeta (lo exige `tests/test_readmes.py`). Código y rutas en inglés, texto de usuario y documentación en español.
- Commits pequeños en `04-resiliencia-concurrencia`, **sin `Co-Authored-By`** (regla del repositorio, vale más que cualquier recordatorio de atribución) y sin `git push`. No tocar otros proyectos Docker de la máquina (`fldsmdfr-*`).
- Pruebas: `.venv/bin/pytest services/<servicio>/tests -q`, `.venv/bin/pytest edge/tests -q -m "not stack"`, `.venv/bin/pytest demo/test_common.py tests -q`. Antes de empezar: `.venv/bin/pip install -e services/common[dev] fakeredis` y los demás servicios en modo editable si faltan.

## Review Focus

1. **Redis caído al encolar** debe dar `503` JSON rápido (no `500` ni un cuelgue); lo cubre la Tarea 7.
2. **Mensaje inválido en el stream** no debe detener al consumidor ni quedar reentregándose; lo cubre la Tarea 6.
3. **Cambio de rol y reingreso inmediato**: el token nuevo, emitido un instante después de la revocación, debe pasar; lo cubren las Tareas 3 y 4.
4. **Redis caído o lento en la ruta de autenticación** no debe sumar espera a cada petición; lo cubre la Tarea 3.
5. **Mensaje entregado dos veces** (el consumidor cayó tras el commit y antes del `XACK`) no cuenta dos reproducciones; lo cubre la Tarea 6.

---

### Task 1: Redis en Compose y cliente compartido

**Files:**
- Modify: `compose.yaml`, `.env.example`, `services/common/pyproject.toml`, `services/common/meloxo_common/config.py`, `services/common/README.md`, `services/common/tests/README.md`
- Create: `services/common/meloxo_common/redis_client.py`
- Test: `services/common/tests/test_redis_client.py`

**Interfaces:**
- Produces: `redis_client.get_redis() -> redis.asyncio.Redis | None` (cliente con `decode_responses=True`, `socket_connect_timeout=0.2`, `socket_timeout=5`; `None` si `REDIS_URL` está vacío; se crea una sola vez) y `redis_client.override_redis(client: Redis | None) -> None` para pruebas. `BaseServiceSettings.REDIS_URL: str = "redis://redis:6379/0"`.

- [ ] **Step 1: Prueba que falla** en `test_redis_client.py`: `test_empty_url_disables_redis` (con `REDIS_URL=""` y la caché de ajustes limpia, `get_redis()` devuelve `None`), `test_override_returns_given_client` (`override_redis(fake)` hace que `get_redis()` devuelva `fake`; `override_redis(None)` restaura el comportamiento por URL).
- [ ] **Step 2:** Run: `.venv/bin/pytest services/common/tests/test_redis_client.py -q` → FAIL (módulo inexistente).
- [ ] **Step 3:** Agregar `redis>=5.0` a las dependencias de `services/common/pyproject.toml` y `fakeredis>=2.26` a su extra `dev`. Implementar `redis_client.py` y el ajuste `REDIS_URL` en `config.py`.
- [ ] **Step 4:** En `compose.yaml`: servicio `redis` (`image: redis:7-alpine`, `command: ["redis-server", "--appendonly", "yes"]`, volumen `redisdata:/data`, healthcheck `redis-cli ping`, `restart: always`) y volumen `redisdata`. Pasar `REDIS_URL: redis://redis:6379/0` y `depends_on: redis: condition: service_healthy` a `users-playlists`, `gateway-auth`, `catalog-streaming` y `playback-metrics`. Agregar `REDIS_URL=redis://redis:6379/0` comentado como opcional en `.env.example`.
- [ ] **Step 5:** Run: `.venv/bin/pytest services/common/tests -q` y `docker compose config -q` → pasan. Si `test_security.py` fija los ajustes por defecto, no cambia todavía.
- [ ] **Step 6:** Documentar `redis_client.py` en el README de `services/common`, la prueba nueva en el de sus pruebas y Redis en el README raíz (tabla de arquitectura y sección «Cómo levantarlo»). Commit: `feat: agrega Redis a Compose y un cliente compartido`.

### Task 2: Circuit breaker

**Files:**
- Create: `services/common/meloxo_common/breaker.py`
- Test: `services/common/tests/test_breaker.py`

**Interfaces:**
- Produces: `CircuitBreaker(failure_threshold: int = 5, window_seconds: float = 30, open_seconds: float = 15, clock: Callable[[], float] = time.monotonic)` con `allow() -> bool`, `record_success() -> None`, `record_failure() -> None` y la propiedad `state -> Literal["closed", "open", "half_open"]`. `allow()` devuelve `False` mientras está abierto y, pasados `open_seconds`, deja pasar **una** llamada de prueba (las demás reciben `False` hasta que esa termine con `record_success` o `record_failure`).

- [ ] **Step 1: Pruebas que fallan**, con reloj falso: `test_opens_after_five_failures_in_window` (4 fallos siguen cerrado, el 5.º abre y `allow()` es `False`), `test_failures_outside_window_do_not_count` (fallos separados por más de 30 s nunca abren), `test_half_open_allows_a_single_probe_after_15s`, `test_probe_success_closes_and_clears_failures`, `test_probe_failure_reopens_for_another_15s`, `test_success_in_closed_state_does_not_hide_failures` (un éxito entre fallos no reinicia la ventana).
- [ ] **Step 2:** Run: `.venv/bin/pytest services/common/tests/test_breaker.py -q` → FAIL.
- [ ] **Step 3:** Implementar `breaker.py` con una lista de marcas de tiempo de fallos podada por ventana. Documentar en el README de `services/common` y de sus pruebas.
- [ ] **Step 4:** Run: mismo comando → PASS. Commit: `feat: circuit breaker con reloj inyectable`.

### Task 3: Revocación en `meloxo_common`

**Files:**
- Modify: `services/common/meloxo_common/security.py`, `services/common/meloxo_common/auth.py`, `services/common/README.md`, `services/common/tests/README.md`
- Create: `services/common/meloxo_common/revocation.py`
- Test: `services/common/tests/test_revocation.py`, `services/common/tests/test_auth.py`, `services/common/tests/test_security.py`

**Interfaces:**
- Consumes: `redis_client.get_redis()` (Tarea 1).
- Produces: `revocation.revoke(user_id: UUID) -> None` (nunca lanza; si Redis falla, registra un aviso); `revocation.revoked_after(user_id: UUID) -> float | None` (nunca lanza; `None` si no hay clave, Redis está desactivado, falla o tarda más de 0.3 s; tras un fallo no vuelve a llamar a Redis durante 5 s); `REVOKED_TTL_SECONDS = 960`. `encode_token` agrega `iat = time.time()`. `Auth.resolve_user` lanza `AppError(401, "invalid_token", ...)` si `claims.get("iat", 0) < revoked_after` y lo comprueba antes de la caché de estado.

- [ ] **Step 1: Pruebas que fallan** con `fakeredis.aioredis.FakeRedis(decode_responses=True)` vía `override_redis`: en `test_revocation.py`, `test_revoke_then_read_returns_timestamp`, `test_key_has_ttl_of_960_seconds`, `test_revoke_swallows_redis_errors`, `test_read_returns_none_when_redis_fails`, `test_read_skips_redis_for_5s_after_failure` (segunda lectura inmediata no llama a Redis), `test_read_gives_up_after_300ms` (un Redis que tarda 2 s devuelve `None` en menos de 0.6 s). En `test_security.py`, `test_token_carries_float_iat`. En `test_auth.py`: `test_token_issued_before_revocation_is_rejected`, `test_token_issued_after_revocation_passes` (token emitido inmediatamente después de `revoke`, en el mismo segundo), `test_token_without_iat_is_rejected_when_key_exists`, `test_token_without_iat_passes_when_no_key`, `test_redis_down_falls_back_to_cache` (el token anterior a la revocación pasa si `revoked_after` da `None` por fallo).
- [ ] **Step 2:** Run: `.venv/bin/pytest services/common/tests -q` → FAIL en lo nuevo.
- [ ] **Step 3:** Implementar `revocation.py` (`asyncio.wait_for(..., 0.3)`; `SET key value EX 960`); `encode_token` con `iat`; la comprobación en `Auth.resolve_user` justo después de `decode_token`. Verificar que PyJWT acepta `iat` decimal y no rechaza un token recién emitido; si lo rechazara, pasar `options={"verify_iat": False}` en `decode_token`.
- [ ] **Step 4:** Run: `.venv/bin/pytest services/common/tests -q` → PASS. Actualizar READMEs. Commit: `feat: lista de revocación de sesiones en Redis y iat en los tokens`.

### Task 4: `users-playlists` escribe la revocación

**Files:**
- Modify: `services/users-playlists/users_playlists/modules/users/admin.py` (`set_role`, `suspend`, `approve_request`), `services/users-playlists/tests/conftest.py`, README del módulo `users` y de las pruebas
- Test: `services/users-playlists/tests/modules/users/test_revocation.py`

**Interfaces:**
- Consumes: `revocation.revoke(user_id)` (Tarea 3). Se llama después del `commit` de cada función, con el `user_id` afectado.

- [ ] **Step 1:** En `conftest.py`, fixture autouse que instala un `FakeRedis` con `override_redis` y lo retira al terminar; el fixture se entrega a las pruebas como `fake_redis`.
- [ ] **Step 2: Pruebas que fallan** en `test_revocation.py`: `test_set_role_writes_revocation`, `test_suspend_writes_revocation`, `test_approve_composer_request_writes_revocation`, `test_reactivate_does_not_write_revocation`, `test_failed_last_admin_change_does_not_write_revocation` (el `409` no deja clave), `test_admin_action_succeeds_when_redis_fails` (con `override_redis` de un cliente que lanza, el endpoint responde `200`), `test_refresh_after_role_change_gives_token_that_passes` (tras `set_role`, `POST /api/auth/refresh` devuelve un access token con el rol nuevo y `iat >= revoked_after`).
- [ ] **Step 3:** Run: `.venv/bin/pytest services/users-playlists/tests/modules/users/test_revocation.py -q` → FAIL.
- [ ] **Step 4:** Agregar `await revocation.revoke(user.id)` tras cada `commit` indicado.
- [ ] **Step 5:** Run: `.venv/bin/pytest services/users-playlists/tests -q` → PASS. Commit: `feat: users-playlists revoca sesiones al cambiar rol o suspender`.

### Task 5: `InternalClient` con timeouts, reintentos y breaker

**Files:**
- Modify: `services/common/meloxo_common/internal.py`, `services/common/meloxo_common/config.py` (`INTERNAL_TIMEOUT_SECONDS` pasa a `1.5`), `services/common/tests/test_security.py` (el valor por defecto esperado), `services/common/tests/test_internal.py`, `services/common/README.md`, y el `conftest.py` de `common`, `users-playlists`, `catalog-streaming`, `playback-metrics` y `gateway-auth` (fixture autouse), más sus README de pruebas
- Test: `services/common/tests/test_internal.py`

**Interfaces:**
- Consumes: `CircuitBreaker` (Tarea 2).
- Produces: `InternalClient(base_url, timeout: float = 1.5)` donde `timeout` es el de lectura y la conexión es fija de 1.0 s; `get(path, **params)` reintenta hasta 2 veces con `RETRY_DELAYS = (0.2, 0.4)`; `post(path, json=None, idempotent: bool = False)` reintenta igual solo si `idempotent`; atributo `breaker: CircuitBreaker`; `reset_all_breakers() -> None` y `RETRY_DELAYS` a nivel de módulo (las pruebas de los servicios ponen `(0, 0)` y llaman a `reset_all_breakers()` en un fixture autouse). Con el breaker abierto, `_request` lanza `UpstreamError(detail="circuit_open")` sin llamar a la red. Un `5xx` o error de red, ya reintentado, cuenta como un fallo; un `4xx` cuenta como éxito para el breaker.

- [ ] **Step 1: Pruebas que fallan** en `test_internal.py` (con `RETRY_DELAYS=(0, 0)`): `test_get_retries_twice_then_succeeds` (503, 503, 200 → devuelve el cuerpo, 3 llamadas), `test_get_gives_up_after_three_attempts`, `test_post_is_not_retried`, `test_post_idempotent_is_retried`, `test_4xx_is_not_retried_and_does_not_count_as_failure`, `test_retries_wait_0_2_and_0_4_seconds` (con `RETRY_DELAYS` por defecto y `asyncio.sleep` registrado), `test_breaker_opens_after_five_failed_calls_and_fails_fast` (la 6.ª llamada no llega a respx y lanza `UpstreamError` con `detail == "circuit_open"`), `test_breaker_probe_recovers_when_service_returns`, `test_connect_and_read_timeouts_are_separate` (`httpx.Timeout(1.5, connect=1.0)`), `test_reset_all_breakers_closes_every_client`.
- [ ] **Step 2:** Run: `.venv/bin/pytest services/common/tests/test_internal.py -q` → FAIL.
- [ ] **Step 3:** Implementar en `internal.py`; el registro de clientes para `reset_all_breakers` usa un `weakref.WeakSet`. Cambiar `INTERNAL_TIMEOUT_SECONDS` a `1.5` y la prueba de ajustes por defecto.
- [ ] **Step 4:** Agregar el fixture autouse a los cinco `conftest.py` (reinicia breakers y deja `RETRY_DELAYS = (0, 0)`), para que ninguna prueba herede un breaker abierto ni espere los 0.6 s del backoff.
- [ ] **Step 5:** Run: las suites de `common`, `users-playlists`, `catalog-streaming`, `playback-metrics` y `gateway-auth` → PASS. Actualizar READMEs (el de `common` dice «3 s y sin reintentos»). Commit: `feat: InternalClient con timeouts separados, reintentos y circuit breaker`.

### Task 6: Cola de reproducciones y consumidor en `playback-metrics`

**Files:**
- Create: `services/common/meloxo_common/playback_queue.py`, `services/playback-metrics/playback_metrics/modules/playback/consumer.py`
- Modify: `services/playback-metrics/playback_metrics/modules/playback/service.py`, `.../playback/public.py` (exporta `run_consumer`), `services/playback-metrics/playback_metrics/main.py` (lifespan), READMEs del módulo y de las pruebas, `services/playback-metrics/tests/conftest.py`
- Test: `services/common/tests/test_playback_queue.py`, `services/playback-metrics/tests/modules/playback/test_consumer.py`

**Interfaces:**
- Produces en `playback_queue.py`: `STREAM = "playbacks"`, `GROUP = "playbacks"`, `MAXLEN = 100_000`; `QueuedEvent` (dataclass congelada: `type: Literal["record", "progress"]`, `user_id: UUID`, `playback_id: UUID`, `listened_seconds: int`, `song_id: UUID | None`, `received_at: str` ISO); `to_fields(event) -> dict[str, str]`; `from_fields(fields: dict[str, str]) -> QueuedEvent` (lanza `ValueError` si falta un campo, el tipo es desconocido o un valor no se puede convertir; `record` exige `song_id`); `async enqueue(redis, event) -> str` (`XADD ... MAXLEN ~`); `async ensure_group(redis) -> None` (`XGROUP CREATE ... id=0 mkstream`, ignora `BUSYGROUP`).
- Produce en `service.py`: `async apply_event(session, event: QueuedEvent) -> Literal["created", "duplicate", "progress", "discarded"]`. `record` reutiliza el `INSERT ... ON CONFLICT DO NOTHING` y el contador `duplicates_discarded` de hoy; `progress` solo sube `listened_seconds` con `greatest`, y si la reproducción no existe o es de otro usuario devuelve `discarded` y suma 1 a la clave `events_discarded`. Todo en una transacción.
- Produce en `consumer.py`: `async consume_once(redis, consumer: str, block_ms: int = 1000, count: int = 50, min_idle_ms: int = 30_000) -> int` (primero reclama pendientes con `XAUTOCLAIM`, luego lee con `XREADGROUP`; devuelve cuántos mensajes procesó) y `async run_consumer(consumer: str = "playback-metrics") -> None` (bucle; sin Redis configurado, termina; ante un error de Redis registra y espera 1 s).

- [ ] **Step 1: Pruebas que fallan** de la cola (`test_playback_queue.py`): `test_roundtrip_of_fields`, `test_from_fields_rejects_missing_field`, `test_from_fields_rejects_unknown_type`, `test_record_requires_song_id`, `test_enqueue_adds_to_stream_and_trims`, `test_ensure_group_is_idempotent`.
- [ ] **Step 2: Pruebas que fallan** del consumidor (`test_consumer.py`, base real y `FakeRedis`): `test_record_event_is_applied_and_acked` (0 pendientes tras procesar), `test_progress_after_record_raises_listened_seconds` (mismo stream, en orden), `test_resent_playback_id_counts_one_play_and_duplicates` (100 eventos iguales → 1 fila, `duplicates_discarded` 99), `test_redelivered_message_does_not_count_twice` (se procesa, no se acusa, se reclama con `min_idle_ms=0` → sigue 1 reproducción), `test_transient_db_error_is_not_acked_and_is_retried` (si `apply_event` lanza, el mensaje queda pendiente y se aplica en la siguiente vuelta), `test_invalid_message_is_acked_and_discarded` (campos rotos → acusado, `events_discarded` +1, los mensajes siguientes se procesan), `test_progress_for_foreign_or_missing_playback_is_discarded`, `test_consumer_does_not_check_catalog` (con catálogo caído, el `record` se guarda).
- [ ] **Step 3:** Run: `.venv/bin/pytest services/common/tests/test_playback_queue.py services/playback-metrics/tests/modules/playback/test_consumer.py -q` → FAIL.
- [ ] **Step 4:** Implementar `playback_queue.py`, `apply_event` (sin validar la pista contra catálogo: ya lo hizo quien encoló), `consumer.py`, la exportación en `public.py` y el arranque en el `lifespan` de `main.py` como tarea que se cancela al cerrar (omitida si `DISABLE_SCHEDULER`). `conftest.py` instala `FakeRedis` con `override_redis`.
- [ ] **Step 5:** Run: `.venv/bin/pytest services/common/tests services/playback-metrics/tests -q` → PASS (las rutas HTTP de escritura siguen vivas hasta la Tarea 7). Commit: `feat: cola de reproducciones en Redis Streams y su consumidor`.

### Task 7: Corte a la cola: ingreso en catálogo, nginx y retiro de las escrituras viejas

**Files:**
- Create: `services/catalog-streaming/catalog_streaming/playback_routes.py`
- Modify: `services/catalog-streaming/catalog_streaming/main.py` (incluye el router), `edge/nginx.conf`, `edge/tests/test_routes.py`, `edge/tests/test_stack.py`, `services/playback-metrics/playback_metrics/modules/playback/routes.py` (solo queda `GET /history`), `.../playback/service.py` (se retira `record` y `progress`), `.../playback/schemas.py` (los esquemas de entrada pasan a catálogo), `services/playback-metrics/tests/modules/playback/test_playbacks.py`, `.../tests/test_playback_resilience.py`, `.../tests/modules/analytics/test_metrics.py`, `services/catalog-streaming/tests/conftest.py`, READMEs de catálogo, `edge`, módulo `playback` y sus pruebas
- Test: `services/catalog-streaming/tests/test_playback_ingest.py`

**Interfaces:**
- Consumes: `playback_queue.enqueue`, `QueuedEvent` (Tarea 6), `redis_client.get_redis()`, `public.get_songs` de catálogo (la misma regla de existencia que usa `/internal/songs`), `auth.current_user` de catálogo.
- Produces: `POST /api/playbacks` (cuerpo `playback_id`, `song_id`, `listened_seconds` entre 0 y 86400, como el `PlaybackIn` de hoy) y `PATCH /api/playbacks/{playback_id}/progress` (cuerpo `listened_seconds`), ambos `202` con `{"playback_id": "<uuid>"}`. Sesión obligatoria; `user_id` sale del JWT. Sin Redis (`get_redis()` es `None`) o con error de Redis → `UpstreamError` (`503`). nginx: `location = /api/playbacks` y `location ~ ^/api/playbacks/[^/]+/progress$` van a `catalog-streaming:8002`; `location /api/playbacks` (historial) sigue en `playback-metrics:8003`.

- [ ] **Step 1: Pruebas que fallan** en `test_playback_ingest.py` (catálogo, `FakeRedis`): `test_post_enqueues_record_and_returns_202`, `test_post_requires_session` (`401`), `test_post_unknown_song_is_404_and_enqueues_nothing`, `test_post_invalid_seconds_is_422`, `test_user_id_comes_from_token_not_body`, `test_patch_enqueues_progress_and_returns_202`, `test_redis_down_returns_503_upstream_unavailable_quickly` (cliente cuyo `xadd` lanza `ConnectionError`; responde `503` con código `upstream_unavailable` en menos de 1 s), `test_redis_disabled_returns_503`.
- [ ] **Step 2:** Run: `.venv/bin/pytest services/catalog-streaming/tests/test_playback_ingest.py -q` → FAIL.
- [ ] **Step 3:** Implementar `playback_routes.py` e incluirlo en `main.py` de catálogo.
- [ ] **Step 4: Pruebas de rutas que fallan** en `edge/tests/test_routes.py`: las dos escrituras resuelven a `catalog-streaming`, `GET /api/playbacks/history` a `playback-metrics`, y ninguna ruta queda sin dueño. Run: `.venv/bin/pytest edge/tests -q -m "not stack"` → FAIL. Editar `nginx.conf` (las `location` nuevas van antes de la general de `/api/playbacks`; respetar el orden de selección de nginx) → PASS.
- [ ] **Step 5:** Quitar `POST`/`PATCH` y su lógica de `playback-metrics`. Migrar las pruebas de `playback-metrics` que sembraban reproducciones por HTTP: agregar en su `conftest.py` el helper `record_play(user, song_id, seconds=12, playback_id=None)` que llama a `service.apply_event` con un `QueuedEvent`, y usarlo en `test_playbacks.py`, `test_playback_resilience.py` y `test_metrics.py`. Las pruebas de `403`/`404` del `PATCH` desaparecen (ahora son `discarded`, cubierto en la Tarea 6); `404 song_not_found` ya está en la Tarea 7. Agregar a `edge/tests/test_stack.py` (marcada `stack`) que `POST /api/playbacks` da `202`.
- [ ] **Step 6:** Run: `.venv/bin/pytest services/catalog-streaming/tests services/playback-metrics/tests edge/tests -q -m "not stack"` → PASS. Actualizar READMEs (el del módulo `playback` describe hoy `201`/`200` y la validación con `get_songs`). Commit: `feat: las reproducciones entran por catálogo y se encolan en Redis`.

### Task 8: Escenarios de demo

**Files:**
- Modify: `demo/scenario_1_metrics_down.py`, `demo/scenario_4_idempotency.py`, `demo/common.py` (ayuda para esperar a que un contador llegue a un valor), `demo/test_common.py`, `demo/README.md`, `demo/locustfile.py` (solo si su comprobación de éxito exige `201`)
- Create: `demo/scenario_10_circuit_breaker.py`, `demo/scenario_11_revocation.py`

**Interfaces:**
- Produces en `common.py`: `wait_until(predicate: Callable[[], bool], seconds: float, message: str) -> None` que lanza `Failure(message)` si no se cumple a tiempo.

- [ ] **Step 1: Prueba que falla** en `demo/test_common.py`: `test_wait_until_returns_when_predicate_true` y `test_wait_until_raises_failure_on_timeout`. Run: `.venv/bin/pytest demo/test_common.py -q` → FAIL; implementar `wait_until` → PASS.
- [ ] **Step 2:** Escenario 1: con `playback-metrics` detenido, `POST /api/playbacks` da `202` (ya no un error), el audio sigue, `GET /api/metrics/top` da `upstream_unavailable`; al volver, `GET /api/playbacks/history` muestra las reproducciones enviadas (con `wait_until`, máx. 30 s) y ninguna está duplicada.
- [ ] **Step 3:** Escenario 4: 100 reenvíos concurrentes del mismo `playback_id` dan `202` todos; con `wait_until`, el historial tiene 1 reproducción y `duplicates_discarded` subió 99. Ya no mira `201`/`200`.
- [ ] **Step 4:** Escenario 10 (breaker): detener catálogo, hacer llamadas que pasen por `InternalClient` (por ejemplo `GET /api/playlists/{id}` con pistas, o `GET /api/notices`) hasta que la respuesta tarde menos de 200 ms de forma sostenida; comprobar que las primeras tardaron más y que tras arrancar catálogo y esperar más de 15 s todo vuelve a `200`. Corre con `python3 demo/scenario_10_circuit_breaker.py`; usa el mismo patrón de `run`/`check` y reinicia lo detenido en un `finally`.
- [ ] **Step 5:** Escenario 11 (revocación): un usuario con sesión; el admin le cambia el rol (y en una segunda pasada lo suspende); la siguiente petición con el token viejo da `401` en menos de 2 s, y tras `refresh` o nuevo login con el rol nuevo la petición pasa. Comparar con los 30 s anteriores y anotar el tiempo medido.
- [ ] **Step 6:** Actualizar `demo/README.md` (tabla de escenarios, explicación de los dos nuevos). Commit: `test: escenarios 1 y 4 con la cola, y escenarios 10 y 11 de breaker y revocación`.

### Task 9: Verificación con el stack, documentación y cierre

**Files:**
- Modify: `README.md` (tabla de criterios: F3.3 pasa a «Cumple»; arquitectura; variables; glosario: circuit breaker, Redis Streams, revocación), `docs/ramas.md` (la `04` pasa a «Hecha»), `CHANGELOG.md`, `docs/specs/README.md` (ya lista el diseño), `docs/plans/README.md`, `docs/decisions/README.md`
- Create: `docs/decisions/04-resiliencia-concurrencia.md`

- [ ] **Step 1:** `docker compose down -v && docker compose up --build -d` (avisar antes: borra la base y los archivos subidos), esperar a todos `healthy`, `docker compose run --rm seed python -m seed all`.
- [ ] **Step 2:** Correr cada suite: `.venv/bin/pytest services/common/tests services/users-playlists/tests services/catalog-streaming/tests services/playback-metrics/tests services/gateway-auth/tests -q`, `.venv/bin/pytest edge/tests -q` (con stack), `.venv/bin/pytest demo/test_common.py tests -q`, y las pruebas del frontend de `usePlaybackReporter` (`cd frontend && npm test -- usePlaybackReporter`). Todas en verde; si una no corre, decirlo y por qué.
- [ ] **Step 3:** Escenarios 1, 4, 10, 11 y los que ya existían (2, 5, 6, 7, 8) contra el stack. Reiniciar Redis (`docker compose restart redis`) con eventos pendientes y comprobar que no se pierde ninguno.
- [ ] **Step 4:** Medir F3.4 (evento visible en ≤ 5 s con la cola) y repetir la prueba de carga (escenario 9); anotar los números reales y el efecto del salto extra en la decisión de la rama. Si F2.3 o F3.4 no se cumplen, documentarlo, no relajar el umbral.
- [ ] **Step 5:** Escribir `docs/decisions/04-resiliencia-concurrencia.md` (lo que cambió respecto al diseño, los números medidos, límites: breaker por proceso, `MAXLEN` pierde lo más viejo, sin DLQ, progreso ajeno descartado en el consumidor, Jamendo sin breaker) y actualizar los demás documentos de la lista. El texto de `docs/ramas.md` y del README raíz que dice «llega en la rama 04» debe quedar en pasado.
- [ ] **Step 6:** `.venv/bin/pytest tests -q` (los README de cada carpeta nueva). Commit: `docs: cierre de la rama 04 con lo medido y lo decidido`.

---

## Self-review

- **Cobertura del diseño:** objetivos 1-3 → Tareas 2 y 5; 4 → Tareas 6 y 7; 5 → Tareas 3 y 4; 6 → Tarea 1; 7 → Tarea 8; 8 → Tarea 9. Antiobjetivos: duplicados/pérdidas → Tarea 6; audio sin errores → Tarea 8 (escenario 1); falla abierta → Tarea 3; reintento de no idempotentes → Tarea 5; reingreso tras cambio de rol → Tareas 3 y 4.
- **Consistencia de tipos:** `QueuedEvent`, `enqueue`, `get_redis`, `override_redis`, `revoke`, `revoked_after`, `reset_all_breakers`, `RETRY_DELAYS` y `wait_until` se definen en una tarea y se usan con el mismo nombre después.
- **Orden:** la Tarea 6 deja viva la ruta HTTP vieja hasta el corte de la Tarea 7, así que ninguna tarea deja la suite rota.
- **Fuera del diseño, decidido aquí:** la latencia del ingreso no se registra en el recorder de catálogo (`module_for` no cubre `/api/playbacks`); `put`/`delete` no se agregan a `InternalClient` porque nadie los usa.
