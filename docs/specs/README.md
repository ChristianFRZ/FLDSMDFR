# Diseños

Un documento por rama, ya aprobado por el equipo, que dice qué se construye y qué reglas sigue. Si un [plan](../plans/README.md) y un diseño se contradicen, manda el diseño.

| Archivo | Rama | Qué cubre |
| --- | --- | --- |
| [`2026-11-05-01-monolito-design.md`](2026-11-05-01-monolito-design.md) | `01-monolito` | Alcance, arquitectura, reglas de producto e interfaz |
| [`2026-11-12-02-separacion-design.md`](2026-11-12-02-separacion-design.md) | `02-separacion` | Tres servicios sobre red interna, bases separadas, nginx de entrada |
| [`2026-11-13-03-gateway-balanceo-design.md`](2026-11-13-03-gateway-balanceo-design.md) | `03-gateway-balanceo` | Gateway nginx con validador de JWT y roles, dos réplicas de catálogo con failover |
| [`2026-11-14-04-resiliencia-concurrencia-design.md`](2026-11-14-04-resiliencia-concurrencia-design.md) | `04-resiliencia-concurrencia` | Timeouts, reintentos y circuit breaker; cola de reproducciones en Redis Streams; revocación de sesiones |
| [`2026-11-14-05-mensajeria-design.md`](2026-11-14-05-mensajeria-design.md) | `05-mensajeria` | `track_published` sobre Redis Streams: outbox, consumidor idempotente, cola de mensajes muertos y avisos desde una tabla local |

Para una rama nueva, agrega aquí su diseño con el nombre `AAAA-MM-DD-<rama>-design.md`.
