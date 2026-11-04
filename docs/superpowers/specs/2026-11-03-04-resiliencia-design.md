# Diseño · `04-resiliencia`

Fecha: 2026-11-03 · Rama: `04-resiliencia` (parte de `03-gateway-discovery-balanceo`, commit `4ddc448`).

## Intención

Tercer paso del plan de ramas del PRD, equivalente a la parte de **circuit breaker** del lab S08
de Mexi Banco. En `03`, la demo mostró dos problemas:

- una réplica muerta deja colgada **unos 7 s** cada petición que le toca y luego responde `503`;
- un catálogo caído se golpea en cada llamada, y favoritas, historial y resumen responden `503`.

En `04` las fallas se vuelven **rápidas, acotadas y visibles**:

- timeouts explícitos;
- un reintento en otra réplica;
- un **circuit breaker hecho a mano** con sus tres estados;
- **degradación con copias** en favoritas e historial, visible en la UI;
- el estado de los circuitos en el **panel del administrador** (la Cabina).

En la defensa, cualquiera del equipo debe poder:

- señalar dónde vive cada mecanismo;
- mostrar el circuito pasando de cerrado a abierto, a semiabierto y otra vez a cerrado;
- explicar por qué MELOXO **no necesita saga**.

## Metas

1. **Timeouts explícitos.** En `app/clients/http.py` (`users-playlists`, `playback-metrics`) cada
   intento tiene un límite total de `FLDSMDFR_CALL_TIMEOUT_S` (1.5 s).

   En el gateway (`services/gateway/app/proxy.py`) el límite corto aplica solo a **conectar**:
   `FLDSMDFR_UPSTREAM_CONNECT_S`, 1.5 s. Es justo lo que costaba los ~7 s en `03`: conectar con la
   IP de una réplica muerta.

   La espera de lectura, escritura y cabeceras es de `FLDSMDFR_UPSTREAM_READ_S`, 30 s, por
   operación (`httpx.Timeout(connect=1.5, read=30, write=30, pool=5)`). *Decisión del agente,
   por la revisión:* un límite corto de cabeceras en el gateway cortaría la petición antes de que
   el servicio pudiera reintentar dentro o responder con copias. Una llamada interna con su
   reintento llega a ~3.3 s, y el resumen hace varias seguidas. También cortaría las subidas de
   21 MB, que el catálogo procesa antes de responder. Los 30 s no cortan un audio lento.

2. **Un reintento en otra réplica.**
   - **En los clientes:** todas las llamadas internas son lecturas (incluido
     `POST /internal/songs/*` y `POST /internal/artists/*`, que solo consultan), así que todas
     se reintentan.

     Reintento = un segundo intento (`FLDSMDFR_RETRIES`, 1) contra **otra** instancia del
     directorio, si hay otra, tras una espera aleatoria de 100–300 ms. Se reintenta ante
     timeout, error de conexión o `5xx`. Nunca ante `4xx`.
   - **En el gateway:** el mismo reintento, solo para `GET` y `HEAD` y solo si **no se pudo
     conectar** (conexión rechazada o timeout de conexión). La petición nunca llegó al servicio.
     Un `5xx`, o un timeout de lectura, se devuelve como hoy (`5xx` tal cual o `503`): el
     servicio ya la recibió.

     Nunca se reintenta un `POST`, `PUT`, `PATCH` o `DELETE` en el gateway.

3. **Circuit breaker hecho a mano** en `app/shared/circuit.py`, una copia en cada servicio que
   llama a otros. Es una clase `CircuitBreaker`, una por servicio remoto: `users-playlists` →
   `catalog-streaming`; `playback-metrics` → `catalog-streaming` y → `users-playlists`.

   Funcionamiento:

   - **Cerrado:** deja pasar. Cuenta las llamadas fallidas **seguidas** y una llamada exitosa
     reinicia el contador. Al llegar a `FLDSMDFR_CB_FAILURES` (5) pasa a **abierto**.
   - **Abierto:** no llama. Responde al instante con `503 service_unavailable` y el mismo
     mensaje de siempre. Pasados `FLDSMDFR_CB_OPEN_S` (10 s) pasa a **semiabierto**.
   - **Semiabierto:** deja pasar **una** llamada de prueba; las demás se rechazan como en
     abierto mientras la prueba está en curso. Si la prueba sale bien → **cerrado**; si falla →
     **abierto** otra vez, por 10 s más.

   Reglas:

   - Cuenta como falla: timeout, error de conexión, `5xx` o que no haya instancias vivas. **No**
     cuenta un `4xx`: un `404` es una respuesta válida del dueño del dato.
   - Un `4xx` distinto de `404` se sigue traduciendo a `503`, como hoy, sin reintento y sin
     contar para el circuito. Es un error de contrato entre servicios, no una caída. *Decisión
     del agente.*
   - El circuito cuenta la **llamada lógica completa**: un intento más su reintento es una falla,
     no dos.
   - Cada cambio de estado deja una línea en el log, con el formato
     `circuito users-playlists→catalog-streaming: cerrado → abierto (5 fallas seguidas)`.
   - El estado vive en memoria de cada proceso. Si el servicio se escalara, cada instancia
     tendría su propio circuito. Se dice así en el README.
   - El gateway **no** lleva circuito: el directorio ya saca a las réplicas muertas, y el
     reintento cubre la ventana de la caché.

