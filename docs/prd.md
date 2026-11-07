# PRD · MELOXO: Sistema Distribuido de Streaming Musical

## Equipo
- **Nombre del equipo:** `FLDSMDFR`
- **Integrantes:**
  - Franco Ramírez Christian (@ChristianFRZ)
  - López Hernández Miriam Amisadai (@AmisadaiLopez)
  - Nava Santiago Erick (@Saiko-E)
  - Pérez Paitán Brent Armando (@zmd-brnt)


---

## 1. Problema y usuarios

### ¿Quién sufre el problema?
Los usuarios que escuchan música bajo demanda experimentan degradación, saturación de ancho de banda o cortes de reproducción cuando un único servidor atiende a la vez cuentas, búsqueda de catálogo, entrega pesada de audio y registro concurrente de estadísticas.

### ¿Por qué no basta un enfoque centralizado?
En un monolito, las peticiones ligeras (login, listas) compiten por CPU, disco y conexiones con las transferencias continuas de audio y la escritura intensiva de telemetría. Si el servidor o la base central fallan, toda la plataforma cae (punto único de falla).

### Posicionamiento (distintivo)
> **"Música para compartir en pequeño, no para exhibir en grande."**

- No es Spotify: la unidad central no es la canción ni el algoritmo, sino el **casete compartido**.
- No es una red social: **no hay feed, ni seguidores de personas, ni likes públicos**. Solo se siguen **artistas** y se **invita** a casetes.
- Descubrimiento por **regalo e invitación**, no por recomendación ni popularidad social.

### Usuarios del sistema
| Rol | Descripción |
|---|---|
| **Oyente** | Explora el catálogo, reproduce, arma playlists y casetes, sigue artistas. |
| **Compositor** | Oyente aprobado por un Administrador que además publica su propia música y ve estadísticas de su obra. |
| **Administrador** | Gestiona usuarios y roles (incluida la promoción de otros administradores), catálogo, moderación y métricas globales. |

---

## 2. Por qué es un sistema distribuido

1. **Perfiles de carga heterogéneos:**
   - Usuarios, roles y playlists: lecturas/escrituras transaccionales con JSON pequeño.
   - Streaming y subida de audio: binarios continuos, ancho de banda e I/O sostenido.
   - Telemetría de reproducciones: ráfagas de escrituras concurrentes que no deben bloquear el audio.
   - Importación desde Jamendo: tarea por lote dependiente de un tercero externo.
2. **Aislamiento de fallos:** si métricas o Jamendo caen, el usuario sigue escuchando y navegando su biblioteca.
3. **Escalabilidad independiente:** el servicio de streaming se replica detrás del gateway; los transaccionales operan a menor escala.
4. **Estado compartido con concurrencia:** un casete lo editan varios miembros a la vez (orden, pistas, límite de capacidad), lo que obliga a manejar conflictos e idempotencia más allá del contador de reproducciones.

---

## 3. Objetivos y fuera de alcance

### Objetivos del prototipo
1. **API Gateway** como punto único de entrada, con balanceo, validación de JWT y control de acceso por rol.
2. **Servicio de Usuarios y Playlists**: cuentas, roles, solicitudes de Compositor, playlists, casetes (módulo `social`), favoritas, seguidos, avisos y bitácora de auditoría.
3. **Servicio de Catálogo y Streaming**: metadatos de Jamendo y locales, importación, subida de audio, streaming con `Range` (proxy para Jamendo, archivo local para subidas).
4. **Servicio de Reproducciones y Métricas**: eventos idempotentes, contadores, agregados para gráficas.
5. **Panel web** con dashboards por rol (gráficas con Chart.js).
6. **Comunicación inter-servicio:** REST síncrono para validaciones; eventos asíncronos para telemetría y avisos.

### Fuera de alcance
- Recomendación con ML/IA.
- Transcodificación en tiempo real a múltiples bitrates.
- Pagos, suscripciones, regalías o DRM.
- Apps móviles nativas.
- Moderación automática de audio (la moderación es manual por el Administrador).
- Subida de archivos que no sean MP3 (validación de tipo y tamaño máximo definidos abajo).

---

## 4. Requisito primordial y lo que dejamos atrás

### Prioridad: Alta disponibilidad y baja latencia en streaming (AP en CAP)
- El usuario puede reproducir y navegar aunque métricas, avisos o Jamendo no respondan.
- El buffer de audio inicia de inmediato.

