# Guion de la presentación MELOXO

Tiempo estimado a 150 palabras por minuto, calculado con el texto de las notas del orador de cada lámina. El video de demostración de la lámina 5 (unos 24 s) corre mientras se narra, así que no suma tiempo: el tiempo real total es de unos 14:30.

| Orador | Láminas | Palabras | Tiempo estimado |
|---|---|---|---|
| Lado A·1 · Christian Franco Ramírez | 1–5 | 557 | 3:43 |
| Lado A·2 · Miriam Amisadai López Hernández | 6–8 | 476 | 3:10 |
| Lado B·1 · Erick Nava Santiago | 9–12 | 584 | 3:54 |
| Lado B·2 · Brent Armando Pérez Paitán | 13–16 | 541 | 3:36 |
| **Total** | 1–16 | 2158 | **14:23** |

El total (14:23) queda dentro del rango objetivo de 14 a 15 minutos, con poco margen; no se añadió relleno. Conviene ensayar con cronómetro.

## Lado A·1 · Christian Franco Ramírez

Láminas 1–5. Tiempo objetivo: 3:43.

### Lámina 1 · Portada (0:32)

Buenas tardes a todos, somos el equipo FLDSMDFR: Miriam López, Erick Nava, Brent Pérez y yo, Christian Franco, de Sistemas Distribuidos. Les presentamos MELOXO, tu casetera de confianza. MELOXO es un servicio de streaming musical construido alrededor del casete compartido: aquí la música no se busca ni se recomienda, se descubre porque alguien te la regala. Hoy les vamos a contar cómo MELOXO pasó de ser un monolito a un sistema distribuido, y qué decisiones y mediciones nos llevaron ahí.

### Lámina 2 · El monolito (0:45)

Empecemos por el problema. La primera versión de MELOXO fue un monolito: una sola aplicación, un solo proceso y una sola base de datos. Ahí conviven tres cargas muy distintas. Primero, el login y las listas, que son consultas cortas y frecuentes. Segundo, el audio continuo, que mantiene conexiones largas mientras alguien escucha. Y tercero, la telemetría, que registra cada reproducción. Las tres compiten por los mismos recursos: si la telemetría se satura, el audio lo siente. Y lo peor es el punto único de falla: si cae el servidor o cae la base de datos, cae todo, incluso la música que alguien estaba escuchando. Eso es justo lo que queremos evitar.

### Lámina 3 · El casete compartido (0:47)

Entonces, ¿qué es MELOXO? Es un servicio de streaming musical construido alrededor del casete compartido. Un casete tiene hasta 12 pistas repartidas en dos lados, el lado A y el lado B, y se arma entre hasta 8 miembros. Cada pista puede llevar una dedicatoria de hasta 140 caracteres, como la nota que le dejarías a un amigo en un casete de verdad. Y para sumar gente no hay buscador de personas: se invita por enlace. Aquí a la izquierda vemos un casete real de la app, con sus dos lados y sus dedicatorias. Lo importante: no hay feed, no hay seguidores de personas y no hay likes. Solo se siguen artistas; la música se comparte en pequeño.

### Lámina 4 · Tres roles y objetivo AP (0:47)

MELOXO tiene tres roles. El Oyente es el usuario base: arma casetes con sus amigos, deja dedicatorias y sigue artistas. El Compositor es un oyente aprobado que publica su propia música: sube un MP3 de hasta 15 megas, con portada de hasta 2, y puede programar la fecha de publicación. Y el Administrador aprueba a los compositores, revisa la auditoría, importa el catálogo de Jamendo y consulta las métricas y la salud del sistema. Abajo a la derecha está el objetivo de disponibilidad que guía todo el diseño: elegimos AP, es decir, que la música se pueda reproducir aunque fallen las métricas, los avisos o Jamendo. El reproductor que ven es el que no debe dejar de sonar.

### Lámina 5 · Demo en video (0:52)

