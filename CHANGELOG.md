# Cambios

Historial de las ramas `04-resiliencia-concurrencia`, `03-gateway-balanceo`, `02-separacion` y `01-monolito`, ordenado del más reciente al más antiguo y agrupado por fecha. Cada línea corresponde a un commit. Las decisiones de diseño tomadas durante la construcción están en [`docs/decisions/04-resiliencia-concurrencia.md`](docs/decisions/04-resiliencia-concurrencia.md), [`docs/decisions/03-gateway-balanceo.md`](docs/decisions/03-gateway-balanceo.md), [`docs/decisions/02-separacion.md`](docs/decisions/02-separacion.md) y [`docs/decisions/01-monolito.md`](docs/decisions/01-monolito.md).

## 2026-11-14

Rama `04-resiliencia-concurrencia`: las llamadas entre servicios tienen timeouts, reintentos y circuit breaker; las reproducciones pasan por una cola en Redis Streams; y un cambio de rol o una suspensión revoca la sesión al instante.

### Agregado
- **Diseño y plan:** diseño y plan de la rama. (`b4187b9`, `73851c2`)
- **Redis:** contenedor con AOF y volumen, y cliente compartido en `meloxo_common`. (`7cba6fb`)
- **Circuit breaker:** abre tras 5 llamadas fallidas en 30 s y prueba a los 15 s. (`9d584b4`)
- **Revocación de sesiones:** `revoked_after:<user_id>` en Redis, `iat` en los tokens, y `users-playlists` la escribe al cambiar un rol, suspender o aprobar una solicitud. (`6f20b87`, `a761634`)
- **Cola de reproducciones:** `catalog-streaming` valida y encola `POST` y `PATCH` de `/api/playbacks` (`202`); `playback-metrics` las consume con grupo de consumidores y `XACK` tras el commit. (`46d948b`, `2551f2e`)
- **Demo y pruebas:** escenarios 10 (breaker) y 11 (revocación), y `wait_until`. (`d0933a0`)

### Cambiado
- `InternalClient`: conexión 1 s y lectura 1.5 s (antes 3 s), 2 reintentos con 0.2 y 0.4 s en lecturas y un breaker por destino. (`577fb2e`)
- `POST /api/playbacks` responde `202` sin `counted` y lo atiende catálogo; un progreso ajeno o inexistente se descarta en el consumidor en vez de dar `403`/`404`. (`2551f2e`)
- Un cambio de rol o una suspensión se ve en la siguiente petición, no hasta 30 s después. Reactivar una cuenta no devuelve el token anterior. (`a761634`)
- Escenarios 1 y 4 comprueban la cola: `202` y el resultado ya aplicado. (`d0933a0`)
- `APP_VERSION` de playback-metrics y gateway-auth pasa a `04-resiliencia-concurrencia`.

### Corregido
- Un token emitido justo después de un cambio de rol seguía viendo el rol viejo hasta 30 s; la revocación ahora descarta el estado de cuenta guardado antes de ella. (`952cb23`)

- El breaker de `InternalClient` ya no se queda en medio abierto si la llamada de prueba se cancela o falla con un error que no es de HTTP.
- El consumidor guarda cada reproducción con la hora en que se recibió, no la de cuando se aplica: tras una caída, lo escuchado durante ella ya no aparece como un pico al volver.

### Documentación
- README, decisiones, `docs/ramas.md` y CHANGELOG de la rama, y [`infra/redis/README.md`](infra/redis/README.md).

### Avisos
- Sin saga con estados, sin cola de mensajes muertos y sin breaker para Jamendo.
- El escenario 3 y `seed all` siguen sin verificar: falta `JAMENDO_CLIENT_ID`. Tampoco se repitieron las pruebas de Playwright.

## 2026-11-13

Rama `03-gateway-balanceo`: nginx valida sesión y rol con `gateway-auth` y `catalog-streaming` corre en dos réplicas con failover.

### Agregado
- **Diseño y plan:** diseño y plan de la rama. (`5a24729`)
- **gateway-auth:** servicio sin base de datos que valida el JWT y el rol para `auth_request`. (`e5f7756`)
- **Infraestructura**
  - `gateway-auth` en compose y catálogo con dos réplicas por defecto. (`9666f32`)
  - El gateway valida sesión y rol por prefijo antes de enrutar, con 401 y 403 en JSON. (`8875bd6`)
  - El gateway reintenta con la réplica sana de catálogo; `POST` y `PATCH` no se reintentan, `GET`, `HEAD`, `PUT` y `DELETE` pueden. (`6f2fffe`)
- **playback-metrics:** drena la latencia de cada réplica de catálogo. (`5f10df7`)
- **Demo y pruebas**
  - Escenario 2 de failover de catálogo (F2.4). (`06464c7`)
  - Pruebas del gateway y del failover con el stack levantado. (`dc68aac`)

