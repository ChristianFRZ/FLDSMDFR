# MELOXO · Streaming musical (resiliencia)

**MELOXO** es el nombre visible de la aplicación; el repositorio, los paquetes y los contenedores conservan el nombre del equipo, `FLDSMDFR`.

Proyecto semestral de **Sistemas Distribuidos** (Semestre 2027-1, FI-UNAM). Esta rama entrega el paso **`04-resiliencia`** del plan del [PRD](docs/PRD.md). Parte de [`03-gateway-discovery-balanceo`](../../tree/03-gateway-discovery-balanceo), donde la demo mostró dos problemas:

- una réplica muerta dejaba colgada **unos 7 s** cada petición que le tocaba, y luego respondía `503`;
- con el catálogo caído, favoritas, historial y resumen respondían `503`, y cada petición volvía a golpear al servicio caído.

Aquí las fallas se vuelven **rápidas, acotadas y visibles**:

- **timeouts** explícitos;
- **un reintento en otra réplica**;
- un **circuit breaker hecho a mano**, con sus tres estados;
- **degradación con copias** en favoritas e historial;
- el estado de los circuitos en el **panel del administrador**.

Es la parte de circuit breaker del lab S08 de Mexi Banco. La saga no está, y la sección [¿Y la saga?](#y-la-saga) explica por qué.

## Equipo

- **Nombre del equipo:** `FLDSMDFR`
- Franco Ramírez Christian ([@ChristianFRZ](https://github.com/ChristianFRZ))
- López Hernández Miriam Amisadai ([@AmisadaiLopez](https://github.com/AmisadaiLopez))
- Nava Santiago Erick ([@Saiko-E](https://github.com/Saiko-E))
- Pérez Paitán Brent Armando ([@zmd-brnt](https://github.com/zmd-brnt))

## Qué cambió respecto a `03-gateway-discovery-balanceo`

| | `03` | `04-resiliencia` |
|---|---|---|
| Petición que cae en una réplica muerta | Cuelga unos 7 s (timeout de conexión de `httpx`) y luego `503` | El gateway corta a los **1.5 s** y **reintenta en otra réplica**: `200` en unos 1.7 s |
| Llamadas internas | Sin timeout propio ni reintento | **1.5 s por intento**, **un reintento en otra réplica**, **circuit breaker** por servicio remoto |
| Catálogo caído | Cada petición lo vuelve a intentar | El circuito se abre tras **5 fallas seguidas** y deja de llamarlo durante **10 s** |
| Favoritas e historial con el catálogo caído | `503` | `200` con **copias** guardadas y `status: "degraded"`; la UI marca "Sin actualizar" |
| Resumen del administrador sin catálogo o sin usuarios | `503` | `200` con el total faltante en `null` ("—" en la Cabina) |
| Cabina | Resumen, subida, catálogo y usuarios | Más la tarjeta **"Resiliencia"** con el estado de cada circuito, refrescada cada 2 s |
| Directorio | La IP se registraba una sola vez | El latido **vuelve a registrar** la instancia si cambió la IP del contenedor |

Las rutas públicas no cambian. Hay dos nuevas, solo para administradores:

- `GET /api/admin/circuits` (`users-playlists`);
- `GET /api/metrics/circuits` (`playback-metrics`).

## Dónde vive cada mecanismo

| Mecanismo | Dónde vive | Qué hace |
|---|---|---|
| **Circuit breaker** | `app/shared/circuit.py` en `users-playlists` y `playback-metrics` (copia por servicio) | Es una clase `CircuitBreaker` por servicio remoto, con tres estados: **cerrado** (deja pasar y cuenta fallas seguidas), **abierto** (no llama y responde `503` al instante) y **semiabierto** (deja pasar **una** prueba). Cada cambio deja una línea en el log. |
| **Timeout y reintento internos** | `app/clients/http.py` en los mismos servicios | Cada intento tiene un límite total de 1.5 s. Ante timeout, error de red o `5xx`, hace un segundo intento en **otra** instancia del directorio, tras 100–300 ms. El circuito cuenta la llamada completa: un intento más su reintento es **una** falla. |
| **Timeout y reintento del gateway** | `services/gateway/app/proxy.py` | Da 1.5 s para **conectar** y 30 s por lectura o escritura, para no cortar el audio ni las subidas. Si no logró conectar, un `GET` o `HEAD` se reintenta en otra réplica. |
| **Copias para el modo degradado** | Columnas `*_snapshot` de `favorites` (base `users_playlists`) y de `playback_events` (base `playback`) | Se llenan al escribir y se corrigen al leer con el catálogo arriba. Se usan cuando el catálogo no responde. |
| **Estado de los circuitos** | `app/clients/circuits_router.py` (API) y `ui/src/components/EstadoCircuitos.vue` (Cabina) | Muestra, por circuito: origen → destino, estado, fallas seguidas, desde cuándo está en ese estado y en cuántos segundos vuelve a probar. |

```text
            ┌──────────── gateway :8000 ────────────┐
navegador ─►│ 1.5 s para conectar; si no conecta,   │──► catalog-streaming ×3
            │ GET/HEAD reintenta en otra réplica    │──► users-playlists ──┐
            └───────────────────────────────────────┘──► playback-metrics ─┤
                                                                           │ http.call(...)
   users-playlists / playback-metrics ── circuito ── intento 1.5 s ── reintento en otra réplica
                                          (cerrado │ abierto │ semiabierto)          │
                                                                                     ▼
                                                               catalog-streaming / users-playlists
```

### Qué cuenta como falla y qué responde cada cosa

| Caso | ¿Se reintenta? | ¿Cuenta para el circuito? | Qué recibe quien llamó |
|---|---|---|---|
| Timeout, error de red, `5xx` o sin instancias | Sí (salvo sin instancias) | Sí | `503 service_unavailable` |
| `404` del dueño del dato | No | No | El mismo `NotFound` de siempre |
| Otro `4xx` (error de contrato) | No | No | `503`, como en `03` |
| Circuito abierto | No llama | — | `503` en milisegundos |

### Qué se degrada y qué sigue con `503`

- **Se degradan, con copias:**
  - **favoritas**: `200` con `degraded: true` y cada canción en `status: "degraded"`;
  - **historial e Inicio**: igual, con la misma forma de respuesta;
  - **detalle de casete**: ya se degradaba desde `01`; ahora la UI también lo marca;
  - **top**: ya se degradaba;
  - **resumen del administrador**: el total faltante va en `null`.
- **Siguen con `503`, ahora rápido:**
  - **marcar favorita, agregar a un casete y registrar una reproducción**: necesitan validar contra el catálogo, y aceptarlas a ciegas cambiaría el negocio. La UI ya reintenta la reproducción con el mismo `playback_id`. Que no se pierda es tema de `05`.
  - **`top-artists`**: los artistas salen del catálogo y no hay copia que mostrar.

Una fila guardada antes de esta rama no tiene copia. Con el catálogo caído se muestra como "Canción no disponible". En la siguiente lectura con el catálogo arriba se completa sola: una migración no puede preguntarle a otro servicio.

### Ajustes

| Variable | Por omisión | Dónde |
|---|---|---|
| `FLDSMDFR_CALL_TIMEOUT_S` | `1.5` | clientes internos |
| `FLDSMDFR_RETRIES` | `1` | clientes internos y gateway |
| `FLDSMDFR_CB_FAILURES` | `5` | clientes internos |
| `FLDSMDFR_CB_OPEN_S` | `10` | clientes internos |
| `FLDSMDFR_UPSTREAM_CONNECT_S` | `1.5` | gateway |
| `FLDSMDFR_UPSTREAM_READ_S` | `30` | gateway |

Se cambian sin tocar archivos, por ejemplo `FLDSMDFR_CB_OPEN_S=30 docker compose up -d`. Los tiempos del directorio de `03` siguen igual: latido 3 s, TTL 10 s, caché 5 s y baja al minuto.

## Inicio rápido

Requisito: Docker con Docker Compose.

```bash
cp .env.example .env     # opcional
docker compose up --build -d
docker compose ps        # catalog-init "Exited (0)"; los demás healthy (3 de catalog-streaming)
```

- Aplicación: <http://localhost:8000>
- Cabina, con la tarjeta "Resiliencia": <http://localhost:8000/cabina> (como administrador)
- Panel del directorio: <http://localhost:8500>

> **Si vienes de `03`:** `docker compose up --build -d` basta. Las migraciones nuevas (`0011` en `users_playlists` y `0012` en `playback`) solo agregan columnas opcionales.

### Credenciales demo

| Rol           | Correo               | Contraseña    |
| ------------- | -------------------- | ------------- |
| Administrador | `admin@fldsmdfr.mx`  | `admin12345`  |
| Oyente        | `oyente@fldsmdfr.mx` | `oyente12345` |

## Demo: una réplica muerta, el circuito y la degradación

```bash
./scripts/demo-04.sh
```

Abre la Cabina como administrador mientras corre: la tarjeta "Resiliencia" cambia en vivo. Salida real (recortada) en esta máquina:

```text
== 2. docker kill fldsmdfr-catalog-streaming-1: en 03 había esperas de ~7 s y 503; ahora se reintenta en otra réplica
t= 0s  canciones 200  1.76s catalog-streaming-d7034950269b   | favoritas 200  1.76s al día
t= 5s  canciones 200  0.02s catalog-streaming-62cfc315b252   | favoritas 200  0.04s al día
t= 6s  canciones 200  1.70s catalog-streaming-d7034950269b   | favoritas 200  1.71s al día
t=11s  canciones 200  0.02s catalog-streaming-62cfc315b252   | favoritas 200  0.03s al día
t=12s… canciones 200 ~0.01s alternando entre las dos réplicas vivas

== 3. docker compose stop catalog-streaming (las tres): el circuito se abre a las 5 fallas
t= 0s  favoritas 200  0.03s degradadas (copias) | circuito cerrado (1 fallas)
t= 4s  favoritas 200  0.02s degradadas (copias) | circuito cerrado (4 fallas)
t= 5s  favoritas 200  0.01s degradadas (copias) | circuito abierto (5 fallas, vuelve a probar en 10 s)
t= 8s  favoritas 200  0.01s degradadas (copias) | circuito abierto (5 fallas, vuelve a probar en 7 s)

== 4. docker compose start catalog-streaming: semiabierto → una prueba → cerrado
t= 0s  circuito semiabierto (5 fallas) | favoritas 200  0.02s degradadas (copias) | réplicas vivas 0
t= 1s  circuito abierto (6 fallas, vuelve a probar en 9 s) | favoritas 200  0.03s degradadas (copias) | réplicas vivas 0
t= 4s  circuito abierto (6 fallas, vuelve a probar en 6 s) | favoritas 200  0.02s degradadas (copias) | réplicas vivas 3
t=11s  circuito semiabierto (6 fallas) | favoritas 200  0.05s al día | réplicas vivas 3
t=12s  circuito cerrado (0 fallas) | favoritas 200  0.05s al día | réplicas vivas 3

== 5. Las transiciones, tal como quedaron en el log de users-playlists
circuito users-playlists→catalog-streaming: cerrado → abierto (5 fallas seguidas)
circuito users-playlists→catalog-streaming: abierto → semiabierto (pasaron 10 s)
circuito users-playlists→catalog-streaming: semiabierto → abierto (falló la prueba)
circuito users-playlists→catalog-streaming: abierto → semiabierto (pasaron 10 s)
circuito users-playlists→catalog-streaming: semiabierto → cerrado (la prueba salió bien)
```

Cómo se lee, que es lo que se pregunta en la defensa:

1. **`kill` de una réplica:**
   - Ya no hay `503`.
   - La petición que cae en la réplica muerta tarda unos 1.7 s: 1.5 s intentando conectar, más el reintento en otra réplica. En `03` eran unos 7 s y terminaba en `503`.
   - Cuando el directorio deja de anunciarla (TTL de 10 s, más la caché de 5 s), todo vuelve a tardar milisegundos.
2. **Catálogo caído entero:**
   - Favoritas responde `200` con sus copias desde la primera petición.
   - A la quinta falla seguida, el circuito se abre, y a partir de ahí `users-playlists` ya no intenta llamar al catálogo.
3. **Semiabierto:**
   - A los 10 s el circuito deja pasar **una** prueba.
   - En la salida de arriba, la primera prueba falló porque las réplicas todavía no estaban registradas, así que el circuito volvió a abrirse otros 10 s.
   - La segunda prueba salió bien y el circuito se cerró. Las favoritas volvieron a estar al día y sus copias se actualizaron.

## ¿Y la saga?

El lab S08 pide una **saga orquestada** para la transferencia de Mexi Banco, porque esa operación escribe en dos cuentas: si el abono falla después del cargo, hay que devolver el dinero.

En MELOXO **ninguna operación escribe en dos servicios**:

- **Agregar una canción a un casete o a favoritas** solo *lee* del catálogo para validarla y escribe en `users-playlists`.
- **Registrar una reproducción** lee del catálogo y escribe solo en `playback-metrics`.
- **Retirar una canción** solo la desactiva en el catálogo. Los casetes y las favoritas conservan su copia, y al leer la marcan como no disponible. Es consistencia eventual al leer, no una compensación.

Si en una rama posterior aparece una escritura en dos servicios (por ejemplo, borrar una cuenta y con ella su historial), se resolverá con una saga orquestada y su compensación, como en el lab S08. El razonamiento completo está en el PRD, §6 y §9.

## Pruebas

```bash
docker compose --profile test run --rm tests-catalog
docker compose --profile test run --rm tests-users
docker compose --profile test run --rm tests-playback
docker compose --profile test run --rm tests-gateway
docker compose --profile test run --rm tests-users ruff check .   # igual en los demás
cd ui && npm ci && npm test && npm run build
```

- **Circuito** (`tests/test_circuit.py`, con un reloj falso):
  - las transiciones de los tres estados;
  - una sola prueba en semiabierto;
  - el `snapshot` y la línea de log.
- **Clientes** (`tests/test_client_resilience.py`):
  - un timeout se reintenta en otra instancia;
  - un `4xx` ni se reintenta ni cuenta;
  - con el circuito abierto, no se llama al servicio remoto.
- **Degradación:**
  - favoritas, historial y resumen con su servicio caído;
  - copias en filas viejas;
  - la copia se actualiza al leer;
  - si falla la escritura de la copia, la respuesta sigue siendo `200`.
- **Gateway** (`tests/test_gateway_resilience.py`):
  - reintento si no conectó;
  - un `POST` nunca se reintenta;
  - un `5xx` no se reintenta;
  - los límites configurados.
- **Directorio:** `test_heartbeat_reregisters_when_address_changes`.
- **UI:**
  - `EstadoCircuitos`: estados, una mitad sin datos, refresco cada 2 s y pausa con la pestaña oculta;
  - el estado "Sin actualizar" en las filas;
  - el aviso en favoritas e historial;
  - el "—" del resumen.

## Mapa de carpetas

```text
services/
  gateway/             app/proxy.py (timeouts y reintento), app/routes.py, tests/test_gateway_resilience.py
  catalog-streaming/   app/modules/catalog/, scripts/{init,entrypoint}.sh
  users-playlists/     app/shared/circuit.py, app/clients/{http,circuits_router}.py, modules/social (copias)
  playback-metrics/    app/shared/circuit.py, app/clients/{http,circuits_router}.py, modules/playback (copias)
ui/src/components/     EstadoCircuitos.vue, FilaCancion.vue (estado "Sin actualizar")
scripts/demo-04.sh     demo de reintento, circuito y degradación
```

## Qué queda fuera (y en qué rama llega)

| Falta | Rama |
|---|---|
| Que una reproducción no se pierda con el catálogo o `playback-metrics` caídos (cola, consumidor idempotente, DLQ y outbox) | `05-mensajeria` |
| Caché del top y del catálogo, y un almacén adecuado para la telemetría | `06-poliglota-cache` |
| Circuito compartido entre instancias, *bulkheads* y *rate limiting* | fuera del alcance del prototipo |
| Alta disponibilidad del gateway y del directorio | fuera del alcance del prototipo |

## Limitaciones conocidas y riesgos

- **El estado del circuito es por instancia y vive en memoria.** Si se escalara `users-playlists`, cada copia tendría su propio circuito, y al reiniciar el servicio vuelve a cerrado.
- **Copias desactualizadas.** Mientras el catálogo no responde, se muestran los datos de la última escritura o lectura buena: es la consistencia eventual que el PRD (§4) ya acepta.
- **1.5 s puede ser poco** para consultas pesadas con mucho historial. El valor es configurable.
- **El primer golpe a una réplica muerta todavía cuesta ~1.7 s.** Lo que se acotó es la espera, no la ventana de TTL más caché del directorio.
- **Los reintentos internos suman carga** a un catálogo lento. El circuito la corta a las 5 fallas.
- **Puntos únicos**, igual que en `03`: hay un solo gateway y un solo directorio. Consul corre en modo `-dev`.

## Etapas del recorrido

| Etapa | Rama                            | Qué muestra                                                          |
| ----- | ------------------------------- | -------------------------------------------------------------------- |
| 01    | `01-monolito`                   | La aplicación completa en un proceso, con módulos de límites claros. |
| 02    | `02-separacion`                 | Tres servicios, una base por servicio, llamadas HTTP por DNS.        |
| 03    | `03-gateway-discovery-balanceo` | Directorio, gateway, réplicas y balanceo.                            |
| 04    | `04-resiliencia`                | **Esta rama.** Timeouts, reintentos, circuit breaker y degradación.  |
| 05    | `05-mensajeria`                 | Reproducciones como eventos en un broker.                            |
| 06    | `06-poliglota-cache`            | Caché y persistencia políglota.                                      |

## Apagar

```bash
docker compose down        # detiene y conserva los datos
docker compose down -v     # borra también las bases, el audio subido y las portadas
```