### Sacrificado: consistencia estricta inmediata
- Contadores, historiales y gráficas son **eventualmente consistentes**.
- No se usa 2PC ni se bloquea la reproducción esperando confirmación de métricas.

### Zonas donde SÍ se exige consistencia fuerte (dentro de un solo servicio)
- Roles y cuentas (nunca debe haber cero administradores).
- Capacidad del casete (nunca más de 12 pistas, aun con ediciones concurrentes).
- Unicidad de `playback_id`.

---

## 5. Roles, permisos y alcances

**N** = núcleo · **O** = opcional (incluidos todos los marcados por el equipo).

### 5.1 Oyente
| Función | Alcance |
|---|---|
| Registro, login, editar perfil | Solo su cuenta |
| Buscar y filtrar catálogo (género, artista, etiqueta, fuente) | Catálogo público activo |
| Reproducir con pausa/reanudación (Range) | Cualquier pista activa |
| Playlists propias (crear, editar, eliminar) | Solo las suyas |
| Casetes: crear, invitar por enlace, agregar pistas con dedicatoria | Casetes donde es miembro |
| Favoritas, seguir artistas, avisos de lanzamientos | Solo los suyos |
| Historial y estadísticas personales | Solo las suyas |
| Solicitar ser Compositor | Una solicitud pendiente a la vez |

No puede: subir canciones, ver métricas globales, gestionar usuarios.

### 5.2 Compositor (hereda todo lo del Oyente)
| Función | Alcance |
|---|---|
| Perfil de artista (nombre artístico, bio, foto, enlaces) | Solo el suyo |
| **Subir pistas propias** (MP3, portada, género, licencia declarada) | Sus obras |
| Editar, ocultar, eliminar sus pistas | Solo las suyas |
| Crear álbumes/EP | Solos los suyos |
| **Programar lanzamientos** (fecha/hora de publicación) | Sus pistas; al publicarse dispara avisos a seguidores |
| Panel de estadísticas de su obra | Solo su obra; datos agregados y anónimos |
| Conteo de casetes/playlists que incluyen sus pistas | Solo conteo, sin identidades |

No puede: modificar pistas de Jamendo o ajenas, ver identidad de oyentes, ver métricas globales.

### 5.3 Administrador (hereda lo del Oyente)
| Función | Alcance |
|---|---|
| **Promover/degradar administradores** | Cualquier usuario |
| Aprobar/rechazar solicitudes de Compositor | Todas |
| Cambiar rol, suspender y reactivar cuentas | Todos los usuarios |
| Importar/sincronizar catálogo desde Jamendo | Todo el catálogo |
| Moderar: ocultar o retirar cualquier pista | Todo el catálogo |
| Dashboard global de métricas | Todo el sistema |
| Bitácora de auditoría | Lectura global |
| Exportar reportes (CSV/PNG) | Métricas globales |
| Ver salud del sistema (servicios arriba/caídos, latencias) | Infraestructura |

### 5.4 Reglas de seguridad de roles
1. El **primer administrador** se crea por *seed* (variables de entorno `ADMIN_EMAIL` / `ADMIN_PASSWORD` al primer arranque).
2. **No se puede degradar ni suspender al último administrador activo** (validación atómica en transacción).
3. Un administrador no puede quitarse el rol si es el único.
4. Toda promoción, degradación, suspensión, aprobación y moderación queda en la **bitácora de auditoría** (quién, qué, a quién, cuándo), inmutable desde la API.
5. Una cuenta suspendida pierde acceso de inmediato (ver sección de JWT).

---

## 6. Historias de usuario y criterios de aceptación

Convención: los umbrales de rendimiento se miden con el script de carga (sección 12) en `docker compose` local.

### F1. Autenticación, roles y playlists
- *Como oyente*, quiero crear y consultar mis playlists para organizar mi música.
- Criterios:
  1. `POST /api/auth/register` y `POST /api/auth/login` devuelven JWT con claims `sub`, `role`, `exp`.
  2. `POST /api/playlists` crea una lista asociada al usuario del token (nunca de un id en el body).
  3. `POST /api/playlists/{id}/songs` agrega una canción por id; reagregar la misma es idempotente.
  4. `GET /api/playlists/{id}` responde con p95 < 200 ms con catálogo sano.
  5. Si catálogo no responde, la playlist se devuelve con metadatos en caché y bandera `degraded: true`.
  6. Acceder a una playlist ajena privada devuelve `403`.

