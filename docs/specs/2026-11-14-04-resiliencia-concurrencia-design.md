# Diseño · Rama `04-resiliencia-concurrencia`

Cuarta rama de MELOXO. Complementa al PRD (`docs/prd.md`, §11 y §12) y al [diseño de `03-gateway-balanceo`](2026-11-13-03-gateway-balanceo-design.md). Aquí se registra qué se construye para que una falla de un servicio no se propague y para que las métricas y los cambios de sesión no dependan de una ventana de espera.

Las decisiones marcadas **(equipo)** las tomó el usuario durante el diseño. Las marcadas **(constructor)** las propuso quien diseña y pueden corregirse.

## 1. Intención

Hoy, cuando un servicio cae, cada llamada de otro servicio espera 3 s y devuelve `503`, una y otra vez. Cuando `playback-metrics` cae, solo el navegador reintenta: si se cierra la pestaña, la reproducción se pierde (F3.3 figura como «Parcial»). Y un cambio de rol o una suspensión tarda hasta 30 s en verse en el borde, porque `gateway-auth` y los servicios guardan el estado de la cuenta en una caché.

`04-resiliencia-concurrencia` cierra esos tres huecos con lo que el PRD ya eligió: tiempos de espera y reintentos con backoff, un circuit breaker por servicio destino, una cola en Redis Streams para las reproducciones y una lista de revocación de sesiones en Redis.

## 2. Objetivos

1. **Timeouts** de conexión y de lectura por separado en `InternalClient`.
2. **Reintentos con backoff** (200 ms y 400 ms), solo en lecturas y en escrituras idempotentes.
3. **Circuit breaker** por servicio destino dentro de `InternalClient`: abierto, medio abierto y cerrado. Cuando está abierto, la llamada falla al instante con `UpstreamError`, y los respaldos que ya existen (estado de cuenta en caché, `degraded: true`) siguen funcionando igual.
4. **Cola de reproducciones (F3.3 y escenario 1 del PRD)**: con `playback-metrics` detenido, escuchar no se corta, el navegador no ve errores y los eventos se aplican al volver, sin duplicados.
5. **Revocación inmediata**: un cambio de rol o una suspensión se ve en la siguiente petición, en el gateway y en los servicios.
6. Un contenedor `redis` en `compose.yaml`, con persistencia, y su `README`.
7. Escenarios de `demo/`: el 1 y el 4 se actualizan; se agregan uno de breaker y uno de revocación.
8. Un `README.md` en cada carpeta nueva y actualización de los existentes, del README raíz (F3.3 pasa a «Cumple»), de `docs/ramas.md` y de `CHANGELOG.md`.

## 3. No objetivos y antiobjetivos

**No objetivos**

- Saga con estados y tabla de auditorías pendientes **(equipo)**. La publicación y la ocultación de pistas siguen con «auditar antes del commit y `rollback`».
- Cola de mensajes muertos, outbox y eventos entre servicios (`track_published`, avisos): rama 05.
- Caché de lectura en Redis y almacén documental: rama 06.
- Circuit breaker en las llamadas de catálogo a Jamendo: queda fuera. Se anota como diferencia con la tabla de parámetros del PRD.
- Mostrar el estado de los breakers en la sección Salud del admin.
- Panel o cliente web para Redis.

**Antiobjetivos: si pasa esto, la rama falló aunque funcione**

- Que una reproducción se cuente dos veces o se pierda por un reinicio de Redis o de `playback-metrics`.
- Que el audio se corte, o que el navegador muestre un error, porque `playback-metrics` o Redis estén caídos.
- Que Redis caído deje a nadie fuera de la app. La revocación falla abierta: sin Redis, manda la caché de 30 s de hoy.
- Que un reintento duplique una escritura que no es idempotente.
- Que un cambio de rol deje al usuario sin poder volver a entrar con un token nuevo.
- Que cambie el comportamiento visible de una función sin estar en este documento.

## 4. Decisiones del equipo

| Tema | Decisión |
|---|---|
| Alcance de la saga | **Sin saga.** Solo timeouts, breaker, reintentos, cola y revocación. |
| Dónde se encola la reproducción | **Siempre por la cola.** nginx manda las escrituras de `/api/playbacks` a `catalog-streaming`, que valida y hace `XADD` a Redis y responde `202`. `playback-metrics` consume con un grupo de consumidores. |
| Revocación | Clave en Redis escrita por `users-playlists` al cambiar un rol o suspender una cuenta, con TTL igual a la vida del token. La consultan `gateway-auth` y la dependencia de autenticación de `meloxo_common`. Si Redis cae, se usa la caché de 30 s. |

## 5. Decisiones del constructor

