# PRD · FLDSMDFR: Sistema Distribuido de Streaming Musical


## 👥 Equipo
- **Nombre del equipo:** `FLDSMDFR`
- **Integrantes:**
-     -Franco Ramírez Christian (@ChristianFRZ)
      -Lopéz Hernández Miriam Amisadai (@AmisadaiLopez )
      -Nava Santiago Erick (@Saiko-E )
      -Pérez Paitán Brent Armando (@zmd-brnt )



---

## 1. Problema y usuarios

### ¿Quién sufre el problema?
Los usuarios que desean escuchar música bajo demanda en plataformas digitales experimentan problemas de degradación de servicio, saturación de ancho de banda o interrupción de reproducción cuando un único servidor centralizado atiende simultáneamente la gestión de cuentas, la búsqueda de canciones en catálogo, la entrega pesada de archivos multimedia (audio) y el registro concurrente de estadísticas de reproducción.

### ¿Cómo se resuelve hoy y por qué no basta un enfoque centralizado?
En arquitecturas monolíticas centralizadas tradicionales, las peticiones transaccionales ligeras (ej. consultar listas de reproducción o iniciar sesión) compiten directamente por I/O de disco, CPU y conexiones abiertas contra las transferencias continuas de streaming de audio y la escritura intensiva de telemetría de reproducciones. Si el servidor se sobrecarga o falla la base de datos central, toda la plataforma queda inutilizable (punto único de falla).

### Usuarios del sistema
1. **Oyente (Usuario Final):** Navega por el catálogo de canciones, crea y organiza playlists personalizadas, y reproduce pistas de audio de forma fluida y continua.
2. **Administrador / Curador de Contenido:** Registra metadatos de nuevas canciones, administra pistas y supervisa métricas globales de reproducciones en el sistema.

---

## 2. Por qué es un sistema distribuido

El proyecto requiere una arquitectura distribuida debido a las siguientes razones inherentes al problema:

1. **Perfiles de carga heterogéneos:**
   - La **gestión de usuarios y playlists** tiene alta frecuencia de lecturas/escrituras transaccionales con payloads pequeños (JSON).
   - El **streaming de canciones** requiere transferencia de datos binarios continuos (chunks de audio), consumo intensivo de ancho de banda e I/O de disco sostenido.
   - El **registro de reproducciones** genera una ráfaga alta de escrituras concurrentes que no debe bloquear ni ralentizar la experiencia de audio del usuario.
2. **Aislamiento de fallos y resiliencia:** Si el subsistema de contadores o registro de historial se satura o cae temporalmente, el usuario debe poder seguir reproduciendo música y consultando su biblioteca.
3. **Escalabilidad horizontal independiente:** El servicio de streaming de audio y el balanceador pueden replicarse en múltiples instancias detrás de un gateway para distribuir el tráfico de red, mientras que los servicios transaccionales operan a menor escala.

---

## 3. Objetivos y lo que no vamos a hacer

### Objetivos del prototipo (Alcance del corazón)
Construir un prototipo académico funcional enfocado en demostrar conceptos clave de sistemas distribuidos:
1. **API Gateway y Enrutamiento Unificado:** Punto único de entrada para clientes con balanceo de carga e invocación a microservicios.
2. **Servicio de Usuarios y Playlists:** Gestión de perfiles, autenticación básica y administración de listas de reproducción.
3. **Servicio de Catálogo y Streaming:** Consulta de metadatos de canciones y transmisión de fragmentos de audio (audio streaming por chunks o HTTP Range requests).
4. **Servicio de Reproducciones y Métricas:** Registro concurrente de eventos de reproducción (`song_played`), incremento de contadores y cálculo de tendencias/popularidad.
5. **Comunicación inter-servicio:** Comunicación síncrona (REST/gRPC) para validación de datos y asíncrona/desacoplada para eventos de telemetría.

### Lo que NO vamos a hacer (Fuera de alcance)
- **Algoritmos complejos de recomendación basados en Machine Learning / IA.**
- **Transcodificación dinámica de audio en tiempo real a múltiples bitrates:** Se emplearán archivos de audio estándar pre-cargados (MP3/WAV/OGG).
- **Pasarelas de pago reales o cobro de suscripciones.**
- **Gestión de licencias DRM (Digital Rights Management).**
- **Aplicaciones móviles nativas:** La interacción se realizará mediante API REST/gRPC documentada, clientes CLI y/o una interfaz web ligera.

