# Diseño · Monolito FLDSMDFR (etapa `01-monolito`)

Fecha: 2026-10-30 · Rama: `feat/monolito-fastapi-vue` · Fuente de requisitos: `docs/PRD.md`

> Las decisiones marcadas **[decisión del agente]** fueron tomadas por Claude y no
> confirmadas explícitamente por el equipo; revisarlas al leer.
>
> **Decisión del equipo (2026-10-30):** este trabajo es una reescritura desde cero. El
> equipo pidió ignorar el código existente, eligió un stack nuevo, rechazó la distribución
> barra lateral + reproductor inferior del `DESIGN.md` anterior y aprobó reemplazar el
> monolito previo en esta rama (el anterior queda en `main` y en el historial).

## 1. Intención

FLDSMDFR es una plataforma de streaming musical académica. Esta etapa construye el
**monolito modular** que el PRD describe en la sección 6: una sola aplicación, un solo
proceso, una sola base de datos, con cuatro módulos (usuarios, playlists, catálogo y
streaming, reproducciones y métricas). El monolito existe para ser **dividido después**
en servicios (`02-separacion` en adelante), así que los límites entre módulos deben ser
reales desde hoy aunque todo corra en el mismo proceso.

Éxito = `docker compose up --build` levanta la app, hay música precargada, un oyente puede
registrarse, buscar, reproducir con saltos (HTTP Range), armar playlists, y un
administrador puede subir canciones y ver el top de reproducciones sin conteos duplicados.

## 2. Objetivos, no‑objetivos y anti‑objetivos

**Objetivos**
- Las tres historias de usuario del PRD (§5) con sus criterios de aceptación.
- Interfaz web propia con el concepto visual "casete mixtape" (ver `DESIGN.md`).
- Módulos con interfaz pública explícita para facilitar la futura separación.
- Pruebas automatizadas de backend y frontend.

**No‑objetivos** (del PRD §3): recomendaciones con ML, transcodificación, pagos, DRM,
apps móviles nativas. Además en esta etapa: gateway, balanceo, réplicas, circuit breaker
real, colas de mensajes, despliegue a la nube.

**Anti‑objetivos** (fracaso aunque "funcione"):
- Que la interfaz parezca un clon de Spotify/Apple Music (barra lateral + reproductor abajo).
- Que el audio se corte o se congele porque falló el registro de una reproducción.
- Que un reintento de red cuente dos veces la misma reproducción.
- Que un módulo lea o escriba directamente las tablas de otro.

## 3. Stack (decidido)

| Capa | Elección |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Datos | PostgreSQL 16, SQLAlchemy 2 (async, driver `asyncpg`), Alembic |
| Auth | JWT (`PyJWT`), contraseñas con Argon2 (`pwdlib[argon2]`) |
| Subidas | `python-multipart`; metadatos de audio con `mutagen` |
| Config | `pydantic-settings`, variables de entorno (`.env`, con `.env.example` versionado) |
| Frontend | Vue 3 + Vite + TypeScript, Vue Router. **Sin Pinia** **[decisión del agente]**: el estado compartido (sesión, reproductor, tema) vive en composables con estado reactivo a nivel módulo, para no sumar dependencias |
| Fuentes | Fraunces (variable, eje SOFT), Figtree, Caveat, auto‑hospedadas con `@fontsource` **[decisión del agente]** (funciona sin internet en la demo) |
| Pruebas | Backend: `pytest`, `pytest-asyncio`, `httpx.AsyncClient`. Frontend: `vitest` + `@vue/test-utils` |
| Calidad | `ruff` (lint + formato) en Python, `vue-tsc` para tipos **[decisión del agente]** |
| Orquestación | Docker Compose (obligatorio) |

## 4. Arquitectura

### 4.1 Estructura de carpetas

Mapeo con `AGENTS.md`: `/ui` → `ui/`, `/core` (lógica de negocio) → `app/modules/`,
`/db` → `app/db/`.