4. **Copias en favoritas e historial.**
   - **Favoritas:** `favorites` (base `users_playlists`, migración nueva) gana `title_snapshot`,
     `artist_snapshot`, `album_snapshot` y `duration_snapshot`. Son opcionales, porque las filas
     viejas no las tienen.
   - **Historial:** la tabla de eventos de reproducción (base `playback`, migración nueva) gana
     las mismas cuatro columnas, también opcionales.
   - **Se llenan al escribir:** marcar favorita y registrar una reproducción ya consultan la
     canción al catálogo para validarla, y guardan la copia en ese momento.
   - **Al leer, con el catálogo arriba:** se usan los datos vivos, como hoy. Si la copia de una
     fila falta o es distinta, **se actualiza** en esa misma lectura. Así las filas viejas se
     completan solas.
   - **Al leer, con el catálogo caído o el circuito abierto:** se responde `200` con las copias,
     y cada elemento lleva `status: "degraded"`. Las filas sin copia salen con título
     "Canción no disponible", artista vacío y duración 0.

     La lista entera lleva `degraded: true`, para que la UI muestre un único aviso.
   - **Escribir la copia durante un `GET`** necesita un `commit` explícito: `get_session` no hace
     commit solo. Si ese commit falla, se registra en el log y la lectura responde igual.

   Contratos:

   - `FavoriteSongOut.status` pasa a `'ok' | 'degraded' | 'unavailable'`. Favoritas no tiene
     `available` y no se le agrega.
   - `HistoryItemOut` gana `status: 'ok' | 'degraded' | 'unavailable'`. Su `available` se
     conserva por compatibilidad y vale `true` solo con `status == "ok"`.
   - **`song` del historial degradado** (*decisión del agente*): se conserva el `SongOut` anidado,
     para no cambiar la forma del contrato. Las cuatro copias llenan `title`, `artist`, `album`
     y `duration_seconds`. El resto se llena así: `id` = el id guardado, `is_active` = `false`,
     `has_cover` = `false`, `created_at` = `last_played_at`, `size_bytes` = `0`,
     `mime_type` = `""`. La UI decide con `status`, no con `is_active`.
   - **Canciones que el catálogo ya no devuelve:** con el catálogo arriba, el historial las sigue
     omitiendo, como hoy (`playback/service.py`). "Canción no disponible" solo aparece en modo
     degradado, para filas sin copia.
   - `InicioView` también lee `/api/me/history` y recibe el mismo tratamiento visual.
   - `FavoritesOut` y `HistoryPage` ganan `degraded: bool`.
   - `total_seconds` de favoritas suma también las degradadas, con su duración copiada.
   - El historial se agrupa por canción, como hoy, y usa la copia del evento más reciente.

5. **Degradación del resumen del administrador.** Hoy `GET /api/metrics/summary` responde `503`
   si no hay catálogo o usuarios.

   En `04` responde `200` con `total_songs` o `total_users` en `null` cuando su servicio no
   responde, y `degraded: true`. El top ya se degradaba.

6. **Qué sigue respondiendo `503`, ahora rápido:** las escrituras que necesitan validar contra el
   catálogo. Son marcar favorita, agregar una canción a un casete y registrar una reproducción.
   No se puede validar sin el dueño del dato, y aceptarlas a ciegas cambiaría el negocio.

   También sigue con `503`, ahora rápido, `GET /api/metrics/top-artists` (Inicio): los artistas
   salen del catálogo y no hay copia que mostrar. Inicio ya muestra su estado de error en esa
   sección. *Decisión del agente.*

   Con el circuito abierto responden en milisegundos, no en 1.5 s. La UI ya reintenta la
   reproducción con el mismo `playback_id`. Que no se pierda es tema de `05`.

