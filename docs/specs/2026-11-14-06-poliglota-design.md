# Diseño · Rama `06-poliglota`

Sexta rama de MELOXO. Complementa al PRD (`docs/prd.md`) y al [diseño de `05-mensajeria`](2026-11-14-05-mensajeria-design.md). Aquí se registra cómo entra Redis como caché de lectura, separada del Redis que guarda datos que no se pueden perder, y qué pasa con las lecturas cuando la caché cae.

Las decisiones marcadas **(equipo)** las tomó el usuario durante el diseño. Las marcadas **(constructor)** las propuso quien diseña y pueden corregirse.

## 1. Intención

Hoy cada lectura del catálogo y de las gráficas llega a PostgreSQL, y el estado de cuenta de 30 s vive en la memoria de cada proceso, así que las dos réplicas de `gateway-auth` no lo comparten. La rama agrega una caché de lectura en Redis para bajar la carga sobre Postgres y la latencia de las lecturas frecuentes, sin cambiar lo que ve el usuario y sin que una caída de la caché tumbe nada: si Redis cae, se lee de Postgres y se responde igual.

PostgreSQL sigue siendo la única fuente de verdad. "Poliglota" aquí son dos motores con papeles distintos: Postgres para lo durable, Redis para lo que se puede perder y reconstruir.

## 2. Objetivos

1. **Instancia de caché aparte.** Un servicio `redis-cache` en `compose.yaml`, con `--maxmemory` fijo, `--maxmemory-policy allkeys-lru` y sin persistencia (`--save "" --appendonly no`). El Redis actual (`redis`, con AOF) no se toca: sigue guardando el stream `track_published` y su DLQ, la cola de reproducciones y la revocación. Variable `CACHE_REDIS_URL`, independiente de `REDIS_URL`.
2. **Módulo de caché en `meloxo_common`.** Un `cache.py` con lectura y escritura con timeout corto y breaker simple (como `revocation.py`: tras un fallo se salta la caché unos segundos), y una función `cached(namespace, key, ttl, loader)` que devuelve el valor guardado o llama a `loader` y lo guarda. Nunca lanza por culpa de Redis.
3. **Caché del catálogo** (`catalog-streaming`): `GET /api/songs`, `GET /api/songs/{id}`, `GET /api/artists/{id}` y `GET /api/genres`.
4. **Caché de agregados** (`playback-metrics`): las lecturas de `/api/metrics/*` que salen de los agregados (`top`, `genres`, `plays`, `heatmap`).
5. **Estado de cuenta compartido.** `AuthStateCache` gana un segundo nivel en Redis (`cache:auth:{user_id}`, 30 s) que comparten las réplicas. El nivel de proceso se conserva como respaldo.
6. **Invalidación al escribir** en el catálogo (ver §5).
7. **Verificación.** Pruebas de unidad del módulo y de cada caché; un escenario nuevo en `demo/` (con `redis-cache` detenido todo responde igual, y al volver se vuelve a llenar); y una corrida del escenario 9 de carga antes y después, con los números en las decisiones de la rama.
8. Un `README.md` por carpeta nueva y actualización de los existentes, del README raíz, de `docs/ramas.md`, del PRD (dueño del dato: la caché no es dueña de nada) y de `CHANGELOG.md`.

## 3. No objetivos y antiobjetivos

**No objetivos**

- MongoDB **(equipo)**: la bitácora de auditoría y los avisos siguen en Postgres. El PRD no cambia en ese punto.
- Cachear contadores de reproducciones: cambian con cada escritura y la cola ya los absorbe.
- Cachear escrituras, el flujo de reproducción, los tickets de streaming o las rutas de administración.
- Un panel de la caché o su métrica de aciertos en el admin. Los aciertos se miden en las pruebas y en la corrida de carga.
- Los pendientes de la rama 05 (`track_hidden`, revisión del DLQ).

**Antiobjetivos: si pasa esto, la rama falló aunque funcione**

- Que el desalojo de la caché toque el stream, la cola o la revocación.
- Que `redis-cache` caído o lento haga fallar o retrasar de forma notable una petición que antes funcionaba.
- Que un usuario vea una pista oculta, borrada o despublicada por culpa de la caché más allá de unos segundos, o que un cambio de rol, bloqueo o cierre de sesión tarde más que hoy en tener efecto.
- Que un usuario reciba datos que le tocan a otro (las claves de las lecturas personales incluyen el usuario y el alcance).
- Que cambie el comportamiento visible de la API sin estar en este documento.

## 4. Decisiones del equipo

| Tema | Decisión |
|---|---|
| MongoDB | **Fuera.** Solo Postgres y Redis. |
| Dónde corre la caché | **Enfoque A:** una instancia de Redis nueva y aparte, con LRU y sin persistencia. Se descartó una sola instancia con `volatile-lru` (el aislamiento dependería de que nadie ponga TTL a una clave durable) y la caché en memoria de proceso (no cruza réplicas). |
| Qué se cachea primero | Lista, detalle de pista, artistas, géneros y agregados de las gráficas. Los contadores de reproducciones quedan fuera. |
| Cómo se mide | Escenario 9 de carga antes y después, y un escenario con `redis-cache` detenido. |

