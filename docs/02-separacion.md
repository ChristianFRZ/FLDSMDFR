# Etapa 02 · Separación

| Servicio | Datos y responsabilidades |
| --- | --- |
| users-playlists-service | Base `users_playlists`. Cuentas, roles vigentes, auditoría, playlists, casetes, favoritos y avisos. Crea al primer administrador. |
| catalog-streaming-service | Base `catalog` y volumen `media`. Búsqueda, artista, cargas, audio Range, cliente Jamendo y publicación programada. |
| playback-metrics-service | Base `playbacks`. Historial, deduplicación, contadores, agregados, reportes y métricas de latencia. |

El navegador conserva un solo origen. Nginx sirve la SPA, la especificación OpenAPI pública y las rutas de la API bajo `/api/`. Las rutas internas requieren un secreto y los servicios de negocio solo escuchan en la red de Compose. La autenticación y los permisos se verifican en el servicio que atiende la operación. Catálogo y Métricas validan el JWT y consultan el rol y estado actuales en Usuarios.

Playlists y casetes obtienen metadatos por lote. Al caer Catálogo, las playlists pueden mostrar su copia guardada. Las métricas de compositor consultan sus canciones en Catálogo y los conteos de inclusión en Usuarios. Los avisos siguen calculándose al leer. Catálogo confirma cada moderación o importación junto con un registro pendiente de auditoría; lo entrega a Usuarios con un UUID estable. Un acuse perdido permite repetir la entrega sin duplicar la bitácora.

## Actualizar una instalación existente

1. Conserva el directorio y nombre del proyecto Compose, `POSTGRES_PASSWORD`, las claves de sesión y los volúmenes `pgdata` y `media`. Añade a `.env` tres contraseñas distintas generadas con `openssl rand -hex 32`: `USERS_DB_PASSWORD`, `CATALOG_DB_PASSWORD` y `PLAYBACK_DB_PASSWORD`. Verifica también `CATALOG_INTERNAL_TOKEN`.
2. Programa el corte. Detén los escritores antiguos, incluyendo semillas y procesos de desarrollo que usen la base `meloxo`. Con PostgreSQL aún en marcha, guarda una copia de la base y respalda el volumen de medios. Por ejemplo, en la instalación del incremento 1:

   ```sh
   docker compose stop app catalog-streaming-service
   docker compose exec -T postgres pg_dump -U meloxo -d meloxo -Fc > "$HOME/meloxo-antes-de-separar.dump"
   ```

3. Con los escritores detenidos ejecuta:

   ```sh
   docker compose config --quiet
   docker compose up -d --build --wait
   docker compose ps -a
   docker compose logs migrate
   ```

4. El proceso `migrate` crea los propietarios y las bases, limita la conexión a cada base y aplica sus revisiones Alembic. Copia desde una instantánea de lectura de la base original (revisión 0011 o 0012), en orden de dependencias. Conserva UUID, hashes, tokens, cursor, eventos y secuencia de reproducción. Verifica el número de filas de cada copia. La marca de finalización se confirma junto con los datos de cada destino; repetir el arranque omite los destinos ya copiados. La fuente conserva sus filas y el volumen de medios se monta en Catálogo. Una instalación vacía ejecuta el mismo comando.
5. Antes de abrir el acceso, comprueba una sesión existente, una playlist, el audio local y el historial. Con una cuenta administrativa configurada en `.env`, puedes verificar las tres bases y los permisos reales:

   ```sh
   python3 demo/check_separation.py
   ```

Si la copia se interrumpe, mantén detenidos los escritores antiguos, revisa los logs y vuelve a ejecutar el arranque. Para volver al despliegue anterior antes de aceptar nuevas escrituras, detén la versión separada y levanta la anterior con la base original y el mismo volumen de medios. Una vez recibidas escrituras en las nuevas bases, volver a la anterior exige reconciliar esos cambios.

## Operación

- `docker compose restart catalog-streaming-service` reinicia únicamente el catálogo. Los demás procesos continúan ejecutándose.
- `docker compose run --rm seed activity` genera actividad y audio sintético sin requerir una clave de Jamendo. `seed all` incluye la importación externa. La semilla es una tarea administrativa con credenciales de los tres dominios.
- `docker compose down` detiene los contenedores conservando los volúmenes.
- `app.main:app` sigue disponible para desarrollo monolítico y pruebas de regresión. Compose arranca los tres puntos de entrada independientes.

El siguiente hito del PRD es `03-gateway-balanceo`, con políticas en el borde y réplicas de catálogo. El detalle histórico del primer incremento está en [su informe](02-separacion-incremento-1.md).

## Verificación de cierre

Se probaron dos proyectos Docker desechables con PostgreSQL 16. Uno arrancó con volúmenes vacíos y el otro con datos creados por la versión del incremento 1.

| Verificación | Resultado |
| --- | --- |
| Migración y segundo arranque | Se conservaron una sesión anterior, su pista MP3, playlist, casete e historial. El audio local respondió 206 con Range. |
| Permisos de las bases | Se comprobó desde cada proceso que su usuario puede conectarse únicamente a su propia base entre las cuatro bases de MELOXO, incluida la antigua. |
| Reinicios individuales | Con Catálogo detenido se leyó la playlist en modo degradado y agregar una pista respondió 503. Con Métricas detenido siguió el audio. Con Usuarios detenido se rechazaron nuevas autorizaciones de streaming. Los flujos se recuperaron tras cada arranque. |
| Contratos | Se verificaron la auditoría de moderación, el bloqueo público de rutas internas, OpenAPI y la navegación directa a una ruta de React. |
| Semilla | Se generaron 40 000 reproducciones, 24 casetes y 30 playlists en el despliegue separado. |
| Regresión | Pasaron 424 pruebas de backend y 143 de frontend. Las 15 pruebas de navegador pasaron contra la SPA compilada servida en el puerto 8080 con Brave (Chromium) en modo sin ventana. |
| Demos | Pasaron los escenarios 3 a 8. La caída de Jamendo se ensayó con una pista externa ficticia; no se utilizó una clave real para importar desde Jamendo. |
