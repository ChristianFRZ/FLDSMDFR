# Monolito FLDSMDFR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el monolito modular de streaming musical FLDSMDFR (API FastAPI + UI Vue "casete mixtape" + PostgreSQL) que se levanta con `docker compose up --build`.

**Architecture:** Una app FastAPI con cuatro módulos verticales (`users`, `catalog`, `playlists`, `playback`) en `app/modules/`, cada uno con `models/schemas/repository/service/router`; los módulos solo se hablan por `service.py` y no hay FK entre módulos. La UI Vue 3 se compila en la imagen Docker y la sirve el mismo proceso FastAPI. PostgreSQL 16 en un contenedor aparte.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async + asyncpg, Alembic, PyJWT, pwdlib[argon2], python-multipart, mutagen, pydantic-settings, pytest + pytest-asyncio + httpx, ruff · Vue 3 + Vite + TypeScript, Vue Router, @fontsource-variable, vitest + @vue/test-utils + jsdom, vue-tsc · Docker Compose.

**Spec:** `docs/superpowers/specs/2026-10-30-monolito-fldsmdfr-design.md` (leer junto con este plan; las secciones citadas como §N son de ese documento).

## Global Constraints

- Rama: `feat/monolito-fastapi-vue`. Commits terminan con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Python 3.12; dependencias solo las listadas arriba (más `uvicorn[standard]`, `alembic`, `asyncpg`). Frontend: solo `vue`, `vue-router`, `@fontsource-variable/fraunces`, `@fontsource-variable/figtree`, `@fontsource-variable/caveat` como runtime. **Sin Pinia.**
- Todas las rutas de API bajo `/api`; Swagger en `/docs`.
- Error JSON uniforme: `{"error": {"code": "<snake_case>", "message": "<texto en español>"}}`.
- Un módulo nunca importa `models` ni `repository` de otro módulo; solo `app.modules.<otro>.service` y `app.modules.<otro>.schemas`.
- Sin FK entre tablas de módulos distintos.
- JWT HS256, expira en 8 h, cookie `fldsmdfr_session` `httpOnly`, `SameSite=Strict`, `Path=/`; también se acepta `Authorization: Bearer`.
- Contraseña ≥ 8 caracteres. Subidas: `.mp3`/`.ogg`/`.wav`, ≤ 20 MB, reconocidas por `mutagen`.
- Reproducción cuenta con `listened_seconds >= 10`; idempotente por `playback_id` (UUID).
- Toda la UI en español, voz activa, sentence case. Temas: `data-lado="A"` (Mostaza y oliva) y `data-lado="B"` (Ámbar nocturno), clave localStorage `fldsmdfr-lado`.
- Espaciado 4/8/12/16/24 px; botones ≥ 40 px, play 52 px; foco visible; `prefers-reduced-motion` desactiva el giro de carretes.
- Puerto expuesto `8000`. Audio en el volumen montado en `/media/audio`.

## Review Focus

1. Cabeceras `Range` raras: sufijo `bytes=-500`, inicio ≥ tamaño, fin mayor al tamaño, múltiples rangos `bytes=0-1,4-5` → sufijo sirve los últimos N bytes; inicio fuera → 416 con `Content-Range: bytes */<size>`; fin se recorta; multirango → 200 completo. (Task 3)
2. Archivo con extensión `.mp3` pero contenido basura → 422 `invalid_audio` y no queda archivo huérfano en `/media/audio`. (Task 4)
3. Búsqueda con `%` o `_` → se tratan literalmente, no como comodines. (Task 3)
4. Cookie JWT expirada o alterada → 401 `unauthorized` (no 500); la UI regresa a `/acceso`. (Task 2, Task 9)
5. Dos peticiones simultáneas con el mismo `playback_id` → el contador sube exactamente 1. (Task 6)

---

## File Structure

```text
docker-compose.yml, Dockerfile, .dockerignore, .env.example, pyproject.toml, alembic.ini
docker/initdb/01-test-db.sql           # crea fldsmdfr_test
app/main.py, app/config.py
app/shared/{errors,security,deps}.py
app/db/{base,session}.py, app/db/migrations/{env.py,script.py.mako,versions/}
app/modules/<m>/{__init__,models,schemas,repository,service,router}.py   (m = users|catalog|playlists|playback)
app/modules/catalog/{audio,streaming}.py
app/spa.py                             # servir ui/dist con fallback
scripts/{entrypoint.sh,seed.py}
media/seed/{seed.json,LICENCIAS.md,.gitkeep}
tests/conftest.py, tests/audio_fixtures.py, tests/test_<area>.py
ui/ (Vite): package.json, vite.config.ts, tsconfig*.json, index.html
ui/src/{main.ts,App.vue,router.ts}
ui/src/api/{http,auth,songs,playlists,playbacks,metrics,users,types}.ts
ui/src/composables/{useTheme,useSession,usePlayer,usePlaybackTelemetry,useCasetes}.ts
ui/src/components/{InterruptorLado,CaseteActivo,ControlesReproductor,BarraProgreso,ListaCasete,EstanteCasetes,PanelCatalogo,PanelTop,Aviso}.vue
ui/src/views/{AccesoView,CaseteraView,CabinaView}.vue
ui/src/styles/{tokens,base}.css
ui/src/**/__tests__/*.spec.ts
DESIGN.md, README.md, AGENTS.md
```

---

### Task 1: Limpieza y esqueleto backend + Docker

**Files:**
- Delete: `main.py`, `core/`, `db/`, `ui/`, `tests/`, `README_MONOLITO.md`, `requirements.txt`, `pytest.ini`, `scripts/generate_samples.py`, `media/audio/`, `Dockerfile`, `docker-compose.yml`
- Create: `pyproject.toml`, `alembic.ini`, `app/__init__.py`, `app/main.py`, `app/config.py`, `app/shared/errors.py`, `app/db/base.py`, `app/db/session.py`, `app/shared/deps.py` (solo `get_session` por ahora), `app/db/migrations/env.py`, `app/db/migrations/script.py.mako`, `Dockerfile` (solo etapa Python por ahora), `docker-compose.yml`, `docker/initdb/01-test-db.sql`, `.env.example`, `.dockerignore`, `tests/conftest.py`, `tests/test_health.py`
- Modify: `.gitignore` (+ `node_modules/`, `ui/dist/`, `.env`, `.ruff_cache/`)

