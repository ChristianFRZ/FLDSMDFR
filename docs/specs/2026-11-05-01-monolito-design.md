# Diseño · Rama `01-monolito`

Documento de diseño de la primera rama de MELOXO. Complementa al PRD (`docs/prd.md`), que sigue siendo la fuente de los criterios de aceptación. Aquí se registra qué se construye en esta rama, cómo, y qué se deja para después.

Las decisiones marcadas **(equipo)** las tomó el usuario. Las marcadas **(constructor)** las propuso quien diseña y pueden corregirse.

## 1. Intención

MELOXO es streaming musical cuya unidad central es el **casete compartido**: "música para compartir en pequeño, no para exhibir en grande". No hay feed, seguidores de personas, likes públicos ni recomendaciones.

`01-monolito` entrega **el producto completo funcionando en un solo proceso**. Las ramas 02 a 04 lo separan en servicios y lo endurecen, sin agregar funciones nuevas. Por eso el valor de esta rama está en dos cosas: que todas las funciones existan, y que las fronteras entre módulos sean reales, para que partirlo en la rama 02 sea cambiar llamadas a funciones por llamadas HTTP.

No hay criterios externos de entrega. El alcance de este documento es el criterio.

## 2. Objetivos

1. Cumplir F1 a F7 del PRD, con las excepciones de la sección 4.
2. Seis módulos con frontera real (sección 6).
3. Interfaz web completa para Oyente, Compositor y Administrador, con la dirección visual aprobada (sección 12).
4. Levantar todo con `docker compose up --build`.
5. Semilla de demo opcional con datos reales de Jamendo y actividad simulada (sección 10).
6. Scripts reproducibles en `/demo` para los escenarios aplicables.
7. Un `README.md` en cada carpeta.

## 3. No objetivos y antiobjetivos

**No objetivos**

- Lo que el PRD deja fuera de alcance: ML, transcodificación, pagos, apps nativas, moderación automática, formatos distintos de MP3.
- **F4.7, la sala de escucha sincronizada: fuera de esta rama (equipo).**
- Redis, gateway, réplicas, circuit breaker y Redis Streams: pertenecen a las ramas 02 a 04.

**Antiobjetivos: si pasa esto, la rama falló aunque funcione**

- Que un módulo lea tablas de otro, o que haya llaves foráneas entre módulos.
- Que aparezca algo parecido a recomendaciones, feed o popularidad social.
- Que la interfaz sea un duplicado de Spotify. Se toma de ahí solo la distribución.
- Que el `client_id` de Jamendo o cualquier secreto quede en un archivo versionado.
- Que el desorden visual afecte controles: menús, búsqueda y reproductor van rectos.

## 4. Reparto de criterios del PRD (equipo)

**Se dejan para ramas posteriores**

| Criterio | Motivo | Rama |
|---|---|---|
| F2.4 y demo 2: failover de réplicas | Hay una sola instancia | 03 |
| Demo 1: `docker stop playback-metrics` | No hay servicio separado | 02/04 |
| F3.3: cola real de eventos | No hay cola. El navegador reintenta | 04 |
| Revocación de tokens en Redis | Se sustituye, ver sección 8 | 03 |
| F4.7: sala de escucha | Decisión del equipo | Sin asignar |

**Se implementan con su forma final, aunque hoy casi no se activen**

- **F1.5:** la respuesta de playlists incluye `degraded`. Se activa si falla la llamada a la interfaz pública de catálogo.
- **F7.3:** el panel muestra aviso de datos no disponibles si la API de métricas falla, sin romper la interfaz.
- **Salud del sistema:** las tarjetas muestran app, base de datos y Jamendo.

**Se cumplen completos**

F2.5 (caída de Jamendo), idempotencia de `playback_id`, límites de casete con `409`, protección del último administrador, publicación programada con `SKIP LOCKED` y demos 3 a 9. La demo 8 corre con dos procesos de la misma app. La demo 9 es la carga de 50 clientes con `locust`.

**F2.3 y la demo 9 se miden solo con pistas `local` (constructor).** El tiempo al primer byte de una pista de Jamendo depende de un tercero, y 50 clientes serían una prueba de carga contra un servicio ajeno con una llave no comercial. El proxy de Jamendo se verifica aparte, con pocas peticiones. El resultado de la demo 9 debe decir esto expresamente.

## 5. Stack

