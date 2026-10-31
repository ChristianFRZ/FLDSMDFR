# AGENTS.md

## 1. Arquitectura del proyecto

FLDSMDFR es un **monolito modular**: una sola aplicación FastAPI, un solo proceso y una sola base de datos PostgreSQL, organizada para poder separarse después en servicios (PRD §6).

- **Módulos claros:** cada módulo tiene una responsabilidad específica.
- **Límites bien definidos:** cada módulo expone solo su interfaz pública.
- **Dependencias controladas:** se evita el acoplamiento innecesario entre módulos.

### 1.1. Estructura general

```text
app/modules/   # Lógica de negocio: users, catalog, playlists, playback
app/db/        # Acceso y gestión de datos: sesión, base declarativa, migraciones Alembic
app/shared/    # Transversal: errores uniformes, seguridad (JWT, hashing), dependencias
app/main.py    # Ensamblado de la aplicación; app/spa.py sirve el SPA compilado
ui/            # Interfaz de usuario (Vue 3 + Vite + TypeScript)
scripts/       # Entrypoint del contenedor y semilla idempotente
tests/         # Pruebas de backend (pytest), incluida la de arquitectura
```

Cada módulo de `app/modules/<nombre>/` tiene `router.py` (HTTP), `service.py` (lógica), `repository.py` (consultas), `models.py` (tablas) y `schemas.py` (contratos Pydantic).

**Regla de módulos (obligatoria):**

- Un módulo solo usa a otro mediante `app.modules.<otro>.service` y `app.modules.<otro>.schemas`. Nunca importa su `models` ni su `repository`.
- No hay llaves foráneas entre tablas de módulos distintos; las referencias entre módulos son identificadores sin FK.
- Lo verifica `tests/test_architecture.py`. Si una prueba de arquitectura falla, se corrige el código, no la prueba.

### 1.2. Archivos del proyecto

- `AGENTS.md`: define cómo debe trabajar el agente de programación.
- `DESIGN.md`: fuente de verdad visual del producto (diseño, componentes y experiencia de usuario). La UI debe seguirlo.
- `SKILLS.md`: reúne habilidades, procedimientos y prompts reutilizables para tareas de desarrollo.
- `docs/PRD.md`: requisitos y plan de separación en servicios.

## 2. Pila tecnológica

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 asíncrono (asyncpg), Alembic, Pydantic, JWT (PyJWT), Argon2 (pwdlib) y mutagen para leer audio.
- **Base de datos:** PostgreSQL 16.
- **Frontend:** Vue 3, Vue Router y Vite con TypeScript. Sin Pinia. Pruebas con Vitest.
- **Empaquetado:** Docker Compose (`db` + `app`; perfil `test` para las pruebas). El SPA se compila en el `Dockerfile` y lo sirve FastAPI.
- **Calidad:** `ruff` para el backend y `vue-tsc` en el build del frontend.

Comandos habituales:

```bash
docker compose up --build                       # levantar todo (http://localhost:8000)
docker compose --profile test run --rm tests    # pruebas de backend
docker compose run --rm tests ruff check .      # lint
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