---

## 4. El requisito que perseguimos y lo que dejamos atrás

### Requisito primordial: Alta Disponibilidad y Baja Latencia en Streaming
Bajo el **Teorema CAP**, priorizamos un modelo orientado a **AP (Availability / Partition Tolerance)** en la capa de reproducción:
- **Disponibilidad:** El usuario debe poder reproducir su música y consultar canciones incluso si ciertos nodos de métricas no responden o si hay lentitud en la sincronización.
- **Baja latencia:** La inicialización del buffer de audio debe ser inmediata.

### Lo que dejamos atrás: Consistencia Estricta Inmediata
Sacrificamos consistencia inmediata (*strong consistency*) en el conteo de reproducciones e historiales en favor de **consistencia eventual**:
- Si un usuario reproduce una canción, el contador global de reproducciones puede actualizarse de manera diferida o agregada.
- No se bloquea la reproducción esperando un bloqueo transaccional distribuido de base de datos de dos fases (2PC).

---

## 5. Historias de usuario

### Funcionalidad 1: Autenticación y Gestión de Playlists
- **Historia:** *Como oyente*, quiero crear y consultar mis playlists personalizadas, *para* organizar las pistas musicales que me gustan.
- **Criterios de aceptación:**
  1. `POST /api/playlists` permite crear una lista asociada al identificador del usuario.
  2. `POST /api/playlists/{id}/songs` agrega una referencia de canción existente.
  3. `GET /api/playlists/{id}` devuelve las canciones y metadatos en formato JSON en menos de 200 ms.
  4. Si el servicio de catálogo no responde al consultar detalles, la playlist muestra las canciones con metadatos en caché o estado degradado amigable.

### Funcionalidad 2: Búsqueda en Catálogo y Streaming de Audio
- **Historia:** *Como oyente*, quiero buscar canciones y reproducir una pista seleccionada, *para* escuchar música continua desde cualquier cliente.
- **Criterios de aceptación:**
  1. `GET /api/songs` lista las canciones disponibles con título, artista, álbum y duración.
  2. `GET /api/songs/{id}/stream` entrega el flujo binario de audio admitiendo peticiones con cabeceras `Range: bytes=...` para permitir pausa, reanudación y buffering.
  3. El streaming no interrumpe la navegación ni bloquea peticiones de otros usuarios concurrentes.

### Funcionalidad 3: Registro de Reproducciones y Métricas
- **Historia:** *Como administrador o curador*, quiero registrar cada reproducción y ver el top de canciones más escuchadas, *para* identificar la popularidad del catálogo.
- **Criterios de aceptación:**
  1. Al reproducirse al menos 10 segundos de una pista, el cliente o gateway emite un evento `POST /api/playbacks`.
  2. Cada evento incluye un identificador único de idempotencia (`playback_id`) para evitar duplicar conteos ante reintentos de red.
  3. `GET /api/metrics/top` devuelve la lista ordenada de canciones más reproducidas con consistencia eventual.

---

## 6. Del monolito a los servicios

### Módulos del monolito inicial (`01-monolito`)
Toda la lógica reside en una sola aplicación con un único proceso:
- `module_users`: Gestión en memoria / base única de usuarios y sesiones.
- `module_playlists`: Gestión de colecciones y asociaciones usuario-canción.
- `module_catalog`: Metadatos y lectura directa de archivos locales de audio.
- `module_playback`: Incremento sincrónico del contador en la misma base de datos e historial de escucha por usuario.
- `module_social`: Favoritas, artistas seguidos y avisos (lanzamientos de artistas seguidos e invitaciones a casetes). Los avisos se calculan al leer, consultando a `catalog` y `playlists` solo por su `service`.