7. **Circuitos en la Cabina.**
   - **Endpoints solo para administradores** (`403` para oyentes, `401` sin sesión), uno por
     servicio cliente, para respetar la tabla de rutas del gateway:
     - `GET /api/admin/circuits` en `users-playlists`;
     - `GET /api/metrics/circuits` en `playback-metrics`.
   - **Respuesta:** `{"instance": "<X-Instancia>", "circuits": [...]}`. Cada elemento es
     `{"source", "target", "state": "closed"|"open"|"half_open", "consecutive_failures",
     "since", "retry_in_s"}`. `retry_in_s` vale `null` salvo en abierto.
   - **En la UI:** un componente nuevo `EstadoCircuitos.vue`, en una tarjeta "Resiliencia" de
     `CabinaView`, junto a `ResumenMetricas`. Muestra:
     - una fila por circuito: origen → destino, estado con texto y un indicador no cromático,
       fallas seguidas, "desde hace N s" y, en abierto, "vuelve a probar en N s";
     - la instancia que respondió.
   - **Refresco:** cada 2 s mientras la pestaña está visible (`visibilitychange`), y se detiene
     al salir de la vista.
   - **Si un endpoint falla:** esa mitad dice "Sin datos de <servicio>" y la otra sigue. El
     panel no se rompe.

8. **UI degradada.**
   - **Estado nuevo "Sin actualizar"** en `DESIGN.md` §7 (tabla de estados): se muestra la copia
     con la etiqueta "Sin actualizar", opacidad 0.6 y sin reproducir. El audio también lo sirve
     el catálogo.
   - **Dónde se ve:** `FilaCancion` recibe el estado y lo aplica en favoritas, historial y en el
     detalle de casete. Hoy el casete marca `degraded`, pero la UI lo pinta como disponible; se
     corrige para que sea consistente.
   - **Aviso:** cuando la lista viene con `degraded: true`, un `AvisoEnLinea` arriba dice que el
     catálogo no responde y que se muestran los últimos datos guardados.
   - **Escrituras con `503`:** el mensaje del backend se muestra con el patrón de error existente.
   - **Resumen:** los totales en `null` se muestran como "—" con la nota "sin datos".

9. **Demo** `scripts/demo-04.sh`:
   1. Mide una consulta con las tres réplicas.
   2. Hace `docker kill` de una réplica y muestra que **ya no hay esperas de 7 s ni `503`**,
      gracias al reintento en otra réplica.
   3. Apaga las tres réplicas y muestra el circuito de `users-playlists`:
      - cinco fallas → abierto;
      - respuestas en milisegundos;
      - favoritas con `degraded`;
      - el endpoint de circuitos.
   4. Las enciende y muestra semiabierto → cerrado.

   Imprime los cambios de estado tomados de `docker logs`. Se puede seguir en paralelo en la
   Cabina.

10. **Documentación:**
    - `README.md` de la rama;
    - `docs/PRD.md`: §6 plan, §7 manejo de fallas, §9 decisiones y la nota "por qué no hay saga"
      reforzada con la operación de retirar una canción;
    - `AGENTS.md`: regla de resiliencia en los clientes;
    - `DESIGN.md`: estado "Sin actualizar" y tarjeta "Resiliencia".

## No metas

- **Saga u orquestador.** No hay escrituras en dos servicios. La justificación se escribe en el
  PRD y el README.
- **`Idempotency-Key` nueva.** Las reproducciones ya son idempotentes por `playback_id`
  (`ON CONFLICT DO NOTHING`), y la UI reintenta con el mismo id. Las demás escrituras no se
  reintentan en ningún punto. Se documenta como resuelto.
- **Circuito en el gateway**, *bulkheads*, *rate limiting*.
- **No perder reproducciones con el catálogo caído** (cola y outbox, en `05`).
- **Circuito compartido entre instancias** (Redis u otro): el estado es por proceso.
- **Llenar las copias de las filas viejas con una migración.** Una migración no puede llamar a
  otro servicio; se completan al leer.

## Anti-metas

- Que una réplica muerta siga costando ~7 s por petición.
- Que el circuito abierto todavía llame al servicio caído.
- Reintentar una escritura en el gateway: cobrar dos veces.
- Que favoritas o historial respondan `503` cuando hay copias que mostrar.
- Que la tarjeta de circuitos rompa la Cabina si un servicio no responde.
- Cambiar rutas públicas existentes o romper la UI con el catálogo arriba.

## Decisiones

**Del equipo:**
- `04` sin saga.
- Copias en favoritas e historial, visibles en la UI.
- El estado del circuito en el panel del administrador.

**Propuestas por el agente y aprobadas en la conversación:**
- Cifras: 1.5 s, un reintento con 100–300 ms, 5 fallas, 10 s abierto y una prueba en
  semiabierto.
- Qué cuenta como falla (no los `4xx`).
- El circuito cuenta la llamada lógica.
- Dos endpoints de circuitos, uno por servicio cliente.
- Refresco de la tarjeta cada 2 s.
- El gateway sin circuito.
- Las escrituras de validación siguen con `503`.

**Propuestas en este documento (a revisar):**
- **Límites del gateway:** 1.5 s para conectar y 30 s por lectura o escritura. El reintento se
  hace solo si no conectó (cambiado tras la revisión: un límite de cabeceras de 1.5 s chocaba
  con el reintento interno y con las subidas).
