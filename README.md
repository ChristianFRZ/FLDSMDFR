# MELOXO · Streaming musical (monolito modular)

**MELOXO** es el nombre visible de la aplicación; el repositorio, los paquetes y los contenedores conservan el nombre del equipo, `FLDSMDFR`.

Proyecto semestral de **Sistemas Distribuidos** (Semestre 2027-1, FI-UNAM). Esta rama entrega el paso `01-monolito` del plan del [PRD](docs/PRD.md): una aplicación de streaming de música con una sola API, una sola base de datos y una interfaz web, organizada en módulos que más adelante se separarán en servicios.

## Equipo

- **Nombre del equipo:** `FLDSMDFR`
- Franco Ramírez Christian ([@ChristianFRZ](https://github.com/ChristianFRZ))
- López Hernández Miriam Amisadai ([@AmisadaiLopez](https://github.com/AmisadaiLopez))
- Nava Santiago Erick ([@Saiko-E](https://github.com/Saiko-E))
- Pérez Paitán Brent Armando ([@zmd-brnt](https://github.com/zmd-brnt))

## Qué es

- **Backend:** FastAPI (Python 3.12) con SQLAlchemy asíncrono y PostgreSQL 16. Migraciones con Alembic.
- **Frontend:** Vue 3 + Vue Router + Vite (TypeScript), compilado en la imagen y servido por la misma app.
- **Funciones:**
  - Registro e inicio de sesión (JWT en cookie `httpOnly`).
  - Catálogo y streaming con soporte de `Range`; panel **Streaming** que muestra los fragmentos descargados, el formato y el bitrate estimado.
  - Reproductor con cola, aleatorio, repetir (todo / una), pantalla completa ("Sonando ahora") y atajo de barra espaciadora.
  - **Casetes** (listas de reproducción) con portada, orden por arrastre o teclado y **casetes colaborativos** por enlace de invitación.
  - **Tus favoritas** (corazón) e **historial** de lo escuchado.
  - **Seguir artistas** desde el Catálogo y **avisos** de lanzamientos e invitaciones (consulta cada 30 s mientras la pestaña está visible).
  - Página de inicio con saludo, lo más escuchado, artistas más escuchados y "Vuelve a lo que te gusta".
  - **Cabina** para administradores: subir canciones con portada, cambiar portadas, retirar temas y gestionar roles.
  - Letras, dispositivos y "Plus" aparecen deshabilitados ("Próximamente").
- **Diseño visual:** tema oscuro oliva y mostaza con el logo Sol‑carrete; ver [DESIGN.md](DESIGN.md). Reglas de trabajo del equipo y de los agentes: [AGENTS.md](AGENTS.md).

## Inicio rápido

Requisito: Docker con Docker Compose.

```bash
cp .env.example .env     # opcional: sin .env se usan los mismos valores por defecto
docker compose up --build
```

- Aplicación: <http://localhost:8000>
- Documentación de la API (Swagger): <http://localhost:8000/docs>
- Salud: <http://localhost:8000/api/health>

Al arrancar, el contenedor aplica las migraciones y ejecuta la semilla (usuarios demo, canciones de `media/seed/` y el casete demo).

### Credenciales demo

| Rol           | Correo               | Contraseña    |
| ------------- | -------------------- | ------------- |
| Administrador | `admin@fldsmdfr.mx`  | `admin12345`  |
| Oyente        | `oyente@fldsmdfr.mx` | `oyente12345` |

Se pueden cambiar con las variables `FLDSMDFR_ADMIN_*` y `FLDSMDFR_LISTENER_*` (ver `.env.example`).

## Agregar música

El repositorio no incluye canciones por defecto: `media/seed/seed.json` está vacío hasta que se agregue música con licencia libre.

1. Copia el archivo `.mp3`, `.ogg` o `.wav` (máximo 20 MB) en `media/seed/`.
2. Agrega una entrada en `songs` de `media/seed/seed.json`:

   ```json
   {"file": "nombre.mp3", "title": "Título", "artist": "Artista", "album": "Álbum"}
   ```

3. Para incluirla en el casete demo, agrega el nombre del archivo en `demo_playlist.files`.
4. Registra la fuente y la licencia en [`media/seed/LICENCIAS.md`](media/seed/LICENCIAS.md).
5. Reconstruye con `docker compose up --build` (la semilla se copia a la imagen). La semilla es idempotente: una canción con el mismo título y artista no se importa dos veces.

También se pueden subir canciones desde la cabina de la interfaz (solo administradores) o con `POST /api/songs`.

## Pruebas

```bash
# Backend (pytest, usa una base de datos aparte: fldsmdfr_test)
docker compose --profile test run --rm tests

# Lint del backend
docker compose run --rm tests ruff check .

# Frontend (Vitest) y build con verificación de tipos
cd ui && npm ci && npm test && npm run build
```

`tests/test_architecture.py` verifica que los módulos respeten sus límites (ver más abajo).

## Desarrollo de la interfaz

Con el backend corriendo en el puerto 8000:

```bash
cd ui
npm ci
npm run dev
```

Requiere Node >= 22.12. Vite sirve la UI con recarga en caliente; la aplicación de Docker sirve la versión compilada.

## Mapa de carpetas y módulos

```text
app/
  main.py, spa.py, config.py   # ensamblado de la app, servir el SPA, configuración
  modules/
    users/       # registro, login, sesión, roles
    catalog/     # canciones, portadas, subida (admin), streaming con Range
    playlists/   # casetes, su orden, portada, miembros e invitaciones por enlace
    playback/    # registro de reproducciones, métricas e historial
    social/      # favoritas, artistas seguidos y avisos
  db/            # sesión, base declarativa, migraciones Alembic
  shared/        # errores uniformes, seguridad (JWT, hashing), dependencias
ui/src/          # api/, components/, composables/, views/, styles/
scripts/         # entrypoint.sh (migra, siembra, arranca) y seed.py
media/seed/      # música semilla, seed.json y LICENCIAS.md
tests/           # pruebas de backend
docs/            # PRD y especificación de diseño
```

Cada módulo contiene `router.py`, `service.py`, `repository.py`, `models.py` y `schemas.py`. Regla: un módulo solo usa a otro mediante su `service.py` y `schemas.py`, y no hay llaves foráneas entre tablas de módulos distintos.

### Relación con los servicios futuros (PRD §6)

| Módulo del monolito | Servicio futuro |
| --- | --- |
| `users`, `playlists` y `social` | `users-playlists-service` |
| `catalog` | `catalog-streaming-service` |
| `playback` | `playback-metrics-service` |

El API Gateway (`02-separacion` y siguientes) será un componente nuevo. Gracias a la regla de módulos, cada carpeta de `app/modules/` puede extraerse con su propia base de datos sin reescribir a sus vecinos.

## Limitaciones conocidas y riesgos

- **Rol dentro del JWT:** el rol del usuario viaja en el token (vigencia de 8 h) y los permisos se deciden con él. Tras una promoción o degradación, la sesión abierta conserva el rol anterior hasta la siguiente llamada a `/api/auth/me` (es decir, la próxima carga de página), que reemite la cookie con el rol vigente. Las peticiones de un token ya emitido que no pasen por `/auth/me` siguen usando el rol antiguo.
- **Subidas sin sesión:** en `POST /api/songs`, la guarda temprana de tamaño (`Content-Length` mayor a 20 MB + 1 MiB responde 422) se ejecuta antes de la autenticación; una subida enorme sin sesión recibe 422 en lugar de 401.
- **Configuración de seguridad:** `FLDSMDFR_COOKIE_SECURE` es `false` por defecto para HTTP local; debe ser `true` detrás de HTTPS. El secreto JWT por defecto de `.env.example` y de `docker-compose.yml` debe cambiarse fuera de desarrollo local.
- **Avisos por consulta periódica:** los avisos se piden cada 30 s solo con la pestaña visible; un lanzamiento puede tardar hasta ese tiempo en aparecer. Los lanzamientos se calculan al leer (últimos 30 días) y, si el catálogo falla, solo se muestran las invitaciones.
- **Enlaces de invitación:** quien tenga el enlace puede unirse al casete y grabar en él. Generar un enlace nuevo, o revocarlo, anula el anterior.
- **Contador de reproducciones:** en el monolito se incrementa de forma síncrona (PRD §6), pero la lista "lo más escuchado" se documenta como eventualmente consistente.
- **Migraciones editadas en sitio:** durante el desarrollo (sin versión publicada) se modificaron las migraciones existentes. Quien tenga un volumen de desarrollo antiguo debe ejecutar `docker compose down -v`.

## Apagar

```bash
docker compose down        # detiene y conserva los datos (volúmenes pgdata y media)
docker compose down -v     # detiene y borra también la base de datos y el audio subido
```