### Servicios resultantes (`02-separacion` en adelante)
1. **API Gateway (`gateway`):** punto de entrada HTTP en el puerto `8000`. En `02-separacion` es un Nginx mínimo (`web`) que sirve la UI y reparte `/api` por prefijo. Desde `03` es un servicio FastAPI propio (`services/gateway/`) que decide el servicio por prefijo, pide las instancias vivas al directorio (Consul) y reparte en round-robin; `web` queda solo con la UI.
2. **Servicio de Usuarios y Playlists (`users-playlists`):** módulos `users`, `playlists` y `social`. Emite los JWT. Dueño de la base `users_playlists` y del volumen de portadas de casetes.
3. **Servicio de Catálogo y Streaming (`catalog-streaming`):** búsqueda, streaming con `Range`, subida y portadas de canciones. Dueño de la base `catalog` y del volumen de audio (`/media/audio`).
4. **Servicio de Métricas y Reproducciones (`playback-metrics`):** eventos de escucha, contadores, top e historial. Dueño de la base `playback`.

Desde `03`, cada instancia de cada servicio se registra en el directorio (`discovery`, Consul) con latido TTL, `catalog-streaming` corre en tres réplicas y las llamadas internas usan el **nombre lógico** del servicio, resuelto en el directorio y balanceado por el cliente.

Las tres bases viven, en `02`, en una sola instancia de PostgreSQL 16; ningún servicio conoce la URL de la base de otro. Lo que antes era un `import` entre módulos de servicios distintos ahora es una llamada HTTP a la API interna del dueño (`/internal/...`, no expuesta por el proxy):

| Quién llama | A quién | Para qué |
|---|---|---|
| `users-playlists` | `catalog-streaming` | validar la canción al agregarla a un casete o a favoritas; detalle de casete y favoritas; artistas seguidos y lanzamientos; resolver el casete demo de la semilla |
| `playback-metrics` | `catalog-streaming` | validar la canción al registrar la reproducción; datos del top, del historial y de los artistas más escuchados; conteo de canciones |
| `playback-metrics` | `users-playlists` | conteo de usuarios para el resumen del administrador |

### Dueño de cada dato (Single Source of Truth)
| Dato / Entidad | Servicio Dueño | Almacenamiento |
|---|---|---|
| Usuarios y credenciales | `users-playlists` | base `users_playlists` |
| Playlists y enlaces usuario-canción (con copia de título, artista y duración) | `users-playlists` | base `users_playlists` |
| Miembros de casetes e invitaciones por enlace (`playlist_members`, `playlist_invites`, `playlist_invite_claims`) | `users-playlists` | base `users_playlists` |
| Favoritas, artistas seguidos y avisos leídos (`favorites`, `artist_follows`, `notification_reads`) | `users-playlists` (módulo `social`) | base `users_playlists`; las canciones se referencian por id, sin llave foránea |
| Portadas de casetes | `users-playlists` | volumen `playlist-covers` |
| Metadatos de canciones (título, artista, duración) y portadas | `catalog-streaming` | base `catalog`; las portadas en el volumen `media` |
| Archivos de audio (binarios MP3/OGG/WAV) | `catalog-streaming` | volumen `media` |
| Eventos de reproducción y contadores | `playback-metrics` | base `playback` |

### Plan de ramas progresivo
Cada rama parte de la anterior y sigue el recorrido de Mexi Banco en el curso. El `README.md` de cada rama dice qué cambió, cómo se comprueba y qué queda fuera.

