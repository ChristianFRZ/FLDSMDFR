# Diseño · Rama `03-gateway-balanceo`

Tercera rama de MELOXO. Complementa al PRD (`docs/prd.md`) y al [diseño de `02-separacion`](2026-11-12-02-separacion-design.md). Aquí se registra qué se construye para que la entrada deje de ser un enrutador por prefijo y pase a ser un gateway, y para que catálogo tenga dos réplicas.

Las decisiones marcadas **(equipo)** las tomó el usuario durante el diseño. Las marcadas **(constructor)** las propuso quien diseña y pueden corregirse.

## 1. Intención

`02-separacion` dejó un `nginx` mínimo en el puerto 8080: enruta por prefijo, sirve la SPA y no valida nada. Cada servicio valida el JWT por su cuenta. `03-gateway-balanceo` convierte esa entrada en el **gateway** del PRD (§7, §11, §12): valida el JWT y aplica el rol por prefijo de ruta antes de que la petición llegue a un servicio, y reparte las peticiones de catálogo entre **dos réplicas** con failover.

El valor está en dos criterios del PRD: la entrada única que corta las peticiones sin sesión o sin rol (F6.4, §12) y el criterio **F2.4**: si se detiene una réplica de catálogo, las peticiones siguientes las atiende la otra, con **a lo sumo 1 petición fallida** durante la transición.

## 2. Objetivos

1. **Gateway** = `nginx` + un validador pequeño en FastAPI (`gateway-auth`) consultado con `auth_request`.
2. El gateway rechaza con `401` (sin sesión o token inválido) o `403` (rol insuficiente) **antes** de enrutar. Reglas por prefijo del PRD §12: `/api/admin/*` → `admin`; `/api/composer/*` → `composer` o `admin`; el resto autenticado → cualquier rol.
3. Los servicios **siguen revalidando** el token y la propiedad del recurso (PRD §12). El gateway no sustituye ninguna comprobación existente.
4. Dos réplicas de `catalog-streaming` detrás del gateway, con reparto y reintento hacia la sana.
5. F2.4 verificado con una prueba automática y el **escenario 2** de `/demo` (detener una réplica bajo carga).
6. El navegador no cambia: mismas rutas `/api/*`, mismo origen, misma SPA.
7. Un `README.md` en cada carpeta nueva y actualización de los existentes.

## 3. No objetivos y antiobjetivos

**No objetivos**

- Lista de revocación en Redis, Redis Streams, circuit breaker, reintentos con backoff entre servicios: rama 04. Esta rama **no agrega Redis**.
- Gateway propio en FastAPI o OpenResty: se descartaron (sección 6).
- Un panel web nuevo: el de `01-monolito` ya cumple F7 y solo se comprueba que siga funcionando tras el gateway.
- Réplicas de `users-playlists` y `playback-metrics`: operan a una instancia (PRD §1, escalabilidad independiente).
- Balanceo activo con sondeos periódicos: nginx de código abierto solo tiene control pasivo (sección 6).

**Antiobjetivos: si pasa esto, la rama falló aunque funcione**

- Que el gateway sea el **único** punto que comprueba rol: si alguien llega a un servicio por la red interna, el servicio debe seguir diciendo `403`.
- Que el navegador alcance una ruta `/internal/*` o un servicio sin pasar por el gateway.
- Que detener una réplica de catálogo deje peticiones fallando más allá de la ventana de transición.
- Que dos réplicas publiquen dos veces una pista programada, o que se pierdan métricas de latencia de una réplica.
- Que cambie el comportamiento visible de una función sin estar en este documento.

## 4. Decisiones del equipo

| Tema | Decisión |
|---|---|
| Tecnología del gateway | **nginx + `auth_request` a un validador FastAPI.** Conserva el balanceo y el streaming con `Range` de nginx y reutiliza `meloxo_common`. Cuesta un salto interno extra por petición autenticada. |

## 5. Decisiones del constructor

