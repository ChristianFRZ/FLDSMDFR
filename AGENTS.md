# AGENTS.md

## 1. Arquitectura del proyecto

En la rama `02-separacion`, FLDSMDFR son **tres servicios FastAPI** independientes, cada uno con **su propia base de datos** PostgreSQL, que se comunican **por HTTP** con los nombres DNS de Docker Compose, más un proxy Nginx (`web`) que sirve la UI y reparte `/api` por prefijo (PRD §6). La rama `01-monolito` conserva el monolito modular del que salieron.

- **Servicios autónomos:** cada uno se construye, se prueba y se despliega solo.
- **Una base por servicio:** ningún servicio lee ni escribe la base de otro.
- **Contratos explícitos:** lo que un servicio necesita de otro lo pide a su API interna (`/internal/...`), nunca por import.

### 1.1. Estructura general

```text
services/
  users-playlists/     # módulos users, playlists y social; emite los JWT
  catalog-streaming/   # módulo catalog: canciones, audio y portadas
  playback-metrics/    # módulo playback: reproducciones, historial y métricas
web/                   # Nginx: compila y sirve ui/, reparte /api por prefijo
ui/                    # Interfaz de usuario (Vue 3 + Vite + TypeScript)
docker/initdb/         # crea las tres bases y sus copias _test
```

Cada servicio tiene la misma forma interna:

```text
app/main.py, app/config.py
app/modules/<nombre>/  # router.py, service.py, repository.py, models.py, schemas.py
app/clients/           # clientes HTTP de otros servicios (solo en quien los consume)
app/db/                # sesión, base declarativa y su propia cadena de migraciones Alembic
app/shared/            # errores uniformes, JWT, dependencias (copia por servicio)
scripts/               # entrypoint y semilla idempotente (si aplica)
tests/                 # pytest, incluida su prueba de arquitectura
```

**Regla de servicios (obligatoria):**

- Un servicio nunca importa código de otro servicio. Lo que necesite lo pide por HTTP a `/internal/...` mediante un cliente en `app/clients/`, que traduce un `404` remoto al mismo `NotFound` y una falla de red o `5xx` a `503 service_unavailable`.
- `/internal/...` no se expone por el proxy; solo se usa dentro de la red de Compose.
- No hay llaves foráneas ni consultas entre bases de servicios distintos; las referencias son identificadores.
- Solo `users-playlists` emite tokens; los demás validan el JWT localmente con `FLDSMDFR_JWT_SECRET`.

**Regla de módulos (dentro de un servicio con varios módulos, como `users-playlists`):**

- Un módulo solo usa a otro mediante `app.modules.<otro>.service` y `app.modules.<otro>.schemas`. Nunca importa su `models` ni su `repository`.

Ambas reglas las verifica `tests/test_architecture.py` de cada servicio. Si una prueba de arquitectura falla, se corrige el código, no la prueba.

### 1.2. Archivos del proyecto

- `AGENTS.md`: define cómo debe trabajar el agente de programación.
- `DESIGN.md`: fuente de verdad visual del producto (diseño, componentes y experiencia de usuario). La UI debe seguirlo.
- `SKILLS.md`: reúne habilidades, procedimientos y prompts reutilizables para tareas de desarrollo.
- `docs/PRD.md`: requisitos y plan de separación en servicios (ramas `02` a `06`).
- `docs/superpowers/`: diseño y plan de implementación de cada rama.

## 2. Pila tecnológica

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 asíncrono (asyncpg), Alembic, Pydantic, JWT (PyJWT), Argon2 (pwdlib) y mutagen para leer audio.
- **Base de datos:** PostgreSQL 16.
- **Frontend:** Vue 3, Vue Router y Vite con TypeScript. Sin Pinia. Pruebas con Vitest.
- **Empaquetado:** Docker Compose (`db`, los tres servicios y `web`; perfil `test` con `tests-catalog`, `tests-users` y `tests-playback`). El SPA se compila en `web/Dockerfile` y lo sirve Nginx.
- **Comunicación entre servicios:** HTTP con `httpx`; en las pruebas, los servicios remotos se sustituyen por versiones falsas con el mismo contrato.
- **Calidad:** `ruff` para el backend y `vue-tsc` en el build del frontend.

Comandos habituales:

```bash
docker compose up --build -d                              # levantar todo (http://localhost:8000)
docker compose --profile test run --rm tests-catalog      # pruebas de catalog-streaming
docker compose --profile test run --rm tests-users        # pruebas de users-playlists
docker compose --profile test run --rm tests-playback     # pruebas de playback-metrics
docker compose --profile test run --rm tests-users ruff check .   # lint (igual en los otros)
cd ui && npm test && npm run build              # pruebas y build del frontend
```

Las dependencias nuevas solo se agregan con una necesidad concreta (regla 8).

## 3. Herramientas generales

- **Codex / Claude Code:** agentes de programación que pueden analizar repositorios, modificar archivos, ejecutar comandos y apoyar en tareas de desarrollo.
- **Docker Compose:** única forma soportada de levantar el entorno completo y de ejecutar las pruebas de backend.

## 4. Reglas de trabajo del agente

1. Analizar la estructura existente antes de modificar archivos.
2. Respetar la arquitectura y las responsabilidades de cada módulo.
3. Evitar duplicación de código y dependencias innecesarias.
4. Priorizar legibilidad, modularidad y mantenibilidad.
5. No modificar funcionalidades existentes sin justificación.
6. Validar entradas y manejar errores de manera explícita.
7. Escribir y ejecutar pruebas cuando corresponda.
8. Evitar agregar dependencias sin una necesidad concreta.
9. Documentar los cambios relevantes y explicar las decisiones técnicas.
10. No afirmar que una prueba pasó si no se ejecutó.
11. Mantener la documentación actualizada cuando cambie la arquitectura.
12. Identificar riesgos y limitaciones antes de proponer cambios importantes.

## 5. Criterios de aceptación

Un cambio se considera terminado cuando:

- Cumple con los requisitos solicitados.
- Respeta la arquitectura del proyecto.
- No introduce duplicación innecesaria.
- Maneja errores y casos límite relevantes.
- Cuenta con pruebas apropiadas cuando corresponda.
- No rompe funcionalidades existentes.
- Se documentan las decisiones importantes.
- Las validaciones ejecutadas y sus resultados se reportan con precisión.
