# AGENTS.md

## 1. Arquitectura del proyecto

En la rama `03-gateway-discovery-balanceo`, FLDSMDFR son **tres servicios FastAPI** independientes, cada uno con **su propia base de datos** PostgreSQL, que se comunican **por HTTP** usando **nombres lógicos** resueltos en un **directorio** (Consul, contenedor `discovery`). Un **gateway propio** (`services/gateway/`) es la única puerta: reparte `/api` por prefijo y en round-robin entre las instancias vivas; `web` (Nginx) solo sirve la UI. `catalog-streaming` corre en tres réplicas (PRD §6–§7). Las ramas `01-monolito` y `02-separacion` conservan los pasos anteriores.

- **Servicios autónomos:** cada uno se construye, se prueba y se despliega solo.
- **Una base por servicio:** ningún servicio lee ni escribe la base de otro.
- **Contratos explícitos:** lo que un servicio necesita de otro lo pide a su API interna (`/internal/...`), nunca por import.

### 1.1. Estructura general

```text
services/
  gateway/             # única puerta (:8000): prefijo → directorio → round-robin; sin base
  users-playlists/     # módulos users, playlists y social; emite los JWT
  catalog-streaming/   # módulo catalog: canciones, audio y portadas
  playback-metrics/    # módulo playback: reproducciones, historial y métricas
web/                   # Nginx: compila y sirve ui/ (detrás del gateway); register.sh lo registra en el directorio
ui/                    # Interfaz de usuario (Vue 3 + Vite + TypeScript)
docker/initdb/         # crea las tres bases y sus copias _test
```

Cada servicio tiene la misma forma interna:

```text
app/main.py, app/config.py
app/modules/<nombre>/  # router.py, service.py, repository.py, models.py, schemas.py
app/clients/           # clientes HTTP de otros servicios (solo en quien los consume)
app/db/                # sesión, base declarativa y su propia cadena de migraciones Alembic
app/shared/            # errores uniformes, JWT, dependencias, discovery.py (copia por servicio)
scripts/               # entrypoint, init (migrar y sembrar) y semilla idempotente (si aplica)
tests/                 # pytest, incluida su prueba de arquitectura
```

**Regla de servicios (obligatoria):**

- Un servicio nunca importa código de otro servicio. Lo que necesite lo pide por HTTP a `/internal/...` mediante un cliente en `app/clients/`, que traduce un `404` remoto al mismo `NotFound` y una falla de red o `5xx` a `503 service_unavailable`.
- `/internal/...` no se expone por el gateway (responde `404`); solo se usa dentro de la red de Compose.
- No hay llaves foráneas ni consultas entre bases de servicios distintos; las referencias son identificadores.
- Solo `users-playlists` emite tokens; los demás validan el JWT localmente con `FLDSMDFR_JWT_SECRET`.

**Regla de módulos (dentro de un servicio con varios módulos, como `users-playlists`):**

- Un módulo solo usa a otro mediante `app.modules.<otro>.service` y `app.modules.<otro>.schemas`. Nunca importa su `models` ni su `repository`.

**Regla de directorio (desde `03`):**

- Ningún servicio usa la URL o el nombre DNS de otro. Los clientes llaman con `http.call("<nombre-lógico>", ...)`, que pide las instancias `passing` al directorio y elige una con `discovery.RoundRobin`. `NoInstances` se traduce a `503 service_unavailable`.
- Cada instancia se registra en el `lifespan` (`discovery.register`) con id `<servicio>-<hostname>`, check TTL y latido, y se da de baja al apagarse. Toda respuesta lleva `X-Instancia`.
- Las pruebas no usan un Consul real: `tests/fake_consul.py` y `http.set_transport(servicio, transporte)` sustituyen el directorio y los servicios remotos.
- Sin reintentos ni circuit breaker en `03`: llegan en `04`.

Las reglas de servicios y de módulos las verifica `tests/test_architecture.py` de cada servicio con base (el gateway no tiene módulos). Si una prueba de arquitectura falla, se corrige el código, no la prueba.

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
- **Empaquetado:** Docker Compose (`db`, `discovery`, `catalog-init`, `catalog-streaming` ×3, `users-playlists`, `playback-metrics`, `gateway` y `web`; perfil `test` con `tests-catalog`, `tests-users`, `tests-playback` y `tests-gateway`). El SPA se compila en `web/Dockerfile` y lo sirve Nginx.
- **Directorio:** Consul 1.20 (`agent -dev`), checks TTL; panel en `:8500`.
- **Comunicación entre servicios:** HTTP con `httpx`; en las pruebas, los servicios remotos se sustituyen por versiones falsas con el mismo contrato.
- **Calidad:** `ruff` para el backend y `vue-tsc` en el build del frontend.

Comandos habituales:

```bash
docker compose up --build -d                              # levantar todo (http://localhost:8000)
docker compose --profile test run --rm tests-catalog      # pruebas de catalog-streaming
docker compose --profile test run --rm tests-users        # pruebas de users-playlists
docker compose --profile test run --rm tests-playback     # pruebas de playback-metrics
docker compose --profile test run --rm tests-gateway      # pruebas del gateway
./scripts/demo-03.sh                                      # demo de balanceo y caída de una réplica
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