| Rama | Sesión del curso | Qué agrega | Cómo se demuestra |
|---|---|---|---|
| `01-monolito` | S05 | Monolito modular: un proceso, una base, módulos con límites verificados por prueba. | La aplicación completa en `:8000`. |
| `02-separacion` | S07 (antes del lab) | Tres servicios con base propia, llamadas HTTP por DNS de Compose, proxy Nginx mínimo para la UI. Sin timeouts ni reintentos a propósito. | `docker compose stop catalog-streaming`: lo que depende del catálogo responde `503` o se degrada; lo demás sigue. |
| `03-gateway-discovery-balanceo` | S07 | Gateway con rutas por servicio, **directorio** donde cada instancia se registra, **tres réplicas** de `catalog-streaming` y balanceo round-robin (también en las llamadas internas, que pasan a usar nombres lógicos del directorio). | Respuestas con cabecera `X-Instancia` alternando réplicas; apagar una réplica y ver que el tráfico sigue en las demás tras el plazo de expiración del directorio. |
| `04-resiliencia` | S08 | Timeouts explícitos (1.5 s), reintentos con backoff solo en llamadas idempotentes (en otra réplica, en el gateway y en los clientes: en `03` una réplica muerta cuelga ≈7 s cada petición que le toca), **circuit breaker** en `app/clients` (cerrado / abierto / semiabierto, hecho a mano), degradación donde hoy hay `503` (favoritas e historial con estado `degraded`) y `Idempotency-Key` en las escrituras que se reintenten. | Apagar el catálogo y mostrar el circuito abriéndose, respondiendo rápido sin llamar, y cerrándose al volver. |
| `05-mensajeria` | S09 | **RabbitMQ.** `playback-metrics` deja de recibir la reproducción por HTTP síncrono: se publica `cancion.reproducida` y un consumidor la cuenta con idempotencia por `playback_id` (restricción `UNIQUE` en la misma transacción), ack manual después de guardar, DLQ para mensajes envenenados y outbox para la doble escritura. `catalog-streaming` publica `cancion.publicada` y `users-playlists` arma los avisos de lanzamientos a partir del evento. | Apagar `playback-metrics`, reproducir varias canciones, ver los mensajes en la cola y los contadores ponerse al día al encenderlo; duplicado y mensaje envenenado resueltos. |
| `06-poliglota-cache` | S11 | **Redis** como caché del top y de los metadatos de canciones más pedidos (derivado, con TTL e invalidación al cambiar), y un almacén orientado a escrituras para la telemetría de reproducciones, manteniendo PostgreSQL como verdad de usuarios, casetes y catálogo. | Hit ratio medido, dato viejo provocado y explicado, y la aplicación funcionando con Redis apagado. |

**Por qué no hay saga en `04`:** hoy ninguna operación escribe en dos servicios. La más parecida, agregar una canción a un casete, solo *lee* del catálogo y escribe en `users-playlists`; si la canción se retira después, el casete conserva la copia y la marca `unavailable` al leer. Si en una rama posterior aparece una escritura en dos servicios (por ejemplo, retirar una canción y limpiar casetes y favoritas), se resolverá con una saga orquestada y su compensación, como en el lab S08.

---

## 7. Dónde vive cada pieza

| Pieza | Dónde vive | Por qué | Qué pasa si falla |
|---|---|---|---|
| **API Gateway / proxy** | `02`: contenedor `web` (Nginx) en el puerto `8000`, que sirve la UI y reparte `/api` por prefijo. `03`: contenedor `gateway` (`services/gateway/`, FastAPI + `httpx`), único puerto público; tabla de prefijos en `app/routes.py`, reenvío en streaming en `app/proxy.py`. | Fachada única para el navegador (un solo origen, la cookie de sesión llega a todos), oculta la topología interna y no expone `/internal`. | Si se cae, el sistema queda inaccesible para los clientes; se mitiga con `restart: unless-stopped`. Si cae un servicio detrás, el proxy sigue arriba y responde `503` en JSON. En `03` hay un solo gateway: es punto único de falla del prototipo. |
| **Directorio / DNS** | `02`: DNS embebido de Docker (`http://catalog-streaming:8000`); Nginx resuelve en cada petición (`resolver 127.0.0.11`). `03`: directorio Consul (contenedor `discovery`, panel en `:8500`); cada instancia se registra al arrancar (`app/shared/discovery.py`, `web/register.sh`) con id `<servicio>-<hostname>`, check TTL de 10 s y latido cada 3 s, y se da de baja al recibir SIGTERM. | Desacopla IPs y permite apagar y encender servicios sin reconfigurar a nadie. | Sin resolución de nombres los servicios no se encuentran; Docker Engine administra este DNS. En `03`, una réplica que deja de latir sale de la lista `passing` al vencer su TTL (≈10 s) y del registro al minuto. Si cae el directorio, las cachés de 5 s sirven un momento y después todo responde `503`. |
| **Balanceo** | `03`: `RoundRobin` de `app/shared/discovery.py`, en el gateway frente a todas las instancias y en `app/clients/http.py` de `users-playlists` y `playback-metrics` para las llamadas internas; lista de instancias cacheada 5 s. | La carga de streaming es pesada; repartirla entre réplicas evita saturación. | Una réplica muerta sin baja sigue recibiendo tráfico hasta ≈15 s (TTL + caché) y cada petición que le toca falla con `503` tras el timeout de conexión (≈7 s). Sin reintento en otra réplica hasta `04`. |
| **Datos (tipo de base, réplicas)** | Una base PostgreSQL por servicio (`users_playlists`, `catalog`, `playback`), en `02` dentro de la misma instancia; volúmenes `media` y `playlist-covers`. | Autonomía de cada servicio: nadie lee las tablas de otro y el esquema puede cambiar sin coordinar. | Cada servicio responde `503` en `/api/health` si pierde su base; los demás siguen. En `02` la instancia es una sola: si cae, caen las tres bases (se separan cuando haga falta). |
| **Operaciones entre servicios** | `02`: HTTP síncrono a `/internal/...` con clientes `httpx` en `app/clients/`. `05`: eventos de reproducción y de lanzamientos por RabbitMQ. | Llamadas explícitas con contrato; la telemetría pasa a asíncrona para no depender de que `playback-metrics` esté vivo. | `02`: sin conexión o `5xx` → `503 service_unavailable`; detalle de casete y top se degradan. `04`: timeouts de 1.5 s, reintentos y circuit breaker. |
| **Avisos (módulo `social`)** | `users-playlists`; el cliente consulta cada 30 s mientras la pestaña está visible | Los lanzamientos se calculan al leer a partir de los artistas seguidos y el catálogo (por HTTP desde `02`, por eventos desde `05`). | Si el catálogo no responde, los avisos se degradan y el siguiente sondeo reintenta. |
| **Manejo de fallas** | `02`: traducción uniforme de fallas remotas a `503`. `04`: timeouts, circuit breaker y claves de idempotencia UUID. `05`: idempotencia del consumidor, DLQ y outbox. | Previene fallas en cascada y conteos duplicados por reintentos. | Si un servicio está caído, el circuit breaker abre el circuito y responde con fallback inmediato (desde `04`). |
| **Autenticación** | `users-playlists` emite el JWT (cookie `httpOnly`); cada servicio lo valida localmente con el secreto compartido. | No hace falta preguntar a `users-playlists` en cada petición: el streaming sigue funcionando aunque ese servicio esté caído. | Si `users-playlists` cae, nadie puede iniciar sesión, pero las sesiones abiertas siguen valiendo hasta que expiran (8 h). |