_El video de unos 24 s corre mientras se narra esta lámina; no suma tiempo._

Ahora, en lugar de explicarlo, vamos a verlo. Este es un video corto, de unos 25 segundos, grabado sobre la aplicación real levantada con docker compose. Les pido que se fijen en tres momentos. Primero, cómo se crea un casete nuevo: le ponemos el nombre, Para el profe, y la etiqueta del casete se va escribiendo sola. Segundo, cómo se agregan dos pistas, cada una con su dedicatoria, y cómo el casete pasa a mostrar sus dos pistas en el lado A. Y tercero, al final, el reproductor sonando: la pista actual aparece en el panel de la derecha y en la barra de abajo. Mientras corre el video lo narramos. Después de la demo, Miriam les explica cómo está construido todo esto por dentro: la arquitectura de contenedores.

## Lado A·2 · Miriam Amisadai López Hernández

Láminas 6–8. Tiempo objetivo: 3:10.

### Lámina 6 · Nueve contenedores (1:05)

Gracias, Christian. Ahora veamos cómo está construido todo esto por dentro. MELOXO corre en nueve contenedores de larga vida con Docker Compose. Arriba está el edge: nginx es la entrada única; hacia fuera solo entra nginx, y en local también se publica PostgreSQL para las pruebas. Para cada petición a la API, nginx le consulta a gateway-auth con auth_request, que valida el token y el rol y no tiene base de datos; después reparte por ruta a users-playlists, a las dos réplicas de catalog-streaming o a playback-metrics. Entre servicios hablamos HTTP por rutas internas: se consultan unos a otros. Abajo están los datos. PostgreSQL, con una base y un rol por servicio. Redis, durable, con dos Redis Streams: playbacks, de catalog-streaming a playback-metrics, y track_published, de catalog-streaming a users-playlists; además guarda la revocación de sesiones. Y redis-cache, aparte con desalojo LRU y sin persistencia, que usan catalog-streaming, playback-metrics y gateway-auth. El stack: Python 3.12, FastAPI, PostgreSQL 16, Redis, React 18 y Docker Compose.

### Lámina 7 · Monolito contra tres servicios (1:02)

Separar el monolito en servicios no fue gratis, así que lo medimos. Hicimos la misma prueba de carga sobre el monolito y sobre los tres servicios, en la misma computadora, con 50 usuarios simultáneos. Estas son las medianas y los percentiles 95, en milisegundos. El primer byte de audio pasó de 12 y 39 a 9 y 20. GET /api/songs pasó de 36 y 71 a 12 y 26: el catálogo ya no compite con el resto por el mismo proceso. Pero fíjense en la fila de abajo: en GET /api/playlists, la mediana sube de 27 a 31 milisegundos, probablemente por el salto HTTP extra, porque ahora la lista le pide las pistas al servicio de catálogo. Es una inferencia nuestra, no lo aislamos. Lo decimos tal cual: ahí la separación parece costar. Eso sí, el p95 baja de 66 a 55, así que las peores peticiones mejoran. Los tres umbrales de latencia se siguen cumpliendo.

### Lámina 8 · Failover con nginx (1:03)

Aquí está la pieza que protege a todo lo demás: nginx en el borde. Cada petición pasa primero por auth_request, que valida el token JWT antes de llegar a cualquier servicio; si el token no sirve, ni siquiera entra. Detrás del borde tenemos dos réplicas del servicio de catálogo y streaming, y nginx reparte la carga entre ellas. Para comprobar que esto sirve, hicimos una prueba de carga y a mitad de ella apagamos una de las réplicas. Resultado: 0 de 293 peticiones fallaron; los usuarios no notaron nada. Tiene un precio, claro: verificar el token en cada petición cuesta alrededor de 3 milisegundos en p50. Así, GET /api/songs queda en 15 milisegundos en p50 y 34 en p95: ya con auth_request, frente a los 12 y 26 de la lámina anterior, sumando esos 3 ms de auth_request en p50. Para nosotros, ese costo vale la tolerancia a fallos. Erick nos cuenta qué pasa cuando algo falla.

