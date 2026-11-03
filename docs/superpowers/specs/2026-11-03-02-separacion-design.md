# Diseño · `02-separacion`

Fecha: 2026-11-03 · Rama: `02-separacion` (parte de `01-monolito`, commit `4c98937`).

## Intención

Dar el primer paso del plan de ramas del PRD, con el mismo recorrido que el curso hace con Mexi
Banco (`01-monolito` → `02-separacion`): el monolito modular se **parte en tres procesos
independientes**, cada uno con **su propia base de datos**, que se hablan **por HTTP** usando los
nombres DNS de Docker Compose. La rama debe permitir, en la defensa, señalar dónde vive cada pieza
y **mostrar a propósito qué se rompe** cuando un servicio cae, porque todavía no hay resiliencia.

## Metas

1. Tres servicios FastAPI, cada uno en su contenedor, con su base y sus migraciones:
   | Servicio | Módulos del monolito | Base | Volumen |
   |---|---|---|---|
   | `users-playlists` | `users`, `playlists`, `social` | `users_playlists` | `playlist-covers` |
   | `catalog-streaming` | `catalog` | `catalog` | `media` (audio y portadas de canciones) |
   | `playback-metrics` | `playback` | `playback` | — |
2. Las llamadas que hoy son `import` entre módulos de servicios distintos pasan a ser **HTTP
   síncrono** a endpoints internos (`/internal/...`), con un cliente pequeño por servicio remoto.
3. Un **proxy mínimo** (`web`, Nginx) en el puerto `8000` que sirve el SPA compilado y reparte
   `/api/...` por prefijo. La interfaz sigue funcionando igual que en `01-monolito`.
4. Semilla, pruebas y lint repartidos por servicio; la prueba de arquitectura se adapta.
5. `README.md` de la rama y `docs/PRD.md` actualizados (plan de ramas completo hasta el final).

## No metas (llegan en ramas siguientes, quedan escritas en el PRD)

- Gateway con balanceo, réplicas y directorio/discovery (`03`).
- Timeouts, reintentos, circuit breaker, degradación elegante, saga (`04`).
- Mensajería con broker para los eventos de reproducción, idempotencia en consumidor, DLQ, outbox
  (`05`).
- Persistencia políglota y caché (`06`).
- Autenticación entre servicios: los endpoints `/internal/...` confían en la red interna.

## Anti-metas

- Que la UI deje de funcionar o cambie su comportamiento visible.
- Bases compartidas, FK entre servicios o un servicio leyendo tablas de otro.
- Un paquete Python "común" importado por los tres: cada servicio es autónomo (ver decisiones).

## Decisiones

**Del equipo (en esta conversación):**
- Solo `02-separacion` se construye ahora; `03` en adelante se documentan en el PRD.
- La UI sigue funcionando con un proxy mínimo que solo reparte por prefijo.

**Propuestas por el agente (a revisar):**
- **Una instancia de PostgreSQL con tres bases** (como `db/init` de Mexi Banco), cada servicio con
  su usuario y su URL; ninguno conoce la base de otro. Cambiar a tres contenedores es solo
  configuración.
- **Código transversal copiado** (`shared/errors.py`, `shared/security.py`, `shared/deps.py`,
  `shared/images.py`) dentro de cada servicio, igual que el `compartido/` de Mexi Banco. Se acepta
  la duplicación para que cada servicio se despliegue y evolucione solo.
- **JWT validado localmente** en cada servicio con el secreto compartido (`FLDSMDFR_JWT_SECRET`):
  solo `users-playlists` emite tokens; los demás solo los decodifican. La cookie `httpOnly` llega
  a todos porque el navegador habla con un único origen (el proxy).
- **Nginx** como proxy (`nginx:alpine`, ya usado en los labs del curso). Construye el SPA en una
  etapa `node` y lo sirve; FastAPI deja de servir el SPA (`spa.py` se retira).
- **Clientes HTTP con `httpx`** (ya es dependencia de desarrollo; pasa a dependencia de ejecución).
  Sin timeouts explícitos ni reintentos más allá del valor por defecto de `httpx`: eso es `04`.
- **Migraciones nuevas por servicio**: cada servicio arranca su propia cadena Alembic con una
  revisión inicial que crea solo sus tablas (equivalente al estado final de `0001`–`0010`).

## Estructura del repositorio

```text
services/
  users-playlists/      app/{main.py,config.py,db/,shared/,modules/{users,playlists,social}/,clients/catalog.py}
  catalog-streaming/    app/{main.py,config.py,db/,shared/,modules/catalog/}
  playback-metrics/     app/{main.py,config.py,db/,shared/,modules/playback/,clients/{catalog.py,users.py}}
  <cada uno>/           Dockerfile, pyproject.toml, alembic.ini, scripts/, tests/
web/                    Dockerfile (node → nginx) y nginx.conf
ui/                     sin cambios funcionales
docker/initdb/          crea las tres bases (y sus copias _test)
docker-compose.yml      db, catalog-streaming, users-playlists, playback-metrics, web; perfil test
```

