# Diseño · `03-gateway-discovery-balanceo`

Fecha: 2026-11-03 · Rama: `03-gateway-discovery-balanceo` (parte de `02-separacion`, commit `c51e7df`).

## Intención

Segundo paso del plan de ramas del PRD, equivalente a la etapa 03 de Mexi Banco (lab S07): los
servicios de `02` **se encuentran solos**. Cada instancia se registra en un **directorio** y manda
latidos; un **gateway propio** es la única puerta y reparte entre las instancias vivas; el
streaming corre en **tres réplicas**; y las llamadas internas dejan de usar el DNS de Compose para
pedir instancias al directorio y **balancear del lado del cliente**. En la defensa, cualquiera del
equipo debe poder señalar dónde vive el gateway, el directorio y el balanceador, y explicar qué
pasa —y cuánto tarda— cuando una réplica muere.

## Metas

1. **Directorio: Consul** (`hashicorp/consul:1.20`, modo `agent -dev`), servicio `discovery`,
   panel publicado en `:8500` (como el `:8761` de Eureka).
2. **Registro con latido** en cada instancia de cada servicio (incluidos `gateway` y `web`):
   - al arrancar: `PUT /v1/agent/service/register` con `Name` lógico, `ID` único por instancia
     (`<servicio>-<hostname>`), `Address` = IP del contenedor, `Port` y un check **TTL**;
   - cada `FLDSMDFR_HEARTBEAT_S` (por omisión 3 s): `PUT /v1/agent/check/pass/<check>`;
   - TTL `FLDSMDFR_TTL_S` (10 s): sin latido, el check pasa a `critical` y la instancia deja de
     aparecer en `?passing=true`;
   - `DeregisterCriticalServiceAfter` `FLDSMDFR_DEREGISTER_AFTER` (`1m`, el mínimo de Consul):
     después, sale del registro;
   - al apagarse en orden (SIGTERM): `PUT /v1/agent/service/deregister/<id>`.
3. **Gateway propio** (`services/gateway/`, FastAPI + `httpx`), único puerto público `:8000`:
   - misma tabla de prefijos que el `nginx.conf` de `02`; todo lo que no es `/api` va a `web`;
   - por petición elige instancia con **round-robin** sobre la lista `passing` del directorio,
     cacheada `FLDSMDFR_LB_CACHE_S` (5 s);
   - proxy en streaming en ambos sentidos (audio con `Range`, subidas de 21 MB) sin cargar el
     cuerpo en memoria; conserva todas las cabeceras, incluidos varios `Set-Cookie`;
   - agrega `X-Gateway-Instancia` y deja pasar `X-Instancia` del servicio;
   - sin instancias vivas o con error de conexión: `503` JSON `service_unavailable` con el nombre
     del servicio; `/internal/...` → `404` JSON; límite de 21 MB → mismo JSON que en `02`
     (`422 file_too_large` en `/api/songs`, `413 image_too_large` en el resto).
4. **`web` (Nginx)** solo sirve el SPA (sin rutas `/api`), detrás del gateway.
5. **Tres réplicas de `catalog-streaming`** (`deploy.replicas: 3`) compartiendo el volumen `media`.
   Migraciones y semilla en un servicio de una sola vez, `catalog-init`, del que las réplicas
   dependen con `service_completed_successfully` (evita que tres réplicas migren y siembren a la
   vez).
6. **Balanceo del lado del cliente** en `users-playlists` y `playback-metrics`: los clientes de
   `app/clients/` llaman por **nombre lógico** (`catalog-streaming`, `users-playlists`), resuelven
   con el directorio (misma caché de 5 s) y reparten en round-robin.
7. **`X-Instancia`** en todas las respuestas de los tres servicios (el `ID` registrado).
8. **Demo** `scripts/demo-03.sh`: instancias en el directorio, nueve consultas mostrando las tres
   réplicas, `docker kill` de una réplica (sin baja ordenada) con la ventana de errores hasta que
   el TTL vence, y `docker stop` (con baja) para comparar.
9. `README.md` de la rama y `docs/PRD.md` (§6 plan, §7, §8, §9, §10.4 cerrada).

## No metas

- Reintentar en otra instancia cuando la elegida falla, timeouts propios, circuit breaker (`04`).
- Alta disponibilidad del gateway o del directorio (una sola instancia de cada uno).
- Seguridad de Consul (ACL), TLS interno, autenticación de `/internal`.
- Réplicas de `users-playlists` o `playback-metrics` (se pueden escalar, pero la demo es catálogo).