**Interfaces:**
- Produces:
  - `app.config.Settings` (pydantic-settings, prefijo env `FLDSMDFR_`): `database_url: str`, `jwt_secret: str`, `jwt_expire_hours: int = 8`, `cookie_name: str = "fldsmdfr_session"`, `cookie_secure: bool = False`, `media_dir: Path = Path("/media/audio")`, `seed_dir: Path = Path("media/seed")`, `max_upload_bytes: int = 20 * 1024 * 1024`, `ui_dist_dir: Path = Path("ui/dist")`, `admin_email`, `admin_password`, `listener_email`, `listener_password: str`. `get_settings() -> Settings` con `lru_cache`.
  - `app.shared.errors`: `class DomainError(Exception)` con `status: int`, `code: str`, `__init__(self, message: str)`; subclases `NotFound(404,"not_found")`, `Conflict(409,"conflict")`, `Forbidden(403,"forbidden")`, `Unauthorized(401,"unauthorized")`, `InvalidInput(422,"invalid_input")`, `RangeNotSatisfiable(416,"range_not_satisfiable")`. Permitir `code` específico por instancia: `__init__(self, message, code: str | None = None)`. `register_error_handlers(app: FastAPI) -> None` (también mapea `RequestValidationError` → 422 `invalid_input` con el mismo formato).
  - `app.db.base.Base(DeclarativeBase)`; `app.db.session.engine`, `SessionLocal: async_sessionmaker[AsyncSession]` (`expire_on_commit=False`).
  - `app.shared.deps.get_session() -> AsyncIterator[AsyncSession]`.
  - `app.main.create_app() -> FastAPI`; `app = create_app()`; `GET /api/health` → `{"status": "ok", "database": "ok"}` (ejecuta `SELECT 1`; si falla, 503 `{"status":"degraded","database":"error"}`).
  - `tests/conftest.py` fixtures: `client` (`httpx.AsyncClient` con `ASGITransport`, base `http://test`), `session` (`AsyncSession`), limpieza `TRUNCATE ... CASCADE` de todas las tablas de `Base.metadata` antes de cada test; migraciones `alembic upgrade head` una vez por sesión; `FLDSMDFR_MEDIA_DIR` apunta a un tmp por sesión. Los env de prueba se fijan **antes** de importar `app`.
- docker-compose: servicios `db` (`postgres:16-alpine`, env `POSTGRES_USER/PASSWORD/DB=fldsmdfr`, volumen `pgdata`, monta `docker/initdb` en `/docker-entrypoint-initdb.d`, healthcheck `pg_isready -U fldsmdfr`), `app` (build `.`, `env_file: .env` con `required: false` y defaults de `.env.example`, `depends_on: db: condition: service_healthy`, puerto `8000:8000`, volumen `media:/media/audio`, healthcheck `curl -f http://localhost:8000/api/health`, `restart: unless-stopped`), `tests` (perfil `test`, misma imagen, `FLDSMDFR_DATABASE_URL=postgresql+asyncpg://fldsmdfr:fldsmdfr@db:5432/fldsmdfr_test`, comando `pytest -q`, monta `./app`, `./tests`, `./scripts`, `./media/seed` para iterar sin rebuild).
- pyproject: `[tool.pytest.ini_options] asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "session"`, `asyncio_default_test_loop_scope = "session"`, `testpaths = ["tests"]`. Ruff `line-length = 100`, `target-version = "py312"`, reglas `E,F,I,B,UP`. Dependencias dev en grupo `[project.optional-dependencies] dev`.

- [ ] **Step 1:** Borrar los archivos de la lista con `git rm -r` y actualizar `.gitignore`.
- [ ] **Step 2: Write the failing test** `tests/test_health.py::test_health_ok`: `GET /api/health` → 200 y `{"status": "ok", "database": "ok"}`. Y `test_unknown_api_route_is_json_404`: `GET /api/no-existe` → 404 con `json()["error"]["code"] == "not_found"`.
- [ ] **Step 3: Run** `docker compose --profile test run --rm --build tests` → FAIL (app no existe).
- [ ] **Step 4: Implement** config, errors (incluye handler para `StarletteHTTPException` 404 → formato uniforme), db, alembic env async (lee URL de `get_settings()`, `target_metadata = Base.metadata` importando los `models` de todos los módulos vía `app.db.models_registry` — ver nota), main, Dockerfile (python:3.12-slim, instala `curl`, `pip install .`, `WORKDIR /app`, `CMD` temporal uvicorn), compose.
  Nota: crear `app/db/models_registry.py` que importa `models` de cada módulo existente; cada tarea que agrega un módulo lo añade ahí. Es el único lugar (además de alembic) que importa modelos de varios módulos.
- [ ] **Step 5: Run** `docker compose --profile test run --rm --build tests` → PASS. `docker compose run --rm tests ruff check .` → sin errores.
- [ ] **Step 6: Commit** `chore: esqueleto FastAPI + Postgres + Docker Compose; elimina monolito anterior`.

---

### Task 2: Módulo users + autenticación

**Files:**
- Create: `app/shared/security.py`, `app/modules/users/{__init__,models,schemas,repository,service,router}.py`, migración `app/db/migrations/versions/0001_users.py`, `tests/helpers.py`, `tests/test_users_auth.py`
- Modify: `app/shared/deps.py`, `app/main.py`, `app/db/models_registry.py`

**Interfaces:**
- Consumes: Task 1 (`Settings`, errores, `get_session`).
- Produces:
  - `security.hash_password(plain: str) -> str`, `verify_password(plain: str, hashed: str) -> bool` (pwdlib Argon2), `create_access_token(user_id: UUID, role: str) -> str` (claims `sub`, `role`, `exp`), `decode_access_token(token: str) -> TokenData` (`@dataclass(frozen=True) TokenData(user_id: UUID, role: str)`; cualquier error de PyJWT → `Unauthorized("Tu sesión expiró o no es válida.")`).
  - `deps.CurrentUser = TokenData`; `async def current_user(request: Request) -> TokenData` (cookie `settings.cookie_name` primero, luego `Authorization: Bearer`; sin token → `Unauthorized`); `async def require_admin(user = Depends(current_user)) -> TokenData` (no admin → `Forbidden`). No consulta la DB.
  - Modelo `User`: tabla `users` (`id UUID pk default uuid4`, `name String(80)`, `email String(254) unique` en minúsculas, `password_hash`, `role` enum `user_role` (`listener`,`admin`), `created_at timestamptz default now()`).
  - schemas: `Role = Literal["listener","admin"]`; `UserOut(id, name, email, role)`; `RegisterIn(name: str 1..80, email: EmailStr, password: str min 8 max 128)`; `LoginIn(email, password)`; `TokenOut(access_token: str, token_type: Literal["bearer"], user: UserOut)`; `RoleIn(role: Role)`.
  - service: `register(session, data: RegisterIn) -> UserOut` (email duplicado → `Conflict(..., code="email_taken")`), `authenticate(session, email, password) -> UserOut` (falla → `Unauthorized("Correo o contraseña incorrectos.")`), `get_user(session, user_id) -> UserOut`, `list_users(session, q: str | None) -> list[UserOut]` (busca en nombre/email, máx 50), `set_role(session, actor_id: UUID, user_id: UUID, role: Role) -> UserOut` (actor == user y role == listener → `Forbidden`), `count_users(session) -> int`, `ensure_user(session, name, email, password, role) -> UserOut` (crea si no existe; si existe lo devuelve sin cambios).
  - Rutas: `POST /api/auth/register` → 201 `TokenOut` + cookie; `POST /api/auth/login` → 200 `TokenOut` + cookie; `POST /api/auth/logout` → 204 y borra cookie; `GET /api/auth/me` → `UserOut`; `GET /api/users?q=` (admin); `PATCH /api/users/{id}/role` (admin).
  - `tests/helpers.py`: `async def signup(client, email="oyente@test.mx", name="Oyente", password="secreta123") -> dict` (devuelve `TokenOut` json; la cookie queda en el client); `async def make_admin_client(session, client, email="admin@test.mx") -> AsyncClient` (usa `ensure_user` con role admin y hace login).

