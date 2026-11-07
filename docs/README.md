# Documentación

Aquí está todo lo que explica el proyecto y no es código. Si llegas por primera vez, empieza por el [PRD](prd.md).

| Qué | Dónde |
| --- | --- |
| Requisitos del producto, que son la referencia de todas las ramas | [`prd.md`](prd.md) |
| Diseños aprobados, con las decisiones del equipo | [`specs/`](specs/README.md) |
| Planes de implementación que salen de esos diseños | [`plans/`](plans/README.md) |
| Lo que se decidió sobre la marcha y lo que quedó pendiente | [`decisions/`](decisions/README.md) |
| Maqueta de la interfaz | [`design/`](design/README.md) |
| Logo, colores y guía de marca | [`brand/`](brand/README.md) |

Los criterios de aceptación salen del PRD. Si un diseño y un plan no coinciden, manda el diseño.

## Cómo se nombran las cosas

Estas son las reglas del repositorio. Cada una sale de la guía oficial de su herramienta o de una decisión del equipo.

| Qué | Regla | Ejemplo | De dónde sale |
| --- | --- | --- | --- |
| Código, archivos de código y rutas | En inglés | `scenario_5_tape_full.py` | Regla del equipo, en el [diseño](specs/2026-11-05-01-monolito-design.md) |
| Módulos de Python | Minúsculas y guion bajo | `tape_routes.py` | [PEP 8](https://peps.python.org/pep-0008/#package-and-module-names) |
| Componentes de React | `PascalCase`, igual que el componente | `TapeDetail.tsx` | Convención de React |
| Hooks de React | `camelCase`, con el prefijo `use` | `useCompact.ts` | Convención de React |
| Documentos | Minúsculas y guiones, sin espacios | `prd.md` | Convención común, y [MADR](https://adr.github.io/madr/) para las decisiones |
| Diseños y planes | Fecha, rama y tema | `2026-11-05-01-monolito-design.md` | Así se ordenan solos por fecha |
| Decisiones | Número de rama y nombre | `01-monolito.md` | Adaptado de [MADR](https://adr.github.io/madr/), pero con un archivo por rama |
| Archivos de Compose | `compose.yaml` | `compose.demo.yaml` | Es el nombre preferido según [Docker](https://docs.docker.com/compose/intro/compose-application-model/) |
| Migraciones | Número de 4 dígitos y tema | `0009_tapes.py` | Ver [`backend/migrations/versions/`](../backend/migrations/versions/README.md) |

Los textos de `docs/` y los README van en español, igual que la interfaz.

## Por qué las carpetas están así

- **Backend por dominio.** Cada [módulo](../backend/app/modules/README.md) guarda juntos sus rutas, modelos y servicios, y [`backend/tests/`](../backend/tests/README.md) repite esa forma. Es lo que recomienda la [guía de buenas prácticas de FastAPI](https://github.com/zhanymkanov/fastapi-best-practices) para un monolito con varios dominios, y es lo que permite separar los servicios en la rama 02.
- **Interfaz por pantallas y piezas.** [Bulletproof React](https://github.com/alan2207/bulletproof-react/blob/master/docs/project-structure.md) propone una carpeta `features/` para proyectos grandes. En [`frontend/src/`](../frontend/src/README.md), las carpetas `player/`, `charts/`, `auth/` y `api/` ya cumplen ese papel, y `pages/` sigue las rutas, así que moverlo todo no aportaría nada.
- **[`demo/`](../demo/README.md) en la raíz.** El PRD pide ahí los scripts. No son pruebas unitarias: corren contra la app levantada.