```text
FLDSMDFR/
├── docker-compose.yml        # servicios: db (postgres), app; perfil "test"
├── Dockerfile                # multi‑stage: node build de ui/ → runtime python
├── .env.example
├── pyproject.toml            # dependencias Python, config de ruff y pytest
├── app/                      # backend FastAPI
│   ├── main.py               # create_app(): routers, manejo de errores, sirve ui/dist
│   ├── config.py             # Settings (pydantic-settings)
│   ├── shared/               # transversal, sin lógica de negocio
│   │   ├── security.py       # hash de contraseñas, emitir/validar JWT
│   │   ├── deps.py           # get_session, current_user, require_admin
│   │   └── errors.py         # excepciones de dominio → respuestas HTTP JSON
│   ├── db/
│   │   ├── base.py           # DeclarativeBase
│   │   ├── session.py        # engine async + sessionmaker
│   │   └── migrations/       # Alembic (env.py, versions/)
│   └── modules/
│       ├── users/            # cuentas, roles, login
│       ├── playlists/        # casetes y sus canciones
│       ├── catalog/          # metadatos, archivos de audio, streaming
│       └── playback/         # eventos de reproducción, contadores, top
│           (cada módulo: models.py, schemas.py, repository.py, service.py, router.py)
├── ui/                       # Vue 3 + Vite + TS
│   └── src/
│       ├── main.ts, App.vue, router.ts
│       ├── api/              # cliente HTTP tipado por módulo
│       ├── composables/      # useSession, usePlayer, useTheme, usePlaybackTelemetry
│       ├── components/       # Casete, Controles, ListaCasete, Estante, Catalogo, ...
│       ├── views/            # Acceso (login/registro), Casetera, CabinaGrabacion
│       └── styles/           # tokens.css (temas Lado A/B), base.css
├── media/seed/               # audio y seed.json para la semilla
├── scripts/
│   ├── entrypoint.sh         # migraciones → semilla → uvicorn
│   └── seed.py               # idempotente
├── tests/                    # pytest: por módulo + integración
└── docs/                     # PRD.md, specs
```

### 4.2 Reglas de módulos

- Capas dentro de cada módulo: `router` (HTTP, valida con `schemas`) → `service`
  (reglas de negocio) → `repository` (SQL) → `models`.
- **La única puerta de un módulo hacia otro es su `service.py`.** Ningún módulo importa
  `models` o `repository` de otro. Se verifica con una prueba que inspecciona imports.
- **Sin llaves foráneas entre tablas de módulos distintos** **[decisión del agente]**:
  p. ej. `playlist_songs.song_id` no tiene FK a `songs`. La integridad se valida en el
  `service`. Así cada módulo puede llevarse sus tablas a su propia base en `02-separacion`.
  Las FK *dentro* de un módulo sí existen.
- Errores de dominio (`NotFound`, `Conflict`, `Forbidden`, `ValidationError`) se lanzan
  en `service` y `shared/errors.py` los traduce a JSON `{ "error": { "code", "message" } }`.

### 4.3 Modelo de datos

**users**: `users(id uuid pk, name, email unique, password_hash, role enum[listener,admin], created_at)`

**catalog**: `songs(id uuid pk, title, artist, album, duration_seconds int, file_path, mime_type, size_bytes, is_active bool default true, created_at)`; índice para búsqueda por título/artista/álbum (`ILIKE`, o `pg_trgm` si hace falta).

**playlists**: `playlists(id uuid pk, owner_id uuid, name, created_at, updated_at)`;
`playlist_songs(playlist_id fk, song_id uuid, position int, title_snapshot, artist_snapshot, duration_snapshot, added_at, pk(playlist_id, song_id))`.
Una canción no se repite en el mismo casete **[decisión del agente]**.

**playback**: `playback_events(playback_id uuid pk, song_id uuid, user_id uuid, listened_seconds int, occurred_at, received_at)`;
`song_play_counts(song_id uuid pk, play_count bigint, last_played_at)`.

### 4.4 API

Todas bajo `/api`. Documentación automática en `/docs`.

| Método y ruta | Quién | Notas |
|---|---|---|
| `POST /api/auth/register` | público | crea oyente; valida email y contraseña ≥ 8 |
| `POST /api/auth/login` / `POST /api/auth/logout` | público / sesión | ver §4.5 |
| `GET /api/auth/me` | sesión | |
| `GET /api/users?q=` | admin | listar/buscar usuarios para promoverlos **[decisión del agente]** |
| `PATCH /api/users/{id}/role` | admin | promover/degradar; un admin no puede degradarse a sí mismo |
| `GET /api/songs?q=&limit=&offset=` | sesión | título, artista, álbum, duración; solo activas |
| `GET /api/songs/{id}` | sesión | |
| `GET /api/songs/{id}/stream` | sesión | Range, ver §4.6 |
| `POST /api/songs` (multipart) | admin | ver §4.7 |
| `PATCH /api/songs/{id}` / `DELETE /api/songs/{id}` | admin | `DELETE` es borrado lógico (`is_active=false`) |
| `GET/POST /api/playlists` | sesión | solo las propias |
| `GET/PATCH/DELETE /api/playlists/{id}` | dueño | `GET` < 200 ms; playlist ajena → 404 (no revela existencia) **[decisión del agente]** |
| `POST /api/playlists/{id}/songs` | dueño | valida existencia vía `catalog.service` |
| `DELETE /api/playlists/{id}/songs/{song_id}` | dueño | |
| `PUT /api/playlists/{id}/order` | dueño | reordenar |
| `POST /api/playbacks` | sesión | ver §4.8 |
| `GET /api/metrics/top?limit=10` | sesión | visible para todos (pestaña "Lo más escuchado") **[decisión del agente]** |
| `GET /api/metrics/summary` | admin | total reproducciones, canciones, usuarios, top |
| `GET /api/health` | público | verifica DB |

