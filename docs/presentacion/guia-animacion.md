# Guía de animación en Canva

Canva no importa las animaciones del archivo `meloxo.pptx`. El equipo las aplica a mano siguiendo esta guía.

## Transiciones: aplicar "Disolver" a todas

1. Seleccione una lámina y abra la pestaña de transición entre páginas.
2. Elija **Disolver**.
3. Pulse **Aplicar a todas las páginas**.

## Animación de elementos

Para cada elemento de las tablas: selecciónelo, pulse **Animar**, elija el efecto **Desvanecer** y active **Aparecer al hacer clic**. Respete el orden de la columna "Clic".

Reglas generales:

- Las láminas 1 y 9 no llevan animaciones.
- El título, el fondo y la nota de papel (pista) están visibles desde que entra la lámina.
- Máximo 4 clics por lámina. El orden sigue la narración de las notas; en los diagramas va emisor, flecha y receptor, y las cifras de resultado van al final.
- Cuando un elemento es una tarjeta, se anima el grupo completo, identificado por su texto de encabezado.

## Por lámina

### Lámina 1 · Portada
Sin animaciones.

### Lámina 2 · En un monolito, todo compite
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | Login y listas | Aparecer al hacer clic | Desvanecer |
| 2 | Audio continuo | Aparecer al hacer clic | Desvanecer |
| 3 | Telemetría | Aparecer al hacer clic | Desvanecer |
| 4 | Un solo punto de falla | Aparecer al hacer clic | Desvanecer |

### Lámina 3 · El casete compartido
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | 12 pistas | Aparecer al hacer clic | Desvanecer |
| 2 | 8 miembros | Aparecer al hacer clic | Desvanecer |
| 3 | 140 | Aparecer al hacer clic | Desvanecer |
| 4 | Por enlace | Aparecer al hacer clic | Desvanecer |

### Lámina 4 · Tres roles, una meta: que suene
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | Oyente | Aparecer al hacer clic | Desvanecer |
| 2 | Compositor | Aparecer al hacer clic | Desvanecer |
| 3 | Administrador | Aparecer al hacer clic | Desvanecer |
| 4 | Objetivo AP: se reproduce aunque fallen las métricas, los avisos o Jamendo. | Aparecer al hacer clic | Desvanecer |

### Lámina 5 · Así se ve
Sin animaciones (el video es el protagonista).

### Lámina 6 · Nueve contenedores
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | auth_request (flecha desde edge · nginx hacia gateway-auth) y la tarjeta gateway-auth | Aparecer al hacer clic | Desvanecer |
| 2 | proxy por ruta (flechas hacia users-playlists, catalog-streaming y playback-metrics) y sus tarjetas | Aparecer al hacer clic | Desvanecer |
| 3 | HTTP /internal entre servicios | Aparecer al hacer clic | Desvanecer |
| 4 | Las tres tarjetas de datos: postgres, redis-cache y redis | Aparecer al hacer clic | Desvanecer |

### Lámina 7 · Monolito contra tres servicios
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | Fila Primer byte de audio (12 / 39 y 9 / 20) | Aparecer al hacer clic | Desvanecer |
| 2 | Fila GET /api/songs (36 / 71 y 12 / 26) | Aparecer al hacer clic | Desvanecer |
| 3 | Fila GET /api/playlists/{id} (27 / 66 y 31 / 55) | Aparecer al hacer clic | Desvanecer |
| 4 | En playlists el p50 sube de 27 a 31 ms, probablemente por el salto HTTP extra | Aparecer al hacer clic | Desvanecer |

### Lámina 8 · Si cae una réplica, nadie lo nota
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | catalog-streaming #2 caída (con la ×) | Aparecer al hacer clic | Desvanecer |
| 2 | 0 / 293 | Aparecer al hacer clic | Desvanecer |
| 3 | +3 ms | Aparecer al hacer clic | Desvanecer |
| 4 | 15 / 34 ms | Aparecer al hacer clic | Desvanecer |

### Lámina 9 · Lado B: cuando algo falla
Sin animaciones.

### Lámina 10 · Un breaker que deja de esperar
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | cerrado | Aparecer al hacer clic | Desvanecer |
| 2 | 5 fallos en 30 s (flecha) y abierto | Aparecer al hacer clic | Desvanecer |
| 3 | a los 15 s, una llamada de prueba (flecha) y semiabierto | Aparecer al hacer clic | Desvanecer |
| 4 | 17 ms en vez de 5,1 s (1.ª llamada) | Aparecer al hacer clic | Desvanecer |

### Lámina 11 · Sin perder, sin esperar
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | 202 responde y encola en Redis Streams, con 3 de 3 aplicadas al volver | Aparecer al hacer clic | Desvanecer |
| 2 | 0,04 s es lo que tarda en dar 401 el token anterior | Aparecer al hacer clic | Desvanecer |

### Lámina 12 · El outbox no pierde avisos
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | Paso 1: catalog-streaming | Aparecer al hacer clic | Desvanecer |
| 2 | Paso 2: relevo de catálogo | Aparecer al hacer clic | Desvanecer |
| 3 | Pasos 3 y 4: users-playlists y aviso, junto con la caja "cola de mensajes muertos tras 5 intentos" (en el mismo clic) | Aparecer al hacer clic | Desvanecer |
| 4 | 132 relevados, 0 sin relevar | Aparecer al hacer clic | Desvanecer |

### Lámina 13 · Una caché separada que acelera
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | sin caché 38 ms (GET /api/songs) | Aparecer al hacer clic | Desvanecer |
| 2 | con caché 13 ms (GET /api/songs) | Aparecer al hacer clic | Desvanecer |
| 3 | Barras del top de métricas: sin caché 31,6 ms y con caché 7,1 ms | Aparecer al hacer clic | Desvanecer |
| 4 | La tarjeta 13 / 28 ms junto con Con caché, el top baja de 31,6 a 7,1 ms (en el mismo clic) | Aparecer al hacer clic | Desvanecer |

### Lámina 14 · Aguantó la carga
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | 5373 peticiones sin caché | Aparecer al hacer clic | Desvanecer |
| 2 | 5203 peticiones con caché | Aparecer al hacer clic | Desvanecer |
| 3 | Cifras optimistas | Aparecer al hacer clic | Desvanecer |

### Lámina 15 · Lo que aprendimos y lo que falta
| Clic | Elemento (texto visible) | Inicio | Efecto |
|---|---|---|---|
| 1 | Cada cosa en su Redis (1) | Aparecer al hacer clic | Desvanecer |
| 2 | Nada espera a la caché (2) | Aparecer al hacer clic | Desvanecer |
| 3 | Medir en las mismas condiciones (3) | Aparecer al hacer clic | Desvanecer |
| 4 | Quedó fuera, con sus cuatro tarjetas | Aparecer al hacer clic | Desvanecer |

### Lámina 16 · Gracias
Sin animaciones: el cierre queda visible para las preguntas.
