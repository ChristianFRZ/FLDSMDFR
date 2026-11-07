# Decisiones de 01-monolito

Lo que se decidió durante la construcción sin preguntarlo al equipo, con lo que cuesta si fue un error, y lo que quedó pendiente. El diseño está en [`../specs/`](../specs/README.md) y el plan en [`../plans/`](../plans/README.md).

## Decisiones

- **Tarea 3:** la carrera de dos admins degradándose acepta 403 o 409 para el perdedor, no solo 409 — el perdedor ya no es admin y ambos códigos son correctos; la garantía real es que queda un admin — costo si es error: ninguno funcional.
- **Tarea 7:** los MP3/JPG de prueba se generan en tests/media.py en vez de archivos en tests/fixtures — menos binarios en el repo — costo si es error: ninguno.
- **Tarea 8:** en vez de solo observar si el token from caduca, el proxy renueva la URL ante 4xx y reintenta una vez — funciona caduque o no, y comprobarlo exigía esperar días — costo si es error: una petición extra a la API en pistas con URL vencida.
- **Tarea 8:** las migraciones reales son 0001..0005 hasta aquí, no la numeración del plan — numeración secuencial real — costo si es error: ninguno.
- **Tarea 9:** migración 0006 en vez de 0005 y agregar con catálogo caído responde 503 — sin catálogo no se puede validar la canción ni llenar la caché — costo si es error: quien agrega durante una caída reintenta.
- **Tarea 10:** migración 0007; el modelo ORM se llama Playback para no chocar con el dataclass público PlaybackEvent; listened_seconds tiene tope de 86400 y canción inexistente da 404 — el brief no lo decía y sin tope un valor enorme daba 500 — costo si es error: un renombre.
- **Tarea 11:** published_since devuelve PublishedRelease(song, published_at) en vez de SongSummary, y el aviso solo cuenta lo publicado después de seguir — sin esto, seguir a un artista llenaba los avisos con todo su catálogo viejo — costo si es error: quien sigue tarde no ve avisos antiguos, aunque sí aparecen en GET /api/releases.
- **Tarea 11:** GET /api/releases devuelve {scheduled, published, degraded} con 12 recientes — Inicio necesita lanzamientos ya vistos, no solo los no leídos — costo si es error: un campo de más.
- **Tarea 12:** tape_tracks lleva metadata_cache, que el brief no incluía — sin ella una pista borrada no podía conservar título y lugar como pide el diseño — costo si es error: una columna JSONB.
- **Tarea 12:** se agregan POST /api/tapes/claims/{invite_id}/join y /dismiss — el token se guarda como hash, así que la lista de pendientes no puede devolverlo y sin estas rutas Inicio no podría aceptar — costo si es error: dos rutas más.
- **Tarea 12:** version sube solo al cambiar pistas, no al unirse alguien ni al renombrar — si no, reordenar fallaría sin motivo — costo si es error: ninguno visible.
- **Tarea 12:** la misma canción dos veces en un casete da 409; PATCH del casete es solo del creador; invitar lo hace cualquier miembro; varios usos exigen expiración (F4.2) — el PRD no decide los dos primeros — costo si es error: quitar una restricción.
- **Tarea 12:** se agrega tests/test_pool.py y se suelta la conexión antes de llamar a otro módulo — cada petición retenía una conexión mientras abría otra, y con carga el pool podía bloquearse — costo si es error: un commit más por lectura.
- **Tarea 13:** refresh_aggregates corta el lote en el primer evento de menos de 1 s — seq se asigna al insertar y un evento confirmado tarde se perdería para siempre — costo si es error: las gráficas van 1 s más atrás, dentro de F3.4.
- **Tarea 13:** cada reproducción cuenta solo en el primer género de la pista — con una fila por género el top sumaría doble — costo si es error: la distribución ignora géneros secundarios.
- **Tarea 13:** horas guardadas en UTC y plays/heatmap reciben tz del navegador — evita suponer una zona fija — costo si es error: ninguno.
- **Tarea 13:** se agrega catalog.public.jamendo_status, reporte top-artists, y los CSV neutralizan fórmulas — health no puede importar jamendo.py y los títulos vienen de terceros — costo si es error: ninguno.
- **Tarea 14:** token de acceso en memoria y refresh token en localStorage — una SPA sin cookies necesita sobrevivir a una recarga, y el refresh rota en cada uso — costo si es error: un XSS podría leer el refresh; se migraría a cookie httpOnly.
- **Tarea 14:** las rutas de la SPA van en inglés (/tapes/:id, /invite/:token), como pide "código y rutas en inglés" — el ejemplo /casetes/123 del brief solo prueba el respaldo a index.html — costo si es error: renombrar rutas.
- **Tarea 15:** se agregan recovery.ts con recovery.test.ts, y GET /api/favorites/ids y /api/follows/ids — <audio> no expone el status HTTP, y el corazón del reproductor necesita saber si cada pista es favorita — costo si es error: una petición de un byte al fallar.
- **Tarea 15:** si el POST falló, el reintento lleva el progreso más nuevo y no se manda PATCH aparte — menos peticiones, mismo dato — costo si es error: ninguno.
- **Tarea 16:** se agregan AddSong, Cover, NoticesBell, SearchBox y NotFound, y NowPlaying queda como player/NowPanel.tsx — agregar a casete o playlist se usa desde varias pantallas; sin ruta 404 la app quedaba en blanco — costo si es error: ninguno.
- **Tarea 17:** GET /api/tapes devuelve max_tracks y la pantalla usa ese valor — el límite es configurable y no debe vivir en el frontend — costo si es error: ninguno.
- **Tarea 18:** la paleta de gráficas usa tonos derivados de la marca (#F0428A,#B08600,#009E8F,#6172FF) — los puros fallan la banda de luminosidad del validador sobre el panel oscuro — costo si es error: cambiar cuatro valores en charts/index.ts.
- **Tarea 18:** upload() usa XMLHttpRequest y renueva el token antes de subir — fetch no informa progreso de subida — costo si es error: una función en api/client.ts.
- **Tarea 18:** ChartCard recibe url, columns, rows, chart y stat en vez de source y render — la tabla accesible necesita columnas y filas explícitas — costo si es error: ajustar firmas en Stats.
- **Tarea 18:** retention_for_songs cuenta el final con int(duration) — encontrado en navegador: el progreso va en segundos enteros y una pista de 40.05 s nunca llegaba al 100 % — costo si es error: una escucha a menos de 1 s del final cuenta como completa.
- **Tarea 18:** fillDays completa con ceros los días sin actividad en el cliente — sin eso, un solo día no dibujaba línea y días lejanos se unían — costo si es error: una función en definitions.ts.
- **Tarea 18:** el enlace a /composer en el menú se agrega en la tarea 19 — ahí está la prueba de menú según rol — costo si es error: ninguno.
- **Tarea 19:** se agregan AdminLayout.tsx y shared.tsx en pages/admin — navegación y paginación se repiten en seis vistas — costo si es error: ninguno.
- **Tarea 19:** /api/admin/composer-requests devuelve user_name y user_email — con solo user_id el administrador no sabe a quién aprueba — costo si es error: dos campos más en la respuesta.
- **Tarea 19:** se agrega el reporte plays-hourly — F7.4 pide exportar lo visible y la gráfica por hora no tenía CSV — costo si es error: un caso más en _report_rows.
- **Tarea 19:** la latencia se muestra como p50/p95 de streaming más barras de errores por módulo — el PRD pide eso y seis módulos por dos métricas rompen el máximo de cuatro series — costo si es error: el detalle de otros módulos solo está en el CSV.
- **Tarea 19:** género usa barras y no dona — el PRD permite ambas y las barras comparan mejor; catálogo por fuente sí usa dona — costo si es error: cambiar el tipo de una gráfica.
- **Tarea 19:** /stats muestra lo que escucha cada persona en todos los roles, con enlace a la vista propia del rol — el Compositor y el Administrador también escuchan — costo si es error: ajustar una página.
- **Tarea 19:** la paleta se revalidó sobre #2E2C35 porque ese es el fondo real de las tarjetas — pasa todas las revisiones — costo si es error: ninguno.
- **Tarea 20:** las pestañas reutilizan el mismo <nav> de la barra lateral con display: contents — evita duplicar enlaces; el orden de Tab recorre las pestañas antes del contenido, y el enlace Saltar al contenido lo compensa — costo si es error: mover el nav en el DOM.
- **Tarea 20:** la hoja del reproductor no incluye pantalla completa — la hoja ya ocupa toda la pantalla — costo si es error: agregar un botón.
- **Tarea 20:** la API de salud guarda el estado de Jamendo 60 s y limita el ping a 1.5 s (delayed si tarda) — medido en 2 a 9 s por consulta, incumplía F7.2 y gastaba la API externa cada 15 s por panel abierto — costo si es error: el estado puede tener hasta un minuto de atraso.
- **Tarea 20:** las tablas de administración pasan a filas apiladas en teléfono — con scroll lateral las acciones quedaban fuera de la pantalla — costo si es error: en ese ancho se pierde la semántica de tabla.
- **Tarea 20:** las líneas usan interpolación monótona — la curva libre subía más allá del dato real — costo si es error: ninguno.
- **Tarea 20:** se agregan @axe-core/playwright, e2e/setup.ts, helpers.ts y fixtures/tone.mp3 — las pruebas no deben depender de lo que haya en la base — costo si es error: cada corrida deja dos usuarios, una pista y un casete en la base local.
- **Tarea 21:** cada módulo tiene demo.py con su inserción y limpieza, expuesto por public.py — el brief pedía bulk_insert_demo_* en public.py; separarlo deja fuera del camino normal el código que solo usa la demo — costo si es error: mover funciones.
- **Tarea 21:** la latencia no se simula — es una medición real y simularla engañaría en la demo; la gráfica se llena con el uso, y la tarea 22 genera tráfico — costo si es error: la gráfica sale vacía si nadie ha usado la app en la última hora.
- **Tarea 21:** los duplicados demo van en un contador aparte (duplicates_demo) que la métrica suma — así clear lo quita sin tocar el contador real — costo si es error: ninguno.
- **Tarea 21:** sin clave fija para las cuentas demo; se usa DEMO_PASSWORD o una al azar impresa al terminar — incluyen administradores — costo si es error: hay que leer la clave en la salida del comando.
- **Tarea 21:** activity borra y recrea lo simulado para ser idempotente — más simple que comparar fila por fila — costo si es error: los ids demo cambian en cada corrida y se pierden casetes hechos a mano con cuentas demo.
- **Tarea 21:** el importador reintenta páginas vacías hasta 6 veces — medido: Jamendo devuelve vacío al azar cerca del 40 % de las veces, y antes eso terminaba el género sin aviso; también afectaba al Administrador — costo si es error: un género agotado cuesta 5 peticiones y 5 s más.
- **Tarea 21:** la semilla repite la importación si la anterior trajo menos del 90 % de lo pedido — evita quedarse con un catálogo corto — costo si es error: más peticiones a Jamendo.
- **Tarea 22:** el plan corre los escenarios con `python`, y este equipo solo tiene `python3` — demo/README.md usa python3 y common.py solo usa biblioteca estándar — si falla: cambiar una palabra en el README.
- **Tarea 22:** JAMENDO_API_URL no corta el audio, porque el proxy abre audio_url directo — compose.demo.yaml también apunta prod-1.storage.jamendo.com a 192.0.2.1 con extra_hosts — si Jamendo usa otro host de audio, el escenario 3 fallaría de forma visible y habría que agregarlo.
- **Tarea 22:** los escenarios 3 y 8 levantan el overlay por sí mismos, con puerto libre, y devuelven el stack al 8080 — así el bucle del plan corre sin pasos manuales — si falla: el contenedor app se recrea mientras alguien lo usa (avisado en el README).
- **Tarea 22:** el escenario 8 vence las pistas con SQL con la app apagada, porque la API rechaza fechas pasadas — no prueba que las dos réplicas consultaran en el mismo instante, solo el resultado — la concurrencia real la cubren las pruebas de publish_due_tracks.
- **Tarea 22:** el escenario 6 suspende a los demás administradores y los reactiva en finally, porque la semilla crea varios — si el proceso muere a mitad quedan suspendidos y hay que reactivarlos a mano.
- **Tarea 22:** las cuentas de escenarios y de carga usan @escenarios.meloxo.dev y quedan en la base, porque no hay API para borrar usuarios y seed clear filtra por is_demo — cuesta filas sobrantes en /admin/users, documentado en demo/README.md.
- **Tarea 23:** el locustfile de la tarea 22 cerraba la conexión en el primer byte, y F2.3 habla de clientes en streaming — ahora descargan cada pista completa y se repitió la carga sobre el stack limpio; siguen sin ser 50 conexiones abiertas todo el tiempo, y demo/README.md lo dice — si se quiere una prueba más dura, habrá que pausar la lectura al ritmo del audio.
- **Tarea 23:** el plan espera 0 resultados en git grep JAMENDO_CLIENT_ID=., y da 1: es el propio comando escrito en el plan — falso positivo, el valor real de la llave no está ni en el árbol ni en los mensajes de commit — no cuesta nada.
- **Tarea 23:** test_readmes ignora también meloxo.egg-info y las carpetas ocultas, además de lo que lista el plan; docs/brand tiene README pero no sus subcarpetas de archivos exportados — si falla, una carpeta generada queda sin README.
- **Tarea 23:** se sacó backend/meloxo.egg-info del repositorio, fuera del plan, porque es un artefacto generado — se regenera con pip install -e — no cuesta nada.
- **Tarea 23:** la semilla reporta 2000 pistas importadas y quedan 1789 únicas, porque una pista llega en varios géneros — 1789 cuenta como unas 2,000 y no se cambió el código; el mensaje exagera — si el equipo quiere 2000 únicas, sube per_genre.
- **Revisión final:** aviso "Se perdió la conexión" no apareció en 30 s sin red en Chromium, que no lanza error — el audio retoma solo al volver la red; queda como está — cuesta silencio mientras no hay red.
- **Revisión final:** un stream ya abierto sigue hasta terminar al suspender una cuenta — el ticket nuevo ya se rechaza y una pista dura minutos — cuesta unos minutos de audio.
- **Revisión final:** sin detección de reutilización de refresh tokens — el diseño no lo pide — un token robado vale hasta que se use el legítimo.
- **Revisión final:** dependencias de Python sin fijar — el diseño no lo trata — una versión nueva puede romper una instalación futura.
- **Revisión final:** LoginLimiter crece sin límite en memoria — bajo impacto, se limpia al reiniciar — algo de memoria con muchos correos distintos.
- **Revisión final:** reproducción contada de una pista ya oculta — legítima si se ocultó mientras sonaba — alguna reproducción de más.
- **Revisión final:** Administrador recibe 403 en gráficas de Compositor — coincide con PRD 5.3 — ninguno.
- **Revisión final:** days ignorado con scope=me — decisión comentada en el código — ninguno.
- **Revisión final:** no probado en Firefox ni Safari — el manejo de audio puede variar — queda pendiente de una prueba manual.

## Pendientes menores

- la hoja del reproductor no se cierra deslizando hacia abajo; se cierra con botón y Esc.
- el texto base es de 14 px fijos; respeta el zoom del navegador (probado a 320 px) pero no el tamaño de letra configurado por la persona.
- el buscador de arriba y la pestaña Buscar se repiten en teléfono.
- portada validada solo por sus primeros bytes; un archivo con prefijo JPEG se guarda y se ve rota.
- ensure_artist tiene carrera; peticiones simultáneas de un Compositor nuevo dan 500, la interfaz hoy no las lanza en paralelo.
- entradas extremas dan 500 en vez de 422 (page enorme, NUL en textos).
- se aceptan pistas no publicadas en playlists, favoritas y reproducciones; se pueden inflar reproducciones de una programada.
- playlists.add_song retiene su conexión mientras llama a catálogo.
- con repetir todo y una cola donde todo falla, el reproductor sigue saltando sin fin.
- el ticket de streaming queda en los logs de acceso, válido 1 hora y solo para esa pista.
- los límites de subida se revisan después de recibir todo el cuerpo.
- las reproducciones pendientes en localStorage no están ligadas al usuario.