### F2. Catálogo y streaming
- *Como oyente*, quiero buscar y reproducir canciones sin cortes.
- Criterios:
  1. `GET /api/songs?q=&genre=&artist=&source=&page=` lista título, artista, álbum, duración, portada, fuente y licencia.
  2. `GET /api/songs/{id}/stream` soporta `Range: bytes=...` y responde `206 Partial Content`, tanto para pistas `local` como `jamendo` (proxy).
  3. Con 50 clientes concurrentes en streaming, el tiempo hasta el primer byte tiene p95 < 500 ms y `GET /api/songs` mantiene p95 < 300 ms.
  4. Si se detiene una réplica de catálogo, las peticiones siguientes se atienden por la otra; máximo 1 petición fallida durante la transición.
  5. Si Jamendo no responde, las pistas `local` y las ya listadas siguen funcionando; las pistas `jamendo` fallan con error claro `503` y el resto del sistema no se afecta.

### F3. Reproducciones y métricas
- *Como administrador o compositor*, quiero ver cuántas veces se escucha la música.
- Criterios:
  1. Tras 10 s reproducidos, el cliente envía `POST /api/playbacks` con `playback_id` (UUID), `song_id`, `listened_seconds`.
  2. Un mismo `playback_id` enviado N veces suma **una sola** reproducción; los duplicados se cuentan en `duplicates_discarded`.
  3. Si `playback-metrics` está caído, el stream no se interrumpe y el evento se encola/reintenta.
  4. `GET /api/metrics/top` refleja un evento en ≤ 5 s en condiciones normales (consistencia eventual).

### F4. Casetes compartidos (distintivo)
- *Como oyente*, quiero armar un casete con amigos y compartirlo por enlace para regalar música en pequeño.
- Criterios:
  1. Un casete tiene **máximo 12 pistas** y **máximo 8 miembros** (valores configurables).
  2. `POST /api/tapes/{id}/invites` genera un enlace con token de un solo uso o con expiración y límite de usos.
  3. `POST /api/tapes/join/{token}` agrega al miembro; reclamar el mismo token dos veces por el mismo usuario es idempotente.
  4. Al agregar una pista, el miembro puede dejar una **dedicatoria** (máx. 140 caracteres) visible para los miembros.
  5. Con dos miembros agregando la pista 12 al mismo tiempo, **solo una** se acepta y la otra recibe `409` (verificación atómica).
  6. Solo miembros leen el casete; solo el creador lo elimina o revoca enlaces.
  7. *(Opcional)* Sala de escucha sincronizada: los miembros reproducen la misma pista con desfase máximo de 2 s.

### F5. Perfil de Compositor, subida y lanzamientos
- *Como oyente*, quiero solicitar ser compositor para publicar mi música.
- *Como compositor*, quiero subir y programar mis pistas para controlar cuándo salen.
- Criterios:
  1. `POST /api/composer-requests` crea una solicitud `pending`; el Administrador la aprueba/rechaza con motivo; el rol cambia solo al aprobar y queda auditado.
  2. `POST /api/composer/tracks` (multipart) acepta **solo MP3**, tamaño máximo 15 MB, portada JPG/PNG máx. 2 MB; valida tipo por contenido, no solo por extensión.
  3. Una pista subida queda en estado `draft`, `scheduled`, `published` o `hidden`.
  4. Con `publish_at` futuro, la pista pasa a `published` automáticamente en esa fecha (tolerancia 1 min) y se generan avisos a los seguidores.
  5. Un compositor no puede editar, ocultar ni borrar pistas de otro (`403`) ni de Jamendo.
  6. El Administrador puede ocultar cualquier pista; queda en bitácora con motivo.

### F6. Administración y moderación
- Criterios:
  1. `POST /api/admin/users/{id}/role` cambia rol; rechaza degradar al último administrador (`409`).
  2. `POST /api/admin/catalog/import` lanza una importación (ver sección 8) y devuelve un `job_id` consultable.
  3. `GET /api/admin/audit` lista la bitácora paginada y filtrable.
  4. Todo endpoint `/api/admin/*` devuelve `403` a no administradores, verificado también dentro del servicio dueño.

### F7. Panel web y gráficas
- Criterios:
  1. La interfaz ofrece vista de Oyente, Compositor y Administrador según el rol del token.
  2. Cada gráfica del catálogo de la sección 10 carga en < 2 s con el dataset de demo.
  3. Si métricas no responde, el panel muestra aviso de datos no disponibles sin romper el resto de la interfaz.
  4. Administrador puede exportar el reporte visible a CSV y PNG.

---

## 7. Del monolito a los servicios