## Lado B·1 · Erick Nava Santiago

Láminas 9–12. Tiempo objetivo: 3:54.

### Lámina 9 · Apertura del lado B (0:45)

Gracias, Miriam. Hasta aquí vimos cómo MELOXO se reparte en servicios y y cuánto cuesta. Ahora damos vuelta al casete: en el lado B van las canciones difíciles, lo que pasa cuando algo falla. Soy Erick Nava y les voy a contar tres cosas. Primero, cómo un servicio caído no arrastra a los demás, con timeouts, reintentos y un circuit breaker. Segundo, cómo no perdemos reproducciones cuando playback-metrics se cae, y cómo cerramos una sesión en el mismo instante en que cambia el rol. Y tercero, cómo los avisos de lanzamientos siguen funcionando aunque catálogo no responda, gracias a la mensajería con Redis Streams. Todo esto lo medimos, así que vienen cifras.

### Lámina 10 · Circuit breaker (0:56)

Empecemos por la primera línea de defensa. Cada llamada entre servicios espera como máximo 1,5 segundos la lectura, y las lecturas se reintentan dos veces, con esperas de 200 y 400 milisegundos. Pero reintentar contra un servicio caído solo empeora las cosas, así que cada cliente lleva un circuit breaker con tres estados. Cerrado: las llamadas pasan. Si acumula cinco fallos en 30 segundos, se abre: ya no llama y falla de inmediato. A los 15 segundos pasa a semiabierto y deja pasar una sola llamada de prueba: si sale bien, se cierra; si falla, vuelve a abrirse. Lo comprobamos congelando catálogo: la primera llamada tardó 5,1 segundos, y con el breaker abierto la respuesta tardó 17 milisegundos. Un detalle honesto: el breaker vive en la memoria de cada réplica, así que con dos réplicas cada una abre por su cuenta.

### Lámina 11 · Cola de reproducciones y revocación (1:05)

Ahora dos casos donde antes algo dependía de una espera. El primero, las reproducciones. Cuando playback-metrics está caído, POST /api/playbacks no falla: catálogo responde 202 y deja la reproducción en una cola de Redis Streams. Antes dependíamos de que el navegador reintentara, y si se cerraba la pestaña, se perdía. En la prueba detuvimos playback-metrics y hicimos tres reproducciones: las tres respondieron 202 y, al volver el servicio, se aplicaron las tres sin duplicar. Incluso con Redis reiniciado y 20 eventos pendientes, se aplicaron exactamente los 20. El segundo caso, la revocación de sesión. Antes, si un administrador cambiaba un rol o suspendía una cuenta, el token anterior podía seguir valiendo hasta 30 segundos por la caché. Ahora la revocación vive en Redis: el token anterior tarda 0,04 segundos en dar 401. Y un evento de reproducción se ve en el historial con una mediana de 0,033 segundos y un máximo de 0,07. La saga con estados la dejamos fuera a propósito.

### Lámina 12 · Outbox (1:08)

Cerramos con mensajería. Cuando se publica una pista, quienes siguen al artista reciben un aviso, y antes eso dependía de que catálogo respondiera. Ahora catálogo escribe la pista y el evento track_published en la misma transacción: es el patrón outbox. Un relevo, cada 2 segundos, lee los eventos sin relevar y los publica en Redis Streams; solo después los marca como relevados. Users-playlists consume de forma idempotente: la clave es el identificador de la pista, así que un evento repetido no cambia nada. Y si un mensaje falla, tras 5 intentos va a la cola de mensajes muertos, sin atascar a los demás. El resultado: 132 eventos relevados y 0 pendientes; de ellos, 101 llegaron como avisos, porque las pistas de Jamendo, ocultas o borradas se marcan sin publicar. Y los avisos ya no dependen de catálogo: con catálogo caído responden completos. Queda pendiente track_hidden: una pista que se oculta después de publicarse sigue apareciendo en los avisos ya guardados. Brent cierra con la caché y lo que aprendimos.