## 5. Decisiones del constructor

| Tema | Decisión | Razón |
|---|---|---|
| Invalidación del catálogo | Un contador de versión `cache:ver:catalog` en `redis-cache`. Las claves lo incluyen (`cache:catalog:{ver}:...`). Escribir en el catálogo hace `INCR`; las claves viejas quedan huérfanas y el LRU las desaloja. | Invalidar por prefijo exigiría `SCAN`, caro y con carreras. Con versión, una escritura invalida toda la lista a la vez, que es lo correcto porque una pista puede aparecer en cualquier página. |
| Qué escrituras suben la versión | Publicar, ocultar, restaurar, editar y borrar pista (composer y admin), crear álbum, editar el perfil de artista, y terminar un lote de importación de Jamendo. Se hace después del commit. | Son los caminos que cambian lo que devuelven las lecturas cacheadas. Lista exacta a cargo del constructor, revisando `service.py`, `publishing.py`, `composer.py` e `import_jobs.py`. |
| Respaldo por TTL | Catálogo: 300 s. Géneros: 300 s. Si una escritura se escapa a la lista de arriba o el `INCR` falla, el dato viejo vive como mucho eso. | Una red de seguridad: la corrección no depende solo de acordarse de invalidar. |
| Agregados | TTL de 15 s, sin invalidación explícita. | Los agregados ya van hasta `MAX_LAG_SECONDS = 30` por detrás de las reproducciones: 15 s más no cambia lo que el usuario puede observar. |
| Claves de lecturas personales | Incluyen `scope`, el id del usuario cuando es `me`, y todos los parámetros (`days`, `tz`, `group`, `kind`, `limit`). Los parámetros se normalizan y se resumen con hash. | Evita mezclar datos de dos usuarios o de dos zonas horarias. |
| Qué se guarda | El cuerpo JSON ya serializado, no objetos de SQLAlchemy. | Es lo que se devuelve y no depende del ORM. |
| Estado de cuenta | Nivel 1 en proceso (como hoy), nivel 2 en Redis. Lectura: nivel 1, luego nivel 2, luego el origen. Si el origen cae se conserva la regla actual de usar el último estado sin importar su edad. La revocación sigue consultándose aparte y manda sobre la caché, como hoy. | Mantiene el comportamiento actual y solo ahorra viajes al origen. `users-playlists` sigue sin caché (`ttl=0`). |
| Timeouts | Lectura 0,2 s, escritura 0,3 s; tras un fallo se salta la caché 5 s. | Coherente con `revocation.py`. Con la caché caída el costo es un timeout cada 5 s, no uno por petición. |
| Memoria | `--maxmemory 64mb`. | Sobra para el volumen del demo y obliga al LRU a trabajar si se llena. |
| Despliegue | `redis-cache` en `compose.yaml` y `compose.demo.yaml`, con healthcheck. Los servicios arrancan sin esperarlo (`depends_on` sin condición de salud) y toleran que falte. | La caché es opcional por diseño. |
| Sin `CACHE_REDIS_URL` | No hay caché y todo funciona igual, como pasa hoy con `REDIS_URL`. | Las pruebas existentes no cambian. |
| Nombre de la rama | `06-poliglota`, el que ya usan el README y `docs/ramas.md`. | Siguen siendo dos motores con papeles distintos. Cambiarlo es trivial si prefieres otro. |

## 6. Riesgos conocidos

- **Carrera entre lectura y escritura.** Una lectura que empezó antes de una escritura puede guardar un valor viejo bajo la versión nueva si lee la versión antes de cargar. Se evita leyendo la versión una sola vez al inicio de la petición y usándola en la clave: lo viejo se guarda bajo la versión vieja, que ya no se consulta.
- **Rebote al llenar la caché en frío.** Tras reiniciar `redis-cache`, todas las lecturas van a Postgres a la vez. Con este volumen es aceptable; no se agrega protección contra estampida.
- **Estado de cuenta ligeramente más viejo entre réplicas.** Hoy cada réplica refresca por su cuenta; con el nivel compartido el dato puede tener hasta 30 s sin importar cuál lo guardó. No empeora el máximo actual. La revocación inmediata no se ve afectada.

## 7. Lo que queda al constructor

Nombres de claves y de módulos, la función exacta de normalización de parámetros, el texto de los logs, el formato de las pruebas, la lista final de escrituras que suben la versión (§5), y cómo reparte el tiempo entre los objetivos 3 a 5. El objetivo 5 es el de menor prioridad: si resulta más invasivo de lo esperado, se deja para el final y se avisa.