### Módulos del monolito inicial (`01-monolito`)
- `modules/users`: cuentas, roles, solicitudes de Compositor, auditoría.
- `modules/playlists`: playlists y asociaciones.
- `modules/catalog`: metadatos, importación de Jamendo, subidas, archivos.
- `modules/playback`: eventos, contadores, historial.
- `modules/social`: favoritas, artistas seguidos, casetes, invitaciones y avisos (se calculan al leer).
- `modules/analytics`: agregados para el panel.

### Servicios resultantes
1. **API Gateway** (`gateway`, puerto `8080`): valida JWT, aplica control por rol/ruta, balancea y sirve el panel web.
2. **`users-playlists-service`**: usuarios, roles, auditoría, playlists, módulo `social`.
3. **`catalog-streaming-service`** (2+ réplicas): catálogo, importación, subida, streaming.
4. **`playback-metrics-service`**: eventos, contadores, agregados para gráficas.
5. **Infraestructura de apoyo:** `postgres` (una instancia, bases lógicas separadas con usuarios distintos) y `redis` (Streams para eventos).

> Cuenta aclarada: **3 servicios de negocio + 1 gateway + 2 componentes de infraestructura**.

### Dueño de cada dato
| Dato | Servicio dueño | Almacenamiento |
|---|---|---|
| Usuarios, credenciales, rol, estado | `users-playlists-service` | DB `users_playlists` |
| Solicitudes de Compositor y bitácora de auditoría | `users-playlists-service` | DB `users_playlists` |
| Playlists, casetes, miembros, invitaciones, dedicatorias | `users-playlists-service` | DB `users_playlists` |
| Favoritas, seguidos, avisos leídos | `users-playlists-service` (`social`) | DB `users_playlists`; canciones por id, sin FK |
| Metadatos de canciones (Jamendo y locales), álbumes, perfil de artista | `catalog-streaming-service` | DB `catalog` |
| Audio subido y portadas | `catalog-streaming-service` | Volumen `/media` |
| Jobs de importación | `catalog-streaming-service` | DB `catalog` |
| Eventos de reproducción y contadores | `playback-metrics-service` | DB `playbacks` |
| Agregados para gráficas | `playback-metrics-service` | DB `playbacks` (tablas de resumen) |

Regla: ningún servicio lee la base de otro; solo por API o eventos.

### Plan de ramas
- `01-monolito`: app única con módulos acoplados y datos semilla de Jamendo.
- `02-separacion`: servicios en Docker, red interna.
- `03-gateway-balanceo`: gateway, JWT/roles, réplicas de catálogo, panel web.
- `04-resiliencia-concurrencia`: timeouts, reintentos con backoff, idempotencia, circuit breaker, Redis Streams, demo de fallas.

---

## 8. Catálogo con Jamendo

### Estrategia de importación (decisión del equipo de ingeniería)
**Lote controlado por el Administrador + refresco programado**, no importación al buscar.

| Alternativa | Decisión | Razón |
|---|---|---|
| Importar bajo demanda en cada búsqueda | Descartada | Acopla la latencia de búsqueda a un tercero, consume cuota de la API y rompe la degradación elegante. |
| **Lote del Administrador** (por género/popularidad, tamaño configurable) | **Elegida** | Búsqueda siempre local y rápida; catálogo reproducible para demo; el admin controla qué entra. |
| **Refresco programado** (diario, solo metadatos cambiados) | **Elegida** | Mantiene catálogo vivo sin intervención. |

Detalles:
- Importación inicial sugerida: 2,000–5,000 pistas variadas por género.
- Cada pista guarda: `jamendo_id`, título, artista, álbum, duración, género/etiquetas, portada, URL de audio, **licencia**, `source = 'jamendo'`, `imported_at`.
- El job es **idempotente** (clave única `jamendo_id`) y reanudable; respeta límites de la API con backoff.
- Las pistas de Jamendo son de solo lectura: ni Compositores ni Oyentes las editan; el Administrador puede ocultarlas.
- Se muestra la licencia y atribución en la interfaz.
- **Verificar** en la documentación de desarrolladores de Jamendo los términos vigentes (uso no comercial, atribución, cuota, y si permite hacer proxy del audio). Si el proxy no estuviera permitido, la alternativa es redirigir al cliente a la URL oficial.

### Streaming
- `source = 'local'`: lectura de archivo con `Range` desde `/media`.
- `source = 'jamendo'`: **proxy** con soporte de `Range` hacia la URL de Jamendo, con timeout (3 s) y sin almacenamiento en disco.

