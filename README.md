# MELOXO

Tu Casetera de Confianza. MELOXO es un servicio de streaming musical que gira alrededor del casete compartido: hasta 12 pistas en dos lados, armado entre amigos, con dedicatorias y repartido por enlace. No hay feed ni recomendaciones: la música se descubre porque alguien te la regala.

Es el proyecto de la materia de Sistemas Distribuidos del equipo FLDSMDFR: Christian Franco Ramírez, Miriam Amisadai López Hernández, Erick Nava Santiago y Brent Armando Pérez Paitán.

Esta rama, `01-monolito`, entrega el producto completo en un solo proceso, como monolito modular. Es el punto de partida: las ramas siguientes lo van separando en servicios.

## Con qué está hecho

| Parte | Tecnologías |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Base de datos | PostgreSQL 16 |
| Interfaz | React 18, TypeScript, Vite, TanStack Query, Chart.js |
| Música | Catálogo de Jamendo y pistas que suben los Compositores |
| Pruebas | pytest, Vitest, Playwright, axe, Locust |
| Despliegue | Docker y Docker Compose |

Todo corre en dos contenedores. El proceso de FastAPI atiende la API, sirve la interfaz ya compilada y entrega el audio:

```text
Navegador ──► app :8080 (FastAPI) ──► postgres :5432
                 │
                 ├── /api/*    seis módulos
                 ├── /*        interfaz de React
                 └── audio     archivo local, o proxy hacia Jamendo
```

## Cómo levantarlo

Necesitas Docker con Compose. Corre esto desde la raíz del repositorio:

```bash
cp .env.example .env                         # después, completa los valores
docker compose up --build -d                 # la app queda en http://localhost:8080
docker compose exec app python -m seed all   # opcional: catálogo y actividad de demo
```