| Pieza | Elección | Origen |
|---|---|---|
| Backend | Python 3.11+, FastAPI, un proceso | Equipo |
| Datos | Un PostgreSQL, una base | Equipo |
| Despliegue | Docker Compose: servicios `app` y `postgres`, puerto `8080` | Equipo |
| Redis | No se usa en esta rama | Equipo |
| Frontend | React con Vite, SPA servida por FastAPI como estáticos | Equipo |
| Gráficas | Chart.js | PRD |
| Lenguaje frontend | TypeScript | Constructor |
| Acceso a datos | SQLAlchemy 2 asíncrono con asyncpg, migraciones con Alembic | Constructor |
| HTTP saliente | `httpx` asíncrono, también para el proxy de audio | Constructor |
| Hash de contraseñas | argon2 | Constructor (el PRD permite bcrypt o argon2) |
| Pruebas | pytest contra PostgreSQL real, Vitest en frontend | Constructor |
| Carga | `locust` | Constructor (el PRD permite `locust` o `k6`) |

Se usa FastAPI asíncrono porque el streaming mantiene conexiones largas y el criterio F2.3 pide 50 clientes concurrentes sin degradar `GET /api/songs`.

Las pruebas usan PostgreSQL real, no SQLite ni simulaciones, porque los criterios críticos dependen de bloqueos reales.

## 6. Arquitectura

Monolito modular **(equipo)**: un proceso, una base, seis módulos con los nombres del PRD.

| Módulo | Dueño de |
|---|---|
| `modules/users` | Cuentas, credenciales, roles, solicitudes de Compositor, auditoría, refresh tokens |
| `modules/playlists` | Playlists y sus pistas |
| `modules/catalog` | Canciones, álbumes, perfil de artista, jobs de importación, audio y portadas en `/media` |
| `modules/playback` | Eventos de reproducción, contadores, historial, `duplicates_discarded` |
| `modules/social` | Favoritas, artistas seguidos, casetes, miembros, invitaciones, dedicatorias, avisos leídos |
| `modules/analytics` | Tablas de resumen para gráficas |

**Reglas de frontera**

1. Cada módulo solo consulta sus propias tablas.
2. Sin llaves foráneas entre módulos: las referencias externas son ids sueltos.
3. Un módulo expone funciones públicas en `public.py`, y los demás solo importan de ahí. Eso es lo que en la rama 02 se vuelve cliente HTTP.
4. La frontera se verifica con una prueba automática de importaciones que falla si se rompe la regla 3.
5. `public.py` acepta y devuelve esquemas simples, nunca objetos del ORM, para que sean serializables.

**Excepción explícita:** `modules/analytics` no lee las tablas de `modules/playback`. Recibe datos por la interfaz pública de playback, igual que recibirá eventos en la rama 04.

**Tareas periódicas**, dentro del mismo proceso:

| Tarea | Frecuencia | Nota |
|---|---|---|
| Publicar pistas `scheduled` vencidas | 30 s | `SELECT ... FOR UPDATE SKIP LOCKED` |
| Actualizar agregados de métricas | 2 s | Para cumplir F3.4 (≤ 5 s) |
| Refresco de metadatos de Jamendo | Diario | Solo metadatos |

Las tareas deben ser seguras con dos procesos corriendo a la vez. La demo 8 lo prueba.

**Avisos:** se calculan al leer, como dice el PRD. `modules/social` cruza artistas seguidos con pistas publicadas, usando la interfaz pública de catálogo. No hace falta un bus de eventos en esta rama. El cliente consulta cada 30 s.

## 7. API

Las rutas, códigos y formatos son los del PRD (sección 6). Reglas comunes:

- El usuario sale siempre del token, nunca del cuerpo de la petición.
- Paginación con `page` y tamaño configurable.
- Errores con forma uniforme: código, mensaje y detalle.

Rutas no nombradas en el PRD quedan a criterio del constructor, siguiendo sus prefijos: `/api/admin/*`, `/api/composer/*`.

**Progreso de reproducción (constructor).** F3.1 envía el evento tras 10 s, y F3.2 cuenta cualquier reenvío del mismo `playback_id` como duplicado. Pero la gráfica de retención (10 s, 50 %, 100 %) necesita saber hasta dónde se escuchó. Se resuelve con una ruta aparte, `PATCH /api/playbacks/{playback_id}/progress`, que solo aumenta `listened_seconds` y no cuenta como reproducción ni como duplicado.

## 8. Seguridad