| Tema | Decisión | Razón |
|---|---|---|
| Parámetros de resiliencia | Conexión 1 s, lectura 1.5 s. Reintentos: 2 en lecturas, con espera de 200 y 400 ms. Breaker: abre con 5 llamadas fallidas en 30 s (cuenta la llamada ya reintentada, no cada intento) y pasa a medio abierto a los 15 s, dejando pasar una llamada de prueba. | Son los valores iniciales del PRD §11. Los números viven en una sola constante de `meloxo_common`. |
| Qué se reintenta | `get`, y `put` y `delete` si se piden. `post` no se reintenta salvo que quien llama lo marque idempotente. El `UpstreamError` por `5xx` y por error de red cuenta como fallo; un `4xx` no. | Un `4xx` es una respuesta del servicio, no una falla. |
| Estado del breaker | En memoria de cada proceso, uno por URL destino. | Con tres servicios y dos réplicas, un estado compartido no aporta y obligaría a depender de Redis. |
| Rutas de escritura de `/api/playbacks` | `POST /api/playbacks` y `PATCH /api/playbacks/{id}/progress` pasan a `catalog-streaming`. `GET /api/playbacks/history` sigue en `playback-metrics`. | El navegador manda las dos escrituras en ese orden, y el progreso exige que la reproducción exista. Por un solo stream, y con un solo consumidor leyendo en orden, el `PATCH` nunca se adelanta al `POST`. |
| Validación al encolar | Catálogo valida el cuerpo y que la pista exista (`404 song_not_found`, como hoy, porque la pista es suya). La identidad sale del JWT. El mensaje lleva `type` (`record` o `progress`), `user_id`, `playback_id`, `song_id`, `listened_seconds` y la hora de recepción. | Conserva los errores `4xx` de cuerpo y de pista que hoy ve el navegador. |
| Qué cambia en la respuesta | `POST` da `202` con `{ "playback_id": ... }`, sin `counted`. El `201`/`200` y `counted` se pierden. La interfaz no los usa. | Aplicar la reproducción ya no ocurre en la petición. |
| Errores que dejan de ser síncronos | El `PATCH` de una reproducción ajena o inexistente ya no da `403`/`404`: el consumidor lo descarta con un aviso en el registro y cuenta `events_discarded`. | No hay dueño que consultar al encolar sin sumar una llamada a `playback-metrics`, que es justo lo que se evita. |
| Consumidor | Dentro de `playback-metrics`, como tarea del proceso: `XREADGROUP` con bloqueo, grupo `playbacks`, `XACK` solo después del commit. Lo pendiente de más de 30 s se reclama con `XAUTOCLAIM`. Un fallo transitorio (base caída) no se acusa y se reintenta. Un mensaje inválido se acusa y se descarta con aviso. | El `playback_id` único ya hace idempotente el reintento y el reparto entre consumidores. |
| Redis caído al encolar | Catálogo responde `503` JSON (`upstream_unavailable`) y el reintento del navegador, que ya existe, lo cubre. No hay camino directo a `playback-metrics`. | Un solo camino; el navegador ya guarda lo pendiente en `localStorage`. |
| Redis en Compose | Imagen `redis:7-alpine`, `appendonly yes`, volumen propio, `healthcheck`, sin publicar el puerto. Los servicios que lo usan dependen de él sano. El stream se recorta con `MAXLEN ~`. `REDIS_URL` en `.env.example`. | Un reinicio no debe borrar lo encolado. Solo la red interna lo alcanza, como Postgres. |
| Revocación: contenido | `revoked_after:<user_id>` guarda la hora de la revocación. Un token es inválido si su `iat` es anterior. `encode_token` pasa a incluir `iat`. Un token sin `iat` (emitido antes de la rama) se trata como emitido en la hora cero. TTL de 15 min, más un margen. | Si la clave solo dijera «revocado», un cambio de rol dejaría al usuario fuera hasta que venza el TTL. Con la hora puede entrar enseguida con un token nuevo. |
| Revocación: quién escribe | `users-playlists`, en los mismos puntos donde ya cambia el rol o el estado, después del commit. Si Redis falla, registra un aviso y la acción del admin se completa. | Una caída de Redis no debe bloquear una suspensión. El respaldo es la caché de 30 s. |
| Revocación: quién lee | Un método de `meloxo_common.auth` consulta Redis antes de usar la caché de estado. `gateway-auth` y todos los servicios lo heredan. Si hay revocación para esa persona, también se descarta lo que la caché de estado guardó antes de ella, para que un token nuevo traiga el rol nuevo sin esperar 30 s. Con Redis caído se omite. | Los servicios internos revalidan, como pide el PRD §12. Sin esto, un reingreso tras un cambio de rol seguiría viendo el rol viejo hasta 30 s (se descubrió al construir). |
| Refrescar sesión | Sin cambios. El refresh token es opaco y vive en la base; `refresh` emite un access token con el rol vigente y un `iat` nuevo, así que tras un cambio de rol se puede renovar sin volver a escribir la contraseña. Una cuenta suspendida ya no renueva. | El usuario no queda fuera tras un cambio de rol, y una suspensión corta de verdad. |

## 6. Enfoques considerados

Para la cola de reproducciones:

