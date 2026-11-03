# MELOXO · Streaming musical (gateway, directorio y balanceo)

**MELOXO** es el nombre visible de la aplicación; el repositorio, los paquetes y los contenedores conservan el nombre del equipo, `FLDSMDFR`.

Proyecto semestral de **Sistemas Distribuidos** (Semestre 2027-1, FI-UNAM). Esta rama entrega el paso **`03-gateway-discovery-balanceo`** del plan del [PRD](docs/PRD.md). Parte de [`02-separacion`](../../tree/02-separacion), donde los tres servicios se llamaban por el DNS de Compose. Aquí **se encuentran solos**:

- cada instancia se registra en un **directorio** (Consul) y manda latidos;
- un **gateway propio** es la única puerta y reparte en **round-robin** entre las instancias vivas;
- el streaming corre en **tres réplicas**;
- las llamadas internas también se balancean, **del lado del cliente**.

Es la misma etapa que Mexi Banco en el lab S07 (Eureka + Spring Cloud Gateway), resuelta en nuestra tecnología.

## Equipo

- **Nombre del equipo:** `FLDSMDFR`
- Franco Ramírez Christian ([@ChristianFRZ](https://github.com/ChristianFRZ))
- López Hernández Miriam Amisadai ([@AmisadaiLopez](https://github.com/AmisadaiLopez))
- Nava Santiago Erick ([@Saiko-E](https://github.com/Saiko-E))
- Pérez Paitán Brent Armando ([@zmd-brnt](https://github.com/zmd-brnt))

## Qué cambió respecto a `02-separacion`

| | `02-separacion` | `03-gateway-discovery-balanceo` |
|---|---|---|
| Puerta de entrada | Nginx (`web`) reparte `/api` por prefijo | **`gateway`** (FastAPI): prefijo → directorio → round-robin |
| Cómo se encuentran los servicios | DNS de Compose (`http://catalog-streaming:8000`) | **Directorio Consul**: registro, latido TTL y baja |
| Réplicas del catálogo | 1 | **3**, con un volumen de audio compartido |
| Llamadas internas | a un nombre DNS fijo | **por nombre lógico**, balanceadas por el cliente |
| Migración y semilla del catálogo | al arrancar el servicio | una vez, en **`catalog-init`**, antes de las réplicas |
| `web` | proxy + SPA | **solo el SPA**, detrás del gateway y registrado en el directorio |
| Cabeceras | — | **`X-Instancia`** (qué réplica contestó) y **`X-Gateway-Instancia`** |

La UI y las rutas públicas (`/api/...`) no cambian.

## Dónde vive cada pieza

| Pieza | Dónde vive | Qué hace |
|---|---|---|
| **Gateway** | `services/gateway/` (contenedor `gateway`, único puerto público `:8000`) | Decide el servicio por prefijo (`app/routes.py`), pide las instancias vivas al directorio y elige una en round-robin (`app/shared/discovery.py`), y reenvía en streaming (`app/proxy.py`). |
| **Directorio** | Contenedor `discovery` (Consul 1.20, panel en <http://localhost:8500>) | Lista de instancias con su estado. Cada una se registra sola; el directorio solo sabe que sigue viva porque recibe su latido. |
| **Registro y latido** | `app/shared/discovery.py` de cada servicio, arrancado en el `lifespan` de FastAPI; `web/register.sh` para Nginx | Registro con id `<servicio>-<hostname>`, IP y check TTL; latido cada 3 s; baja al recibir SIGTERM. |
| **Balanceador del gateway** | `RoundRobin` en el gateway | Round-robin sobre la lista `passing` del directorio, cacheada 5 s. |
| **Balanceador interno** | `app/clients/http.py` de `users-playlists` y `playback-metrics` | El mismo `RoundRobin`: `catalog.get_songs_by_ids(...)` va a una réplica distinta en cada llamada. |

```text
navegador ──► :8000 gateway ── prefijo ──► ¿quién atiende?
                  │                         │
                  │ GET /v1/health/service/<nombre>?passing=true   (caché 5 s)
                  ▼                         ▼
           discovery (Consul :8500) ◄── latido cada 3 s ── todas las instancias
                  ▲
                  │ mismo directorio, mismo round-robin
   users-playlists ──► catalog-streaming ×3 ◄── playback-metrics
   playback-metrics ──► users-playlists
                      web (SPA) ◄── gateway (todo lo que no es /api)

   db: un postgres:16 con users_playlists, catalog y playback · volúmenes media y playlist-covers
```

### Tiempos del directorio

| Variable | Por omisión | Qué controla |
|---|---|---|
| `FLDSMDFR_HEARTBEAT_S` | `3` | cada cuánto manda latido cada instancia |
| `FLDSMDFR_TTL_S` | `10` | sin latido durante este tiempo, la instancia pasa a `critical` y deja de recibir tráfico |
| `FLDSMDFR_DEREGISTER_AFTER` | `1m` | en `critical` durante este tiempo, Consul la borra del registro (1 min es el mínimo de Consul) |
| `FLDSMDFR_LB_CACHE_S` | `5` | cuánto guarda cada balanceador la lista de instancias |

Se cambian sin tocar archivos, por ejemplo `FLDSMDFR_TTL_S=30 docker compose up -d`. Una réplica que muere **sin darse de baja** puede seguir recibiendo tráfico hasta unos `TTL + caché` (≈15 s).

## Inicio rápido

Requisito: Docker con Docker Compose.

```bash
cp .env.example .env     # opcional
docker compose up --build -d
docker compose ps        # catalog-init "Exited (0)"; los demás healthy (3 de catalog-streaming)
```

- Aplicación: <http://localhost:8000>
- Panel del directorio: <http://localhost:8500>
- Salud del gateway: <http://localhost:8000/api/health> (`{"status":"ok","directory":"ok"}`)

> **Si vienes de `02-separacion`:** `docker compose down` en esa rama y luego `up --build` en esta. Los volúmenes se conservan: la semilla es idempotente.

### Credenciales demo

| Rol           | Correo               | Contraseña    |
| ------------- | -------------------- | ------------- |
| Administrador | `admin@fldsmdfr.mx`  | `admin12345`  |
| Oyente        | `oyente@fldsmdfr.mx` | `oyente12345` |

## Rutas del gateway

| Prefijo público | Servicio lógico |
|---|---|
| `/api/playbacks`, `/api/metrics/`, `/api/me/history` | `playback-metrics` |
| `/api/songs` | `catalog-streaming` (3 réplicas) |
| `/api/...` (auth, users, playlists, invites, el resto de `/api/me/`) | `users-playlists` |
| `/api/health` | responde el gateway |
| `/internal/...` | **404**: la API interna no se expone |
| todo lo demás | `web` (SPA) |

Errores del gateway, con el mismo formato JSON que la API:

| Situación | Respuesta |
|---|---|
| No hay instancias vivas del servicio | `503 service_unavailable` con el nombre del servicio |
| La instancia elegida no responde | `503 service_unavailable` (sin reintento en otra; eso es `04`) |
| Subida de más de 21 MB | `422 file_too_large` en `/api/songs`, `413 image_too_large` en el resto |

## Demo: el balanceo y una réplica que muere

```bash
./scripts/demo-03.sh
```

Salida real (recortada) en esta máquina:

```text
== 2. Nueve consultas por el gateway: round-robin entre las réplicas
200 catalog-streaming-e2ccc57a28e2
200 catalog-streaming-f64ef425e61f
200 catalog-streaming-2c0bfe736dd0
200 catalog-streaming-e2ccc57a28e2
...

== 3. docker kill fldsmdfr-catalog-streaming-1 (muere SIN darse de baja)
t= 0s  200 catalog-streaming-e2ccc57a28e2  | vivas: 2c0b… e2cc… f64e…
t= 1s  503 -                               | vivas: 2c0b… e2cc… f64e…
t= 8s  200 catalog-streaming-2c0bfe736dd0  | vivas: 2c0b… e2cc… f64e…
t= 9s  200 catalog-streaming-e2ccc57a28e2  | vivas: 2c0b… e2cc…
t=10s  503 -                               | vivas: 2c0b… e2cc…
t=14s  200 catalog-streaming-e2ccc57a28e2  | vivas: 2c0b… e2cc…
t=15s… 200 alternando entre las dos réplicas que quedan

== 5. docker stop fldsmdfr-catalog-streaming-1 (SIGTERM: se da de baja antes de salir)
t= 0s  200 catalog-streaming-2c0bfe736dd0  | vivas: 2c0b… e2cc…
t= 2s  503 -                               | vivas: 2c0b… e2cc…
t= 8s… 200 alternando entre las dos réplicas que quedan
```

Cómo se lee, que es lo que se pregunta en la defensa:

1. **`kill`:** la réplica muere sin avisar y sigue apareciendo como viva unos 9 s, hasta que vence su TTL. Mientras tanto, a cada tercera petición le toca la réplica muerta.
2. **Esas peticiones no fallan de inmediato.** Se quedan colgadas unos 6–7 s, que es el timeout de conexión por omisión de `httpx` hacia una IP que ya no existe, y luego responden `503`. En `03` no hay timeouts propios ni reintento en otra réplica: es la razón de ser de la rama `04`.
3. **Cuando el directorio ya no la anuncia,** la caché del balanceador (5 s) todavía alcanza a mandarle una petición más. Después, todo va a las dos réplicas que quedan.
4. **`docker start`:** la réplica se vuelve a registrar con el mismo id y recibe tráfico de nuevo en cuanto la caché se refresca.
5. **`stop`:** sale del directorio al instante, porque se da de baja. Solo la caché del gateway puede mandarle alguna petición antes de enterarse.

El balanceo interno se ve en los logs. Abre un casete varias veces y cuenta las llamadas `POST /internal/songs/batch` en cada réplica (`docker logs fldsmdfr-catalog-streaming-N`): se reparten por igual (2/2/2 con seis aperturas).

## Contratos internos

Igual que en `02`: `catalog-streaming` expone `GET /songs/{id}`, `POST /songs/batch`, `GET /songs/count`, `GET /songs/lookup`, `POST /artists/counts`, `POST /artists/latest` y `POST /artists/releases` bajo `/internal`; `users-playlists` expone `GET /internal/users/count`. Lo que cambia es **cómo se llega**: `http.call("catalog-streaming", ...)` pide la lista al directorio y elige una instancia en round-robin. Sin instancias vivas o sin respuesta → `503 service_unavailable`; un `404` remoto → el mismo `NotFound` de siempre.

## Pruebas

```bash
docker compose --profile test run --rm tests-catalog
docker compose --profile test run --rm tests-users
docker compose --profile test run --rm tests-playback
docker compose --profile test run --rm tests-gateway
docker compose --profile test run --rm tests-gateway ruff check .   # igual en los demás
cd ui && npm ci && npm test && npm run build
```

- **Directorio:** las pruebas de registro, latido, baja, caché y round-robin (`tests/test_discovery.py` en cada servicio) usan un Consul falso en memoria (`tests/fake_consul.py`).
- **Balanceo de los clientes:** `tests/test_client_balancing.py` registra dos instancias falsas y comprueba que las llamadas alternan.
- **Gateway:** sus pruebas (`services/gateway/tests/`) cubren:
  - rutas por prefijo y round-robin;
  - `503` sin instancias o con una instancia muerta;
  - `/internal` bloqueado y `Range` con `206`;
  - varias cabeceras `Set-Cookie`, subidas y límite de tamaño;
  - la caché del balanceador.

## Mapa de carpetas

```text
services/
  gateway/             app/{main,routes,proxy,config}.py, app/shared/discovery.py, tests/
  catalog-streaming/   app/modules/catalog/, app/shared/discovery.py, scripts/{init,entrypoint}.sh
  users-playlists/     app/modules/{users,playlists,social}/, app/clients/, app/shared/discovery.py
  playback-metrics/    app/modules/playback/, app/clients/, app/shared/discovery.py
web/                   SPA con Nginx y register.sh (registro en el directorio)
scripts/demo-03.sh     demo de balanceo y caída de una réplica
docker/initdb/         crea las tres bases y sus copias _test
```

## Qué queda fuera (y en qué rama llega)

| Falta | Rama |
|---|---|
| Timeouts propios, reintento en otra réplica, circuit breaker, degradación donde hoy hay `503` | `04-resiliencia` |
| Reproducciones como eventos en RabbitMQ, consumidor idempotente, DLQ y outbox | `05-mensajeria` |
| Caché del top y del catálogo, almacén adecuado para la telemetría | `06-poliglota-cache` |
| Alta disponibilidad del gateway y del directorio | fuera del alcance del prototipo |

## Limitaciones conocidas y riesgos

- **Puntos únicos:** hay un solo gateway y un solo directorio.
  - Si cae el gateway, no hay entrada al sistema.
  - Si cae el directorio, las cachés sirven hasta 5 s y después nadie encuentra a nadie (`503`). Las sesiones y los datos no se pierden.
- **Ventana de falla:** con los tiempos por omisión, una réplica muerta sin baja recibe tráfico hasta unos 15 s. Cada petición que le toca tarda unos 7 s en fallar.
- **Volumen compartido:** las tres réplicas leen y escriben el mismo volumen `media`. Una subida hecha en una réplica la ven las otras porque es el mismo disco, no por replicación.
- **Consul en modo `-dev`:** guarda todo en memoria, sin ACL ni TLS. Si se reinicia, cada instancia se vuelve a registrar en su siguiente latido.
- **`/internal` sin autenticación** (igual que en `02`) y **código transversal copiado** por servicio (`shared/`, `discovery.py`, clientes).
- **Salto extra:** el gateway en Python agrega un salto y CPU al streaming. Es aceptable para el prototipo.

## Etapas del recorrido

| Etapa | Rama | Qué muestra |
|---|---|---|
| 01 | `01-monolito` | La aplicación completa en un proceso, con módulos de límites claros. |
| 02 | `02-separacion` | Tres servicios, una base por servicio, llamadas HTTP por DNS. |
| 03 | `03-gateway-discovery-balanceo` | **Esta rama.** Directorio, gateway, réplicas y balanceo. |
| 04 | `04-resiliencia` | Timeouts, reintentos, circuit breaker y degradación. |
| 05 | `05-mensajeria` | Reproducciones como eventos en un broker. |
| 06 | `06-poliglota-cache` | Caché y persistencia políglota. |

## Apagar

```bash
docker compose down        # detiene y conserva los datos
docker compose down -v     # borra también las bases, el audio subido y las portadas
```