### Cambiado
- `proxy_connect_timeout` baja de 3 s a 1 s y vale para todos los servicios. (`6f2fffe`)
- Un cambio de rol o una suspensión tarda hasta 30 s en verse en el gateway (caché de `gateway-auth`). (`8875bd6`)
- `APP_VERSION` de playback-metrics pasa a `03-gateway-balanceo`. (`7f84b5a`)

### Corregido
- `/_auth` usa su propio upstream y el rol se calcula en la petición principal; antes toda ruta protegida terminaba en gateway-auth y el gateway no exigía el rol. (`8875bd6`)
- `/_auth` no reenvía a gateway-auth la identidad que manda el cliente. (`22d1622`)
- `new_composer` espera a que el gateway vea el rol de Compositor, y solo reintenta un `403`. (`f70670d`, `d1bab25`)
- La latencia valida cada réplica por separado y descarta clientes de réplicas viejas. (`b19563a`)
- El escenario 2 no tapa su error al restaurar y cuenta solo el tráfico posterior a la caída. (`e7d7830`)
- `wait_edge` sondea con sesión de administrador: el 401 sin token ya lo da el gateway, y el escenario 8 limpiaba contra direcciones viejas. (`7f84b5a`)

### Documentación
- README, decisiones y CHANGELOG de la rama.

### Avisos
- La lista de revocación en Redis pasa a la rama `04`, y el control de salud de las réplicas es solo pasivo.
- El escenario 3 y `seed all` siguen sin verificar: falta `JAMENDO_CLIENT_ID`.

## 2026-11-12

Rama `02-separacion`: el monolito se parte en `users-playlists`, `catalog-streaming` y `playback-metrics`, con nginx de entrada y una base de datos por servicio.

### Agregado
- **Diseño y plan:** diseño y plan de la rama. (`d3000fe`, `712c3db`)
- **Base compartida**
  - Paquete `meloxo_common` con el cliente interno y los contratos. (`5155e02`)
  - Autenticación con caché de estado de 30 s. (`4e96837`)
  - Registro de latencia por servicio con drenaje interno. (`740564f`)
  - `boundaries` reconoce servicios con carpeta `modules`. (`a7877eb`)
- **catalog-streaming**
  - Esqueleto con migraciones propias y cliente de users. (`05111d6`)
  - Auditoría antes del commit y `ensure_artist` sin carrera. (`ff059dd`)
  - Módulo `catalog` trasladado con sus pruebas. (`83e8c26`)
  - Rutas internas. (`b8e03a0`)
- **users-playlists**
  - Esqueleto con migraciones propias. (`cd48fdc`)
  - Módulos `users`, `playlists` y `social` trasladados, con cliente de catálogo. (`d4f0ddb`)
  - Pruebas de fronteras, cliente de catálogo, modo degradado y `add_song` sin retener conexión. (`8ddbcac`)
  - Rutas internas. (`f4dcde0`)
- **playback-metrics**
  - Esqueleto con migraciones propias. (`710f7c6`)
  - Clientes de catálogo y usuarios con autenticación en caché. (`41eb046`)
  - Servicio con reproducciones y analítica. (`bfe9925`)
  - Salud por servicio y volcado de latencia. (`79a32de`)
- **Infraestructura**
  - Tres bases aisladas, imágenes por servicio y compose. (`ce23221`)
  - nginx de entrada con rutas por prefijo y errores JSON. (`98a73a5`)
- **Semilla y demo**
  - Semilla por las rutas internas. (`3c9b03d`)
  - Escenarios de demo para tres servicios y escenario 1. (`302be44`)
- **Pruebas:** README exigido en cada carpeta del repositorio. (`3262468`)

### Cambiado
- Se retira el monolito `backend/` y su Dockerfile. (`94c55ac`)
- `docker compose down -v` borra el volumen del monolito: hay que volver a sembrar con `seed`. (`ce23221`)
- La prueba de README ignora carpetas sin archivos del repositorio. (`df9ab3b`)
- Se silencia un aviso de pytest-asyncio en `meloxo_common`. (`d10699b`)

### Corregido
- El ticket de streaming firmado sigue valiendo con users-playlists caído. (`53a77c1`)
- Restaurar `catalog-streaming` en los escenarios no tapa errores, y el escenario 3 comprueba su precondición. (`3e628cc`)
- Revisión final: `JWT_SECRET` y las claves de base de datos son obligatorias en Compose y el secreto exige 32 caracteres; el puerto de catálogo del overlay de demo solo escucha en `127.0.0.1`; `edge` arranca aunque playback-metrics esté caído; las rutas `/api/*` desconocidas dan 404 JSON en vez de la SPA; `add_song` relee la playlist de la base; agregar pista a un casete solo convierte `UpstreamError` en 503.

### Documentación
- Resultados, decisiones y pendientes de la rama. (`3a51d7e`)
- Avisos al equipo y medición de agregar a una playlist. (`4d4138e`)
- README, CHANGELOG e índices de la rama.

