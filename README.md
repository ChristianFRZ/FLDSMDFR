# MELOXO

Tu Casetera de Confianza. MELOXO es un servicio de streaming musical que gira alrededor del casete compartido: hasta 12 pistas en dos lados, armado entre amigos, con dedicatorias y repartido por enlace. No hay feed ni recomendaciones: la música se descubre porque alguien te la regala.

Es el proyecto de la materia de Sistemas Distribuidos del equipo FLDSMDFR: Christian Franco Ramírez, Miriam Amisadai López Hernández, Erick Nava Santiago y Brent Armando Pérez Paitán.

Esta rama, `04-resiliencia-concurrencia`, parte del gateway y las dos réplicas de catálogo de `03-gateway-balanceo` y hace que una falla no se propague: las llamadas entre servicios tienen tiempos de espera, reintentos y un circuit breaker; las reproducciones pasan por una cola en Redis, así que no se pierden si `playback-metrics` cae; y un cambio de rol o una suspensión se ve en la siguiente petición, no 30 s después. El producto es el mismo; cambia cómo está armado por dentro. La rama siguiente, `05-mensajeria`, es una propuesta.

## Con qué está hecho

| Parte | Tecnologías |
| --- | --- |
| Servicios | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Entrada | nginx con `auth_request`, que también sirve la interfaz compilada |
| Base de datos | PostgreSQL 16, una base y un rol por servicio |
| Interfaz | React 18, TypeScript, Vite, TanStack Query, Chart.js |
| Música | Catálogo de Jamendo y pistas que suben los Compositores |
| Pruebas | pytest, Vitest, Playwright, axe, Locust |
| Despliegue | Docker y Docker Compose |

## Arquitectura

Ocho contenedores de larga vida (seis servicios, con `catalog-streaming` en dos réplicas): `edge`, `gateway-auth`, los tres servicios de negocio, `postgres` y `redis`, más `seed`, que solo corre cuando se le pide. Solo `edge` y, en `127.0.0.1:5433`, PostgreSQL publican puertos al host; los servicios se hablan por la red interna de Compose.

```text
Navegador ──► edge :8080 (nginx)
                │  /*     interfaz de React
                │  /api/* auth_request ──► gateway-auth :8004 ──► users-playlists (estado de la cuenta)
                │         y después, reparto por prefijo
                ├──► users-playlists :8001   ──► base users_playlists
                ├──► catalog-streaming :8002 (×2 réplicas, con failover) ──► base catalog (+ volumen media)
                │        └─ POST /api/playbacks ──► redis (stream playbacks) ──┐
                └──► playback-metrics :8003  ──► base playbacks ◄── consume ───┘

Entre servicios: HTTP por /internal/* (1.5 s de espera, reintentos en lecturas y circuit breaker; sin autenticación, no publicadas por nginx)
Redis: la cola de reproducciones y la lista de revocación de sesiones (sin puerto publicado)
```

| Servicio | Responsabilidad | Puerto interno |
| --- | --- | --- |
| [`users-playlists`](services/users-playlists/README.md) | Cuentas, roles, solicitudes de Compositor, auditoría, playlists, favoritas, seguidos, casetes, invitaciones y avisos | 8001 |
| [`catalog-streaming`](services/catalog-streaming/README.md) | Canciones, artistas, importación de Jamendo, subidas, publicación programada y audio | 8002 |
| [`playback-metrics`](services/playback-metrics/README.md) | Reproducciones, agregados, gráficas, latencia y salud | 8003 |
| [`gateway-auth`](services/gateway-auth/README.md) | Valida el JWT y el rol que nginx le consulta con `auth_request`; no tiene base de datos | 8004 |
| [`edge`](edge/README.md) | Entrada única: valida sesión y rol, reparte rutas y reintenta con la otra réplica de catálogo; si un servicio no responde, devuelve el error JSON de la API | 80 (8080 en el host) |

Lo que ya no pasa dentro de un proceso ahora es una llamada HTTP: users-playlists pide pistas a catalog-streaming, y playback-metrics pide pistas a catalog-streaming y el estado de cada cuenta a users-playlists. Cada servicio guarda 30 s el estado de las cuentas, y si el origen cae usa el último conocido. Un cambio de rol o una suspensión, en cambio, se ve en la siguiente petición: `users-playlists` escribe una revocación en Redis y `gateway-auth` y los servicios la consultan antes de la caché (si Redis cae, manda la caché de 30 s). Las reproducciones entran por `catalog-streaming`, que las valida y las encola en Redis; `playback-metrics` las aplica al volver, así que no se pierden si cae. Lo compartido (errores, JWT, cliente interno, autenticación) vive en [`services/common`](services/common/README.md).

## Cómo levantarlo

Necesitas Docker con Compose. Corre esto desde la raíz del repositorio:

```bash
cp .env.example .env                              # después, completa los valores
docker compose up --build -d                      # la app queda en http://localhost:8080
docker compose run --rm seed python -m seed all   # opcional: catálogo y actividad de demo
```

