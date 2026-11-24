# Diseño · Rama `02-separacion`

Segunda rama de MELOXO. Complementa al PRD (`docs/prd.md`) y al [diseño de `01-monolito`](2026-11-05-01-monolito-design.md). Aquí se registra qué se construye al separar el monolito en servicios, cómo, y qué se deja para después.

Las decisiones marcadas **(equipo)** las tomó el usuario durante el diseño. Las marcadas **(constructor)** las propuso quien diseña y pueden corregirse.

## 1. Intención

`01-monolito` entregó el producto completo en un solo proceso, con seis módulos cuya única vía de comunicación es `public.py`. `02-separacion` parte ese proceso en **tres servicios de negocio sobre una red interna de Docker**, sin agregar funciones nuevas. Las llamadas a funciones entre módulos pasan a ser llamadas HTTP entre servicios.

El valor de la rama está en que la frontera deje de ser una convención y pase a ser física: cada servicio con su código, su imagen, su base de datos y su usuario de base de datos. Las ramas 03 y 04 (gateway, réplicas, resiliencia) se apoyan en eso.

## 2. Objetivos

1. Tres servicios de negocio: `users-playlists`, `catalog-streaming` y `playback-metrics`, más `postgres` y un `nginx` de entrada.
2. El producto se comporta igual que en `01-monolito` desde el navegador: mismas rutas `/api/*`, misma interfaz.
3. Ningún servicio lee la base de otro, y la base lo impide (usuarios de base de datos distintos).
4. Levantar todo con `docker compose up --build`.
5. Demo 1 del PRD funcional: con `docker stop playback-metrics`, el streaming, las playlists y el catálogo siguen funcionando.
6. Escenarios de `/demo` y prueba de carga adaptados y pasando contra la nueva arquitectura.
7. Un `README.md` en cada carpeta nueva, como en la fase 1.

## 3. No objetivos y antiobjetivos

**No objetivos** (pertenecen a ramas posteriores)

- Gateway real, validación de roles por ruta en la entrada y réplicas de catálogo: rama 03.
- Reintentos con backoff, idempotencia entre servicios, circuit breaker, Redis y Redis Streams: rama 04.
- Funciones nuevas de producto. F4.7 (sala de escucha) sigue fuera.
- Migrar datos de la instancia anterior: se vuelve a sembrar **(equipo)**.

**Antiobjetivos: si pasa esto, la rama falló aunque funcione**

- Que un servicio importe código de otro servicio.
- Que un servicio pueda conectarse a la base de otro.
- Que el navegador alcance una ruta `/internal/*`.
- Que una caída de `playback-metrics` rompa el streaming, las playlists o el catálogo.
- Que una función del monolito cambie de comportamiento visible sin que esté en este documento.

## 4. Decisiones del equipo

| Tema | Decisión |
|---|---|
| `analytics` | Vive en `playback-metrics`. Al responder una gráfica pide por HTTP lo que le falta a catálogo y a `users-playlists`. Si algo falla, el panel muestra «datos no disponibles» (F7.3). |
| Autenticación entre servicios | Cada servicio valida el JWT por sí mismo y guarda en caché 30 s el estado del usuario que le da `users-playlists`. Una suspensión surte efecto en 30 s como máximo. Si `users-playlists` no responde, se usa el último estado conocido. |
| Estructura del código | Una carpeta por servicio y un paquete `common`. Cada servicio solo puede importar `common`. |
| Datos existentes | No se migran. Se vuelve a sembrar. |

## 5. Decisiones del constructor

| Tema | Decisión | Razón |
|---|---|---|
| Entrada | Un `nginx` mínimo en el puerto 8080 que enruta por prefijo y sirve el frontend compilado. La rama 03 lo reemplaza por el gateway. | El frontend sigue llamando a `/api/*` en un solo origen y no cambia. |
| Rutas internas | Cada servicio expone `/internal/*` y nginx no las publica. Sin autenticación más allá de la red de Docker. | La red interna es la frontera en esta rama. La rama 03 puede agregar un token de servicio. |
| Tiempo de espera | Toda llamada interna tiene timeout de 3 s. | Evita que una llamada colgada retenga la petición. Sin reintentos. |
| Degradación | Se reutiliza `degraded` de playlists (F1.5), que se activa si falla la llamada a catálogo. | Ya existe en la fase 1. |
| Volumen `/media` | Lo monta solo `catalog-streaming`. | Nadie más toca los archivos. |
| Pendientes de la fase 1 | Se resuelven `playlists.add_song` (retiene su conexión mientras llama a catálogo) y la carrera de `ensure_artist`. El resto de los pendientes menores sigue igual. | La separación los toca directamente. |
| Semilla y `/demo` | Cada servicio trae su semilla y un script las coordina por las rutas internas. | Una semilla única tendría que escribir en tres bases. |

