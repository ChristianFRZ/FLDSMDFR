# Ramas del proyecto y qué falta

Este documento junta las seis ramas del recorrido del curso. Las cuatro primeras ya están construidas; las otras dos (`05` y `06`) son la propuesta de qué traería cada una en MELOXO. El plan aprobado en el [PRD](prd.md#plan-de-ramas) llegaba hasta la `04`, ya hecha: lo de las ramas `05` y `06` sale de la guía del recorrido del curso, que lo cuenta con el caso de Mexi Banco, y necesita que el equipo lo apruebe antes de convertirse en diseño.

## Mapa

| Rama | Estado | Tema | Equivalente en Mexi Banco |
| --- | --- | --- | --- |
| `01-monolito` | Hecha | Una aplicación con módulos y una base de datos | `01-monolito` |
| `02-separacion` | Hecha | Tres servicios, una base por servicio, nginx de entrada | `02-separacion` |
| `03-gateway-balanceo` | Hecha | Gateway que valida sesión y rol, dos réplicas de catálogo con failover | `03-gateway-discovery-balanceo` |
| `04-resiliencia-concurrencia` | Hecha | Timeouts, reintentos, circuit breaker, Redis para revocación y cola | `04-saga-circuit-breaker` |
| `05-mensajeria` | Propuesta | Eventos entre servicios con acuse manual, cola de mensajes muertos y outbox | `05-mensajeria-base` |
| `06-poliglota` | Propuesta | Caché en Redis y un almacén documental para lo que no es relacional | `06-poliglota-base` |

Los nombres de `05` y `06` son provisionales. Cada rama nueva sigue el [flujo de siempre](README.md#cómo-se-nombran-las-cosas): diseño en [`specs/`](specs/README.md), plan en [`plans/`](plans/README.md) y decisiones en [`decisions/`](decisions/README.md).

## Diferencias que ya existen con Mexi Banco

| Mexi Banco | MELOXO | Por qué |
| --- | --- | --- |
| Eureka para descubrir servicios | Docker Compose resuelve los nombres por DNS y nginx reparte | Con tres servicios y una réplica escalada no hace falta un registro. [Decisiones de la rama 03](decisions/03-gateway-balanceo.md) |
| Balanceo del lado del cliente (`@LoadBalanced`) | Balanceo en nginx, con failover pasivo | nginx de código abierto no sondea servicios; el costo está en las decisiones de la rama 03 |
| Spring Cloud Gateway | nginx con `auth_request` hacia [`gateway-auth`](../services/gateway-auth/README.md) | Mismo papel: un solo punto de entrada que valida sesión y rol |
| Transferencias de dinero | Casetes, playlists, publicaciones y reproducciones | No hay saldos ni asientos contables |
| Java y Spring | Python y FastAPI | Las bibliotecas de Java (Resilience4j, Spring AMQP) no existen aquí; se usan equivalentes de Python o código propio en [`meloxo_common`](../services/common/README.md) |

## Rama 04: resiliencia y concurrencia

| Función del documento de referencia | ¿Cabe en MELOXO? | Cómo sería aquí | Lo que ya hay en el código |
| --- | --- | --- | --- |
| Timeouts estrictos entre servicios | Sí | Fijar tiempo de conexión y de lectura por separado en `InternalClient` | [`internal.py`](../services/common/meloxo_common/internal.py) tiene un solo valor de 3 s y ningún reintento; nginx ya corta la conexión a 1 s |
| Circuit breaker (abierto, medio abierto, cerrado) | Sí | Un breaker por servicio destino dentro de `InternalClient`: `users-playlists` hacia catálogo, catálogo hacia `users-playlists` (auditoría) y `playback-metrics` hacia ambos | Hoy un servicio caído da `503 upstream_unavailable` en cada llamada, sin fallo rápido |
| Reintentos con backoff | Sí | Solo en lecturas y en escrituras idempotentes | El gateway ya reintenta `GET`, `HEAD`, `PUT` y `DELETE` entre réplicas |
| Idempotencia con clave | Parcial | Ya existe donde importa: `playback_id` en las reproducciones ([escenario 4](../demo/scenario_4_idempotency.py)), importación por `jamendo_id` y `job_id`. Falta una clave genérica para las escrituras entre servicios que se reintenten | Agregar a playlist y marcar favorita ya son idempotentes, con prueba |
| Saga orquestada con compensaciones | Adaptada | No hay dinero que devolver. El caso parecido son las escrituras en dos servicios: ocultar una pista o publicarla en catálogo y auditarlo en `users-playlists` | [`publishing.py`](../services/catalog-streaming/catalog_streaming/modules/catalog/publishing.py) resuelve hoy el orden con auditoría antes del commit y `rollback` si el otro servicio no responde. Una saga con estados y reintento de la auditoría pendiente sería el paso siguiente |
| Reintento en segundo plano de lo pendiente | Sí | Misma tarea periódica que ya usa la publicación programada | [`scheduler.py`](../services/common/meloxo_common/scheduler.py) |
| Lista de revocación en Redis | Sí | Está en el PRD y se difirió desde la rama 03 por decisión del equipo | El gateway tarda hasta 30 s en ver un cambio de rol o una suspensión |
| Cola cuando `playback-metrics` no responde (F3.3) | Sí | Redis Streams, que el PRD ya eligió | Hoy el navegador reintenta; la cola real está marcada como parcial en el README |

Estado tras la rama: la columna «Lo que ya hay en el código» describe el punto de partida. Se hicieron los timeouts, los reintentos (solo `get` y `post` idempotente), el breaker por destino, la cola con Redis Streams y la revocación en Redis. La saga con estados quedó fuera por decisión del equipo, y tampoco se hicieron el breaker de Jamendo ni una clave de idempotencia genérica. Las [decisiones de la rama](decisions/04-resiliencia-concurrencia.md) dicen cómo quedó cada cosa.

## Rama 05: mensajería

La referencia usa RabbitMQ. El PRD de MELOXO ya eligió Redis Streams, que tiene lo necesario: grupos de consumidores, acuse con `XACK`, mensajes pendientes recuperables y una lista de entregas fallidas que se puede llevar a un stream aparte. Hay que decidir con el equipo cuál de los dos usar (ver [decisiones pendientes](#decisiones-pendientes)).

| Función del documento de referencia | ¿Cabe en MELOXO? | Cómo sería aquí | Lo que ya hay en el código |
| --- | --- | --- | --- |
| Eventos asíncronos entre servicios | Sí | Eventos de dominio: `track_published`, casete compartido, artista seguido, reproducción registrada | `track_published` ya existe como nombre en el PRD y como tabla `PublishedEvent` |
| Que un servicio caído no tire la operación principal | Sí, es el caso más claro | Los avisos de lanzamientos de [`social/service.py`](../services/users-playlists/users_playlists/modules/social/service.py) hoy se calculan al leer y le piden las pistas a catálogo; si catálogo cae, se devuelven sin lanzamientos. Con eventos, `users-playlists` los guardaría al recibirlos | Existe el modo degradado `degraded: true` |
| Patrón outbox | Sí | Escribir el evento en una tabla de la misma transacción y publicarlo desde un relevo con `SKIP LOCKED` | `publish_due_tracks` ya cambia el estado y registra `PublishedEvent` en la misma transacción, y ya usa `SKIP LOCKED`: falta el relevo que lo publique |
| Acuse manual y reintento de lo no acusado | Sí | `XACK` solo después de guardar; lo pendiente se reclama con `XAUTOCLAIM` | Nada todavía |
| Cola de mensajes muertos | Sí | Mensajes con formato inválido o que fallan N veces van a un stream aparte, con el motivo | Nada todavía |
| Consumo idempotente | Sí | Tabla de eventos ya aplicados, como `PublishedEvent` | La idea ya está en catálogo |
| Panel del broker | No hace falta | Redis no trae panel; se puede ver con `redis-cli` o sumarlo a la sección de Salud del admin | La sección de Salud ya lista los servicios |

## Rama 06: persistencia políglota

| Función del documento de referencia | ¿Cabe en MELOXO? | Cómo sería aquí | Lo que ya hay en el código |
| --- | --- | --- | --- |
| PostgreSQL como fuente de verdad | Sí, no cambia | Usuarios, roles, casetes, catálogo y reproducciones siguen ahí | Una base y un rol por servicio |
| Redis como caché de lectura con desalojo LRU | Sí | Caché aparte del estado de cuenta: `GET /api/songs`, detalle de pista, contadores de reproducciones y agregados de las gráficas, con invalidación al escribir. El estado de cuenta de 30 s, que hoy vive en memoria de cada proceso, podría compartirse entre las dos réplicas | [`gateway-auth`](../services/gateway-auth/README.md) y `meloxo_common` ya guardan el estado de cuenta 30 s por proceso. La prueba de carga ya da una línea base de latencia |
| MongoDB para datos de forma variable | Parcial | Candidatos: la bitácora de auditoría (su campo `detail` cambia según la acción) y los avisos persistidos si se pasa a eventos en la rama 05. Lo demás es relacional | Es una decisión de alcance: el PRD fija PostgreSQL para todo, así que MongoDB necesita que el equipo la apruebe y se anote en el PRD |
| Caché degradable | Sí | Si Redis cae, se lee de PostgreSQL y se responde igual | El criterio de degradación elegante ya existe en el PRD |

## Lo que no se traslada

- El `@Transactional` y el rollback del monolito sobre dinero: en MELOXO el equivalente del monolito ya está en la rama 01.
- La demostración de dinero perdido de la rama 02: aquí no hay saldos, y la historia de fallas la cubren los [escenarios de `demo/`](../demo/README.md).
- Resilience4j, Spring Cloud y Spring AMQP, por el lenguaje.

## Decisiones pendientes

1. **Broker de la rama 05:** Redis Streams (ya aprobado en el PRD, un contenedor menos, pero sin panel ni enrutamiento) o RabbitMQ (como la referencia, con panel y colas de mensajes muertos nativas, pero un componente nuevo).
2. ~~**Dónde entra Redis:**~~ Resuelta: entró en la `04`, con la cola de reproducciones y la revocación. La `06` solo agrega la caché.
3. **MongoDB:** si el equipo lo quiere en la `06`, hay que actualizar el PRD (dueño de cada dato) y la regla de "una base por servicio".
4. **Nombres de las ramas `05` y `06`.**
5. ~~**Alcance de la saga en la `04`:**~~ Resuelta: sin saga, solo timeouts, breaker, reintentos, cola y revocación.