Las variables de `.env` se explican en [Variables de entorno](#variables-de-entorno). Para `POSTGRES_PASSWORD`, `JWT_SECRET` y las tres claves de rol (`USERS_DB_PASSWORD`, `CATALOG_DB_PASSWORD`, `PLAYBACKS_DB_PASSWORD`) sirve cualquier cadena larga, como la que genera `openssl rand -hex 32`. Compose se niega a arrancar si falta alguna de ellas, y los servicios no aceptan un `JWT_SECRET` de menos de 32 caracteres.

> **Si vienes de la rama 01, el volumen de PostgreSQL del monolito no sirve.** `infra/postgres/init.sh` crea las tres bases solo cuando el volumen `pgdata` está vacío. Para estrenarlo hay que correr `docker compose down -v`, que **borra la base de datos y los archivos subidos**, y volver a sembrar. Esa orden también sirve cuando cambias `init.sh` o las claves de los roles. No la uses si tienes datos que quieras conservar.

La semilla tarda cerca de un minuto y necesita `JAMENDO_CLIENT_ID` para importar el catálogo. Sin esa llave, `docker compose run --rm seed python -m seed activity` carga pistas locales y actividad simulada. Para borrar lo simulado, corre `docker compose run --rm seed python -m seed clear`. Los demás subcomandos están en [`seed/`](seed/README.md).

Con la app en marcha, cada servicio publica su documentación interactiva dentro de la red de Docker, no en el host. Para apagar todo, usa `docker compose down`; agrega `-v` solo si quieres borrar los datos.

### Probarlo desde una URL fija

Para pruebas fuera de `localhost`, [Tailscale Funnel](https://tailscale.com/kb/1223/funnel) publica la app en una dirección HTTPS fija, con la forma `https://<equipo>.<tailnet>.ts.net`. La app sigue corriendo en tu computadora, así que la URL solo responde si el equipo está prendido y Docker en marcha.

> La URL es pública: cualquiera que la conozca llega a la app. Antes de activarla, cambia las contraseñas de las cuentas de administrador y de demo. Cambiar `.env` no modifica las cuentas que ya existen.

```bash
curl -fsSL https://tailscale.com/install.sh | sh   # solo la primera vez
sudo tailscale up                                  # abre el inicio de sesión en el navegador
tailscale funnel --bg 8080                         # la primera vez pide habilitar Funnel en un enlace
tailscale funnel status                            # muestra la URL
```

Con `--bg`, la publicación sigue activa después de reiniciar el equipo. Para retirarla, usa `tailscale funnel reset`. Funnel tiene límites de ancho de banda y la dirección nueva puede tardar hasta 10 minutos en responder.

### Cuentas de acceso

Las contraseñas son las que definas en `.env`. El archivo [`.env.example`](.env.example) las deja vacías, así que no hay una contraseña predeterminada.

| Rol | Correos | Contraseña | Qué puede hacer |
| --- | --- | --- | --- |
| **Administrador** | El de `ADMIN_EMAIL` | `ADMIN_PASSWORD` | Ver las métricas del sistema, aprobar Compositores y consultar la auditoría |
| **Administrador** | `admin00@demo.meloxo.dev`<br>`admin01@demo.meloxo.dev` | `DEMO_PASSWORD` | Lo mismo que el anterior |
| **Compositor** | De `compositor00@demo.meloxo.dev`<br>a `compositor09@demo.meloxo.dev` | `DEMO_PASSWORD` | Subir temas propios y portadas, y ver sus métricas de artista |
| **Oyente** | De `oyente00@demo.meloxo.dev`<br>a `oyente59@demo.meloxo.dev` | `DEMO_PASSWORD` | Crear y escuchar casetes compartidos, playlists y favoritos |

El primer administrador lo crea `users-playlists` al arrancar, solo si todavía no hay ninguno. Por eso, cambiar `ADMIN_EMAIL` o `ADMIN_PASSWORD` después no modifica esa cuenta. Las cuentas `@demo.meloxo.dev` solo existen después de correr la semilla.

> Si `DEMO_PASSWORD` está vacía al correr la semilla, se genera una contraseña al azar y se imprime en la terminal al terminar.

## Variables de entorno

Estas van en `.env`; [`.env.example`](.env.example) es la plantilla:

| Variable | Para qué sirve |
| --- | --- |
| `POSTGRES_PASSWORD` | Contraseña del superusuario `meloxo` de PostgreSQL. Las pruebas la leen de aquí |
| `USERS_DB_PASSWORD`, `CATALOG_DB_PASSWORD`, `PLAYBACKS_DB_PASSWORD` | Claves de los roles de cada servicio. Las usa [`init.sh`](infra/postgres/init.sh) y Compose arma con ellas el `DATABASE_URL` de cada servicio |
| `JWT_SECRET` | Firma de las sesiones. Es la misma para los tres servicios y para `gateway-auth` |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Primer administrador, creado al arrancar si todavía no hay ninguno |
| `DEMO_PASSWORD` | Contraseña de las cuentas de demo. Si está vacía, se genera una al azar |
| `JAMENDO_CLIENT_ID` | Llave de Jamendo. Va solo en `.env`, nunca en archivos versionados |
| `JAMENDO_AUDIO_MODE` | `proxy` (por defecto) o `redirect` |

Estas otras tienen un valor por defecto y casi nunca hay que tocarlas. Cada una se define en la configuración de su servicio. **Ponerlas en `.env` no basta:** solo llegan a un contenedor las variables que `compose.yaml` pasa en su `environment`, y de esta tabla Compose no pasa ninguna (`JAMENDO_API_URL` solo la fija `compose.demo.yaml`). Para cambiar una hay que agregarla al `environment` del servicio en `compose.yaml`; mientras tanto rige el valor por defecto.

| Variable | Por defecto | Servicio | Para qué sirve |
| --- | --- | --- | --- |
| `TAPE_MAX_TRACKS` | `12` | users-playlists | Pistas por casete |
| `TAPE_MAX_MEMBERS` | `8` | users-playlists | Miembros por casete |
| `COMPOSER_MAX_TRACKS` | `20` | catalog-streaming | Pistas por Compositor |
| `UPLOAD_MAX_MP3_MB` | `15` | catalog-streaming | Peso máximo del MP3 |
| `UPLOAD_MAX_COVER_MB` | `2` | catalog-streaming | Peso máximo de la portada |
| `UPLOAD_MAX_MINUTES` | `10` | catalog-streaming | Duración máxima de una pista |
| `JAMENDO_API_URL` | `https://api.jamendo.com/v3.0` | catalog-streaming | API de Jamendo. El escenario 3 la cambia para simular la caída |
| `MEDIA_DIR` | `/media` | catalog-streaming, playback-metrics | Dónde se guardan el audio y las portadas |
| `APP_VERSION` | `04-resiliencia-concurrencia` | playback-metrics, gateway-auth | Versión que muestra la sección de Salud |
| `AUTH_CACHE_SECONDS` | `30` | los tres y gateway-auth | Cuánto se recuerda el estado de una cuenta |
| `USERS_URL` | `http://users-playlists:8001` | gateway-auth | Dónde pide el estado de la cuenta. Compose lo pasa |
| `REDIS_URL` | `redis://redis:6379/0` | los cuatro servicios | Redis de la cola y la revocación. Compose lo pasa; vacío lo desactiva (así corren las pruebas) |
| `INTERNAL_TIMEOUT_SECONDS` | `1.5` | los tres y gateway-auth | Espera de lectura por llamada entre servicios (la de conexión es de 1 s) |
| `DISABLE_SCHEDULER` | `false` | los tres | Apaga las tareas periódicas. Lo usan las pruebas |

Los valores están en [`meloxo_common/config.py`](services/common/meloxo_common/config.py) y en el `config.py` de cada servicio.

## Estructura del repositorio

```text
MELOXO/
├── services/
│   ├── common/              # paquete meloxo_common, compartido
│   ├── users-playlists/     # servicio :8001
│   ├── catalog-streaming/   # servicio :8002
│   ├── playback-metrics/    # servicio :8003
│   └── gateway-auth/        # validador de sesión y rol :8004
├── edge/                    # nginx de entrada y su configuración
├── infra/
│   └── postgres/            # crea una base y un rol por servicio
├── seed/                    # datos de demo, por las rutas /internal/demo
├── frontend/
│   ├── e2e/                 # pruebas de navegador
│   ├── public/              # íconos y manifiesto
│   └── src/                 # código de la interfaz
├── demo/                    # escenarios del PRD y prueba de carga
├── tests/                   # pruebas que miran el repositorio entero
├── docs/
│   ├── prd.md               # requisitos del producto
│   ├── specs/               # diseños aprobados
│   ├── plans/               # planes de implementación
│   ├── decisions/           # lo que se decidió sobre la marcha
│   ├── design/              # maqueta de la interfaz
│   └── brand/               # logo y guía de marca
├── compose.yaml             # postgres, los servicios, gateway-auth, edge y seed
├── compose.demo.yaml        # overlay de los escenarios 3 y 8
├── .env.example             # plantilla de variables
└── LICENSE                  # licencia MIT
```

Para seguir leyendo, entra por el README de cada parte:

| Parte | Empieza aquí |
| --- | --- |
| Los servicios y lo que comparten | [`services/`](services/README.md) |
| Entrada y reparto de rutas | [`edge/`](edge/README.md) |
| Bases de datos | [`infra/`](infra/README.md) |
| Datos de demo | [`seed/`](seed/README.md) |
| Interfaz web | [`frontend/`](frontend/README.md) |
| Escenarios y prueba de carga | [`demo/`](demo/README.md) |
| Requisitos, diseños y marca | [`docs/`](docs/README.md) |

Cada carpeta tiene su README, y [`test_readmes.py`](tests/test_readmes.py) falla si falta alguno. Dentro de `docs/brand/`, esa comprobación no entra en las subcarpetas, porque contienen archivos de logo. Las reglas de nombres y sus motivos se explican en [`docs/`](docs/README.md#cómo-se-nombran-las-cosas).

## Fronteras

Cada servicio es dueño de sus tablas y no hay llaves foráneas entre bases. Dentro de un servicio, cada módulo es dueño de su tema y solo entra a otro por su `public.py` o, entre servicios, por HTTP. [`boundaries.py`](services/common/meloxo_common/boundaries.py) detecta los imports prohibidos y cada servicio lo ejecuta en su prueba de fronteras. Las llaves foráneas no las revisa ninguna prueba. [`infra/tests`](infra/tests/README.md) comprueba que un servicio no pueda abrir la base de otro.

| Servicio | Módulos |
| --- | --- |
| `users-playlists` | [`users`](services/users-playlists/users_playlists/modules/users/README.md), [`playlists`](services/users-playlists/users_playlists/modules/playlists/README.md), [`social`](services/users-playlists/users_playlists/modules/social/README.md) |
| `catalog-streaming` | [`catalog`](services/catalog-streaming/catalog_streaming/modules/catalog/README.md) |
| `playback-metrics` | [`playback`](services/playback-metrics/playback_metrics/modules/playback/README.md), [`analytics`](services/playback-metrics/playback_metrics/modules/analytics/README.md) |

## Pruebas

Las pruebas de cada servicio leen `POSTGRES_PASSWORD` de `.env`, así que hace falta ese archivo, y usan PostgreSQL en `localhost:5433` con el superusuario `meloxo`. Cada una crea su propia base `<servicio>_test`. Todos los comandos se corren desde la raíz del repositorio:

```bash
docker compose up -d postgres
python3 -m venv .venv                       # solo la primera vez

# Cada servicio, contra un PostgreSQL real (el mismo patrón en los tres; gateway-auth no la necesita)
.venv/bin/pip install -e services/common -e 'services/users-playlists[dev]'
(cd services/users-playlists && ../../.venv/bin/pytest -q)
.venv/bin/pip install -e 'services/catalog-streaming[dev]'
(cd services/catalog-streaming && ../../.venv/bin/pytest -q)
.venv/bin/pip install -e 'services/playback-metrics[dev]'
(cd services/playback-metrics && ../../.venv/bin/pytest -q)
.venv/bin/pip install -e 'services/gateway-auth[dev]'   # sin base de datos
(cd services/gateway-auth && ../../.venv/bin/pytest -q)

# Lo compartido, la entrada y el repositorio
.venv/bin/pip install -e 'services/common[dev]'
(cd services/common && ../../.venv/bin/pytest -q)
.venv/bin/pytest edge/tests -q -m "not stack"    # con -m stack, necesita el stack arriba
.venv/bin/pytest infra/tests tests -q

# Interfaz, con Vitest
(cd frontend && npm install && npm test)

# Navegador, con la app en marcha
(cd frontend && npx playwright install chromium && npm run e2e)

# Escenarios del PRD, con la app en marcha y la semilla cargada
for f in demo/scenario_*.py; do python3 "$f"; echo "$f -> código $?"; done
```

La semilla y la demo tienen sus propias pruebas: `seed/tests` (ver [`seed/tests/README.md`](seed/tests/README.md)) y `demo/test_common.py`. Cada parte tiene más detalle en su README: [navegador](frontend/e2e/README.md), [escenarios y prueba de carga](demo/README.md) y el de cada servicio.

### Prueba de carga

Locust no es una dependencia del proyecto, así que se instala aparte. Con la pila arriba y sembrada, desde la raíz:

```bash
python3 -m venv /tmp/locust && /tmp/locust/bin/pip install locust
/tmp/locust/bin/locust -f demo/locustfile.py --headless -u 50 -r 10 -t 2m --host http://localhost:8080 --only-summary
```

Los resultados y sus límites están en [`demo/`](demo/README.md#prueba-de-carga).

## Estado de los criterios

Verificado el 2026-11-14 sobre el stack en marcha (`seed activity`, porque `JAMENDO_CLIENT_ID` estaba vacía): 85 pruebas de `common`, 182 de `users-playlists`, 169 de `catalog-streaming`, 109 de `playback-metrics`, 14 de `gateway-auth`, 115 de `edge` (14 de ellas contra el stack), 17 de `demo` y 144 de frontend. Los escenarios 1, 2, 4 a 8, 10 y 11 pasan; el 3 no se corrió y `seed all` tampoco: ambos siguen sin verificar hasta tener una llave real de Jamendo. También pasaron `seed/tests` (18), `infra/tests` (7) y `tests` (2). Las pruebas de navegador (Playwright) no se repitieron en esta rama. Las mediciones de carga son de la corrida del 2026-11-14, en `docker compose` local y sin una red real de por medio. Los criterios completos están en la [sección 6 del PRD](docs/prd.md#6-historias-de-usuario-y-criterios-de-aceptación), y los resultados y avisos de la rama, en [`docs/decisions/04-resiliencia-concurrencia.md`](docs/decisions/04-resiliencia-concurrencia.md#resultados-de-la-verificación).

La columna Evidencia dice dónde se comprueba cada criterio; las mediciones marcadas con 01 salen de la corrida del monolito (2026-11-06) y no se repitieron.

| Criterio | Estado | Evidencia |
| --- | --- | --- |
| F1.1 Registro e inicio de sesión con JWT | Cumple | [`test_auth.py`](services/users-playlists/tests/modules/users/test_auth.py) |
| F1.2 Lista ligada al usuario del token | Cumple | [`test_playlists.py`](services/users-playlists/tests/modules/playlists/test_playlists.py) |
| F1.3 Reagregar es idempotente | Cumple | [`test_playlists.py`](services/users-playlists/tests/modules/playlists/test_playlists.py) |
| F1.4 `GET /api/playlists/{id}` p95 < 200 ms | Cumple | 94 ms con 50 clientes |
| F1.5 Lista degradada | Cumple | [`test_playlists.py`](services/users-playlists/tests/modules/playlists/test_playlists.py). Se activa si catalog-streaming no responde |
| F1.6 Lista ajena privada da `403` | Cumple | [`test_playlists.py`](services/users-playlists/tests/modules/playlists/test_playlists.py) |
| F2.1 Búsqueda con filtros | Cumple | [`test_songs.py`](services/catalog-streaming/tests/modules/catalog/test_songs.py) |
| F2.2 `Range` y `206`, local y Jamendo | Cumple | [`test_streaming.py`](services/catalog-streaming/tests/modules/catalog/test_streaming.py). El audio contra Jamendo real se probó en 01 |
| F2.3 Primer byte p95 < 500 ms, búsqueda p95 < 300 ms | Cumple | 21 ms y 34 ms, solo pistas locales |
| F2.4 Failover de réplicas | Cumple | [Escenario 2](demo/scenario_2_failover.py) (0 fallidas de 293 al caer una réplica) y [`test_stack.py`](edge/tests/test_stack.py) (a lo sumo 1 de 120) |
| F2.5 Jamendo caído | Sin verificar en 02 | [Escenario 3](demo/scenario_3_jamendo_down.py): falta una llave de Jamendo para correrlo |
| F3.1 Evento a los 10 s | Cumple | [`usePlaybackReporter.test.ts`](frontend/src/player/usePlaybackReporter.test.ts) |
| F3.2 `playback_id` idempotente | Cumple | [Escenario 4](demo/scenario_4_idempotency.py) |
| F3.3 Métricas caídas sin cortar el audio | Cumple | [Escenario 1](demo/scenario_1_metrics_down.py): el audio sigue, las reproducciones se encolan en Redis (`202`) y se aplican al volver, sin duplicar. [`test_consumer.py`](services/playback-metrics/tests/modules/playback/test_consumer.py) cubre el consumidor |
| F3.4 Evento visible en ≤ 5 s | Medido en 04 | Con la cola, mediana de 0.03 s y máximo de 0.07 s en diez mediciones ([decisiones de la rama 04](docs/decisions/04-resiliencia-concurrencia.md#f34-evento-visible-en--5-s)) |
| F4.1 Límites de casete | Cumple | [`test_tapes.py`](services/users-playlists/tests/modules/social/test_tapes.py) |
| F4.2 Enlaces de invitación | Cumple | [`test_invites.py`](services/users-playlists/tests/modules/social/test_invites.py) |
| F4.3 Reclamar dos veces es idempotente | Cumple | [`test_invites.py`](services/users-playlists/tests/modules/social/test_invites.py) |
| F4.4 Dedicatorias | Cumple | [`test_tapes.py`](services/users-playlists/tests/modules/social/test_tapes.py) |
| F4.5 Carrera por la pista 12 | Cumple | [Escenario 5](demo/scenario_5_tape_full.py) |
| F4.6 Permisos de miembro y creador | Cumple | [`test_tapes.py`](services/users-playlists/tests/modules/social/test_tapes.py), [`test_invites.py`](services/users-playlists/tests/modules/social/test_invites.py) |
| F4.7 Sala de escucha (opcional) | Fuera | Decisión del equipo; no tiene rama asignada |
| F5.1 Solicitud de Compositor | Cumple | [`test_composer_requests.py`](services/users-playlists/tests/modules/users/test_composer_requests.py) |
| F5.2 Subida validada por contenido | Cumple | [`test_composer.py`](services/catalog-streaming/tests/modules/catalog/test_composer.py). La portada se comprueba solo por sus primeros bytes |
| F5.3 Estados de pista | Cumple | [`test_composer.py`](services/catalog-streaming/tests/modules/catalog/test_composer.py) |
| F5.4 Publicación programada y avisos | Cumple | [`test_publishing.py`](services/catalog-streaming/tests/modules/catalog/test_publishing.py), [escenario 8](demo/scenario_8_double_publish.py). La tarea corre cada 30 s |
| F5.5 Pistas ajenas dan `403` | Cumple | [Escenario 7](demo/scenario_7_permissions.py) |
| F5.6 Ocultar con motivo | Cumple | [`test_publishing.py`](services/catalog-streaming/tests/modules/catalog/test_publishing.py) |
| F6.1 Último administrador | Cumple | [Escenario 6](demo/scenario_6_last_admin.py) |
| F6.2 Importación con `job_id` | Cumple | [`test_import.py`](services/catalog-streaming/tests/modules/catalog/test_import.py) |
| F6.3 Bitácora paginada y filtrable | Cumple | [`test_admin.py`](services/users-playlists/tests/modules/users/test_admin.py) |
| F6.4 `/api/admin/*` da `403` | Cumple | [`test_admin.py`](services/users-playlists/tests/modules/users/test_admin.py), [escenario 7](demo/scenario_7_permissions.py), [`test_stack.py`](edge/tests/test_stack.py) (`403` del gateway) |
| F7.1 Vista por rol | Cumple | Pruebas de [`frontend/src/pages/`](frontend/src/pages/README.md) y [Playwright](frontend/e2e/README.md) |
| F7.2 Gráficas en < 2 s | Medido en 01 | Las 12 rutas de métricas tardaron menos de 90 ms, sin carga; no se repitió |
| F7.3 Aviso si no hay métricas | Cumple | [`ChartCard.test.tsx`](frontend/src/charts/ChartCard.test.tsx) |
| F7.4 Exportar a CSV y PNG | Cumple | [`export.test.ts`](frontend/src/charts/export.test.ts) |

De los escenarios del PRD, el 2 (una réplica de catálogo cae) y el 1 (`playback-metrics` caído) corren aquí. El 9 es la [prueba de carga](demo/README.md#prueba-de-carga). El escenario 8 comprueba el resultado con dos réplicas reales, pero la concurrencia exacta se verifica en [`test_publishing.py`](services/catalog-streaming/tests/modules/catalog/test_publishing.py).

## Lo que sigue

El recorrido completo, con lo que cabe en MELOXO de cada rama y lo que está pendiente de decidir, está en [`docs/ramas.md`](docs/ramas.md).

- `04-resiliencia-concurrencia` (hecha): tiempos de espera, reintentos con backoff, circuit breaker por servicio destino, la cola de reproducciones en Redis Streams (F3.3) y la lista de revocación de sesiones en Redis. Sin saga con estados ni cola de mensajes muertos. [Diseño](docs/specs/2026-11-14-04-resiliencia-concurrencia-design.md) y [decisiones](docs/decisions/04-resiliencia-concurrencia.md).
- `05-mensajeria` (propuesta): eventos entre servicios con acuse manual, cola de mensajes muertos y outbox, de modo que los avisos de lanzamientos no dependan de que catálogo responda. Falta decidir el broker.
- `06-poliglota` (propuesta): caché de lectura en Redis y, si el equipo lo aprueba, un almacén documental para la bitácora y los avisos.

## Documentación

- [`docs/prd.md`](docs/prd.md): qué se construye y por qué. Es la referencia de todas las ramas.
- [`docs/specs/`](docs/specs/README.md): los diseños de cada rama.
- [`docs/plans/`](docs/plans/README.md): los planes de implementación.
- [`docs/decisions/`](docs/decisions/README.md): lo que se decidió sobre la marcha y lo que quedó pendiente, con los avisos al equipo de cada rama.
- [`docs/design/`](docs/design/README.md): la maqueta de la interfaz.
- [`docs/brand/`](docs/brand/README.md): logo, colores y tipografía.
- [`CHANGELOG.md`](CHANGELOG.md): historial de cambios por rama.

## Licencia

El código es [MIT](LICENSE), con copyright del Equipo FLDSMDFR. Hay tres cosas que esa licencia no cubre:

- **La marca.** El nombre MELOXO, el logo y el contenido de [`docs/brand/`](docs/brand/README.md) no se pueden reutilizar sin permiso del equipo.
- **La música.** Las pistas de Jamendo tienen la licencia de cada artista, y la app muestra el crédito de cada una.
- **Las dependencias.** Cada una conserva la suya. `mutagen` es GPL-2.0-or-later, así que quien distribuya la imagen de Docker debe cumplir esa licencia para el conjunto. Unbounded y Caveat usan la SIL Open Font License.

## Glosario

Los términos que aparecen en el código y en la documentación, agrupados por tema.

### Del producto

| Término | Qué significa aquí |
| --- | --- |
| Administrador | Rol que modera el catálogo, aprueba Compositores y ve la salud del sistema |
| Aviso | Notificación de que un artista que sigues publicó algo. Se calcula al leer, no se guarda |
| Bitácora | Registro de las acciones administrativas, en la tabla `audit_log` |
| Casete | La unidad central de MELOXO: hasta 12 pistas en dos lados, armado por hasta 8 personas |
| Compositor | Oyente aprobado para subir y publicar su propia música |
| Dedicatoria | Nota personal que acompaña a una pista dentro de un casete |
| Estados de pista | `draft` (borrador), `scheduled` (programada), `published` (publicada) y `hidden` (oculta) |
| Inclusión | Cada vez que una pista entra a un casete o playlist. El Compositor solo ve el conteo, nunca quién fue |
| Invitación | Enlace para unirse a un casete. Es la única forma de entrar: no se buscan personas |
| Lado A y Lado B | Las dos mitades de un casete. Dependen solo de la posición: de la 1 a la 6 es el Lado A, y de la 7 a la 12, el Lado B |
| Lanzamiento | Publicación de una pista, inmediata o programada |
| Oyente | Rol base de quien se registra: escucha, guarda música y arma casetes |
| Pista | Una canción del catálogo. Su fuente es `local` si la subió un Compositor o `jamendo` si se importó |
| Plaza | Lugar de un miembro en un casete. Hay 8 |
| Retención | Qué parte de una pista escucha la gente antes de dejarla |
| Semilla | [Comando](seed/README.md) que llena la app con catálogo real y actividad simulada para la demo |

### Arquitectura y sistemas distribuidos

| Término | Qué significa |
| --- | --- |
| 2PC | Confirmación en dos fases entre varios sistemas. El PRD la descarta para no frenar la reproducción |
| Agregado | Dato ya resumido, como reproducciones por hora, para que una gráfica no recorra todos los eventos |
| API Gateway | Punto de entrada único que valida y reparte las peticiones. Llega en la rama 03 |
| Backoff | Esperar cada vez más entre reintentos, para no saturar a quien ya está fallando |
| Balanceo de carga | Repartir peticiones entre réplicas. El PRD plantea round-robin: una a cada una, por turnos |
| CAP | Teorema: con la red partida hay que elegir entre consistencia y disponibilidad. MELOXO elige disponibilidad (AP) |
| Circuit breaker | Deja de llamar por un rato a un servicio que falla, para que el error no se propague. Desde la rama 04 está en `InternalClient` |
| Consistencia eventual | Un dato tarda un poco en verse igual en todos lados. Aplica a contadores y gráficas |
| Consistencia fuerte | El dato siempre es exacto. Aplica a roles, cupo del casete y `playback_id` |
| Degradación elegante | Si algo falla, se responde con lo que se tiene y con `degraded: true`, en vez de un error |
| Failover | Pasar el trabajo a una réplica sana cuando otra cae. Llega en la rama 03 |
| Frontera de módulo | Regla de que un módulo solo entra a otro por su `public.py`, y de que un servicio solo habla con otro por HTTP |
| Idempotencia | Repetir una operación da el mismo resultado que hacerla una vez |
| Interfaz pública | El archivo `public.py` de cada módulo, para llamadas dentro de un servicio. Entre servicios, el equivalente son las rutas `/internal/*` por HTTP |
| Módulo | Parte de un servicio dueña de un tema y de sus tablas |
| Monolito modular | Una sola aplicación desplegada, dividida por dentro en módulos con fronteras claras |
| Monorepo | Un solo repositorio para los servicios, la interfaz y la documentación |
| Proxy | Intermediario. `catalog-streaming` pide el audio a Jamendo y lo pasa al navegador sin guardarlo |
| Punto único de falla | Pieza que, si cae, tira todo el sistema. Es el problema que motivó separar en servicios |
| Réplica | Otra copia del mismo servicio corriendo a la vez |
| Revocación | Invalidar un acceso antes de que venza. Se guarda en Redis la hora de la revocación y se rechaza el token emitido antes; si Redis cae, manda la caché de 30 s |
| Servicio | Programa independiente con su propia responsabilidad y sus datos. Aquí hay tres: `users-playlists`, `catalog-streaming` y `playback-metrics` |
| Timeout | Tiempo máximo que se espera una respuesta antes de darla por fallida |

### Datos y concurrencia

| Término | Qué significa |
| --- | --- |
| Bloqueo asesor | Bloqueo de PostgreSQL que controla la propia aplicación. Evita que dos procesos actualicen los agregados a la vez |
| Caché | Copia guardada de un dato para no pedirlo otra vez. `metadata_cache` guarda así los datos de una pista |
| Condición de carrera | Error que aparece cuando dos operaciones simultáneas se pisan, como dos personas agregando la pista 12 |
| Cursor | Marca de hasta dónde se han leído los eventos |
| `FOR UPDATE` | Cláusula de SQL que bloquea las filas leídas hasta terminar la transacción |
| JSONB | Tipo de PostgreSQL para guardar JSON de forma consultable |
| Llave foránea | Restricción que liga una tabla con otra. Entre módulos no se usan |
| Migración | Cambio versionado del esquema de la base de datos |
| `ON CONFLICT` | Cláusula de SQL que decide qué hacer si un registro ya existe. Da la idempotencia de `playback_id` |
| ORM | Capa que permite trabajar las tablas como clases de Python |
| Pool de conexiones | Conjunto de conexiones a la base de datos que las peticiones reutilizan |
| `SKIP LOCKED` | Junto con `FOR UPDATE`, salta las filas ya bloqueadas: dos réplicas no publican la misma pista |
| Transacción | Grupo de cambios que se aplica completo o no se aplica |
| Upsert | Insertar un registro, o actualizarlo si ya existe |
| UTC | Hora universal. Las horas se guardan así y se convierten a la zona del navegador |
| UUID | Identificador aleatorio prácticamente irrepetible |

### Web y seguridad

| Término | Qué significa |
| --- | --- |
| Access token | Token de corta duración (aquí, 15 minutos) que acompaña cada petición |
| API | Conjunto de rutas con las que la interfaz habla con los servicios |
| Argon2 | Algoritmo para guardar contraseñas de forma segura |
| ASGI | Estándar con el que un servidor de Python atiende aplicaciones asíncronas |
| CSV | Archivo de texto con datos en columnas. Los reportes se exportan así |
| Endpoint | Una ruta concreta de la API, como `GET /api/songs` |
| Hash | Huella irreversible de un dato. Así se guardan contraseñas, refresh tokens y tokens de invitación |
| HS256 | Algoritmo con el que se firman los JWT |
| JWT | Token firmado que dice quién eres y qué rol tienes |
| `localStorage` | Almacenamiento del navegador. Aquí viven el refresh token y los eventos pendientes |
| Manifiesto web | Archivo que describe la app para poder instalarla en un dispositivo |
| Middleware | Código que corre en cada petición. `LatencyMiddleware` mide tiempos |
| Multipart | Formato de petición para subir archivos |
| OpenAPI | Descripción estándar de una API. FastAPI la genera y la muestra en `/api/docs` |
| `Range` | Encabezado HTTP para pedir solo un tramo de un archivo. Permite adelantar una canción |
| Refresh token | Token de larga duración (aquí, 30 días) que sirve para pedir un access token nuevo |
| Rol | Lo que puede hacer una cuenta: `listener`, `composer` o `admin` |
| SPA | Aplicación de una sola página: navegar no recarga, por eso la música no se corta |
| Ticket de streaming | JWT de 1 hora ligado a una pista. Existe porque `<audio>` no puede enviar encabezados |
| XSS | Ataque que inyecta código en una página para robar datos |

Los códigos de respuesta que más aparecen en este proyecto:

| Código | Significado |
| --- | --- |
| `200`, `201` | La petición salió bien. `201` indica además que se creó algo |
| `206` | Contenido parcial: la respuesta a una petición con `Range` |
| `401` | No hay una sesión válida |
| `403` | Hay sesión, pero no tiene permiso |
| `404` | El recurso no existe |
| `409` | Conflicto con el estado actual, como un casete lleno |
| `410` | Ya no está disponible, como un enlace revocado |
| `422` | Los datos enviados no son válidos |
| `503` | Un servicio del que depende la respuesta no está disponible, como Jamendo |

### Medición y pruebas

| Término | Qué significa |
| --- | --- |
| Accesibilidad | Que la app se pueda usar con teclado, lector de pantalla y buen contraste |
| Escenario | Script de [`demo/`](demo/README.md) que reproduce una situación del PRD y dice `PASA` o `FALLA` |
| Fixture | Dato o preparación que una prueba reutiliza |
| Latencia | Tiempo que tarda una respuesta |
| Overlay | Archivo de Compose que se suma a otro para cambiar algunos valores |
| p50, p95, p99 | Percentiles: p95 de 66 ms quiere decir que el 95 % de las peticiones tardó eso o menos |
| PRD | [Documento de requisitos del producto](docs/prd.md) |
| Primer byte | Tiempo hasta que empieza a llegar la respuesta. Es lo que se siente al dar play |
| Prueba de carga | Muchos clientes simulados a la vez, para medir cómo responde el sistema. La de este proyecto está en [`demo/`](demo/README.md#prueba-de-carga) |
| Prueba de navegador (e2e) | Prueba que usa la app de punta a punta, como lo haría una persona |
| Simulación (mock) | Reemplazar algo externo durante una prueba, como la API de Jamendo |

### Tecnologías

| Tecnología | Para qué se usa aquí |
| --- | --- |
| Alembic | Migraciones de la base de datos |
| AnyIO | Lee archivos y calcula hashes de contraseñas sin frenar el servidor |
| argon2-cffi | Hash de contraseñas con Argon2 |
| asyncpg | Conexión asíncrona a PostgreSQL |
| axe | Revisión automática de accesibilidad, con `@axe-core/playwright` |
| Caveat, Unbounded | Tipografías de dedicatorias y títulos, instaladas con Fontsource |
| Chart.js | Gráficas. `chartjs-chart-matrix` agrega el mapa de calor |
| Docker | Empaqueta la app y sus dependencias en contenedores |
| Docker Compose | Levanta varios contenedores con un solo comando |
| FastAPI | Framework de los servicios |
| ffmpeg | Genera los tonos de audio de la semilla |
| Git | Control de versiones, con una rama por etapa del proyecto |
| HTTPX | Llamadas HTTP desde Python, sobre todo a Jamendo |
| Jamendo | Plataforma de música con licencias libres. De ahí sale el catálogo |
| jsdom | Simula un navegador para las pruebas de Vitest |
| Locust | Prueba de carga |
| mutagen | Lee los datos de un MP3 para validarlo |
| Nginx | Servidor web. Aquí es `edge`, la entrada que sirve la interfaz, valida sesión y rol con `gateway-auth` y reparte `/api/*` por prefijo |
| Node.js, npm | Compilan la interfaz e instalan sus dependencias |
| Playwright | Pruebas de navegador |
| PostgreSQL | Base de datos |
| Pydantic | Valida datos de entrada y variables de entorno, con `pydantic-settings` |
| PyJWT | Crea y verifica los JWT |
| pytest | Pruebas de los servicios. `pytest-asyncio` agrega las pruebas asíncronas |
| Python | Lenguaje de los servicios |
| python-multipart | Lee las subidas de archivos en FastAPI |
| React | Biblioteca de la interfaz |
| React Router | Rutas de la interfaz |
| Redis | Almacén en memoria para la cola de reproducciones y la revocación (rama 04); en la 06 servirá también de caché |
| Redis Streams | La cola de eventos de Redis. Desde la rama 04 guarda las reproducciones hasta que `playback-metrics` las aplica |
| respx | Simula las respuestas de Jamendo en las pruebas |
| SQLAlchemy | ORM de los servicios |
| TanStack Query | Pide datos a la API y los mantiene en caché en la interfaz |
| Testing Library | Pruebas de componentes de React como los usaría una persona |
| TypeScript | JavaScript con tipos. Lenguaje de la interfaz |
| Uvicorn | Servidor que corre FastAPI |
| Vite | Servidor de desarrollo y compilador de la interfaz |
| Vitest | Pruebas de la interfaz |