| Tema | Decisión | Razón |
|---|---|---|
| Qué hace el validador | `gateway-auth` expone `GET /auth` (uso interno). Reutiliza `Auth.resolve_user` de `meloxo_common` (firma, expiración, `status == active`, rol), con la misma caché de 30 s del estado del usuario. Responde `204` con las cabeceras `X-User-Id` y `X-User-Role`, o `401`/`403` en JSON. El rol exigido llega en la cabecera `X-Required-Roles`, que fija nginx por `location`. | Una sola fuente de verdad para validar tokens, y el mapa de roles queda visible en `nginx.conf`. |
| Rutas sin sesión | Las que hoy no exigen sesión pasan sin `auth_request`: `POST /api/auth/register`, `/login`, `/refresh`, `/logout`, `GET /api/health`, la SPA, `GET /api/songs/{id}/stream` (usa el ticket de streaming, que valida catálogo) y `GET /api/media/*`. El builder confirma la lista contra el código con una prueba (sección 8). | No cambiar lo que ya funciona; el ticket de audio existe porque `<audio>` no envía `Authorization`. |
| Cabeceras de identidad | nginx borra `X-User-Id` y `X-User-Role` de lo que envíe el cliente y reenvía solo las del validador. **Los servicios no las usan todavía** y siguen leyendo el JWT. | Se deja preparado para la rama 04 sin crear una confianza ciega en el gateway (PRD §12). |
| Estado de cuenta | Se mantiene la decisión de `02`: una suspensión o cambio de rol surte efecto en 30 s como máximo. La lista de revocación inmediata del PRD §12 pasa a la rama 04, que trae Redis. | Redis no entra en esta rama. Se anota como diferencia con el PRD. |
| Caída del validador | Si `gateway-auth` no responde, las rutas protegidas dan `503` JSON con el mismo formato de `upstream_unavailable`. No se deja pasar la petición. | Fallar cerrado; la autorización no puede depender de que el servicio esté sano. |
| Réplicas | Servicio `catalog-streaming` con `deploy.replicas: 2` en `compose.yaml` (dos contenedores bajo el mismo nombre DNS). nginx ya resuelve por DNS en cada petición (`resolver 127.0.0.11`). | Mantiene el arranque de nginx aunque haya réplicas caídas, que es una propiedad ya probada en `02`. |
| Reparto y failover | `proxy_next_upstream error timeout http_502 http_503` con `proxy_next_upstream_tries 2` para métodos idempotentes (GET/HEAD); `proxy_connect_timeout 1s`. nginx reintenta con la otra dirección que devolvió el DNS. Las escrituras (POST/PUT/DELETE) **no** se reintentan. | Es lo que mantiene el máximo de 1 petición fallida: la fallida es la que ya iba en vuelo a la réplica que murió. |
| Streaming | Un `Range` interrumpido no se reintenta de forma transparente: el reproductor reanuda con un `Range` nuevo, que el gateway reparte a la réplica sana. | `Range` ya es reanudable por diseño. |
| Métricas de latencia | `playback-metrics` pasa a resolver **todas** las direcciones del nombre `catalog-streaming` y llama a `/internal/latency/drain` en cada una. | Hoy llama al nombre y cae en una réplica al azar: perdería los buckets de la otra. |
| Importación | Cada job vive en la base de catálogo y se consulta por `job_id` en cualquier réplica. La tarea de importación corre en la réplica que la recibió; si esa réplica cae, `resume` (ya existe) la reanuda. | Evita compartir estado en memoria. |
| Publicaciones programadas | Sin cambios: `SELECT ... FOR UPDATE SKIP LOCKED` ya impide la doble publicación con dos réplicas. | Es el diseño de `01`; el escenario 8 lo comprueba con réplicas reales. |
| Escenario 2 | `demo/scenario_2_failover.py`: carga continua de `GET /api/songs`, `docker stop` de una réplica, cuenta las peticiones fallidas, exige `<= 1` y que las siguientes den 200. | Reproduce F2.4 tal como lo pide el PRD. |

## 6. Enfoques considerados

| Enfoque | Qué cuesta | Decisión |
|---|---|---|
| **A. nginx + `auth_request` a FastAPI** | Un salto interno por petición autenticada; sin balanceo activo. | **Elegido (equipo).** |
| B. Gateway FastAPI completo | Proxy de streaming con `Range` y balanceo con health checks hechos a mano. | Descartado: reescribe lo que nginx ya hace bien. |
| C. OpenResty con Lua | Un lenguaje nuevo en el repo. | Descartado. |

