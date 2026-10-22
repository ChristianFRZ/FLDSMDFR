# FLDSMDFR · Monolito Modular (Fase 01-monolito)

Documento explicativo de la arquitectura monolítica inicial desarrollada para el proyecto semestral de **Sistemas Distribuidos (FI-UNAM)**.

---

## 1. Resumen de la Implementación

Siguiendo estrictamente lo especificado en la **Sección 6 del PRD (`01-monolito`)**, se ha implementado una aplicación única en **Python 3.11+ con FastAPI y SQLite**, donde la lógica reside en un solo proceso pero con una separación modular estricta de responsabilidades (Clean Architecture / Modular Monolith) para facilitar la posterior descomposición en microservicios (`02-separacion`).

---

## 2. Archivos Creados y Modificados

### 2.1. Configuración y Reglas del Proyecto
- [`AGENTS.md`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/AGENTS.md): Reglas de operación para agentes, responsabilidades de capas y criterios de aceptación.
- [`SKILLS.md`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/SKILLS.md): Catálogo de prompts de ingeniería, testing, refactorización y rol de Asesor Técnico Crítico.
- [`DESIGN.md`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/DESIGN.md): Guía de estilo visual, tokens de diseño, paleta de colores y especificación de experiencia de usuario.
- [`.gitignore`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/.gitignore): Exclusión de entornos virtuales, bases de datos locales SQLite, cachés de Python y binarios.
- [`requirements.txt`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/requirements.txt): Dependencias de Python (`fastapi`, `uvicorn`, `aiofiles`, `pydantic`, `pytest`, `httpx`, `email-validator`).
- [`pytest.ini`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/pytest.ini): Configuración del entorno de pruebas unitarias y de integración.
- [`Dockerfile`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/Dockerfile): Empaquetado en contenedor del monolito sobre Python 3.13-slim.
- [`docker-compose.yml`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/docker-compose.yml): Orquestación del contenedor único con volúmenes persistentes y healthchecks.

### 2.2. Capa de Base de Datos (`/db`)
- [`db/schema.sql`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/db/schema.sql): Esquema relacional centralizado con llaves foráneas (`PRAGMA foreign_keys = ON`), índices optimizados para lecturas en menos de 200 ms y tablas:
  - `users`: Cuentas de oyentes y curadores.
  - `songs`: Metadatos del catálogo y referencias a archivos multimedia.
  - `playlists` y `playlist_songs`: Colecciones y relaciones usuario-canción.
  - `playbacks`: Telemetría de eventos con clave de idempotencia (`playback_id` UUID).
  - `song_metrics`: Agregación sincrónica de contadores de reproducciones.
- [`db/connection.py`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/db/connection.py): Manejador de conexiones SQLite en modo `WAL` (*Write-Ahead Logging*) para soportar lecturas y escrituras concurrentes sin bloqueos.
- [`db/init_db.py`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/db/init_db.py): Script de inicialización y sembrado automático con usuarios del equipo, canciones demo y playlists iniciales.

### 2.3. Lógica de Negocio y Módulos (`/core`)
- [`core/config.py`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/core/config.py): Variables de entorno, umbral de reproducción (10s según PRD) y rutas locales.
- **`core/module_users`**:
  - `models.py`: Esquemas Pydantic (`UserCreate`, `UserResponse`).
  - `service.py`: Lógica de creación y consulta de usuarios con validación de duplicados.
  - `router.py`: Endpoints REST (`/api/users`, `/api/users/{id}`).
- **`core/module_catalog`**:
  - `models.py`: Esquemas de canciones (`SongCreate`, `SongResponse`).
  - `service.py`: Búsqueda y listado en catálogo de canciones.
  - `streaming.py`: **Manejador de streaming binario con HTTP Range Requests (RFC 7233)**. Permite responder con `206 Partial Content`, cabeceras `Content-Range: bytes start-end/total`, `Accept-Ranges: bytes` y lectura asíncrona por fragmentos (chunks) para no saturar memoria.
  - `router.py`: Endpoints REST (`GET /api/songs`, `POST /api/songs`, `GET /api/songs/{id}/stream`).