Las variables de `.env` se explican en [Variables de entorno](#variables-de-entorno). Para `POSTGRES_PASSWORD` y `JWT_SECRET` sirve cualquier cadena larga, como la que genera `openssl rand -hex 32`. Usa esa misma contraseña de PostgreSQL en lugar de `CAMBIA_ESTO` dentro de `DATABASE_URL`.

La semilla tarda cerca de un minuto y necesita `JAMENDO_CLIENT_ID`. Para borrar lo simulado, corre `docker compose exec app python -m seed clear`. Los demás subcomandos están en [`backend/seed/`](backend/seed/README.md).

Con la app en marcha, la documentación interactiva de la API está en <http://localhost:8080/api/docs>. Para apagar todo, usa `docker compose down`; agrega `-v` si además quieres borrar la base de datos y los archivos subidos.

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
| **Administrador** | El de `ADMIN_EMAIL` (localmente, `admin@meloxo.local`) | `ADMIN_PASSWORD` | Ver las métricas del sistema, aprobar Compositores y consultar la auditoría |
| **Administrador** | `admin00@demo.meloxo.dev`<br>`admin01@demo.meloxo.dev` | `DEMO_PASSWORD` | Lo mismo que el anterior |
| **Compositor** | De `compositor00@demo.meloxo.dev`<br>a `compositor09@demo.meloxo.dev` | `DEMO_PASSWORD` | Subir temas propios y portadas, y ver sus métricas de artista |
| **Oyente** | De `oyente00@demo.meloxo.dev`<br>a `oyente59@demo.meloxo.dev` | `DEMO_PASSWORD` | Crear y escuchar casetes compartidos, playlists y favoritos |

El primer administrador se crea al arrancar la app, solo si todavía no hay ninguno. Por eso, cambiar `ADMIN_EMAIL` o `ADMIN_PASSWORD` después no modifica esa cuenta. Las cuentas `@demo.meloxo.dev` solo existen después de correr la semilla.

> Si `DEMO_PASSWORD` está vacía al correr la semilla, se genera una contraseña al azar y se imprime en la terminal al terminar.

## Variables de entorno

Estas van en `.env`:

| Variable | Para qué sirve |
| --- | --- |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL |
| `DATABASE_URL` | Conexión desde fuera de Docker, para correr las migraciones a mano. Dentro de Docker, Compose la reemplaza |
| `JWT_SECRET` | Firma de las sesiones |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Primer administrador, creado al arrancar si todavía no hay ninguno |
| `DEMO_PASSWORD` | Contraseña de las cuentas de demo. Si está vacía, se genera una al azar |
| `JAMENDO_CLIENT_ID` | Llave de Jamendo. Va solo en `.env`, nunca en archivos versionados |
| `JAMENDO_AUDIO_MODE` | `proxy` (por defecto) o `redirect` |

Estas otras tienen un valor por defecto y casi nunca hay que tocarlas. Se definen en [`backend/app/core/config.py`](backend/app/core/config.py):

| Variable | Por defecto | Para qué sirve |
| --- | --- | --- |
| `TAPE_MAX_TRACKS` | `12` | Pistas por casete |
| `TAPE_MAX_MEMBERS` | `8` | Miembros por casete |
| `COMPOSER_MAX_TRACKS` | `20` | Pistas por Compositor |
| `UPLOAD_MAX_MP3_MB` | `15` | Peso máximo del MP3 |
| `UPLOAD_MAX_COVER_MB` | `2` | Peso máximo de la portada |
| `UPLOAD_MAX_MINUTES` | `10` | Duración máxima de una pista |
| `JAMENDO_API_URL` | `https://api.jamendo.com/v3.0` | API de Jamendo. El escenario 3 la cambia para simular la caída |
| `MEDIA_DIR` | `/media` | Dónde se guardan el audio y las portadas |
| `STATIC_DIR` | Vacía | Interfaz compilada. El [`Dockerfile`](Dockerfile) la fija en `/app/static` |
| `APP_VERSION` | `01-monolito` | Versión que muestra la sección de Salud |
| `DISABLE_SCHEDULER` | `false` | Apaga las tareas periódicas. Lo usan las pruebas |

## Estructura del repositorio

```text
MELOXO/
├── backend/
│   ├── app/
│   │   ├── core/            # lo que comparten todos los módulos
│   │   ├── modules/         # los seis módulos de negocio
│   │   └── main.py          # crea la app y arranca las tareas periódicas
│   ├── migrations/          # esquema de la base de datos, con Alembic
│   ├── seed/                # datos de demo
│   └── tests/               # misma forma que app/
├── frontend/
│   ├── e2e/                 # pruebas de navegador
│   ├── public/              # íconos y manifiesto
│   └── src/                 # código de la interfaz
├── demo/                    # escenarios del PRD y prueba de carga
├── docs/
│   ├── prd.md               # requisitos del producto
│   ├── specs/               # diseños aprobados
│   ├── plans/               # planes de implementación
│   ├── decisions/           # lo que se decidió sobre la marcha
│   ├── design/              # maqueta de la interfaz
│   └── brand/               # logo y guía de marca
├── compose.yaml             # los dos contenedores
├── compose.demo.yaml        # overlay de los escenarios 3 y 8
├── Dockerfile               # compila la interfaz y arma la imagen
├── .env.example             # plantilla de variables
└── LICENSE                  # licencia MIT
```

Para seguir leyendo, entra por el README de cada parte:

| Parte | Empieza aquí |
| --- | --- |
| API, módulos y base de datos | [`backend/`](backend/README.md) |
| Interfaz web | [`frontend/`](frontend/README.md) |
| Escenarios y prueba de carga | [`demo/`](demo/README.md) |
| Requisitos, diseños y marca | [`docs/`](docs/README.md) |

Cada carpeta tiene su README, y [`test_readmes.py`](backend/tests/test_readmes.py) falla si falta alguno. Dentro de `docs/brand/`, esa comprobación no entra en las subcarpetas, porque contienen archivos de logo. Las reglas de nombres y sus motivos se explican en [`docs/`](docs/README.md#cómo-se-nombran-las-cosas).

## Módulos

Cada módulo es dueño de sus tablas, no hay llaves foráneas entre módulos y solo se comunican a través de su `public.py`. [`test_boundaries.py`](backend/tests/test_boundaries.py) comprueba las importaciones entre módulos; las llaves foráneas no las revisa ninguna prueba.

| Módulo | Responsabilidad |
| --- | --- |
| [`users`](backend/app/modules/users/README.md) | Cuentas, roles, solicitudes de Compositor y auditoría |
| [`playlists`](backend/app/modules/playlists/README.md) | Playlists y sus pistas |
| [`catalog`](backend/app/modules/catalog/README.md) | Canciones, artistas, álbumes, importación, subidas y streaming |
| [`playback`](backend/app/modules/playback/README.md) | Eventos de reproducción, contadores e historial |
| [`social`](backend/app/modules/social/README.md) | Favoritas, seguidos, casetes, invitaciones y avisos |
| [`analytics`](backend/app/modules/analytics/README.md) | Agregados para gráficas, latencia y salud |

## Pruebas

Las pruebas de backend leen `POSTGRES_PASSWORD` de `.env`, así que hace falta ese archivo. Todos los comandos se corren desde la raíz del repositorio:

```bash
docker compose up -d postgres

# Backend, contra un PostgreSQL real
(cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/pytest)

# Interfaz, con Vitest
(cd frontend && npm install && npm test)

# Navegador, con la app en marcha
(cd frontend && npx playwright install chromium && npm run e2e)

# Escenarios del PRD, con la app en marcha y la semilla cargada
for f in demo/scenario_*.py; do python3 "$f" || break; done
```

Cada parte tiene más detalle en su README: [backend](backend/tests/README.md), [navegador](frontend/e2e/README.md) y [escenarios y prueba de carga](demo/README.md).

## Estado de los criterios

Verificado el 2026-11-06 sobre una imagen reconstruida: 410 pruebas de backend, 127 de frontend, 15 de navegador y los escenarios 3 a 8 pasan. Las mediciones de carga son de la corrida de ese mismo día, desde cero (`docker compose down -v`, reconstrucción y semilla), en `docker compose` local y sin una red real de por medio. Los criterios completos están en la [sección 6 del PRD](docs/prd.md#6-historias-de-usuario-y-criterios-de-aceptación).

| Criterio | Estado | Evidencia |
| --- | --- | --- |
| F1.1 Registro e inicio de sesión con JWT | Cumple | [`test_auth.py`](backend/tests/modules/users/test_auth.py) |
| F1.2 Lista ligada al usuario del token | Cumple | [`test_playlists.py`](backend/tests/modules/playlists/test_playlists.py) |
| F1.3 Reagregar es idempotente | Cumple | [`test_playlists.py`](backend/tests/modules/playlists/test_playlists.py) |
| F1.4 `GET /api/playlists/{id}` p95 < 200 ms | Cumple | 66 ms con 50 clientes |
| F1.5 Lista degradada | Cumple | [`test_playlists.py`](backend/tests/modules/playlists/test_playlists.py). Solo se activa si falla la interfaz pública del catálogo |
| F1.6 Lista ajena privada da `403` | Cumple | [`test_playlists.py`](backend/tests/modules/playlists/test_playlists.py) |
| F2.1 Búsqueda con filtros | Cumple | [`test_songs.py`](backend/tests/modules/catalog/test_songs.py) |
| F2.2 `Range` y `206`, local y Jamendo | Cumple | [`test_streaming.py`](backend/tests/modules/catalog/test_streaming.py) y 3 pistas contra Jamendo real |
| F2.3 Primer byte p95 < 500 ms, búsqueda p95 < 300 ms | Cumple | 39 ms y 71 ms, solo pistas locales |
| F2.4 Failover de réplicas | Rama 03 | Esta rama tiene una sola instancia |
| F2.5 Jamendo caído | Cumple | [Escenario 3](demo/scenario_3_jamendo_down.py) |
| F3.1 Evento a los 10 s | Cumple | [`usePlaybackReporter.test.ts`](frontend/src/player/usePlaybackReporter.test.ts) |
| F3.2 `playback_id` idempotente | Cumple | [Escenario 4](demo/scenario_4_idempotency.py) |
| F3.3 Métricas caídas sin cortar el audio | Parcial | El navegador reintenta. La cola real llega en la rama 04 |
| F3.4 Evento visible en ≤ 5 s | Cumple | 1.1 s y 2.8 s en dos mediciones |
| F4.1 Límites de casete | Cumple | [`test_tapes.py`](backend/tests/modules/social/test_tapes.py) |
| F4.2 Enlaces de invitación | Cumple | [`test_invites.py`](backend/tests/modules/social/test_invites.py) |
| F4.3 Reclamar dos veces es idempotente | Cumple | [`test_invites.py`](backend/tests/modules/social/test_invites.py) |
| F4.4 Dedicatorias | Cumple | [`test_tapes.py`](backend/tests/modules/social/test_tapes.py) |
| F4.5 Carrera por la pista 12 | Cumple | [Escenario 5](demo/scenario_5_tape_full.py) |
| F4.6 Permisos de miembro y creador | Cumple | [`test_tapes.py`](backend/tests/modules/social/test_tapes.py), [`test_invites.py`](backend/tests/modules/social/test_invites.py) |
| F4.7 Sala de escucha (opcional) | Fuera | Decisión del equipo; no tiene rama asignada |
| F5.1 Solicitud de Compositor | Cumple | [`test_composer_requests.py`](backend/tests/modules/users/test_composer_requests.py) |
| F5.2 Subida validada por contenido | Cumple | [`test_composer.py`](backend/tests/modules/catalog/test_composer.py). La portada se comprueba solo por sus primeros bytes |
| F5.3 Estados de pista | Cumple | [`test_composer.py`](backend/tests/modules/catalog/test_composer.py) |
| F5.4 Publicación programada y avisos | Cumple | [`test_publishing.py`](backend/tests/modules/catalog/test_publishing.py), [escenario 8](demo/scenario_8_double_publish.py). La tarea corre cada 30 s |
| F5.5 Pistas ajenas dan `403` | Cumple | [Escenario 7](demo/scenario_7_permissions.py) |
| F5.6 Ocultar con motivo | Cumple | [`test_publishing.py`](backend/tests/modules/catalog/test_publishing.py) |
| F6.1 Último administrador | Cumple | [Escenario 6](demo/scenario_6_last_admin.py) |
| F6.2 Importación con `job_id` | Cumple | [`test_import.py`](backend/tests/modules/catalog/test_import.py) |
| F6.3 Bitácora paginada y filtrable | Cumple | [`test_admin.py`](backend/tests/modules/users/test_admin.py) |
| F6.4 `/api/admin/*` da `403` | Cumple | [`test_admin.py`](backend/tests/modules/users/test_admin.py), [escenario 7](demo/scenario_7_permissions.py) |
| F7.1 Vista por rol | Cumple | Pruebas de [`frontend/src/pages/`](frontend/src/pages/README.md) y [Playwright](frontend/e2e/README.md) |
| F7.2 Gráficas en < 2 s | Cumple | Las 12 rutas de métricas tardan menos de 90 ms, sin carga |
| F7.3 Aviso si no hay métricas | Cumple | [`ChartCard.test.tsx`](frontend/src/charts/ChartCard.test.tsx) |
| F7.4 Exportar a CSV y PNG | Cumple | [`export.test.ts`](frontend/src/charts/export.test.ts) |

De los escenarios del PRD, el 1 y el 2 necesitan servicios separados y quedan para las ramas siguientes. El 9 es la [prueba de carga](demo/README.md#prueba-de-carga). El escenario 8 comprueba el resultado con dos réplicas reales, pero la concurrencia exacta se verifica en [`test_publishing.py`](backend/tests/modules/catalog/test_publishing.py).

## Lo que sigue

- `02-separacion`: servicios en Docker sobre una red interna.
- `03-gateway-balanceo`: gateway, JWT y roles en el borde, y réplicas de catálogo. Trae el criterio F2.4.
- `04-resiliencia-concurrencia`: tiempos de espera, reintentos, circuit breaker y Redis Streams. Trae la cola del criterio F3.3.

## Documentación

- [`docs/prd.md`](docs/prd.md): qué se construye y por qué. Es la referencia de todas las ramas.
- [`docs/specs/`](docs/specs/README.md): el diseño de esta rama.
- [`docs/plans/`](docs/plans/README.md): el plan de implementación de esta rama.
- [`docs/decisions/`](docs/decisions/README.md): lo que se decidió sobre la marcha y lo que quedó pendiente.
- [`docs/design/`](docs/design/README.md): la maqueta de la interfaz.
- [`docs/brand/`](docs/brand/README.md): logo, colores y tipografía.

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
| Semilla | [Comando](backend/seed/README.md) que llena la app con catálogo real y actividad simulada para la demo |

### Arquitectura y sistemas distribuidos

| Término | Qué significa |
| --- | --- |
| 2PC | Confirmación en dos fases entre varios sistemas. El PRD la descarta para no frenar la reproducción |
| Agregado | Dato ya resumido, como reproducciones por hora, para que una gráfica no recorra todos los eventos |
| API Gateway | Punto de entrada único que valida y reparte las peticiones. Llega en la rama 03 |
| Backoff | Esperar cada vez más entre reintentos, para no saturar a quien ya está fallando |
| Balanceo de carga | Repartir peticiones entre réplicas. El PRD plantea round-robin: una a cada una, por turnos |
| CAP | Teorema: con la red partida hay que elegir entre consistencia y disponibilidad. MELOXO elige disponibilidad (AP) |
| Circuit breaker | Deja de llamar por un rato a un servicio que falla, para que el error no se propague. Llega en la rama 04 |
| Consistencia eventual | Un dato tarda un poco en verse igual en todos lados. Aplica a contadores y gráficas |
| Consistencia fuerte | El dato siempre es exacto. Aplica a roles, cupo del casete y `playback_id` |
| Degradación elegante | Si algo falla, se responde con lo que se tiene y con `degraded: true`, en vez de un error |
| Failover | Pasar el trabajo a una réplica sana cuando otra cae. Llega en la rama 03 |
| Frontera de módulo | Regla de que un módulo solo entra a otro por su `public.py` |
| Idempotencia | Repetir una operación da el mismo resultado que hacerla una vez |
| Interfaz pública | El archivo `public.py` de cada módulo. En la rama 02, esas funciones se vuelven llamadas HTTP |
| Módulo | Parte del monolito dueña de un tema y de sus tablas |
| Monolito modular | Una sola aplicación desplegada, dividida por dentro en módulos con fronteras claras |
| Monorepo | Un solo repositorio para backend, interfaz y documentación |
| Proxy | Intermediario. El backend pide el audio a Jamendo y lo pasa al navegador sin guardarlo |
| Punto único de falla | Pieza que, si cae, tira todo el sistema. Es el problema que motiva separar en servicios |
| Réplica | Otra copia del mismo servicio corriendo a la vez |
| Revocación | Invalidar un acceso antes de que venza. Hoy se revisa en la base de datos; en la rama 03 pasa a Redis |
| Servicio | Programa independiente con su propia responsabilidad y sus datos. Es en lo que se convierten los módulos |
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
| API | Conjunto de rutas con las que la interfaz habla con el backend |
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
| FastAPI | Framework del backend |
| ffmpeg | Genera los tonos de audio de la semilla |
| Git | Control de versiones, con una rama por etapa del proyecto |
| HTTPX | Llamadas HTTP desde Python, sobre todo a Jamendo |
| Jamendo | Plataforma de música con licencias libres. De ahí sale el catálogo |
| jsdom | Simula un navegador para las pruebas de Vitest |
| Locust | Prueba de carga |
| mutagen | Lee los datos de un MP3 para validarlo |
| Nginx | Servidor web que el PRD contempla para el gateway. No se usa en esta rama |
| Node.js, npm | Compilan la interfaz e instalan sus dependencias |
| Playwright | Pruebas de navegador |
| PostgreSQL | Base de datos |
| Pydantic | Valida datos de entrada y variables de entorno, con `pydantic-settings` |
| PyJWT | Crea y verifica los JWT |
| pytest | Pruebas de backend. `pytest-asyncio` agrega las pruebas asíncronas |
| Python | Lenguaje del backend |
| python-multipart | Lee las subidas de archivos en FastAPI |
| React | Biblioteca de la interfaz |
| React Router | Rutas de la interfaz |
| Redis | Almacén en memoria para eventos y revocación. Llega en las ramas 03 y 04 |
| Redis Streams | La cola de eventos de Redis. Llega en la rama 04 |
| respx | Simula las respuestas de Jamendo en las pruebas |
| SQLAlchemy | ORM del backend |
| TanStack Query | Pide datos a la API y los mantiene en caché en la interfaz |
| Testing Library | Pruebas de componentes de React como los usaría una persona |
| TypeScript | JavaScript con tipos. Lenguaje de la interfaz |
| Uvicorn | Servidor que corre FastAPI |
| Vite | Servidor de desarrollo y compilador de la interfaz |
| Vitest | Pruebas de la interfaz |