---

## 8. Stack y cómo se levanta

### Tecnologías seleccionadas
- **Lenguaje:** Python 3.12.
- **Servicios:** FastAPI, SQLAlchemy 2 asíncrono (asyncpg), Alembic (una cadena de migraciones por servicio), Pydantic, PyJWT, `httpx` para las llamadas entre servicios.
- **Bases de datos:** PostgreSQL 16, una base por servicio.
- **Proxy:** Nginx (`02`); desde `03`, gateway propio en FastAPI + `httpx` y Nginx solo para la UI.
- **Directorio:** Consul 1.20 en modo `agent -dev` (desde `03`), checks TTL por instancia.
- **Interfaz:** Vue 3 + Vite + TypeScript, compilada en la imagen de `web`.
- **Orquestación y contenedores:** Docker y Docker Compose.

### Cómo se levanta el entorno
Toda la arquitectura se despliega con un solo comando desde la raíz del proyecto:

```bash
docker compose up --build -d
docker compose ps        # 03: db, discovery, tres catalog-streaming, users-playlists, playback-metrics, gateway y web healthy; catalog-init terminado
```

Pruebas por servicio:

```bash
docker compose --profile test run --rm tests-catalog
docker compose --profile test run --rm tests-users
docker compose --profile test run --rm tests-playback
docker compose --profile test run --rm tests-gateway    # desde 03
```

Y para apagar el sistema:
```bash
docker compose down -v
```

---

## 9. Decisiones de arquitectura