Sobre el control de salud: nginx de código abierto no sondea réplicas. El «health check» del PRD (§11) se cumple de forma **pasiva**: `max_fails`/`fail_timeout` implícitos por reintento y el `healthcheck` de compose, que reinicia o marca la réplica. Un sondeo activo exigiría nginx Plus o un módulo de terceros. Se anota como diferencia con el PRD.

## 7. Arquitectura

```
navegador ──► edge (nginx :8080) ──auth_request──► gateway-auth :8004 ──► users-playlists (estado de cuenta, caché 30 s)
                 │
                 ├─ /api/auth, /playlists, /tapes, ...  ─► users-playlists :8001
                 ├─ /api/songs, /composer, /admin/catalog ─► catalog-streaming :8002  (2 réplicas, DNS Docker)
                 └─ /api/playbacks, /metrics, /admin/reports ─► playback-metrics :8003
```

- `gateway-auth` es un servicio nuevo en `services/gateway-auth/`, con imagen propia; solo importa `meloxo_common`. Sin base de datos. Puerto interno 8004, no publicado.
- `edge` conserva sus 40 `location` por prefijo; a las protegidas se les agrega `auth_request /_auth`, `auth_request_set` para las cabeceras y `proxy_set_header X-Required-Roles`.
- `edge` depende de `gateway-auth` sano. `restart: always` en `edge` y `gateway-auth` (PRD §11).
- Orden de comprobación en nginx: ruta sin sesión → pasa; si no, `auth_request`; `401`/`403` se devuelven con el JSON de error de la API.

## 8. Pruebas y criterios de cierre

- **Unitarias de `gateway-auth`**: token válido, expirado, mal firmado, usuario suspendido, rol insuficiente, ticket de streaming no aceptado como sesión (`scope`).
- **`edge/tests/test_routes.py`** (sin stack): cada `location` protegida declara su rol exigido; ninguna ruta de un servicio queda sin regla (se cruza con las aplicaciones FastAPI, como hoy). Una prueba separada fija la **lista de rutas sin sesión** contra el código de los servicios, para que una ruta pública nueva no pase inadvertida.
- **`edge/tests/test_stack.py`** (con stack): 401 sin token, 403 de un oyente en `/api/admin/*` y `/api/composer/*` **desde el gateway** (sin llegar al servicio), cabeceras de identidad enviadas por el cliente descartadas, `503` si `gateway-auth` está caído, streaming con `Range` intacto.
- **F2.4**: escenario 2 y una prueba con stack que detiene una réplica.
- **Escenario 8** repetido con las dos réplicas reales; **escenario 7** (permisos) debe seguir dando los mismos códigos.
- **Carga (F2.3)**: se repite la prueba de 50 clientes; p95 de primer byte < 500 ms y de `GET /api/songs` < 300 ms. Se anota cuánto suma el salto de `auth_request`.
- `docker compose up --build` levanta todo; el panel web carga y las gráficas siguen respondiendo.

## 9. Riesgos y lo que se deja al constructor

- **Latencia del salto extra**: si pasa el umbral de F2.3, la caché de 30 s de `gateway-auth` es el primer ajuste; una caché de decisiones en nginx (`proxy_cache` sobre `auth_request`) queda como segunda opción, con el costo de alargar la ventana de suspensión.
- **Reintento de peticiones en vuelo**: la única petición que falla en F2.4 es la que iba a la réplica al morir. Si la prueba mide más de 1, revisar `proxy_connect_timeout` y el DNS (`valid=`) antes de tocar la lógica.
- **Variables de entorno**: `compose.yaml` ya no pasa las variables con valor por defecto (pendiente de `02`). Aquí se agregan solo las del servicio nuevo.
- Los nombres de archivo, la estructura interna de `gateway-auth` y el formato exacto de los mensajes de error quedan a criterio del constructor, siguiendo el estilo de los otros servicios.