La carpeta `app/` raíz del monolito se elimina en esta rama (sigue intacta en `01-monolito`).

## Rutas del proxy

| Prefijo público | Servicio |
|---|---|
| `/api/me/history` | `playback-metrics` |
| `/api/playbacks`, `/api/metrics/` | `playback-metrics` |
| `/api/songs` | `catalog-streaming` (con `proxy_buffering off` para el streaming con `Range`) |
| `/api/auth`, `/api/users`, `/api/playlists`, `/api/invites`, `/api/me/` | `users-playlists` |
| `/api/health` | responde el proxy; cada servicio tiene además su `/api/health` interno |
| `/internal/...` | **no se expone** (404 en el proxy) |
| todo lo demás | SPA (`index.html` como respaldo para Vue Router) |

`client_max_body_size` igual al límite de subida (20 MB).

## Contratos internos (HTTP, red de Compose)

`catalog-streaming` (`http://catalog-streaming:8000/internal`):
- `GET /songs/{id}` → `SongOut` o 404 si no existe o está inactiva.
- `POST /songs/batch` `{ids}` → `[SongOut]` (equivale a `get_songs_by_ids`).
- `GET /songs/count` → `{count}`.
- `POST /artists/counts` `{artists}` → `{artista_normalizado: n}`.
- `POST /artists/latest` `{artists}` → `{artista_normalizado: SongOut}`.
- `POST /artists/releases` `{follows: [{artist, since}], not_before}` → `[SongOut]`.
- `GET /songs/lookup?title=&artist=` → `SongOut` o 404 (para la semilla del casete demo).

`users-playlists` (`http://users-playlists:8000/internal`):
- `GET /users/count` → `{count}`.

`normalize_artist` (strip + lower) es una regla pura: se copia en el cliente de `users-playlists`
para normalizar sus propias claves de seguimiento, documentando que la fuente es el catálogo.

Errores remotos: un 404 del catálogo se traduce al mismo `NotFound` de antes (mismo código de
error); cualquier otra falla de red o 5xx se traduce a un `503` uniforme `service_unavailable`
con el nombre del servicio. Sin degradación todavía: es el comportamiento que `04` mejora.

## Semilla

- `catalog-streaming`: importa las canciones de `media/seed/seed.json`.
- `users-playlists`: crea los usuarios demo y el casete demo, resolviendo cada archivo por
  `GET /internal/songs/lookup`. Arranca después de que `catalog-streaming` esté `healthy`.
- `playback-metrics`: sin semilla.

Todas siguen siendo idempotentes.

## Pruebas

- Cada servicio tiene su `tests/` con las pruebas del monolito que le corresponden, contra su base
  `_test`. Las dependencias remotas se sustituyen con `httpx.MockTransport` (sin dependencias
  nuevas).
- Prueba de arquitectura por servicio: ningún archivo importa código de otro servicio, y dentro de
  `users-playlists` se mantiene la regla de módulos (`service`/`schemas` solamente).
- Pruebas nuevas de los clientes: 404 remoto → `NotFound`; servicio caído → `503`.
- `docker compose --profile test run --rm tests-<servicio>` por servicio; `ui` con `npm test` y
  `npm run build`.
- Verificación manual: `docker compose up --build`, la UI en `http://localhost:8000` (login,
  catálogo, reproducir, casetes, favoritas, métricas) y la demo de falla.

## Demo de falla (para el README)

`docker compose stop catalog-streaming` → el login y la lista de casetes siguen; abrir un casete,
el catálogo, el inicio con "lo más escuchado" y registrar una reproducción responden `503`. Al
encenderlo vuelve todo. Muestra por qué `04` agrega timeouts, degradación y circuit breaker.

## Documentación

- `README.md`: qué cambió respecto a `01`, diagrama de contenedores, cómo levantar y probar, rutas,
  demo de falla, qué queda fuera y tabla de etapas.
- `AGENTS.md`: estructura y regla de servicios actualizadas (regla 11).
- `docs/PRD.md` §6–§8: servicios reales, `web` como proxy de `02`, plan de ramas `02`–`06`
  alineado con el curso (S07 gateway/discovery/balanceo, S08 saga y circuit breaker, S09
  mensajería, S11 políglota y caché), y corrección del stack (PostgreSQL 16, Python 3.12).

## Riesgos y limitaciones

- Más llamadas de red en vistas que antes eran un solo proceso (p. ej. detalle de casete): mayor
  latencia; aceptable en `02` y se medirá en `03`.
- Código transversal duplicado en tres lugares: un arreglo de seguridad hay que replicarlo.
- Las bases existentes del monolito (`pgdata`) no se migran: la rama arranca con volúmenes nuevos
  (`docker compose down -v` si se viene de `01`).
- `/internal` sin autenticación: aceptable solo porque el proxy no lo expone.

## Lo que queda a criterio de quien construye

Nombres de funciones de los clientes, orden de los commits, forma exacta del `nginx.conf` y de los
scripts de entrada, y cómo agrupar las pruebas, siempre que se cumpla lo anterior.