- **`core/module_playlists`**:
  - `models.py`: Esquemas (`PlaylistCreate`, `PlaylistAddSong`, `PlaylistDetailResponse`).
  - `service.py`: Creación de listas, inserción idempotente de canciones y consulta de metadatos con latencia < 200 ms.
  - `router.py`: Endpoints REST (`POST /api/playlists`, `POST /api/playlists/{id}/songs`, `GET /api/playlists/{id}`).
- **`core/module_playback`**:
  - `models.py`: Esquemas (`PlaybackEventCreate`, `PlaybackEventResponse`, `TopSongMetric`).
  - `service.py`: **Idempotencia mediante UUID**, validación de duración mínima de 10s e incremento sincrónico del contador de popularidad.
  - `router.py`: Endpoints REST (`POST /api/playbacks`, `GET /api/metrics/top`, `GET /api/metrics/songs/{id}`).

### 2.4. Archivos Multimedia (`/media/audio`)
- [`scripts/generate_samples.py`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/scripts/generate_samples.py): Generador de audio sintetizado PCM/WAV a 44.1 kHz.
- Archivos generados para reproducción real:
  - `media/audio/cosmic_lofi.wav` (20.0s)
  - `media/audio/neon_cyberpunk.wav` (22.0s)
  - `media/audio/chillwave_beats.wav` (18.0s)

### 2.5. Interfaz de Usuario (`/ui`)
- [`ui/index.html`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/ui/index.html): SPA completa para oyentes y administradores.
- [`ui/css/style.css`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/ui/css/style.css): Estilos modernos en modo oscuro conforme a `DESIGN.md`.
- [`ui/js/app.js`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/ui/js/app.js): Controlador del cliente:
  - Reproductor con soporte nativo de Range requests y barra de búsqueda interactiva (seek).
  - Emisión automática de telemetría idempotente tras 10 segundos continuos con generación de UUID v4.
  - Botón de prueba de idempotencia en vivo para simular reintentos de red y verificar que el servidor descarta conteos duplicados.
  - Creación y visualización de playlists.
  - Leaderboard de métricas en tiempo real.

### 2.6. Punto de Entrada
- [`main.py`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/main.py): Aplicación principal FastAPI montando Swagger UI (`/docs`), endpoints estáticos (`/static`) y los routers de la API.

### 2.7. Batería de Pruebas Automatizadas (`/tests`)
- [`tests/conftest.py`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/tests/conftest.py): Fixtures de testing con base de datos SQLite aislada y cliente de pruebas `httpx`.
- [`tests/test_users.py`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/tests/test_users.py): 4 pruebas de registro, duplicados y consulta.
- [`tests/test_catalog_stream.py`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/tests/test_catalog_stream.py): 7 pruebas de listado, búsqueda, streaming completo (200 OK), streaming parcial (206 Partial Content), cabecera `Range` y límites (416).
- [`tests/test_playlists.py`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/tests/test_playlists.py): 5 pruebas de creación, asociación y verificación del criterio de latencia JSON < 200 ms.
- [`tests/test_playback.py`](file:///home/christian/GodsDocs2/UNIVERSIDAD/9noSemestre/SD/FLDSMDFR/tests/test_playback.py): 3 pruebas de umbral de 10s, verificación de idempotencia ante reintentos con mismo UUID y ordenamiento del Top de canciones más escuchadas.

---

## 3. Instrucciones de Ejecución

### Opción A: Ejecución Local con Entorno Virtual de Python

1. **Crear y activar el entorno virtual:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Generar archivos de audio de prueba (si no existen):**
   ```bash
   python scripts/generate_samples.py
   ```

4. **Ejecutar el servidor del monolito:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Acceder a la aplicación:**
   - **Interfaz Web (Oyente/Admin):** [http://localhost:8000](http://localhost:8000)
   - **Documentación Interactiva Swagger / OpenAPI:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Comprobación de Salud:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Opción B: Ejecución con Docker Compose (Requisito PRD Sección 8)

1. **Levantar el monolito:**
   ```bash
   docker compose up --build
   ```

2. **Apagar el monolito y limpiar volúmenes:**
   ```bash
   docker compose down -v
   ```

---

## 4. Ejecución de Pruebas Automatizadas

Para validar todos los criterios de aceptación del PRD:

```bash
.venv/bin/pytest -v
```

Resultado verificado:
- **19 pruebas ejecutadas y aprobadas (100% éxito)**.