## Lado B·2 · Brent Armando Pérez Paitán

Láminas 13–16. Tiempo objetivo: 3:36.

### Lámina 13 · Caché separada (1:02)

Gracias, Erick. Yo soy Brent Pérez y cierro el lado B con la última rama, la 06: una caché de lectura. Es redis-cache, una instancia de Redis aparte del Redis durable. Tiene 64 megas, desalojo LRU y ninguna persistencia, así que sacar lo menos usado nunca toca las colas ni la revocación de sesiones. Y nada espera a la caché: si cae o se pone lenta, las lecturas van a PostgreSQL y responden igual. Con ella, GET /api/songs pasó de una mediana de 38 milisegundos a 13, y el percentil 95 de 70 a 28. En las gráficas, el top de métricas bajó de 31,6 a 7,1 milisegundos. Dos advertencias. El top lo medimos con 300 lecturas seguidas del administrador, no con 50 clientes. Y esos 38 milisegundos sin caché son más lentos que los 15 de la rama 03: no investigamos por qué, así que solo comparamos corridas hechas en las mismas condiciones.

### Lámina 14 · Prueba de carga (0:58)

Para ver si aguantaba, usamos Locust: 50 clientes durante 2 minutos, primero sin redis-cache y luego con ella, con los mismos parámetros y sin tocar nada más. Sin caché fueron 5373 peticiones, con caché 5203, y en las dos corridas cero fallos. Con la caché, redis-cache terminó con 1368 aciertos, 1189 fallos y ninguna clave desalojada. Y ahora la parte honesta. La búsqueda de Locust usa solo seis palabras distintas, así que casi todas sus búsquedas son aciertos de caché. Además, el contador de 1368 aciertos y 1189 fallos incluye otras claves: los fallos incluyen las lecturas de versión y de estado de cuenta, no solo la lista. Con consultas más variadas la mejora sería menor: por eso decimos que estas cifras son optimistas. Las playlists y el primer byte de audio no cambian, porque esas rutas no se cachean; la diferencia entre corridas es ruido.

### Lámina 15 · Aprendizajes y pendientes (0:52)

Nos quedan tres aprendizajes. Primero, la caché va en su propia instancia: con límite de memoria y desalojo LRU, y sin tocar el Redis que lleva las colas y la revocación. Segundo, nada debe esperar a una optimización: ningún servicio la declara como dependencia y, sin ella, todo responde igual desde PostgreSQL. Y tercero, medir bien es comparar dentro de las mismas condiciones, y decir lo que no sabemos. También hay cosas que dejamos fuera. La saga con estados, que hoy se resuelve con auditoría antes del commit y rollback. MongoDB, que el equipo descartó: todo sigue en PostgreSQL, una base por servicio. Los eventos track_hidden y track_restored, de modo que una pista oculta puede seguir en avisos ya guardados. Y la sala de escucha sincronizada, que no tuvo rama.

### Lámina 16 · Cierre y preguntas (0:44)

Con esto cerramos el casete. Empezamos con un monolito donde todo competía, y terminamos con servicios que se reparten el trabajo: una base por servicio, réplicas que se pueden caer sin que nadie lo note, un circuit breaker, colas que no pierden reproducciones, una revocación de sesión de 0,04 segundos y una caché que baja las lecturas de 38 a 13 milisegundos. Cada cifra que mostramos sale de la documentación del repositorio. Si quieren revisar el código, las decisiones o repetir las pruebas, el repositorio es público: escaneen el código QR o usen la dirección que está debajo. Muchas gracias por su atención. Ahora los escuchamos: estamos listos para sus preguntas.