---

## 9. Subida de audio de Compositores

- Endpoint multipart solo para Compositor/Admin.
- Validaciones: MIME real (firma del archivo), MP3, máx. 15 MB, duración máxima configurable (p. ej. 10 min), portada JPG/PNG máx. 2 MB.
- Nombre de archivo en disco = UUID (nunca el nombre del usuario) para evitar *path traversal*.
- Estados: `draft → scheduled → published → hidden`.
- **Lanzamientos programados:** una tarea periódica (cada 30 s) en `catalog-streaming-service` promueve pistas `scheduled` cuyo `publish_at` ya pasó, usando bloqueo (`SELECT ... FOR UPDATE SKIP LOCKED`) para que **dos réplicas no publiquen dos veces**. Al publicar emite el evento `track_published`.
- El volumen `/media` se comparte entre réplicas; las escrituras ocurren en una ruta con nombre UUID para evitar colisiones.

---

## 10. Panel web y gráficas

Chart.js servido por el gateway; datos desde `/api/metrics/*` (agregados precalculados, consistencia eventual).

| Gráfica | Tipo | Vista |
|---|---|---|
| Reproducciones por día/hora | Línea | Admin, Compositor (la suya) |
| Top N canciones/artistas | Barras horizontales | Admin, Oyente (su top) |
| Distribución por género | Dona/barras | Admin, Oyente (la suya) |
| Mapa de calor día de semana × hora | Heatmap | Admin |
| Catálogo por fuente (Jamendo vs local) | Dona | Admin |
| Crecimiento de usuarios por rol | Líneas apiladas | Admin |
| Retención por pista (llegan a 10 s / 50 % / 100 %) | Embudo/barras | Compositor |
| Actividad en casetes (miembros, pistas, dedicatorias) | Barras | Admin |
| Lanzamientos programados vs publicados | Barras | Compositor, Admin |
| **Latencia p50/p95 del streaming y errores por servicio** | Línea | Admin |
| **Eventos duplicados descartados por idempotencia** | Contador/línea | Admin |
| Salud del sistema (servicios arriba/caídos) | Tarjetas de estado | Admin |

Privacidad: el Compositor solo ve agregados anónimos; el Oyente solo sus propios datos.

---

## 11. Dónde vive cada pieza

| Pieza | Dónde vive | Si falla |
|---|---|---|
| **API Gateway** | Contenedor frontal `:8080`, `restart: always` | El sistema queda inaccesible desde fuera; mitigación con reinicio automático. |
| **DNS/Directorio** | Red `sd-net` de Docker Compose | Docker administra el DNS embebido. |
| **Balanceo** | Gateway/Nginx con round-robin hacia `catalog_1`, `catalog_2` y *health checks* | Si una réplica cae, se redirige a la sana. |
| **Datos** | PostgreSQL con bases lógicas y usuarios separados por servicio; Redis para eventos | Caída de una DB afecta solo al servicio dueño. |
| **Eventos asíncronos** | **Redis Streams** con grupos de consumidores | Los eventos quedan en el stream y se procesan al volver el consumidor. |
| **Jamendo (externo)** | Proxy y job de importación | Metadatos en caché local; pistas `local` intactas. |
| **Avisos** | `social` en `users-playlists-service`; cliente consulta cada 30 s | Si catálogo no responde, solo se muestran invitaciones. |
| **Manejo de fallas** | Timeouts, reintentos con backoff, circuit breaker, idempotencia | Fallback inmediato sin cascada. |

### Parámetros de resiliencia (valores iniciales)
| Llamada | Timeout | Reintentos | Circuit breaker | Fallback |
|---|---|---|---|---|
| Gateway → servicios internos | 2 s | 1 (solo GET) | Abre tras 5 fallos en 30 s, prueba a los 15 s | Error `503` claro |
| `users-playlists` → catálogo (metadatos) | 1.5 s | 2 con backoff 200/400 ms | Igual | Metadatos en caché + `degraded: true` |
| Cliente/gateway → `playbacks` | 1.5 s | Encola en Redis y reintenta | Igual | Se descarta del camino crítico, el stream continúa |
| Catálogo → Jamendo | 3 s | 1 | Igual | `503` solo para esa pista |

---

## 12. Autenticación y autorización (decisión)