### 4.5 Autenticación

- JWT firmado (HS256, secreto en env), expira en 8 h **[decisión del agente]**.
- Se entrega en **cookie `httpOnly`, `SameSite=Strict`** **[decisión del agente]**: el
  elemento `<audio>` no puede mandar cabeceras `Authorization`, y la cookie permite que
  el streaming quede protegido sin poner el token en la URL. La API también acepta
  `Authorization: Bearer` para Swagger/CLI (login devuelve el token en el cuerpo).
- Registro abierto solo para oyentes. El admin se crea en la semilla
  (credenciales desde env). Un admin puede promover a otros.
- Al recibir 401, la UI vuelve a la pantalla de acceso.

### 4.6 Streaming

- `GET /api/songs/{id}/stream` responde `Accept-Ranges: bytes`; sin `Range` → 200 con el
  archivo completo; con `Range` válido → 206 + `Content-Range`; rango inválido → 416.
- Lectura en bloques asíncrona, sin cargar el archivo a memoria; no bloquea a otros
  usuarios. Si `FileResponse` de Starlette ya implementa Range correctamente, usarlo; si
  no, implementación propia. Decide el constructor, pero las pruebas de §6 aplican igual.
- `Content-Type` según el archivo (`audio/mpeg`, `audio/ogg`, `audio/wav`).

### 4.7 Subida de canciones (Cabina de grabación)

- Campos: título, artista, álbum (requeridos), archivo.
- Acepta MP3/OGG/WAV ≤ 20 MB; valida extensión **y** que `mutagen` reconozca el archivo.
  La duración sale de `mutagen`. Errores explícitos (formato, tamaño, archivo corrupto).
- Archivo guardado en el volumen `/media/audio` con nombre `{uuid}.{ext}`.
- Escritura atómica: se escribe a temporal y se mueve; si falla la inserción en DB, se
  borra el archivo.

### 4.8 Reproducciones e idempotencia

- El cliente genera un `playback_id` (UUID v4) **por sesión de escucha** de una canción y
  envía `POST /api/playbacks {playback_id, song_id, listened_seconds}` cuando el tiempo
  realmente reproducido (no posición del cursor; saltos no cuentan) llega a 10 s.
  Una **sesión de escucha** empieza al cargar una canción en el reproductor (incluye
  repetirla desde el inicio tras terminar); pausar, reanudar o saltar dentro de la misma
  canción no crea una sesión nueva **[decisión del agente]**.
- Servidor: `listened_seconds >= 10` o 422; canción debe existir. En una transacción:
  `INSERT ... ON CONFLICT (playback_id) DO NOTHING`; solo si insertó, incrementa
  `song_play_counts` con upsert. Respuesta `201` si es nuevo, `200` si es duplicado.
- En el monolito el contador es síncrono (PRD §6), pero `GET /api/metrics/top` se
  documenta como eventualmente consistente.
- Cliente: si el POST falla, reintenta con **el mismo** `playback_id` (backoff 1 s, 2 s,
  4 s, máx. 3 intentos) y nunca interrumpe el audio; solo muestra un aviso discreto.

### 4.9 Degradación (preparación para servicios)

- Playlists guarda una copia (snapshot) de título, artista y duración al agregar una
  canción. `GET /api/playlists/{id}` intenta enriquecer con `catalog.service`; si falla o
  la canción está inactiva, devuelve el snapshot con `"status": "degraded"` o
  `"unavailable"` por canción, y la UI lo muestra de forma amigable (PRD §5, F1‑c4).
- La UI trata errores de métricas como no críticos: el reproductor sigue.

### 4.10 Semilla

- `scripts/seed.py` es idempotente (no duplica si ya existe).
- Crea un admin y un oyente de prueba (credenciales en `.env.example`), las canciones
  descritas en `media/seed/seed.json` y una playlist de ejemplo para el oyente.
- **Audio de semilla (decisión del equipo):** el equipo consigue música real libre de
  derechos y la coloca en `media/seed/`. El constructor define y documenta el formato de
  `seed.json` (archivo, título, artista, álbum) e incluye `media/seed/LICENCIAS.md` donde
  el equipo anota fuente y licencia de cada pista. La duración la lee `mutagen` del archivo.
- Si `seed.json` referencia un archivo ausente o ilegible, la semilla lo omite con una
  advertencia en el log y continúa; la app arranca aunque `media/seed/` esté vacío.
- Las pruebas **no** dependen de esa música: usan archivos de audio diminutos generados
  en fixtures.

### 4.11 Docker