- [ ] **Step 1: Write the failing tests** en `tests/test_users_auth.py`:
  - `test_register_sets_cookie_and_returns_listener`: 201, `json()["user"]["role"] == "listener"`, `"fldsmdfr_session" in client.cookies`.
  - `test_register_duplicate_email_conflict`: segundo registro mismo email (con mayúsculas distintas) → 409, code `email_taken`.
  - `test_register_short_password_rejected`: password `"corta"` → 422, code `invalid_input`.
  - `test_login_wrong_password`: → 401, code `unauthorized`.
  - `test_me_with_cookie` y `test_me_with_bearer` (client sin cookies + header) → 200.
  - `test_me_without_token` → 401.
  - `test_tampered_token_is_401`: cookie `"abc.def.ghi"` → 401 (Review Focus 4).
  - `test_expired_token_is_401`: token creado con `exp` en el pasado (usar `jwt.encode` directo con el secreto) → 401.
  - `test_listener_cannot_list_users` → 403; `test_admin_lists_and_promotes`: admin `PATCH` rol de un oyente a `admin` → 200 `role == "admin"`.
  - `test_admin_cannot_demote_self` → 403.
  - `test_logout_clears_cookie`: después `GET /api/auth/me` → 401.
- [ ] **Step 2: Run** `docker compose --profile test run --rm tests pytest tests/test_users_auth.py -q` → FAIL.
- [ ] **Step 3: Implement** security, deps, módulo users, migración `0001_users`. Cookie: `max_age = jwt_expire_hours*3600`, `httponly=True`, `samesite="strict"`, `secure=settings.cookie_secure`.
- [ ] **Step 4: Run** → PASS (todas, incluida `test_health`).
- [ ] **Step 5: Commit** `feat(users): registro, login JWT en cookie y roles`.

---

### Task 3: Catálogo: listado, búsqueda y streaming con Range

**Files:**
- Create: `app/modules/catalog/{__init__,models,schemas,repository,service,router,audio,streaming}.py`, migración `0002_catalog.py`, `tests/audio_fixtures.py`, `tests/test_catalog_stream.py`, `tests/test_range_parser.py`
- Modify: `app/main.py`, `app/db/models_registry.py`