## Anti-metas

- Que la UI o las rutas públicas cambien.
- Que el gateway consulte Consul en cada petición sin caché (el curso explica la caché del
  balanceador; se quiere ver).
- Ocultar la ventana de falla con reintentos: en `03` debe verse.

## Decisiones

**Del equipo:** solo `03` ahora; Consul como directorio con gateway propio en FastAPI.

**Propuestas por el agente (aprobadas en la descripción):** `web` solo SPA detrás del gateway y
registrado; tres réplicas solo del catálogo; sin reintentos; script de demo; tiempos cortos
configurables por variables.

**Propuestas en este documento (a revisar):**
- **Check TTL** (la instancia avisa que vive) y no check HTTP (Consul pregunta): es el modelo de
  latido de Eureka que se ve en clase.
- **Código de directorio copiado** en cada servicio (`app/shared/discovery.py`), igual que el resto
  de `shared/` en `02`. El gateway es un servicio más con su propia copia.
- **`catalog-init`** de una sola vez para migrar y sembrar, en lugar de un candado en la base.
- **`users-playlists` espera a que `catalog-streaming` esté sano** (Compose espera a las réplicas)
  y cada instancia se registra en el directorio antes de declararse sana, así la semilla del casete
  demo encuentra réplicas. Si aun así no hay, la semilla ya tolera el `503` y deja el casete
  pendiente.
- El gateway responde su propio `/api/health` (`{"status":"ok","directory":"ok|error"}`).

## Interfaces

`app/shared/discovery.py` (igual en los cuatro servicios Python):
- `async def register(name: str, port: int) -> str` → id de instancia; arranca la tarea de latido.
- `async def deregister() -> None` → baja y detiene la tarea.
- `async def instances(name: str) -> list[str]` → URLs base `http://ip:puerto` de las instancias
  `passing`, con caché de `FLDSMDFR_LB_CACHE_S`.
- `def instance_id() -> str` → para `X-Instancia`.
- `class RoundRobin` con `pick(name) -> str`; levanta `NoInstances(name)` si la lista está vacía.
- Configuración: `FLDSMDFR_CONSUL_URL` (`http://discovery:8500`), `FLDSMDFR_SERVICE_NAME`,
  `FLDSMDFR_SERVICE_PORT` (8000), `FLDSMDFR_DISCOVERY_ENABLED` (`false` en pruebas).

`app/clients/http.py`: `call(service, method, path, **kwargs)` (sin `base_url`): resuelve con
`RoundRobin.pick(service)`; `NoInstances` → `RemoteUnavailable`. `set_transport(service, t)` en
pruebas salta el directorio.

## Pruebas

- `services/gateway/tests/`: con directorio falso y servicios falsos ASGI —
  `test_round_robin_alternates_instances`, `test_no_instances_503`, `test_connect_error_503`,
  `test_internal_is_404`, `test_routes_by_prefix` (incluye `/api/me/history` → playback),
  `test_range_passthrough_206`, `test_multiple_set_cookie_preserved`,
  `test_upload_over_limit_json`, `test_spa_goes_to_web`, `test_lb_cache_hides_new_instances`.
- En cada servicio: `test_discovery.py` (registro, latido y baja contra un Consul falso por
  `httpx.MockTransport`; `X-Instancia` presente) y los tests de clientes adaptados a nombres
  lógicos.
- Verificación en vivo: 9 contenedores sanos (`db`, `discovery`, `catalog-init` terminado, tres
  catálogos, `users-playlists`, `playback-metrics`, `gateway`, `web`), panel de Consul con las
  instancias, `X-Instancia` alternando, Range `206`, subida 19 MB, UI por `:8000`, y el script de
  demo con `kill` y `stop`.

## Riesgos y limitaciones

- Gateway en Python: un salto más y CPU en el streaming; aceptable para el prototipo y medible.
- Ventana de falla: con TTL 10 s y caché 5 s, una réplica muerta sin baja ordenada puede recibir
  tráfico hasta ~15 s (por eso la demo usa `kill`).
- Volumen `media` compartido entre réplicas: una subida en una réplica la ven las otras porque es
  el mismo disco, no por replicación.
- El directorio es un punto único: si `discovery` cae, las cachés siguen sirviendo hasta 5 s y
  después nadie encuentra a nadie (`503`). Se documenta en el README.
