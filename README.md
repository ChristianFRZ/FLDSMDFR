# MELOXO · Streaming musical (separación en servicios)

**MELOXO** es el nombre visible de la aplicación; el repositorio, los paquetes y los contenedores conservan el nombre del equipo, `FLDSMDFR`.

Proyecto semestral de **Sistemas Distribuidos** (Semestre 2027-1, FI-UNAM). Esta rama entrega el paso **`02-separacion`** del plan del [PRD](docs/PRD.md): el monolito modular de [`01-monolito`](../../tree/01-monolito) se parte en **tres servicios con su propia base de datos**, que se hablan **por HTTP** usando los nombres DNS de Docker Compose. Es la misma etapa que recorre Mexi Banco en el curso (`01-monolito` → `02-separacion`).

## Equipo

- **Nombre del equipo:** `FLDSMDFR`
- Franco Ramírez Christian ([@ChristianFRZ](https://github.com/ChristianFRZ))
- López Hernández Miriam Amisadai ([@AmisadaiLopez](https://github.com/AmisadaiLopez))
- Nava Santiago Erick ([@Saiko-E](https://github.com/Saiko-E))
- Pérez Paitán Brent Armando ([@zmd-brnt](https://github.com/zmd-brnt))

## Qué cambió respecto a `01-monolito`

| | `01-monolito` | `02-separacion` |
|---|---|---|
| Procesos | 1 FastAPI | 3 FastAPI + 1 Nginx |
| Bases de datos | 1 (`fldsmdfr`) | 3 (`users_playlists`, `catalog`, `playback`) en la misma instancia de PostgreSQL |
| Llamadas entre módulos | `import` de `service.py` | HTTP a `/internal/...` con `httpx` |
| Quién sirve la UI | FastAPI (`app/spa.py`) | `web` (Nginx) |
| Si `catalog` falla | falla una función dentro del mismo proceso | el servicio sigue vivo; quien lo llama recibe `503` o se degrada |

La UI y las rutas públicas (`/api/...`) **no cambian**: el navegador sigue hablando con un único origen, `http://localhost:8000`.

## Diagrama de contenedores

```text
navegador ──► :8000  web (Nginx: SPA + reparto de /api por prefijo)
                      │                    │                       │
       /api/auth, /users, /playlists,   /api/songs        /api/playbacks, /api/metrics/,
       /invites, /me/*                     │               /api/me/history
                      ▼                    ▼                       ▼
              users-playlists      catalog-streaming       playback-metrics
                      │                    ▲    ▲                  │
                      └── HTTP /internal ──┘    └─ HTTP /internal ─┤
                      ▲                                            │
                      └────────────── HTTP /internal (conteo) ─────┘
                      │                    │                       │
             base users_playlists     base catalog           base playback
             vol. playlist-covers     vol. media (audio)
                      └──────────── un solo postgres:16 (db) ──────┘
```

| Servicio | Módulos | Dueño de | Llama a |
|---|---|---|---|
| `users-playlists` | `users`, `playlists`, `social` | usuarios, casetes, miembros, invitaciones, favoritas, artistas seguidos, avisos leídos, portadas de casetes | `catalog-streaming` |
| `catalog-streaming` | `catalog` | canciones, archivos de audio y portadas de canciones | — |
| `playback-metrics` | `playback` | eventos de reproducción, historial y contadores | `catalog-streaming`, `users-playlists` |
| `web` | — | SPA compilado | los tres, por prefijo |

Solo `users-playlists` emite los JWT de sesión; los otros dos los validan localmente con el mismo secreto (`FLDSMDFR_JWT_SECRET`), sin preguntarle a nadie.

## Inicio rápido

Requisito: Docker con Docker Compose.

```bash
cp .env.example .env     # opcional: sin .env se usan los mismos valores por defecto
docker compose up --build -d
docker compose ps        # espera 5 contenedores healthy: db, los 3 servicios y web
```

- Aplicación: <http://localhost:8000>
- Salud del proxy: <http://localhost:8000/api/health>

Solo se publica el puerto **8000**. Los servicios escuchan en el `8000` de la red interna de Compose (`http://catalog-streaming:8000`, etc.) y su Swagger queda dentro de esa red, por ejemplo:

```bash
docker compose exec catalog-streaming curl -s localhost:8000/openapi.json | head -c 300
```

Al arrancar, cada servicio aplica sus migraciones. `catalog-streaming` importa las canciones de `media/seed/` y `users-playlists` crea los usuarios demo y el casete demo, resolviendo cada canción contra el catálogo por HTTP (por eso arranca después de que el catálogo esté `healthy`).

> **Si vienes de `01-monolito`:** esta rama usa un volumen nuevo de PostgreSQL (`pgdata-servicios`) porque las tres bases se crean al iniciar un volumen vacío. El volumen `pgdata` del monolito no se toca. Detén el contenedor del monolito si sigue ocupando el puerto 8000.

### Credenciales demo

| Rol           | Correo               | Contraseña    |
| ------------- | -------------------- | ------------- |
| Administrador | `admin@fldsmdfr.mx`  | `admin12345`  |
| Oyente        | `oyente@fldsmdfr.mx` | `oyente12345` |

## Rutas del proxy

| Prefijo público | Servicio |
|---|---|
| `/api/playbacks`, `/api/metrics/`, `/api/me/history` | `playback-metrics` |
| `/api/songs` (streaming sin buffer, con `Range`) | `catalog-streaming` |
| `/api/...` (auth, users, playlists, invites, el resto de `/api/me/`) | `users-playlists` |
| `/api/health` | responde el proxy |
| `/internal/...` | **404**: la API interna no se expone |
| todo lo demás | SPA (`index.html` para Vue Router) |

Nginx resuelve el nombre del servicio en cada petición (DNS embebido de Docker, `127.0.0.11`). Si un servicio está apagado, el proxy sigue arriba y responde `503` con el formato de error de la API.

## Contratos internos

`catalog-streaming` (`/internal`): `GET /songs/{id}`, `POST /songs/batch`, `GET /songs/count`, `GET /songs/lookup`, `POST /artists/counts`, `POST /artists/latest`, `POST /artists/releases`.
`users-playlists` (`/internal`): `GET /users/count`.

Cada servicio consumidor tiene un cliente en `app/clients/` que conserva el nombre y el tipo de retorno de la función que antes importaba (`catalog.get_song(id)`, `catalog.get_songs_by_ids(ids)`, …). Las fallas se traducen así:

| Respuesta remota | Lo que ve el cliente de la API |
|---|---|
| `404` | el mismo `404` de antes (`song_not_found`) |
| sin conexión o `5xx` | `503` `service_unavailable`, con el nombre del servicio |

## Demo: qué pasa si se cae el catálogo

En esta rama **no hay timeouts propios, reintentos ni circuit breaker**: se dejan ver a propósito, como en el `--roto` de Mexi Banco 02.

```bash
docker compose stop catalog-streaming
```

| Acción | Resultado |
|---|---|
| Iniciar sesión, listar casetes, `/api/auth/me` | `200`: no necesitan al catálogo |
| Abrir un casete | `200` **degradado**: canciones con estado `degraded` a partir de las copias guardadas (comportamiento heredado del monolito) |
| "Lo más escuchado" (`/api/metrics/top`) | `200` degradado: "Canción no disponible" con sus conteos |
| Catálogo, streaming, portadas | `503` desde el proxy |
| Marcar favorita, registrar reproducción, historial | `503` `service_unavailable` (`El servicio catalog-streaming no está disponible…`) |

```bash
docker compose start catalog-streaming   # todo vuelve a responder 200
```

Lo mismo con `docker compose stop users-playlists`: el resumen de métricas del administrador responde `503`, pero el streaming sigue funcionando para quien ya tiene sesión (el JWT se valida en cada servicio). La rama `04` agrega timeouts, reintentos con backoff, circuit breaker y degradación donde hoy hay `503`.

## Pruebas

```bash
# Backend, un servicio a la vez (cada uno usa su base _test)
docker compose --profile test run --rm tests-catalog
docker compose --profile test run --rm tests-users
docker compose --profile test run --rm tests-playback

# Lint
docker compose --profile test run --rm tests-users ruff check .   # igual para tests-catalog y tests-playback

# Frontend (Vitest) y build con verificación de tipos
cd ui && npm ci && npm test && npm run build
```

En las pruebas de `users-playlists` y `playback-metrics` los otros servicios se sustituyen por versiones falsas en memoria con el mismo contrato `/internal` (`tests/fake_catalog.py`, `tests/fake_users.py`), conectadas por un transporte ASGI de `httpx`: el código bajo prueba hace peticiones HTTP de verdad. Cada servicio tiene un `tests/test_architecture.py` que verifica que no importe código de otro.

## Desarrollo de la interfaz

Con todo corriendo en el puerto 8000:

```bash
cd ui && npm ci && npm run dev
```

Vite reenvía `/api` a `localhost:8000` (el proxy). Requiere Node >= 22.12.

## Agregar música

1. Copia el archivo `.mp3`, `.ogg` o `.wav` (máximo 20 MB) en `media/seed/`.
2. Agrega una entrada en `songs` de `media/seed/seed.json`: `{"file": "nombre.mp3", "title": "Título", "artist": "Artista", "album": "Álbum"}`.
3. Para incluirla en el casete demo, agrega el nombre del archivo en `demo_playlist.files`.
4. Registra la fuente y la licencia en [`media/seed/LICENCIAS.md`](media/seed/LICENCIAS.md).
5. `docker compose up --build -d`. Ambas semillas son idempotentes.

También se pueden subir canciones desde la cabina (solo administradores) o con `POST /api/songs`.

## Mapa de carpetas

```text
services/
  catalog-streaming/   app/{main,config}.py, app/modules/catalog/ (+ internal_router.py), db/, shared/, scripts/, tests/
  users-playlists/     app/modules/{users,playlists,social}/, app/clients/catalog.py, db/, shared/, scripts/, tests/
  playback-metrics/    app/modules/playback/, app/clients/{catalog,users}.py, db/, shared/, tests/
web/                   Dockerfile (compila ui/ y lo sirve con Nginx) y nginx.conf
ui/src/                interfaz (sin cambios respecto a 01)
docker/initdb/         crea las tres bases y sus copias _test
media/seed/            música semilla, seed.json y LICENCIAS.md
docs/                  PRD, diseño y plan de esta rama
```

## Qué queda fuera (y en qué rama llega)

| Falta | Rama |
|---|---|
| Gateway con balanceo, varias réplicas de `catalog-streaming` y directorio de servicios | `03-gateway-discovery-balanceo` |
| Timeouts, reintentos con backoff, circuit breaker, degradación donde hoy hay `503` | `04-resiliencia` |
| Eventos de reproducción por broker (RabbitMQ), consumidor idempotente, DLQ y outbox | `05-mensajeria` |
| Caché del top y del catálogo, almacén adecuado para la telemetría | `06-poliglota-cache` |

## Limitaciones conocidas y riesgos

- **`/internal` sin autenticación:** se confía en la red de Compose; solo es aceptable porque el proxy no la expone.
- **Código transversal copiado:** `shared/` (errores, JWT, imágenes) y los clientes HTTP están duplicados en cada servicio, como el `compartido/` de Mexi Banco. Un arreglo de seguridad se replica a mano en cada uno.
- **Más latencia:** vistas que antes eran un solo proceso (detalle de casete, favoritas, inicio) ahora hacen una o dos llamadas de red.
- **Sin transacción entre servicios:** agregar una canción a un casete valida la canción en el catálogo y luego escribe en otra base; si el catálogo la retira entre ambos pasos, el casete conserva la copia y la marca `unavailable` al leer.
- **Semilla del casete demo:** si el catálogo deja de responder a mitad de la semilla, el casete puede quedar incompleto y no se vuelve a llenar en el siguiente arranque.
- **Rol dentro del JWT:** igual que en `01`, el rol viaja en el token; tras un cambio de rol, la sesión abierta conserva el anterior hasta la siguiente llamada a `/api/auth/me`.
- **Configuración de seguridad:** `FLDSMDFR_COOKIE_SECURE` debe ser `true` detrás de HTTPS y el secreto JWT por defecto debe cambiarse fuera de desarrollo local.

## Etapas del recorrido

| Etapa | Rama | Qué muestra |
|---|---|---|
| 01 | `01-monolito` | La aplicación completa en un proceso, con módulos de límites claros. |
| 02 | `02-separacion` | **Esta rama.** Tres servicios, una base por servicio, llamadas HTTP. |
| 03 | `03-gateway-discovery-balanceo` | Gateway, directorio y réplicas del streaming. |
| 04 | `04-resiliencia` | Timeouts, reintentos, circuit breaker y degradación. |
| 05 | `05-mensajeria` | Reproducciones como eventos en un broker. |
| 06 | `06-poliglota-cache` | Caché y persistencia políglota. |

## Apagar

```bash
docker compose down        # detiene y conserva los datos
docker compose down -v     # borra también las bases, el audio subido y las portadas
```