### Decisiones del constructor tras la revisión

| Tema | Decisión |
|---|---|
| Escrituras que dependen de otro servicio | **(equipo)** La auditoría no se pierde: si `users-playlists` no responde, la acción del administrador falla con 503. **(constructor)** `add_song` en una playlist devuelve 503 si catálogo no responde. Una reproducción se guarda igual si catálogo no responde. |
| Referencias entre servicios | Los ids que apuntan a otro servicio (`songs.artist_id` a un usuario, pistas en playlists y casetes, eventos de reproducción) son ids sueltos, sin llave foránea, como ya pedía la fase 1. Si el dato referido no existe, se tolera y se filtra al leer: el monolito ya muestra «no disponible» (`missing_song`). Borrar o suspender no se propaga por `/internal`. |
| Migraciones | Un historial de Alembic por servicio, con las tablas del módulo que le toca. Se ejecutan al arrancar cada servicio. |
| Lotes y tamaños | Las rutas `/internal/*` que reciben listas de ids (`get_songs`, `get_artists`) aceptan hasta 200 y el cliente parte las listas más grandes. Las que devuelven series para gráficas (`events_since`, `catalog_by_source`, `tape_activity`) paginan. |
| Funciones de demo | `insert_demo_*`, `clear_demo_*`, `demo_user_ids` e `import_demo_catalog` pasan a rutas `/internal/demo/*` con el mismo contrato. nginx no las publica. |
| Caché de autenticación | Sin edad máxima en esta rama: si `users-playlists` cae se usa el último estado conocido, y un ticket de streaming firmado sigue valiendo. Los cambios de rol siguen la misma regla de 30 s que la suspensión. Los tres servicios comparten una clave HS256 por la configuración de `common`. |
| Caída de `playback-metrics` en el navegador | nginx devuelve el error con el mismo formato JSON de la API para que el reintento del navegador siga igual. Se comprueba al construir si el frontend necesita algún cambio. |
| Prueba de rutas | Se escribe a mano `nginx.conf` y la prueba levanta las tres aplicaciones, lista sus rutas y comprueba contra el archivo que cada una cae en un solo servicio. |
| Streaming en nginx | Sin buffer de respuesta y con timeouts largos en las rutas de audio. |
| Arranque | `docker compose up --build` en un clon nuevo, con las contraseñas de las tres bases leídas de `.env`. Los servicios esperan a Postgres con `healthcheck`. El volumen del monolito se borra con `docker compose down -v`, y el README lo avisa. |
| Carga | Los umbrales de F2.3 siguen igual. Si no se cumplen por el salto extra de red, se documenta el resultado en `docs/decisions/` y se decide con el equipo. No se relajan en silencio. |

## 6. Aproximaciones consideradas

| Opción | Qué es | Ventaja | Desventaja |
|---|---|---|---|
| A | Un código, tres arranques | Casi no mueve archivos | La frontera sigue siendo disciplina, y eso fue un antiobjetivo de la fase 1 |
| **B (elegida)** | Carpeta por servicio y un paquete `common` | La estructura impone la frontera. Sirve para tener réplicas en la rama 03 | Más trabajo al mover código. Tres imágenes que mantener |
| C | Carpeta por servicio con `common` copiado | Máxima independencia | Cada arreglo de seguridad se repite tres veces |

## 7. Arquitectura

```
navegador ──► nginx :8080 ──┬─► users-playlists    :8001 ─► db users_playlists
 (SPA estática en nginx)    ├─► catalog-streaming  :8002 ─► db catalog   + volumen /media
                            └─► playback-metrics   :8003 ─► db playbacks
                                      │
          servicios ◄── HTTP /internal/* ──► servicios (red interna, sin puertos publicados)
```

Los puertos 8001 a 8003 existen solo dentro de la red de Docker. Postgres sigue limitado a `127.0.0.1`.

### Reparto de módulos

| Servicio | Módulos del monolito | Base | Usuario de base |
|---|---|---|---|
| `users-playlists` | `users`, `playlists`, `social` | `users_playlists` | `users_playlists` |
| `catalog-streaming` | `catalog` | `catalog` | `catalog` |
| `playback-metrics` | `playback`, `analytics` | `playbacks` | `playbacks` |

Un solo servidor PostgreSQL con tres bases lógicas. Cada usuario solo tiene permisos sobre su base. Un script de inicialización las crea.

### Contratos internos