- **JWT firmado (HS256 para el prototipo)**, emitido por `users-playlists-service` en el login, con `sub`, `role`, `exp` (15 min) y refresh token.
- El **gateway valida** firma y expiración y aplica reglas por prefijo de ruta:
  - `/api/admin/*` → `admin`
  - `/api/composer/*` → `composer` o `admin`
  - resto autenticado → cualquier rol
- Los **servicios internos revalidan** el token y la propiedad del recurso; no confían ciegamente en el gateway. Los servicios internos no se exponen fuera de `sd-net`.
- **Suspensión/degradación inmediata:** al cambiar rol o suspender, se registra el `user_id` en una lista de revocación (Redis, TTL = vida del token) consultada por el gateway.
- Contraseñas con hash (bcrypt/argon2). Límite de intentos de login.

---

## 13. Stack y despliegue

- **Python 3.11+**, FastAPI (servicios), Nginx o gateway FastAPI.
- **PostgreSQL** (separación por base y usuario) y **Redis** (Streams + revocación).
- **Chart.js** para el panel web.
- **Docker y Docker Compose.**
- *Nota:* con réplicas de catálogo y escrituras de subida/importación, SQLite deja de ser adecuado para catálogo y métricas; por eso se adopta PostgreSQL.

```bash
docker compose up --build      # levantar todo
docker compose down -v         # apagar y limpiar
```

---

## 14. Pruebas y demo de fallas

| # | Escenario | Resultado esperado |
|---|---|---|
| 1 | `docker stop playback-metrics` durante un stream | El audio no se corta; los eventos se acumulan en Redis y se aplican al volver. |
| 2 | `docker stop catalog_1` bajo carga | Failover a `catalog_2`; ≤ 1 petición fallida. |
| 3 | Bloquear salida a Jamendo | Pistas `local` y metadatos en caché siguen; pistas `jamendo` dan `503` controlado. |
| 4 | Reenviar 100 veces el mismo `playback_id` | Contador +1; `duplicates_discarded` = 99. |
| 5 | Dos miembros agregan la pista 12 de un casete a la vez | Una `201`, otra `409`. |
| 6 | Intentar degradar al único administrador | `409`, sin cambios, queda registrado el intento. |
| 7 | Compositor intenta editar pista ajena / usar `/api/admin/*` | `403`. |
| 8 | Dos réplicas con una pista `scheduled` vencida | Se publica una sola vez, un solo evento `track_published`. |
| 9 | Carga: 50 clientes concurrentes de streaming | Cumple p95 de criterios F2 (script con `locust` o `k6`). |

Cada escenario tiene script reproducible en `/demo` y su efecto se muestra en el panel (latencia, errores, duplicados).

---

## 15. Decisiones de arquitectura

| Decisión | Alternativas descartadas | Justificación |
|---|---|---|
| Database-per-service (bases lógicas y usuarios separados) | Base única compartida | Evita acoplamiento de esquema y bloqueos cruzados. |
| Streaming por HTTP Range (REST) | gRPC streaming | Compatibilidad directa con el navegador. |
| Proxy de audio de Jamendo | Redirección al cliente | Mantiene control de flujo, medición y argumento de balanceo (sujeto a verificar términos). |
| Importación por lote del admin + refresco programado | Importar al buscar | Búsqueda local y estable; independencia de Jamendo. |
| Redis Streams para eventos | RabbitMQ / cola en memoria | Ligero, persistente, con grupos de consumidores y reintentos. |
| JWT con rol + revalidación en servicios | Sesiones centralizadas | Sin estado, encaja con escalabilidad horizontal. |
| Idempotencia por UUID | `counter += 1` directo | Reintentos de red no duplican conteos. |
| PostgreSQL | SQLite | Escrituras concurrentes y réplicas. |
| Degradación elegante | Fallar toda la petición | El usuario sigue escuchando. |
| Casetes con límites (12 pistas) | Playlists ilimitadas | Distintivo del producto y caso natural de concurrencia. |

---

## 16. Riesgos

| Riesgo | Mitigación |
|---|---|
| Términos de Jamendo no permiten proxy o limitan cuota | Verificar antes de `03`; plan B de redirección; caché de metadatos. |
| Contenido subido ilegal o con derechos de terceros | Declaración de licencia obligatoria, moderación manual, bitácora, botón de ocultar; fuera de alcance moderación automática. |
| Almacenamiento creciente por subidas | Límites de tamaño y cuota por Compositor (p. ej. 20 pistas). |
| Alcance demasiado amplio | Priorizar por ramas; sala de escucha sincronizada es la primera en recortarse. |
| Carrera en publicación programada | `SKIP LOCKED` y estado atómico. |
