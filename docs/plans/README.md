# Planes

Cómo se construye cada [diseño](../specs/README.md), tarea por tarea. Cada plan registra lo que se pidió en su momento; lo que cambió durante la construcción está en [`docs/decisions/`](../decisions/README.md).

| Archivo | Rama | Qué cubre |
| --- | --- | --- |
| [`2026-11-05-01-monolito.md`](2026-11-05-01-monolito.md) | `01-monolito` | Las 23 tareas de la rama |
| [`2026-11-12-02-separacion.md`](2026-11-12-02-separacion.md) | `02-separacion` | Las 16 tareas que parten el monolito en tres servicios |
| [`2026-11-13-03-gateway-balanceo.md`](2026-11-13-03-gateway-balanceo.md) | `03-gateway-balanceo` | Las 8 tareas del gateway con validación de sesión y rol, y las dos réplicas de catálogo |
| [`2026-11-14-04-resiliencia-concurrencia.md`](2026-11-14-04-resiliencia-concurrencia.md) | `04-resiliencia-concurrencia` | Las 9 tareas de timeouts, reintentos, circuit breaker, cola de reproducciones y revocación en Redis |

Para una rama nueva, agrega aquí su plan con el nombre `AAAA-MM-DD-<rama>.md`.