| Enfoque | Qué cuesta | Decisión |
|---|---|---|
| **C. Siempre por la cola** | Cambia el contrato de la respuesta y mueve dos rutas a catálogo. Un solo camino que probar. | **Elegido (equipo).** |
| D. Cola solo como respaldo | nginx intenta primero `playback-metrics` y, si falla, manda al endpoint de ingreso. Dos caminos y el orden de los eventos se mezcla. | Descartado. |
| E. Servicio `playback-ingest` | Un contenedor nuevo para una sola ruta. | Descartado: con tres servicios no se justifica. |

Para la revocación se descartó consultar solo desde `gateway-auth`: dejaría a los servicios sin revalidar por Redis.

## 7. Arquitectura

```
navegador ──► edge ──► gateway-auth ──► Redis (revoked_after:<user>) ; si Redis cae: caché 30 s
                │
                ├─ POST /api/playbacks, PATCH .../progress ─► catalog-streaming (×2) ──XADD──► Redis stream playbacks
                │                                                                                  │
                │                                           playback-metrics ◄──XREADGROUP / XACK───┘
                └─ GET /api/playbacks/history, /api/metrics ─► playback-metrics

users-playlists ──(cambio de rol o suspensión)──► Redis (revoked_after)
cada servicio ──InternalClient (timeouts + reintentos + breaker)──► el servicio destino
```

- `InternalClient` se queda en `meloxo_common`; el breaker es una clase aparte en el mismo paquete, con reloj inyectable para probarlo.
- El productor del stream vive en catálogo y el consumidor en `playback-metrics`; ambos usan un módulo pequeño de `meloxo_common` con el nombre del stream y el formato del mensaje, de modo que el contrato quede en un solo lugar.

## 8. Pruebas y criterios de cierre

- **Breaker**: transiciones cerrado → abierto → medio abierto → cerrado, con reloj falso; la llamada de prueba que falla reabre el breaker.
- **Reintentos**: `get` reintenta con la espera indicada; `post` no; un `4xx` no se reintenta ni cuenta como fallo.
- **Cola**: el productor valida y encola; el consumidor aplica en orden, deja de acusar ante un fallo transitorio, reclama lo pendiente, descarta lo inválido y no duplica un `playback_id` reenviado.
- **Revocación**: un token anterior a `revoked_after` da `401` en el gateway y en un servicio; uno posterior pasa; con Redis caído funciona la caché de 30 s; una suspensión y un cambio de rol escriben la clave.
- **`edge/tests/`**: las rutas nuevas de `/api/playbacks` quedan en `catalog-streaming` y el `GET /history` en `playback-metrics`.
- **Escenario 1 (actualizado)**: con `playback-metrics` detenido, el audio sigue, `POST /api/playbacks` da `202` y, al volver, el contador sube exactamente lo enviado.
- **Escenario 4 (actualizado)**: 100 reenvíos del mismo `playback_id`; contador +1 y `duplicates_discarded` = 99, medidos en las métricas y no en la respuesta.
- **Escenario nuevo, breaker**: con catálogo detenido, tras 5 fallos las llamadas fallan sin esperar el timeout; al volver el servicio y pasar 15 s, se recupera.
- **Escenario nuevo, revocación**: suspender o cambiar el rol hace que la siguiente petición dé `401` o `403` en menos de 2 s, en lugar de hasta 30 s.
- **Redis reiniciado** con eventos pendientes: no se pierde ninguno (AOF).
- **F3.4** (evento visible en ≤ 5 s) se mide de nuevo con la cola. Se repite la prueba de carga (escenario 9) y se anota el efecto del salto extra.
- Pruebas de las suites de siempre en verde. `docker compose up --build` levanta todo, y la interfaz sigue mostrando gráficas e historial.

## 9. Riesgos y lo que se deja al constructor

- **Latencia de F3.4**: el consumidor debe leer con bloqueo corto para que el evento se vea en segundos. Si no llega a 5 s, el primer ajuste es el tiempo de bloqueo.
- **Orden y progreso**: si el consumidor se vuelve más de uno, el orden entre `record` y `progress` de un mismo `playback_id` puede perderse. Hoy es un solo consumidor; si cambia, hay que fijar el `progress` huérfano con un reintento corto.
- **`iat` y relojes**: `iat` y `revoked_after` son segundos con decimales (`time.time()`), y el token es inválido si `iat < revoked_after`. Emisor y validador comparten host en Compose, así que sus relojes coinciden.
- **Crecimiento del stream** si el consumidor está caído mucho tiempo: lo acota `MAXLEN ~`. Con el recorte, lo más viejo se pierde; se anota en el README.
- **Variables de entorno**: se agrega `REDIS_URL` y se actualizan `.env.example`, `compose.yaml` y el README raíz.
- Los nombres de archivo, la forma exacta del módulo de cola y el texto de los mensajes de error quedan a criterio del constructor, siguiendo el estilo de los otros servicios.