| Decisión | Alternativas descartadas | Justificación técnica |
|---|---|---|
| **Database-per-Service:** Bases independientes para cada servicio | Base de datos compartida única | Evita el acoplamiento a nivel de esquema y cuellos de botella de bloqueo en concurrencia masiva. |
| **Una instancia de PostgreSQL con tres bases en `02`** | Tres contenedores de PostgreSQL | Mismo aislamiento lógico (cada servicio solo conoce su URL) con menos memoria en las laptops del equipo; separarlas es solo configuración. |
| **Streaming por HTTP Range Requests:** Servir archivos de audio con soporte de chunks | Descarga completa previa en memoria | Permite reproducción instantánea sin esperar a descargar canciones completas de 5-10 MB. El proxy no guarda en buffer `/api/songs`. |
| **Idempotencia en reproducciones mediante UUIDs** | Incremento directo `counter += 1` en URL simple | Evita que reintentos de red generen múltiples incrementos erróneos para la misma sesión de escucha. |
| **Docker Compose con DNS embebido en `02`** | Configuración manual de IPs fijas o directorio desde el inicio | Simplifica la operación académica y permite el uso de nombres canónicos estables (`http://catalog-streaming:8000`). En `03` se reemplaza por el directorio. |
| **Consul como directorio en `03`, con checks TTL** | Eureka (JVM), DNS de Compose con réplicas, checks HTTP de Consul | El check TTL es el modelo de latido de Eureka que se ve en clase (la instancia avisa que vive); Consul es una imagen oficial ligera con panel. |
| **Gateway propio en FastAPI en `03`** | Nginx con `upstream` generado, Traefik leyendo Consul | El round-robin, la caché del balanceador y la traducción a `503` quedan en ~200 líneas de Python que el equipo puede leer y defender; el costo es un salto más en el streaming. |
| **Balanceo del lado del cliente en las llamadas internas** | Que las llamadas internas pasen por el gateway | Evita un salto y un punto único más entre servicios, como el `lb://` de Spring Cloud LoadBalancer. |
| **`catalog-init` de una sola vez** | Que cada réplica migre y siembre al arrancar; candado en la base | Tres réplicas migrando a la vez chocan; un trabajo previo con `service_completed_successfully` lo evita sin código extra. |
| **Proxy Nginx mínimo en `02`** | Que el navegador llame a cada servicio por su puerto; gateway completo desde `02` | Mantiene la UI funcionando con un solo origen (cookie y sin CORS) sin adelantar el gateway, que es el tema de `03`. |
| **JWT validado en cada servicio** | Validar la sesión preguntándole a `users-playlists` en cada petición | El token se firma con un secreto compartido y no guarda estado: el streaming no depende de que `users-playlists` responda. |
| **API interna `/internal/...` con clientes que conservan la firma del monolito** | Reescribir la lógica de negocio alrededor de llamadas remotas | El cambio de `import` a HTTP queda en `app/clients/`; `service.py` de cada módulo casi no cambia y la diferencia entre ramas se lee fácil. |
| **Código transversal copiado por servicio** (`shared/`, clientes) | Un paquete común instalado en los tres | Cada servicio se construye y evoluciona solo, como el `compartido/` de Mexi Banco; se acepta la duplicación. |
| **Degradación elegante en el Gateway** | Cancelar la petición completa si algún servicio secundario falla | Si el servicio de métricas no está disponible, el usuario puede seguir escuchando su canción sin interrupciones. |

---

## 10. Preguntas abiertas y desacuerdos

1. **Protocolo de comunicación interna para streaming:** ¿Conviene exponer el streaming directamente por HTTP REST con `StreamingResponse` de FastAPI o implementar un canal gRPC con streaming unidireccional? *(Acuerdo inicial: HTTP Range Requests en REST por facilidad de consumo desde navegador/cliente estándar).*
2. **Almacenamiento de archivos binarios:** ¿Montar una carpeta compartida en el host con volúmenes de Docker o levantar un contenedor con almacenamiento de objetos tipo MinIO compatible con S3? *(Acuerdo inicial: volumen local montado en el contenedor de catálogo para simplicidad y menor sobrecarga). En `03`, con tres réplicas del catálogo, el volumen `media` se comparte entre ellas; si eso estorba, MinIO vuelve a la mesa.*
3. **Manejo de autenticación distribuida:** *(Resuelto en `02`: JWT firmado por `users-playlists` y validado localmente en cada servicio con el secreto compartido.)* En `03` el gateway **no** valida el token: solo enruta, y cada servicio sigue validándolo. Queda abierto moverlo al gateway.
4. **Gateway y directorio para `03`:** *(Resuelto en `03`: Consul con checks TTL como directorio y gateway propio en FastAPI con round-robin; ver §9.)*
5. **Almacén de telemetría para `06`:** ¿Mantener los eventos en PostgreSQL con particiones por fecha o moverlos a un almacén orientado a escrituras? Se decide con mediciones de `05`.