- **Historial degradado** con el `SongOut` anidado y valores por omisión, y `available` solo en
  el historial.
- **`top-artists` sin degradación**, y los `4xx` distintos de `404` siguen dando `503`.
- **El resumen se degrada** con `null` y `degraded: true` en lugar de `503`.
- **"Sin actualizar" no se reproduce.**
- **El casete también usa el estado nuevo**, para que la UI sea consistente.
- **La copia se refresca al leer** cuando difiere de los datos vivos.

## Interfaces

`app/shared/circuit.py` (copia en `users-playlists` y `playback-metrics`):

```python
class CircuitOpen(Exception): ...           # el cliente la traduce a RemoteUnavailable (503)

class CircuitBreaker:
    def __init__(self, source: str, target: str, failures: int, open_s: float,
                 clock: Callable[[], float] = time.monotonic) -> None: ...
    def before_call(self) -> None            # levanta CircuitOpen si no debe llamar
    def record_success(self) -> None
    def record_failure(self) -> None
    def snapshot(self) -> dict                # lo que devuelve el endpoint de circuitos
    @property
    def state(self) -> Literal["closed", "open", "half_open"]
```

- `clock` se inyecta para probar los tiempos sin dormir.
- `app/clients/http.py` guarda un `CircuitBreaker` por servicio remoto, `breakers() -> list[CircuitBreaker]`
  para el endpoint, y `reset_breakers()` para las pruebas.
- `call(service, method, path, **kwargs)` conserva su firma; dentro hace circuito → intento → reintento.

Configuración nueva (`FLDSMDFR_*`):

| Variable | Por omisión | Dónde |
|---|---|---|
| `CALL_TIMEOUT_S` | `1.5` | servicios cliente |
| `RETRIES` | `1` | servicios cliente y gateway |
| `CB_FAILURES` | `5` | servicios cliente |
| `CB_OPEN_S` | `10` | servicios cliente |
| `UPSTREAM_CONNECT_S` | `1.5` | gateway |
| `UPSTREAM_READ_S` | `30` | gateway |

## Pruebas

- **Del circuito** (`tests/test_circuit.py` en cada servicio cliente, con un reloj falso):
  - cerrado → abierto a las 5 fallas;
  - un éxito reinicia el contador;
  - abierto rechaza sin llamar;
  - a los 10 s pasa a semiabierto;
  - en semiabierto deja pasar una sola prueba y rechaza las concurrentes;
  - si la prueba sale bien, cierra; si falla, reabre;
  - el `snapshot` y la línea de log en cada transición.
- **De los clientes** (`tests/test_client_resilience.py`):
  - timeout → reintento en **otra** instancia;
  - un `4xx` no se reintenta y no abre el circuito;
  - un `5xx` sí se reintenta y cuenta;
  - con el circuito abierto, el servicio remoto falso **no recibe** la llamada;
  - intento más reintento cuentan como una falla.
- **Del gateway:**
  - una instancia que rechaza conexión en un `GET` → el reintento contesta `200` desde otra;
  - un `POST` con la instancia muerta → `503` sin reintento;
  - un `5xx` del servicio no se reintenta;
  - un timeout de conexión en un `GET` → reintento en otra instancia;
  - una respuesta lenta (más de 1.5 s, menos de 30 s) no se corta.
- **De la degradación:**
  - favoritas e historial con el catálogo caído → `200` con las copias, `status: "degraded"` y
    `degraded: true`;
  - una fila vieja sin copia → "Canción no disponible";
  - la copia se completa al leer con el catálogo arriba;
  - resumen con usuarios caídos → `total_users: null`.
- **De los endpoints de circuitos:** un oyente recibe `403` y un administrador ve el estado.
- **UI (Vitest):**
  - `EstadoCircuitos`: estados, una mitad "Sin datos", y el refresco se detiene al salir;
  - `FilaCancion` en estado "Sin actualizar";
  - el aviso de lista degradada en favoritas e historial;
  - el resumen con "—".
- **Verificación en vivo:** la demo completa, con la Cabina abierta durante el recorrido del
  circuito.

## Riesgos y limitaciones

- **El estado del circuito es por instancia y en memoria:** si el servicio se reinicia, vuelve a
  cerrado.
- **1.5 s puede ser poco** para consultas pesadas del top con mucha historia. Es configurable.
- **Copias desactualizadas:** mientras el catálogo no responde, se muestran datos de la última
  escritura o lectura buena. Es la consistencia eventual que el PRD (§4) ya acepta.
- **Reintentar las lecturas internas aumenta la carga** sobre un catálogo lento; el circuito la
  corta tras 5 fallas.
- **El refresco cada 2 s del panel** genera tráfico solo mientras un administrador lo tiene
  abierto.