### Avisos
- Se perdió la cobertura de `test_pool.py` (6 pruebas de soltar la conexión antes de llamar a otro módulo): ya no hay pool compartido porque la llamada entre dominios es HTTP.
- Posible regresión de latencia al agregar a una playlist: en la prueba de carga, la fase de preparación tuvo p50 de 780 ms y p95 de 1400 ms con 50 clientes. Con un solo usuario la misma ruta da p50 de 26 ms. Está por confirmar; ver "Avisos al equipo" en [`docs/decisions/02-separacion.md`](docs/decisions/02-separacion.md#avisos-al-equipo).
- `seed all`, la importación de Jamendo y el escenario 3 no se verificaron: no había `JAMENDO_CLIENT_ID`.

## 2026-11-07

### Agregado
- Estante de 12 colores y color libre para los casetes.
- Zona de arrastre para el MP3, la portada y la foto de perfil.
- La pantalla Salud suma resumen, tráfico, módulos, recursos y actividad.
- Documentación de la URL fija con Tailscale Funnel. (`e8c235d`)

### Corregido
- La pantalla completa del reproductor se cerraba al avanzar la canción. (`e8c235d`)
- El crédito de la pista se muestra como artista y origen, sin la licencia. (`e8c235d`)
- Los README tenían datos que no coincidían con el código. (`62effab`)

### Documentación
- Aclaración de los README y corrección de saltos de línea y enlaces. (`a2a103e`)

## 2026-11-06

### Agregado
- Frontend: adaptación a teléfono y accesibilidad. (`da9fdc1`)
- Semilla de demo con Jamendo y actividad simulada. (`dd89059`)
- Escenarios de demo reproducibles y prueba de carga. (`61a8623`)
- Edición de pistas, foto y enlaces del perfil de artista. (`5a5a7b3`)
- Licencia MIT del Equipo FLDSMDFR. (`f0d6b33`)

### Corregido
- **Catálogo**
  - Rechaza campos nulos y enlaces que no son web. (`c741935`)
  - Restaurar devuelve la pista a su estado anterior. (`ad20337`)
  - Maneja un Range enorme, el 416 de Jamendo y las respuestas que no son JSON. (`9741064`)
  - El refresco de Jamendo escribe por lotes. (`14f8789`)
- **Social:** una favorita eliminada se muestra como no disponible. (`a03defc`)
- **Infraestructura:** la clave sale de las pruebas y PostgreSQL queda limitado a localhost. (`162e6eb`)
- **Frontend**
  - Una pista rota salta sola a la siguiente. (`3618ab1`)
  - La sesión sobrevive a dos pestañas y a cortes de red. (`f7ae281`)
  - Unirse a un casete muestra el error en Inicio y Biblioteca. (`061b250`)
  - El panel distingue quién ocultó una pista. (`daa450c`)
  - En teléfono los títulos de Tu música se leen enteros. (`c3bc0a7`)
- La carga de prueba transmite cada pista completa. (`e3ce4ae`)

### Cambiado
- Se saca `egg-info` del repositorio. (`731b814`)
- Se ordena el repositorio y se completan los README. (`3bc443c`)

### Documentación
- Guía del proyecto y verificación final. (`9c64564`)
- Resultados finales tras la revisión de la rama. (`20baa5f`)
- Registro de decisiones y pendientes de la rama. (`3f56aa9`)

### Frontend (construcción)
- Base, marca, sesión e imagen de la app. (`2ce80d5`)
- Reproductor persistente con carretes. (`2ede11c`)
- Inicio, búsqueda, biblioteca y playlists. (`bacb3fa`)
- Casetes, lados, dedicatorias e invitaciones. (`a2669a2`)
- Vistas de compositor y base de gráficas. (`3eef788`)
- Panel de administración y estadísticas. (`daa50a8`)

## 2026-11-05

### Backend (construcción)
- **Base:** esqueleto del backend, base de datos y prueba de fronteras entre módulos. (`07afe35`)
- **Usuarios**
  - Registro, login, refresh y estado en cada petición. (`0173f7d`)
  - Roles, auditoría y solicitudes de compositor. (`0a1713d`)
- **Catálogo**
  - Modelo de catálogo y búsqueda. (`2f607b0`)
  - Streaming con Range, proxy de Jamendo y ticket. (`22ad724`)
  - Importación idempotente y reanudable de Jamendo. (`0d1757d`)
  - Subida validada y gestión de pistas de compositor. (`d80d7f3`)
  - Publicación programada y moderación. (`610d3d9`)
- **Playlists:** playlists con degradación elegante. (`d8bc392`)
- **Reproducción:** eventos idempotentes, progreso e historial. (`3271a88`)
- **Social**
  - Favoritas, artistas seguidos y avisos. (`f807107`)
  - Casetes, invitaciones y dedicatorias. (`04764fb`)
- **Analítica:** agregados, gráficas, salud y CSV. (`548596b`)

### Corregido
- Se suelta la conexión antes de llamar a otro módulo, para que el pool no se bloquee. (`442e2dc`)

### Documentación
- PRD, marca, maqueta, diseño y plan de 01-Monolito. (`074eeb8`)

### Inicio
- Commit inicial. (`f1017c6`)