Cada función de los `public.py` que cruza servicios pasa a ser una ruta `/internal/*` del servicio dueño, con el mismo contrato:

| Quién llama | A quién | Función hoy | Para qué |
|---|---|---|---|
| Todos | `users-playlists` | `get_auth_state` | Estado de la cuenta (con caché de 30 s) |
| `catalog-streaming` | `users-playlists` | `record_audit`, `get_display_names` | Bitácora y nombres |
| `users-playlists`, `playback-metrics` | `catalog-streaming` | `get_songs`, `get_artists` | Metadatos de pistas y artistas |
| `users-playlists` | `catalog-streaming` | `published_since`, `upcoming_for_artists`, `song_is_playable`, `songs_owned_by` | Avisos y validaciones |
| `playback-metrics` | `catalog-streaming` | `catalog_by_source`, `release_counts`, `jamendo_status` | Gráficas y Salud |
| `playback-metrics` | `users-playlists` | `user_growth`, `count_inclusions`, `count_tape_inclusions`, `tape_activity` | Gráficas |

Los tipos de los contratos (modelos de datos que viajan entre servicios) viven en `common`. Cada cliente HTTP vive en el servicio que llama. `common` no importa nada de los servicios.

Dos cosas cambian de dirección respecto a hoy: `playback` ya no llama a nadie para escribir un evento, y `analytics` pasa de leer cinco módulos a llamar a dos servicios.

### Paquete `common`

Errores, paginación, seguridad (JWT), configuración base, sesión de base de datos y la caché de estado de autenticación. Sin dependencias de dominio.

### Tareas periódicas

| Tarea | Servicio |
|---|---|
| `publicar_programadas`, `refrescar_jamendo` | `catalog-streaming` |
| `actualizar_agregados` | `playback-metrics` |
| `volcar_latencia` | cada servicio guarda la suya. Cómo se agrega en Salud queda al constructor, sin cambiar lo que muestra la pantalla |
| `ensure_first_admin` | arranque de `users-playlists` |

### Rutas de entrada

nginx enruta por prefijo de `/api`. Hay prefijos que se parten entre servicios, por ejemplo `/api/admin/*`: usuarios y auditoría van a `users-playlists`, y la importación del catálogo va a `catalog-streaming`. La tabla exacta se arma en el plan a partir de las rutas reales, y una prueba comprueba que cada ruta del monolito llega a un solo servicio.

El streaming (`Range`, ticket firmado) pasa por nginx a `catalog-streaming` sin buffer. El ticket se valida localmente porque va firmado.

## 8. Fallas esperadas

| Falla | Comportamiento |
|---|---|
| Cae `playback-metrics` | Streaming, catálogo y playlists siguen. El panel muestra «datos no disponibles». Los eventos de reproducción se reintentan desde el navegador, como en la fase 1. |
| Cae `catalog-streaming` | `users-playlists` responde playlists con `degraded`. No hay audio. |
| Cae `users-playlists` | Quien ya tiene estado en la caché de un servicio sigue usándolo, aunque haya pasado de 30 s. Quien no lo tiene, y todo inicio de sesión, recibe error hasta que vuelva. |
| Llamada interna lenta | Timeout de 3 s y error controlado. |
| Auditoría con `users-playlists` caído | La acción de administrador falla con 503 y no se ejecuta. |
| `add_song` con catálogo caído | 503. |
| Reproducción con catálogo caído | Se guarda igual. |

## 9. Pruebas

- La prueba de fronteras (`test_boundaries.py`) pasa de comprobar imports entre módulos a comprobar dos cosas: cada servicio solo importa `common`, y cada usuario de base recibe «permiso denegado» al leer la base de otro.
- Las pruebas de cada módulo se mudan con su servicio y siguen pasando.
- Hay una prueba de rutas: cada ruta `/api/*` del monolito llega a exactamente un servicio.
- Escenarios de `/demo`: se adaptan a la nueva arquitectura. Se agrega el escenario 1 (`docker stop playback-metrics`). El 2 (failover de réplicas) sigue en la rama 03.
- Carga: `locustfile.py` pasa contra el nuevo stack con los mismos criterios de F2.3.

## 10. Documentación

README en cada carpeta nueva. Se actualizan el README raíz, `docs/decisions/` (nuevo `02-separacion.md`), `docs/plans/` y `CHANGELOG.md`.

## 11. Qué queda para el constructor

- Tabla exacta de rutas por servicio.
- Cómo se agrega la latencia por servicio para la pantalla Salud.
- Si `common` se instala como paquete o se copia al construir cada imagen.
- Orden de extracción de los servicios y estrategia de pruebas durante el paso intermedio.