- JWT HS256 con `sub`, `role` y `exp` de 15 min, más refresh token.
- En cada petición se valida el token **y se consulta en base el estado y rol actual del usuario**. Esto sustituye la lista de revocación en Redis y cumple "pierde acceso de inmediato".
- Las reglas de ruta del PRD (sección 12) se aplican en una dependencia de FastAPI, además de revisar propiedad del recurso en cada módulo.
- Primer administrador por `ADMIN_EMAIL` y `ADMIN_PASSWORD` al arrancar.
- Último administrador: validación atómica en transacción. El intento rechazado también queda en bitácora (demo 6).
- Bitácora inmutable desde la API.
- Límite de intentos de login, en memoria o en base, a criterio del constructor.
- Subidas: tipo por contenido, nombre en disco UUID, límites de tamaño del PRD, cuota de 20 pistas por Compositor.

## 9. Jamendo

**Verificado el 2026-11-05**

- El `client_id` responde `200`, y el audio responde `206` a peticiones `Range`.
- Uso no comercial permitido. Cuota publicada: hasta 35,000 peticiones al mes. Máximo 200 pistas por petición.
- Los términos no mencionan el proxy de audio, ni para permitirlo ni para prohibirlo.
- Los términos no permiten diseñar la app para guardar contenido ni ofrecerlo sin conexión.

**Decisiones**

- **Proxy de audio sin escritura a disco (equipo)**, con timeout de 3 s. La redirección a la URL oficial queda como plan B detrás de una variable de entorno.
- **Atribución (términos, cláusula 4.1):** cada pista de Jamendo muestra artista, crédito a Jamendo, licencia y enlace a su página. Esto va más allá del PRD y es obligatorio.
- El `client_id` vive solo en `.env`, que se crea localmente con el valor que dio el usuario. En el repo solo hay `.env.example` sin valor.
- Importación por lote del administrador, idempotente por `jamendo_id`, reanudable y con backoff.

**Riesgo abierto:** la URL de audio incluye un parámetro `from` que parece un token. Hay que comprobar si caduca. Si caduca, la URL se pide de nuevo al reproducir, en vez de usar la guardada, cuidando la cuota.

## 10. Semilla de demo (equipo)

Comando opcional, separado del arranque normal:

1. Importa unas 2,000 pistas reales de Jamendo, variadas por género.
2. Genera usuarios ficticios de los tres roles, casetes, playlists y unos 90 días de reproducciones simuladas.
3. **Genera pistas `local` de Compositores con MP3 sintéticos (constructor):** audio breve generado con `ffmpeg`, que no se versiona. Sin ellas quedarían vacías las gráficas de Compositor y de Jamendo contra local, y no habría audio para la demo 9. Si el equipo tiene MP3 propios, pueden sustituirlos.

Todo lo simulado queda marcado como tal en base, para poder distinguirlo y borrarlo. Debe ser idempotente. Debe bastar para que las doce gráficas de la sección 10 del PRD carguen en menos de 2 s.

## 11. Reglas de producto que el PRD deja abiertas (equipo)

**Invitaciones: solo por enlace**

- No hay búsqueda de personas ni invitación directa. El enlace se comparte fuera de la app.
- Quien abre un enlace válido con sesión iniciada ve solo el nombre del casete y quién invita. Es una excepción acotada a F4.6: no ve pistas ni dedicatorias hasta unirse.
- La invitación queda pendiente en su Inicio y en su biblioteca hasta que se una o la descarte.
- Sin sesión, el enlace lleva a entrar o registrarse, y después vuelve a la invitación.

**Lanzamientos y avisos**

- Se puede seguir a artistas de Jamendo y a Compositores. Los artistas de Jamendo son registros propios en `modules/catalog`.
- Solo las publicaciones de Compositores generan avisos. Importar de Jamendo no avisa.
- Inicio muestra también las pistas programadas con su fecha. `modules/catalog` expone título y fecha de publicación de las pistas `scheduled` de los artistas seguidos, sin audio.

**Edición de casetes**

- Cualquier miembro agrega y reordena.
- Quitar una pista solo lo hace quien la agregó o el creador.
- Si dos miembros reordenan a la vez, el segundo recibe `409` y recarga. Esto requiere versión en el casete.
- Lado A y Lado B son solo la posición: 1 a 6 y 7 a 12. El miembro no elige lado, y la única capacidad es el máximo del casete.
- Una pista oculta o eliminada conserva su lugar y su dedicatoria, y se muestra como no disponible.