- `db`: `postgres:16-alpine`, volumen `pgdata`, healthcheck `pg_isready`.
- `app`: imagen multi‑stage (Node 22 compila `ui/` → Python 3.12‑slim). Depende de `db`
  sano. `entrypoint.sh`: `alembic upgrade head` → `seed.py` → `uvicorn`. Puerto `8000`.
  Volumen `media` montado en `/media/audio`. Healthcheck a `/api/health`.
  `restart: unless-stopped`.
- FastAPI sirve `ui/dist` en `/` con fallback a `index.html` para rutas del SPA; `/api`
  y `/docs` tienen prioridad.
- Perfil `test`: servicio `tests` que corre `pytest` contra una base `fldsmdfr_test` en el
  mismo Postgres, creada por un script en `/docker-entrypoint-initdb.d` del servicio `db`;
  las pruebas crean el esquema con las migraciones y limpian tablas entre casos. Para desarrollo del frontend: `npm run dev` con proxy de `/api` a `:8000`.

## 5. Interfaz (resumen; detalle en `DESIGN.md`)

- Concepto **casete mixtape**, dos columnas. Izquierda "casetera": casete activo (etiqueta
  manuscrita = nombre de la playlist, ventanita con carretes que giran al reproducir),
  controles ⏮ ▶ ⏭ y volumen, título/artista/tiempo, barra de progreso con salto, lista del
  casete y estante de casetes + "Nueva". Derecha: pestañas Catálogo / Lo más escuchado,
  buscador y lista con botón "+" para grabar en el casete activo.
- Barra de progreso dibuja también los rangos ya descargados (`audio.buffered`)
  **[decisión del agente]**: muestra el streaming por fragmentos.
- Temas: **Lado A** = Mostaza y oliva (claro), **Lado B** = Ámbar nocturno (oscuro).
  Interruptor "Lado A / Lado B"; inicia según `prefers-color-scheme`; recuerda la elección
  en `localStorage`.
- Tipografía: Fraunces (SOFT) títulos, Figtree texto, Caveat solo en etiquetas de casete.
- Espaciado 4/8/12/16/24 px; botones ≥ 40 px (play 52 px); foco de teclado visible;
  respeta `prefers-reduced-motion` (los carretes no giran).
- Móvil: casetera compacta arriba; lista del casete y estante en una pestaña.
- Vistas: Acceso (login/registro), Casetera (principal), Cabina de grabación (solo admin:
  subir/editar/desactivar canciones, resumen de métricas, promover usuarios).
- Textos en español, voz activa ("Grabar en el casete", "Crear casete").

## 6. Pruebas

Backend (pytest, contra Postgres real):
- users: registro, email duplicado, login correcto/incorrecto, rutas admin con oyente → 403.
- catalog: listado y búsqueda; stream sin Range (200), con Range (206 y bytes exactos),
  rango abierto `bytes=N-`, rango inválido (416); subida válida, formato inválido,
  tamaño excedido; borrado lógico.
- playlists: crear, agregar canción existente, canción inexistente (404), duplicada (409),
  playlist ajena (403/404), modo degradado con snapshot.
- playback: evento nuevo (201), mismo `playback_id` (200 y el contador no cambia),
  `listened_seconds < 10` (422), eventos concurrentes con distintos ids cuentan bien, top
  ordenado.
- arquitectura: ningún módulo importa `models`/`repository` de otro módulo.

Frontend (vitest): telemetría de reproducción (umbral 10 s acumulados, mismo UUID en
reintentos, un solo envío por sesión de escucha), cambio de tema y persistencia,
componente de barra de progreso con rangos.

Verificación manual: `docker compose up --build`, flujo completo oyente y admin en el navegador.

## 7. Documentación a actualizar

- `DESIGN.md`: reescrito con el sistema visual (tokens de ambos temas, tipografía,
  espaciado, componentes, estados, accesibilidad, responsive).
- `README.md`: cómo levantar, credenciales de prueba, cómo correr pruebas.
- `AGENTS.md`: sustituir Laravel/Vue/MySQL por el stack real y la estructura de carpetas.
- Se eliminan: `main.py`, `core/`, `db/`, `ui/` antiguos, `tests/` antiguos,
  `README_MONOLITO.md`, `requirements.txt`, `pytest.ini`, `scripts/generate_samples.py`,
  `media/audio/*.wav` (quedan en el historial y en `main`). `SKILLS.md` se conserva sin cambios.
- `.gitignore`: agregar `.superpowers/`, `node_modules/`, `ui/dist/`, `.env`.

## 8. Lo que queda al constructor

Nombres internos, organización fina de componentes Vue, consultas exactas, estrategia de
búsqueda (ILIKE vs trigram), implementación de Range (con las pruebas de §6), copy exacto
de la interfaz dentro del tono definido, generación de las pistas sintetizadas.