**Interfaces:**
- Consumes: Task 2 (`current_user`).
- Produces:
  - Modelo `Song`: tabla `songs` (`id UUID pk`, `title String(200)`, `artist String(200)`, `album String(200)`, `duration_seconds int`, `file_path String` relativo a `media_dir`, `mime_type`, `size_bytes bigint`, `is_active bool default true`, `created_at`); índice en `lower(title)`, `lower(artist)`.
  - schemas: `SongOut(id, title, artist, album, duration_seconds, is_active)`; `SongPage(items: list[SongOut], total: int)`.
  - `audio.py`: `@dataclass AudioInfo(duration_seconds: int, mime_type: str)`; `inspect_audio(path: Path) -> AudioInfo` (`mutagen.File(path)`; `None` o excepción → `InvalidInput("El archivo no es un audio válido.", code="invalid_audio")`; mime por extensión: `.mp3 audio/mpeg`, `.ogg audio/ogg`, `.wav audio/wav`; duración `round(info.length)`, mínimo 1).
  - `streaming.py`: `parse_range(header: str | None, size: int) -> tuple[int, int] | None` (inclusivo; `None` = servir completo; reglas en Review Focus 1); `async def file_response(path: Path, mime_type: str, size: int, range_header: str | None) -> Response` (`StreamingResponse` que lee en bloques de 64 KiB con `anyio.open_file`; 206 incluye `Content-Range: bytes a-b/size`, `Content-Length`; siempre `Accept-Ranges: bytes`).
  - service: `list_songs(session, q: str | None, limit: int = 50, offset: int = 0) -> SongPage` (solo activas; `ILIKE` sobre título/artista/álbum con `%`, `_` y `\` escapados; orden `title`), `get_song(session, song_id) -> SongOut` (inactiva o no existe → `NotFound`), `get_songs_by_ids(session, ids: Sequence[UUID]) -> dict[UUID, SongOut]` (incluye inactivas), `song_is_available(session, song_id) -> bool`, `get_stream_file(session, song_id) -> StreamFile` (`@dataclass StreamFile(path: Path, mime_type: str, size: int)`; inactiva → `NotFound`; archivo faltante → `NotFound`), `count_songs(session) -> int`.
  - Rutas (todas con `current_user`): `GET /api/songs?q=&limit=(1..100)&offset=(>=0)` → `SongPage`; `GET /api/songs/{id}` → `SongOut`; `GET /api/songs/{id}/stream`.
  - `tests/audio_fixtures.py`: `make_wav(path: Path, seconds: float = 2.0) -> Path` (stdlib `wave`, 8 kHz mono 16 bit, tono simple); `async def insert_song(session, media_dir: Path, title="Nubes de agosto", artist="Los Meteoros", album="Pronóstico", seconds=2.0, is_active=True) -> SongOut` (crea WAV en `media_dir` y fila vía `catalog.repository` — permitido en tests).

- [ ] **Step 1: Write the failing tests** `tests/test_range_parser.py` (unitarios, size=1000):
  - `None` → `None`; `"bytes=0-99"` → `(0, 99)`; `"bytes=900-"` → `(900, 999)`; `"bytes=-100"` → `(900, 999)`; `"bytes=900-5000"` → `(900, 999)`; `"bytes=0-1,4-5"` → `None`; `"bytes=1000-"` → `RangeNotSatisfiable`; `"bytes=50-10"` → `RangeNotSatisfiable`; `"items=0-1"` → `None`; `"bytes=-0"` → `RangeNotSatisfiable`.
- [ ] **Step 2: Write the failing tests** `tests/test_catalog_stream.py`:
  - `test_list_songs_requires_session` → 401.
  - `test_list_and_search`: 3 canciones; `q="meteoros"` devuelve solo las de ese artista; `total` correcto; inactiva no aparece.
  - `test_search_wildcards_are_literal`: canción "100% Lluvia" y "Lluvia"; `q="%"` → solo "100% Lluvia"; `q="_"` → 0 resultados (Review Focus 3).
  - `test_stream_full`: sin Range → 200, `accept-ranges: bytes`, bytes == archivo.
  - `test_stream_partial`: `Range: bytes=0-99` → 206, `content-range: bytes 0-99/<size>`, `len(content) == 100`, contenido == `file[0:100]`.
  - `test_stream_suffix`: `bytes=-50` → 206, últimos 50 bytes.
  - `test_stream_unsatisfiable`: `bytes=<size>-` → 416, `content-range: bytes */<size>`.
  - `test_stream_inactive_song_404` y `test_stream_unknown_song_404`.
- [ ] **Step 3: Run** `docker compose --profile test run --rm tests pytest tests/test_range_parser.py tests/test_catalog_stream.py -q` → FAIL.
- [ ] **Step 4: Implement** el módulo, migración `0002_catalog`, registro en `models_registry`. El handler de `RangeNotSatisfiable` agrega `Content-Range: bytes */<size>`: lanzar con atributo `size` y que `streaming.file_response` construya la respuesta 416 directamente (no pasa por el handler genérico).
- [ ] **Step 5: Run** → PASS.
- [ ] **Step 6: Commit** `feat(catalog): listado, búsqueda y streaming con HTTP Range`.

---

### Task 4: Catálogo: administración (subir, editar, desactivar)

**Files:**
- Modify: `app/modules/catalog/{schemas,service,router,repository}.py`
- Test: `tests/test_catalog_admin.py`

**Interfaces:**
- Consumes: Task 3 (`inspect_audio`, `Song`), Task 2 (`require_admin`).
- Produces:
  - schemas: `SongUpdate(title: str | None, artist: str | None, album: str | None)` (cada uno 1..200 si viene).
  - service: `async def create_song(session, title: str, artist: str, album: str, filename: str, stream: AsyncIterator[bytes] | UploadFile) -> SongOut` — escribe a `media_dir/.tmp-<uuid>`, corta con `InvalidInput(code="file_too_large")` al superar `max_upload_bytes`, valida extensión (`InvalidInput(code="unsupported_format")`), `inspect_audio`, mueve a `media_dir/<uuid>.<ext>`, inserta; ante cualquier error borra temporal/final. `async def import_song_file(session, source: Path, title, artist, album) -> SongOut` (para la semilla: copia el archivo con el mismo flujo de validación). `update_song(session, song_id, data: SongUpdate) -> SongOut`. `deactivate_song(session, song_id) -> None`.
  - Rutas (admin): `POST /api/songs` multipart (`title`, `artist`, `album`, `file`) → 201 `SongOut`; `PATCH /api/songs/{id}` → `SongOut`; `DELETE /api/songs/{id}` → 204.

- [ ] **Step 1: Write the failing tests** `tests/test_catalog_admin.py`:
  - `test_listener_cannot_upload` → 403.
  - `test_admin_uploads_wav`: WAV de 3 s → 201, `duration_seconds == 3`, aparece en `GET /api/songs`, `GET /stream` → 200.
  - `test_upload_garbage_mp3_rejected_without_orphan`: bytes `b"no soy audio"*100` como `x.mp3` → 422 code `invalid_audio`; `list(media_dir.iterdir())` no cambia (Review Focus 2).
  - `test_upload_unsupported_extension` (`.flac`) → 422 `unsupported_format`.
  - `test_upload_too_large`: con `max_upload_bytes` parcheado a 1024 vía `get_settings.cache_clear()` + env, archivo de 2048 bytes → 422 `file_too_large`, sin huérfano.
  - `test_upload_missing_title` → 422 `invalid_input`.
  - `test_admin_updates_title` → 200 título nuevo.
  - `test_admin_deactivates_song`: 204; luego `GET /api/songs/{id}` → 404 y no aparece en listado.
- [ ] **Step 2: Run** `docker compose --profile test run --rm tests pytest tests/test_catalog_admin.py -q` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** toda la suite → PASS.
- [ ] **Step 5: Commit** `feat(catalog): subida, edición y desactivación de canciones para admin`.

---

### Task 5: Módulo playlists (casetes) con modo degradado

**Files:**
- Create: `app/modules/playlists/{__init__,models,schemas,repository,service,router}.py`, migración `0003_playlists.py`, `tests/test_playlists.py`
- Modify: `app/main.py`, `app/db/models_registry.py`

**Interfaces:**
- Consumes: `catalog.service.get_songs_by_ids`, `catalog.service.get_song`; `current_user`.
- Produces:
  - Modelos: `playlists(id UUID pk, owner_id UUID index, name String(60), created_at, updated_at)`; `playlist_songs(playlist_id FK→playlists ON DELETE CASCADE, song_id UUID, position int, title_snapshot, artist_snapshot, album_snapshot, duration_snapshot int, added_at, PK(playlist_id, song_id))`.
  - schemas: `PlaylistIn(name: str 1..60)`; `PlaylistSummary(id, name, song_count: int, updated_at)`; `PlaylistSongOut(song_id, title, artist, album, duration_seconds, position, status: Literal["ok","degraded","unavailable"])`; `PlaylistDetail(id, name, songs: list[PlaylistSongOut], total_seconds: int)`; `AddSongIn(song_id: UUID)`; `ReorderIn(song_ids: list[UUID])`.
  - service: `create_playlist(session, owner_id, data) -> PlaylistSummary`, `list_playlists(session, owner_id) -> list[PlaylistSummary]` (orden `created_at`), `get_playlist(session, owner_id, playlist_id) -> PlaylistDetail`, `rename_playlist(...) -> PlaylistSummary`, `delete_playlist(...) -> None`, `add_song(session, owner_id, playlist_id, song_id) -> PlaylistDetail` (`catalog.service.get_song` → `NotFound` si no existe/inactiva; repetida → `Conflict(code="song_already_in_playlist")`; position = max+1), `remove_song(...) -> PlaylistDetail` (recompacta posiciones), `reorder(session, owner_id, playlist_id, data: ReorderIn) -> PlaylistDetail` (debe ser permutación exacta, si no `InvalidInput(code="invalid_order")`). Playlist ajena o inexistente → `NotFound`.
  - Enriquecimiento en `get_playlist`: llama `catalog.service.get_songs_by_ids`; si lanza cualquier excepción → todas `status="degraded"` con snapshot (registrar warning en log); canción ausente o `is_active=False` → `"unavailable"` con snapshot; si no, `"ok"` con datos frescos.
  - Rutas: `GET/POST /api/playlists`, `GET/PATCH/DELETE /api/playlists/{id}`, `POST /api/playlists/{id}/songs` → 201 `PlaylistDetail`, `DELETE /api/playlists/{id}/songs/{song_id}`, `PUT /api/playlists/{id}/order`.

- [ ] **Step 1: Write the failing tests** `tests/test_playlists.py`:
  - `test_create_and_list` → 201; listado con `song_count == 0`.
  - `test_add_song_and_get_detail`: dos canciones → posiciones 1, 2; `total_seconds` suma; `status == "ok"`.
  - `test_add_unknown_song_404`, `test_add_duplicate_song_409` (code `song_already_in_playlist`).
  - `test_other_users_playlist_is_404`: segundo usuario `GET`/`POST songs` → 404.
  - `test_remove_and_reorder`: reorden `[b, a]` → posiciones invertidas; reorden con id ajeno → 422 `invalid_order`.
  - `test_deactivated_song_shows_unavailable`: desactivar canción → `status == "unavailable"`, título del snapshot.
  - `test_catalog_failure_degrades`: `monkeypatch` de `app.modules.catalog.service.get_songs_by_ids` para lanzar `RuntimeError` → 200 y todas `status == "degraded"` con snapshots (PRD F1‑c4).
  - `test_get_playlist_under_200ms`: playlist de 50 canciones; `time.perf_counter()` alrededor del `GET` < 0.2 s.
  - `test_delete_playlist` → 204 y luego 404.
- [ ] **Step 2: Run** `docker compose --profile test run --rm tests pytest tests/test_playlists.py -q` → FAIL.
- [ ] **Step 3: Implement.** El router importa `catalog.service` como módulo (`from app.modules.catalog import service as catalog_service`) para que el monkeypatch funcione.
- [ ] **Step 4: Run** toda la suite → PASS.
- [ ] **Step 5: Commit** `feat(playlists): casetes con snapshot y modo degradado`.

---

### Task 6: Módulo playback: eventos idempotentes, top y resumen

**Files:**
- Create: `app/modules/playback/{__init__,models,schemas,repository,service,router}.py`, migración `0004_playback.py`, `tests/test_playback.py`, `tests/test_architecture.py`
- Modify: `app/main.py`, `app/db/models_registry.py`

**Interfaces:**
- Consumes: `catalog.service.get_song`, `catalog.service.get_songs_by_ids`, `catalog.service.count_songs`, `users.service.count_users`; `current_user`, `require_admin`.
- Produces:
  - Modelos: `playback_events(playback_id UUID pk, song_id UUID index, user_id UUID, listened_seconds int, occurred_at timestamptz, received_at default now())`; `song_play_counts(song_id UUID pk, play_count bigint, last_played_at)`.
  - schemas: `PlaybackIn(playback_id: UUID, song_id: UUID, listened_seconds: int ≥ 10 ≤ 86400, occurred_at: datetime | None)`; `PlaybackOut(playback_id, counted: bool)`; `TopSongOut(song_id, title, artist, album, play_count: int)`; `MetricsSummary(total_playbacks: int, total_songs: int, total_users: int, top: list[TopSongOut])`.
  - service: `record_playback(session, user_id, data: PlaybackIn) -> bool` (valida `catalog.service.get_song`; en una transacción `INSERT ... ON CONFLICT (playback_id) DO NOTHING RETURNING playback_id`; solo si devolvió fila: upsert `song_play_counts` `play_count = play_count + 1`), `top_songs(session, limit: int = 10) -> list[TopSongOut]` (orden `play_count desc, last_played_at desc`; enriquece con `get_songs_by_ids`; omite inactivas; si el catálogo falla, devuelve `title="Canción no disponible"`), `total_playbacks(session) -> int`, `summary(session) -> MetricsSummary`.
  - Rutas: `POST /api/playbacks` → 201 `PlaybackOut(counted=True)` o 200 `PlaybackOut(counted=False)`; `GET /api/metrics/top?limit=(1..50)` (sesión); `GET /api/metrics/summary` (admin).

- [ ] **Step 1: Write the failing tests** `tests/test_playback.py`:
  - `test_first_event_counts` → 201 `counted is True`; top muestra `play_count == 1`.
  - `test_retry_same_id_not_double_counted` → segundo POST 200 `counted is False`; `play_count == 1`.
  - `test_concurrent_same_id_counts_once`: `asyncio.gather` de 5 POST con el mismo `playback_id` (cada uno con su propia sesión de DB) → exactamente un 201; `play_count == 1` (Review Focus 5).
  - `test_concurrent_distinct_ids`: 20 ids distintos en paralelo → `play_count == 20`.
  - `test_under_10_seconds_rejected` (`9`) → 422.
  - `test_unknown_song_404`.
  - `test_top_ordering`: A con 3, B con 1 → `[A, B]`.
  - `test_summary_admin_only`: oyente → 403; admin → totales correctos.
- [ ] **Step 2: Write the failing test** `tests/test_architecture.py::test_modules_only_use_public_interfaces`: recorre `app/modules/*/*.py` con `ast`; falla si un archivo del módulo X importa `app.modules.Y.(models|repository)` con Y ≠ X. Permitido: `service`, `schemas`.
- [ ] **Step 3: Run** `docker compose --profile test run --rm tests pytest tests/test_playback.py tests/test_architecture.py -q` → FAIL.
- [ ] **Step 4: Implement.** Para la prueba concurrente, `get_session` crea una sesión por petición (ya es así); el fixture `client` no debe compartir una sesión entre peticiones.
- [ ] **Step 5: Run** toda la suite → PASS.
- [ ] **Step 6: Commit** `feat(playback): reproducciones idempotentes, top y resumen de métricas`.

---

### Task 7: Semilla y arranque del contenedor

**Files:**
- Create: `scripts/seed.py`, `scripts/entrypoint.sh`, `media/seed/seed.json`, `media/seed/LICENCIAS.md`, `tests/test_seed.py`
- Modify: `Dockerfile` (`ENTRYPOINT ["/app/scripts/entrypoint.sh"]`), `.env.example`

**Interfaces:**
- Consumes: `users.service.ensure_user`, `catalog.service.import_song_file`, `catalog.service.list_songs`, `playlists.service.create_playlist/add_song/list_playlists`.
- Produces:
  - `seed.json`: `{"songs": [{"file": "nombre.mp3", "title": "...", "artist": "...", "album": "..."}], "demo_playlist": {"name": "Para la tarde lluviosa", "files": ["nombre.mp3", ...]}}`. Se entrega con `"songs": []` y un ejemplo comentado en `LICENCIAS.md` (el equipo pone la música).
  - `LICENCIAS.md`: tabla `Archivo | Título | Artista | Fuente (URL) | Licencia` vacía + instrucciones de cómo agregar pistas.
  - `async def run_seed(session: AsyncSession, seed_dir: Path) -> SeedReport` (`@dataclass SeedReport(users_created: int, songs_imported: int, songs_skipped: list[str])`); idempotencia de canciones por `(title, artist)` existente; archivo faltante o inválido → se agrega a `songs_skipped`, `logger.warning`, continúa. Crea admin y oyente desde `Settings`; crea la playlist demo para el oyente solo si no tiene playlists.
  - `python -m scripts.seed` ejecuta `run_seed` e imprime el reporte.
  - `entrypoint.sh` (`set -euo pipefail`): `alembic upgrade head` → `python -m scripts.seed` → `exec uvicorn app.main:app --host 0.0.0.0 --port 8000`.

- [ ] **Step 1: Write the failing tests** `tests/test_seed.py`:
  - `test_seed_imports_and_is_idempotent`: tmp `seed_dir` con 2 WAV + `seed.json`; primera corrida `songs_imported == 2`, `users_created == 2`; segunda `songs_imported == 0`, `users_created == 0`; `GET /api/songs` total 2; el oyente tiene 1 playlist con 2 canciones.
  - `test_seed_skips_missing_files`: `seed.json` referencia `falta.mp3` → `songs_skipped == ["falta.mp3"]`, sin excepción.
  - `test_seed_with_empty_song_list`: `songs: []` → no falla, crea usuarios, no crea playlist.
- [ ] **Step 2: Run** `docker compose --profile test run --rm tests pytest tests/test_seed.py -q` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** suite → PASS. Luego `docker compose up --build -d && curl -s localhost:8000/api/health` → `{"status":"ok","database":"ok"}`; `docker compose logs app` muestra el reporte de semilla; `docker compose down`.
- [ ] **Step 5: Commit** `feat: semilla idempotente y entrypoint con migraciones`.

---

### Task 8: DESIGN.md, base del frontend, temas y servido del SPA

**Files:**
- Create: `DESIGN.md` (reescrito), `ui/package.json`, `ui/vite.config.ts`, `ui/tsconfig.json`, `ui/tsconfig.node.json`, `ui/index.html`, `ui/src/{main.ts,App.vue,router.ts,env.d.ts}`, `ui/src/styles/{tokens.css,base.css}`, `ui/src/composables/useTheme.ts`, `ui/src/components/InterruptorLado.vue`, `ui/src/composables/__tests__/useTheme.spec.ts`, `app/spa.py`, `tests/test_spa.py`
- Modify: `Dockerfile` (etapa `node:22-alpine` → `npm ci && npm run build` → copia `ui/dist` a la imagen Python), `app/main.py`, `.dockerignore`

**Interfaces:**
- Produces:
  - `DESIGN.md` con: concepto casete mixtape y su porqué; anti‑patrones (no barra lateral + reproductor inferior); distribución dos columnas con ASCII wireframe; tokens de **ambos** temas (tabla abajo); tipografía y escala (títulos Fraunces SOFT 100 peso 800: 28/22/18 px; texto Figtree 15/13 px, line-height 1.5; Caveat 22 px solo etiquetas de casete); espaciado; componentes (`CaseteActivo`, `ControlesReproductor`, `BarraProgreso`, `ListaCasete`, `EstanteCasetes`, `PanelCatalogo`, `PanelTop`, `InterruptorLado`, `Aviso`) con estados (hover, foco, deshabilitado, cargando, vacío, error, degradado, no disponible); vista Cabina de grabación; responsive (< 900 px apila: casetera compacta arriba, pestañas "Catálogo / Mi casete / Lo más escuchado"); accesibilidad (contraste AA, foco visible 3 px `--accent2`, `aria-label` en botones de icono, reduced motion); tono de los textos con ejemplos ("Grabar en el casete", "Crear casete", vacíos: "Este casete está vacío. Busca una canción y pulsa + para grabarla.").
  - Tokens (`tokens.css`, mismos nombres en ambos temas, en `:root[data-lado="A"]` y `:root[data-lado="B"]`):

    | token | Lado A (Mostaza y oliva) | Lado B (Ámbar nocturno) |
    |---|---|---|
    | `--bg` | `#F5D7A1` | `#2A1B1D` |
    | `--ink` | `#33210F` | `#FCE9D8` |
    | `--paper` | `#FFF3DC` | `#3A2629` |
    | `--deck` | `#5B5A24` | `#1D1213` |
    | `--deck-ink` | `#FFF3DC` | `#FCE9D8` |
    | `--tape` | `#8A3A16` | `#B4452F` |
    | `--accent` | `#C4501E` | `#F2A541` |
    | `--on-accent` | `#FFF3DC` | `#2A1B1D` |
    | `--accent2` | `#F2B33D` | `#F2A541` |
    | `--rule` | `#E3BC7E` | `#4A3236` |
    | `--rule-deck` | `#76753A` | `#3A2629` |
    | `--danger` | `#9E2A1C` | `#FF8A6B` |

    Más `--space-1..5: 4,8,12,16,24px`, `--radius-s: 6px`, `--radius-m: 12px`, `--font-display`, `--font-body`, `--font-hand`.
  - `useTheme()` → `{ side: Readonly<Ref<'A' | 'B'>>, toggle(): void, set(side: 'A' | 'B'): void }`; estado singleton a nivel módulo; inicial = `localStorage['fldsmdfr-lado']` válido, si no `matchMedia('(prefers-color-scheme: dark)').matches ? 'B' : 'A'`; aplica `document.documentElement.dataset.lado`; `localStorage` envuelto en try/catch.
  - `InterruptorLado.vue`: `role="switch"`, `aria-checked` = lado B, texto visible "Lado A" / "Lado B".
  - `router.ts`: rutas `/acceso` (`AccesoView`), `/` (`CaseteraView`, `meta.auth`), `/cabina` (`CabinaView`, `meta.admin`); vistas placeholder en esta tarea; guard se completa en Task 9.
  - `app/spa.py`: `mount_spa(app: FastAPI, dist_dir: Path) -> None` — si `dist_dir/index.html` existe: monta `/assets` con `StaticFiles` y registra `GET /{full_path:path}` que devuelve archivo existente en `dist_dir` o `index.html`; rutas que empiezan por `api/` o `docs` → 404 JSON uniforme. Se llama al final de `create_app()`.
  - `vite.config.ts`: proxy `/api` → `http://localhost:8000`; vitest `environment: 'jsdom'`.
  - Scripts npm: `dev`, `build` (`vue-tsc --noEmit && vite build`), `test` (`vitest run`).
  - `main.ts` importa `@fontsource-variable/fraunces/full.css` (incluye eje SOFT), `@fontsource-variable/figtree`, `@fontsource-variable/caveat`, `tokens.css`, `base.css`, e inicializa `useTheme()` antes de montar.

- [ ] **Step 1:** Escribir `DESIGN.md` según lo anterior.
- [ ] **Step 2: Write the failing tests**
  - `tests/test_spa.py`: con tmp dist (`index.html` = `<div id="app"></div>`, `assets/app.js`): `GET /` y `GET /cabina` → 200 HTML con `id="app"`; `GET /assets/app.js` → 200; `GET /api/nada` → 404 JSON `not_found`.
  - `useTheme.spec.ts`: sin storage y `matchMedia` dark → `'B'` y `dataset.lado === 'B'`; con storage `'A'` → `'A'`; `toggle()` cambia y persiste; `localStorage` que lanza → no rompe y usa `matchMedia`.
- [ ] **Step 3: Run** `docker compose --profile test run --rm tests pytest tests/test_spa.py -q` y `cd ui && npm install && npm test` → FAIL.
- [ ] **Step 4: Implement** scaffolding Vite (Vue + TS a mano, sin plantillas de ejemplo), estilos, `useTheme`, `InterruptorLado`, `spa.py`, Dockerfile multi‑stage.
- [ ] **Step 5: Run** ambos → PASS; `cd ui && npm run build` sin errores de tipos; `docker compose up --build -d` y `curl -s localhost:8000/ | grep 'id="app"'`; `docker compose down`.
- [ ] **Step 6: Commit** `feat(ui): DESIGN.md, base Vue con temas Lado A/B y servido del SPA`.

---

### Task 9: Cliente API, sesión y vista de acceso

**Files:**
- Create: `ui/src/api/{types,http,auth,songs,playlists,playbacks,metrics,users}.ts`, `ui/src/composables/{useSession,useAvisos}.ts`, `ui/src/views/AccesoView.vue`, `ui/src/components/Aviso.vue`, `ui/src/api/__tests__/http.spec.ts`, `ui/src/composables/__tests__/useSession.spec.ts`
- Modify: `ui/src/router.ts`

**Interfaces:**
- Consumes: contratos de la API (Tasks 2–6).
- Produces:
  - `types.ts`: interfaces TS espejo de `UserOut`, `SongOut`, `SongPage`, `PlaylistSummary`, `PlaylistSongOut`, `PlaylistDetail`, `PlaybackIn`, `PlaybackOut`, `TopSongOut`, `MetricsSummary`.
  - `http.ts`: `class ApiError extends Error { status: number; code: string }`; `request<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T>` (`credentials: 'same-origin'`, serializa `json`, 204 → `undefined`, error → `ApiError` con `code` del cuerpo o `'network_error'` si falla `fetch`); `onUnauthorized(handler: () => void): void` (se invoca en cualquier 401 excepto de `/api/auth/login`).
  - Un archivo por recurso con funciones finas: `auth.login(email, password)`, `auth.register(name, email, password)`, `auth.logout()`, `auth.me()`; `songs.list(q?, offset?)`, `songs.streamUrl(id): string` (`/api/songs/${id}/stream`), `songs.upload(form: FormData)`, `songs.update(id, data)`, `songs.deactivate(id)`; `playlists.list/create/get/rename/remove/addSong/removeSong/reorder`; `playbacks.send(body: PlaybackIn): Promise<PlaybackOut>`; `metrics.top(limit?)`, `metrics.summary()`; `users.list(q?)`, `users.setRole(id, role)`.
  - `useSession()` → `{ user: Readonly<Ref<UserOut | null>>, isAdmin: ComputedRef<boolean>, ready: Ref<boolean>, load(): Promise<void>, login(email, password), register(name, email, password), logout() }`; singleton; `onUnauthorized` limpia `user` y navega a `/acceso`.
  - Guard en `router.ts`: espera `load()` una vez; `meta.auth` sin usuario → `/acceso`; `meta.admin` sin admin → `/`; usuario logueado en `/acceso` → `/`.
  - `AccesoView.vue`: dos pestañas "Entrar" / "Crear cuenta"; errores en línea por campo (mensaje del API); botón "Entrar" / "Crear cuenta" deshabilitado mientras envía; interruptor de lado visible. Estética: un solo casete grande con la etiqueta "FLDSMDFR" en Caveat como identidad.
  - `ui/src/composables/useAvisos.ts` → `{ avisos: Readonly<Ref<Array<{ id: number; texto: string; tipo: 'info' | 'error' }>>>, mostrar(texto: string, tipo?: 'info' | 'error'): void }`; autodescarta a los 5 s. `Aviso.vue` los pinta en una región `role="status"` `aria-live="polite"` montada en `App.vue`.

- [ ] **Step 1: Write the failing tests**
  - `http.spec.ts` (mock `fetch`): 200 JSON → objeto; 204 → `undefined`; 409 con `{"error":{"code":"email_taken","message":"..."}}` → `ApiError` con `code === 'email_taken'`; 401 en `/api/playlists` llama al handler de `onUnauthorized`; 401 en `/api/auth/login` no lo llama; `fetch` rechazado → `code === 'network_error'`.
  - `useSession.spec.ts`: `load()` con `me` 401 → `user === null`, `ready === true`; `login` exitoso → `user` poblado; `isAdmin` según rol.
- [ ] **Step 2: Run** `cd ui && npm test` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `npm test` y `npm run build` → PASS.
- [ ] **Step 5: Commit** `feat(ui): cliente API, sesión y pantalla de acceso`.

---

### Task 10: Reproductor: telemetría, estado y barra de progreso

**Files:**
- Create: `ui/src/composables/{usePlaybackTelemetry,usePlayer}.ts`, `ui/src/components/{BarraProgreso,ControlesReproductor,CaseteActivo}.vue`, tests `ui/src/composables/__tests__/usePlaybackTelemetry.spec.ts`, `ui/src/components/__tests__/BarraProgreso.spec.ts`

**Interfaces:**
- Consumes: `playbacks.send`, `songs.streamUrl`, `useAvisos`.
- Produces:
  - `createPlaybackTelemetry(deps: { send: (b: PlaybackIn) => Promise<unknown>; uuid?: () => string; sleep?: (ms: number) => Promise<void> })` → `{ startSession(songId: string): void; onTimeUpdate(currentTime: number): void; status: Readonly<Ref<'idle' | 'counting' | 'sending' | 'sent' | 'failed'>> }`.
    Algoritmo: `startSession` genera un `playback_id` nuevo y reinicia acumulado/último tiempo. En `onTimeUpdate(t)`: `delta = t - last`; si `0 < delta <= 1.5` se suma (saltos y retrocesos no suman); `last = t`. Al llegar a `>= 10` por primera vez en la sesión: envía `{ playback_id, song_id, listened_seconds: Math.floor(acc) }`; si falla, reintenta con el **mismo** cuerpo tras 1000, 2000 y 4000 ms (1 intento + 3 reintentos); agota → `'failed'` (el que llama muestra aviso). Nunca lanza.
  - `usePlayer()` singleton → `{ current: Ref<SongOut | null>, queue: Ref<SongOut[]>, isPlaying: Ref<boolean>, currentTime: Ref<number>, duration: Ref<number>, buffered: Ref<Array<[number, number]>>, volume: Ref<number>, attach(el: HTMLAudioElement): void, play(song: SongOut, queue?: SongOut[]): Promise<void>, toggle(): void, next(): void, prev(): void, seek(seconds: number): void, setVolume(v: number): void }`. `play` asigna `src = songs.streamUrl(id)` y llama `telemetry.startSession`; `timeupdate` alimenta `currentTime`, `buffered` (desde `el.buffered`) y `telemetry.onTimeUpdate`; `ended` → `next()`; `prev()` reinicia a 0 si `currentTime > 3`, si no va a la anterior; error de audio → aviso "No se pudo reproducir la canción." y `isPlaying=false`. Telemetría `failed` → aviso info "No pudimos registrar esta reproducción; la música sigue." (el audio no se toca).
  - `BarraProgreso.vue` props `{ currentTime: number; duration: number; buffered: Array<[number, number]> }`, emite `seek(seconds: number)`; `role="slider"`, `aria-valuemin=0`, `aria-valuemax=duration`, `aria-valuenow=currentTime`, `aria-valuetext="1:12 de 3:41"`; un `.segmento-descargado` por rango con `left/width` en % de `duration`; clic → seek proporcional; teclas ←/→ ∓5 s, Home/End.
  - `ControlesReproductor.vue`: botones ⏮ ▶/⏸ ⏭ (40 px, play 52 px, `aria-label` "Anterior", "Reproducir"/"Pausar", "Siguiente"), volumen (`input type=range`, `aria-label="Volumen"`), título/artista, tiempo `m:ss / m:ss`, `BarraProgreso`.
  - `CaseteActivo.vue` props `{ etiqueta: string; girando: boolean }`: casete con etiqueta en Caveat y ventanita con dos carretes; `.girando` anima rotación salvo `prefers-reduced-motion`.

- [ ] **Step 1: Write the failing tests** (`vi.useFakeTimers()`, `sleep` inyectado con timers):
  - `sends once after 10 listened seconds`: ticks de 0.25 s hasta 12 s → `send` llamado 1 vez con `listened_seconds === 10`.
  - `seeks do not count`: ticks 0→5 s, salto a 60, ticks 60→64 → no envía; seguir hasta acumular 10 → envía.
  - `retries with same playback_id`: `send` falla 2 veces y luego resuelve → 3 llamadas, mismo `playback_id`, `status === 'sent'`; esperas 1000 y 2000 ms.
  - `gives up after 4 attempts`: siempre falla → 4 llamadas, `status === 'failed'`, no lanza.
  - `new session gets new id`: segundo `startSession` y 10 s más → segundo envío con `playback_id` distinto.
  - `BarraProgreso.spec.ts`: `duration=200`, `buffered=[[0,50],[100,150]]` → 2 `.segmento-descargado` con `left:0%;width:25%` y `left:50%;width:25%`; `ArrowRight` con `currentTime=10` emite `seek(15)`; `aria-valuetext` "0:10 de 3:20".
- [ ] **Step 2: Run** `cd ui && npm test` → FAIL.
- [ ] **Step 3: Implement.** `usePlayer` usa `createPlaybackTelemetry({ send: playbacks.send })`.
- [ ] **Step 4: Run** `npm test`, `npm run build` → PASS.
- [ ] **Step 5: Commit** `feat(ui): reproductor con telemetría idempotente y barra de fragmentos`.

---

### Task 11: Vista Casetera (casetes, catálogo, top, responsive)

**Files:**
- Create: `ui/src/composables/useCasetes.ts`, `ui/src/components/{ListaCasete,EstanteCasetes,PanelCatalogo,PanelTop}.vue`, `ui/src/views/CaseteraView.vue`, test `ui/src/composables/__tests__/useCasetes.spec.ts`, `ui/src/components/__tests__/PanelCatalogo.spec.ts`

**Interfaces:**
- Consumes: `playlists.*`, `songs.list`, `metrics.top`, `usePlayer`, `useAvisos`, `useSession`, Task 10 componentes.
- Produces:
  - `useCasetes()` singleton → `{ casetes: Ref<PlaylistSummary[]>, activo: Ref<PlaylistDetail | null>, cargar(): Promise<void>, seleccionar(id: string): Promise<void>, crear(nombre: string): Promise<void>, renombrar(nombre: string), eliminar(): Promise<void>, grabar(songId: string): Promise<void>, quitar(songId: string): Promise<void>, mover(songId: string, direccion: -1 | 1): Promise<void> }`. `cargar` selecciona el primero si no hay activo. `grabar` sin casete activo → aviso "Crea un casete primero."; `song_already_in_playlist` → aviso "Esa canción ya está en este casete.". Éxito → aviso "Grabada en «<nombre>»".
  - `ListaCasete.vue`: filas del casete activo; clic reproduce desde esa canción (cola = canciones `ok`/`degraded`); `unavailable` atenuada con texto "No disponible" y sin reproducir; `degraded` con marca discreta "Datos guardados" y `title` explicativo; botones subir/bajar/quitar (40 px, `aria-label`). Vacío: "Este casete está vacío. Busca una canción y pulsa + para grabarla."
  - `EstanteCasetes.vue`: lomos de casete (≥ 40 px alto) por playlist con `aria-pressed` para el activo; último lomo punteado "Nuevo casete" que abre input en línea (Enter crea, Esc cancela).
  - `PanelCatalogo.vue`: buscador con debounce 250 ms (`aria-label="Buscar canción, artista o álbum"`), lista con título, artista · álbum, duración, botón "+" (`aria-label="Grabar «<título>» en el casete"`), clic en fila reproduce; "Cargar más" con `offset`; estados cargando/vacío ("No encontramos canciones con «<q>».")/error con "Reintentar".
  - `PanelTop.vue`: lista ordenada de `metrics.top(10)` con conteo; nota "Se actualiza cada pocos segundos" (refresca cada 15 s mientras está visible); error → mensaje y reintento sin afectar al reproductor.
  - `CaseteraView.vue`: dos columnas (izq. casetera: `CaseteActivo` con etiqueta = nombre del casete activo, `ControlesReproductor`, `ListaCasete`, `EstanteCasetes`; der.: pestañas "Catálogo" / "Lo más escuchado", encabezado con `InterruptorLado`, nombre de usuario, "Cabina de grabación" si admin, "Salir"). Contiene el único `<audio>` (`usePlayer().attach`). < 900 px: casetera compacta arriba (casete pequeño + controles) y pestañas "Catálogo / Mi casete / Lo más escuchado".

- [ ] **Step 1: Write the failing tests**
  - `useCasetes.spec.ts` (mock de `api/playlists`): `cargar` selecciona el primero; `grabar` sin activo → `mostrar` llamado con "Crea un casete primero." y no llama al API; `grabar` con `ApiError('song_already_in_playlist')` → aviso correspondiente; `mover(id, -1)` llama `reorder` con el arreglo intercambiado.
  - `PanelCatalogo.spec.ts`: escribir "lluvia" → tras 250 ms una sola llamada `songs.list('lluvia', 0)`; clic en "+" llama `grabar(songId)`; respuesta vacía muestra el texto de vacío con la búsqueda.
- [ ] **Step 2: Run** `cd ui && npm test` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `npm test`, `npm run build` → PASS. Verificación manual con `docker compose up --build`: entrar como oyente demo, buscar, reproducir, saltar en la barra (los segmentos descargados se ven), crear casete, grabar, reordenar, ver top tras 10 s de escucha, alternar Lado A/B, recargar (lado persiste), ancho 375 px sin scroll horizontal, navegación completa con teclado.
- [ ] **Step 5: Commit** `feat(ui): casetera con casetes, catálogo y lo más escuchado`.

---

### Task 12: Cabina de grabación (admin)

**Files:**
- Create: `ui/src/views/CabinaView.vue`, `ui/src/components/{FormularioSubida,TablaCanciones,ResumenMetricas,GestionUsuarios}.vue`, test `ui/src/components/__tests__/FormularioSubida.spec.ts`

**Interfaces:**
- Consumes: `songs.upload/update/deactivate/list`, `metrics.summary`, `users.list/setRole`, `useSession`, `useAvisos`.
- Produces:
  - `FormularioSubida.vue`: campos título, artista, álbum, archivo (`accept=".mp3,.ogg,.wav"`); validación local (requeridos, extensión, ≤ 20 MB → "El archivo pesa más de 20 MB.") antes de enviar; errores del API por `code` (`invalid_audio`, `unsupported_format`, `file_too_large`) con texto claro; botón "Subir canción" → aviso "Canción subida" y emite `subida(song: SongOut)`.
  - `TablaCanciones.vue`: búsqueda, edición en línea de título/artista/álbum ("Guardar"), "Retirar del catálogo" con confirmación (`window.confirm` con el título).
  - `ResumenMetricas.vue`: total de reproducciones, canciones, usuarios y top 10.
  - `GestionUsuarios.vue`: buscador, lista con rol, botón "Hacer admin" / "Quitar admin" (oculto para uno mismo).
  - `CabinaView.vue`: encabezado "Cabina de grabación" + "Volver a la casetera"; las cuatro secciones; mismo sistema visual.

- [ ] **Step 1: Write the failing test** `FormularioSubida.spec.ts`: archivo `.flac` → mensaje "Formato no compatible. Usa MP3, OGG o WAV." sin llamar al API; archivo de 21 MB → "El archivo pesa más de 20 MB."; envío válido llama `songs.upload` con `FormData` que contiene `title`, `artist`, `album`, `file`; `ApiError('invalid_audio')` → "El archivo no es un audio válido.".
- [ ] **Step 2: Run** `cd ui && npm test` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `npm test`, `npm run build` → PASS. Manual: entrar como admin demo, subir un WAV/MP3, reproducirlo desde la casetera, editarlo, retirarlo (desaparece del catálogo y queda "No disponible" en casetes), promover al oyente, entrar como oyente y confirmar que `/cabina` redirige a `/`.
- [ ] **Step 5: Commit** `feat(ui): cabina de grabación para administradores`.

---

### Task 13: Documentación y verificación final

**Files:**
- Modify: `README.md`, `AGENTS.md`, `.env.example` (revisar)

**Interfaces:** ninguna nueva.

- [ ] **Step 1:** `README.md`: qué es, requisitos (Docker), `cp .env.example .env` (opcional), `docker compose up --build`, URL `http://localhost:8000` y `/docs`, credenciales demo, cómo agregar música (`media/seed/` + `seed.json` + `LICENCIAS.md`), pruebas (`docker compose --profile test run --rm tests` y `cd ui && npm test`), desarrollo de UI (`npm run dev`), mapa de carpetas y módulos, `docker compose down -v`.
- [ ] **Step 2:** `AGENTS.md`: reemplazar §1.1 y §2 (Laravel/Vue/MySQL) por el stack y la estructura reales (`app/modules` = lógica, `app/db` = datos, `ui/` = interfaz) y la regla de interfaces públicas entre módulos; conservar §4 y §5.
- [ ] **Step 3: Verify** desde cero: `docker compose down -v && docker compose up --build -d`; health ok; `docker compose --profile test run --rm tests` → todas pasan; `docker compose run --rm tests ruff check .` → limpio; `cd ui && npm ci && npm test && npm run build` → PASS. Registrar los resultados reales en el mensaje de entrega.
- [ ] **Step 4: Commit** `docs: README y AGENTS.md acordes al nuevo monolito`.