## 12. Interfaz

La marca está en `docs/brand/`, con su guía en `docs/brand/README.md`.

**Dirección visual aprobada (equipo)**

- Moderno con un poco de desorden ochentero: Memphis sobre negro.
- Fondo tinta `#141317`, paneles `#201F25`, patrón de puntos sutil. Bordes papel de 2 px, sombra dura rosa en el panel central.
- Acentos: rosa `#FF3D8B` para la acción principal, amarillo `#FFD233`, turquesa `#00D1BE`, cobalto `#4A5CFF`.
- Títulos en Unbounded 800. Dedicatorias y etiquetas de casete en Caveat. Texto de interfaz en fuente del sistema.
- Logo: Nota casete.

**Distribución:** biblioteca a la izquierda, contenido al centro, "sonando" a la derecha, reproductor abajo. Solo se toma la distribución de Spotify.

**Elementos propios**

- Pila de casetes inclinados entre 2 y 5 grados en lugar de carruseles.
- Dedicatorias e invitaciones como notas de papel rasgado con cinta adhesiva.
- Reproductor con dos carretes que giran y cambian de tamaño según el avance. Se detienen con `prefers-reduced-motion`.
- Casetes con **Lado A y Lado B**: 6 pistas por lado, porque el máximo son 12 **(equipo)**. Si el máximo se configura distinto, cada lado toma la mitad.

**Reproductor:** aleatorio, anterior, reproducir, siguiente, repetir, favorita, agregar a casete, dedicatoria, cola, volumen y pantalla completa. **Barra izquierda:** Inicio, Buscar, Tu biblioteca, Estadísticas, Crear casete.

**Inicio:** solo tus casetes, invitaciones, "Seguir escuchando" y lanzamientos de artistas que sigues. Nada de recomendaciones.

**Requisitos**

- SPA: el audio no se interrumpe al navegar.
- **Adaptable a teléfono (equipo):** en pantalla angosta, los paneles pasan a pestañas abajo y el reproductor se compacta, con las mismas funciones que en escritorio.
- Vistas por rol según el token (F7.1). Las doce gráficas de la sección 10 del PRD.
- Accesibilidad: texto con contraste de al menos 4.5:1, controles con nombre accesible, teclado completo, foco visible.
- Desorden solo en contenido. Menús, búsqueda y reproductor rectos.
- **Solo modo oscuro (constructor).**
- **Interfaz en español; código y rutas en inglés (constructor).**
- La referencia visual aprobada está en `docs/design/`.
- Revisar la interfaz con la skill `apple-design`, aplicando principios y fundamentos, porque es una app web.

## 13. Estructura del repositorio

```text
MELOXO/
├── README.md
├── .env.example
├── compose.yaml
├── backend/
│   ├── app/
│   │   ├── core/              # configuración, base, seguridad, errores
│   │   └── modules/
│   │       ├── users/
│   │       ├── playlists/
│   │       ├── catalog/
│   │       ├── playback/
│   │       ├── social/
│   │       └── analytics/
│   ├── migrations/
│   └── tests/
├── frontend/
│   └── src/
├── demo/                      # scripts de escenarios
└── docs/
```

Cada módulo separa rutas, servicios, modelos, esquemas y `public.py`. Cada carpeta lleva su `README.md`.

## 14. Pruebas y verificación

- Desarrollo guiado por pruebas en backend.
- Las concurrencias críticas se prueban de verdad, con peticiones paralelas contra PostgreSQL: pista 12 del casete, último administrador, reenvío de `playback_id`, doble publicación, reordenamiento simultáneo.
- Prueba automática de fronteras entre módulos.
- Jamendo simulado en pruebas automáticas. Una verificación manual contra el servicio real.
- Se comprueban en navegador las pantallas principales de cada rol.
- Los umbrales de rendimiento se miden con el script de carga en `docker compose` local, como dice el PRD.

## 15. Trabajo en git (equipo)

- Rama `01-monolito`, creada desde `main`. PRD, marca y código entran en esta rama, sin tocar `main`.
- Commits pequeños.
- Nada se sube a GitHub sin que se pida.
- Los commits no llevan a Claude como co-autor.

## 16. A criterio del constructor

- Nombres internos, esquema exacto de tablas y organización del código dentro de cada módulo.
- Librerías menores de frontend y backend.
- Rutas que el PRD no nombra.
- Orden de implementación.
