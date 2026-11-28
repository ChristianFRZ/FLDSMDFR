# Presentación de MELOXO — diseño

## Para qué es

El equipo FLDSMDFR (4 integrantes) expone MELOXO ante el profesor de Sistemas Distribuidos, en unos 15 minutos. Pesa más la arquitectura distribuida y lo medido en cada rama. El producto, el casete compartido, da el contexto. La presentación debe:

- repartir el tiempo de forma pareja, unos 3½ minutos por expositor;
- ser clara y concisa, seguir un orden y resaltar solo las palabras clave;
- verse formal y neutra, con la identidad de la app, y no como una plantilla;
- usar animaciones suaves y solo donde tengan sentido;
- llevar pistas para quien expone, camufladas en el diseño.

**No es** un documento para leer sin narración, ni un pitch comercial.
**Fracasa si** tiene láminas saturadas, animaciones decorativas, cifras sin contexto o pistas que se lean como "ayuda para el orador".

## Restricciones comprobadas

- La presentación vive en **Canva**, en la cuenta del usuario. Se proyecta desde una laptop.
- Canva **no admite .pptx** por la carga de la API. El usuario lo importa arrastrándolo a canva.com; después se edita por la conexión (textos, notas, formas).
- Al importar .pptx, Canva **conserva** Montserrat (negrita), Roboto, Caveat, el fondo de imagen, las formas, las rotaciones, los colores y las notas del orador. Agrega un número de lámina suelto al final de cada nota; se corrige después por la conexión.
- Canva **sustituye** Unbounded por Arimo. Se descartó subirla porque requiere Pro.
- Canva **no importa animaciones** y la conexión no puede crearlas. Las aplica el equipo con "Animar → Aparecer al hacer clic", siguiendo una guía.

## Enfoques considerados

1. **.pptx generado por código, importado a Canva y terminado por la conexión.** Elegido: es el que da más control del diseño.
2. IA de Canva con la estructura aprobada. Descartado: se ve a plantilla y no se pueden fijar las fuentes.
3. Google Slides. Descartado por el usuario a favor de Canva.

## Sistema visual (aprobado en la prueba de 2 láminas)

- **Lienzo:** 16:9 (10 × 5.625 in en pptx, 1920 × 1080 en Canva). Márgenes ≥ 0.5 in. Retícula de 12 columnas. El contenido debe usar el alto disponible, sin huecos grandes.
- **Fondo:** como el de la app (`frontend/src/styles/app.css:7`). Es una imagen `fondo-puntos.png` con tinta `#141317` y puntos `#34323B` cada 32 px, igual en todas las láminas.
- **Colores:**
  - Papel `#F4F1EA` para el texto, Atenuado `#BDB9AF` para lo secundario.
  - Panel `#201F25` con línea `#4A4852`.
  - **Rosa `#FF3D8B`** solo para palabras clave (1–2 por lámina) y la sombra del panel.
  - **Turquesa `#00D1BE`** para las cifras de resultado.
  - **Amarillo `#FFD233`** solo para la cinta de la nota de pista.
  - Cobalto `#4A5CFF` solo en ilustraciones de casete.
- **Tipografías:**
  - Montserrat en negrita para títulos y cifras.
  - Roboto para el cuerpo (es la fuente del sistema que usa la app).
  - Caveat para la nota de pista, las etiquetas de casete y los "lados".
  - Títulos de 30–36 pt, con mayúscula solo al inicio. Cuerpo de 14–18 pt. Mínimo 12 pt.
- **Motivos:**
  - **Panel destacado:** borde papel con sombra rosa desplazada, como el panel principal de la app. Máximo uno por lámina.
  - **Nota de pista:** papel rotado −2° con cinta amarilla, en la esquina inferior derecha, sin tapar contenido.
  - **Casete dibujado con formas:** en la portada, en el divisor del lado B y en el cierre.
- **Prohibido:** barras o franjas decorativas, líneas bajo los títulos, viñetas genéricas, degradados y texto a menos de 12 pt.
- **Diagramas:** con formas nativas y cajas de panel. Cada texto va en su propio cuadro y cada elemento tiene un `objectName` legible, para animarlo por separado en Canva.

## Pistas camufladas

- **En la lámina:** la nota de pista escrita en Caveat lleva el lado y la pista, y una secuencia de 3 ideas con flechas, por ejemplo `Lado A · 07 — failover → 0 de 293 → costo: 3 ms`. Se ve como una dedicatoria de la app.
- **En las notas del orador:** el guion completo de la lámina, de 30 a 75 s, en primera persona del plural y en un tono natural.
- **Entregable aparte:** `guion.md`, con el guion por expositor, por si hay que imprimirlo.

## Estructura (16 láminas con la demo, unos 15 min; ver "Decisiones del usuario")

Cada expositor tiene un "lado" del casete. La nota de pista numera las pistas.

| # | Lado | Expositor | Lámina | Mensaje y contenido |
|---|------|-----------|--------|---------------------|
| 1 | A·01 | 1 | Portada | Logo, "Tu casetera de confianza", lema y equipo en 4 columnas con su lado. *(Ya hecha en la prueba.)* |
| 2 | A·02 | 1 | El problema | En un monolito, el login, el audio continuo y la telemetría compiten. Si cae el servidor o la base, cae todo. Visual: una sola caja que contiene los tres flujos. |
| 3 | A·03 | 1 | MELOXO | El casete compartido: 12 pistas en 2 lados, 8 miembros, dedicatorias de 140 caracteres e invitación por enlace. Sin feed ni likes. Visual: un casete grande con esas cifras como etiquetas. |
| 4 | A·04 | 1 | Usuarios | Oyente, Compositor y Administrador, cada uno con 2–3 funciones. Objetivo AP: se reproduce aunque fallen las métricas, los avisos o Jamendo. |
| 5 | A·05 | 2 | Arquitectura | Los 9 contenedores (edge, gateway-auth, users-playlists, catalog-streaming ×2, playback-metrics, postgres, redis, redis-cache) y cómo se comunican: HTTP `/internal/*` y Redis Streams. Pila tecnológica en una línea. |
| 6 | A·06 | 2 | Rama 01→02 | Del monolito a 3 servicios, con una base por servicio. Comparativa p50/p95: audio 12/39 → 9/20 ms, `GET /api/songs` 36/71 → 12/26 ms. Playlists sube en p50 y baja en p95 (27/66 → 31/55 ms), porque tiene un salto HTTP extra, y se dice así. |
| 7 | A·07 | 2 | Rama 03 | "Si cae una réplica, nadie lo nota": 0 / 293, +3 ms, 15/34 ms. *(Ya hecha en la prueba.)* |
| 8 | B·01 | 3 | Divisor | "Lado B: cuando algo falla". Casete volteado. Lámina breve que da paso al expositor 3. |
| 9 | B·02 | 3 | Rama 04: breaker | Timeouts de 1.5 s, reintentos y circuit breaker: se abre tras 5 fallos en 30 s y prueba a los 15 s. Visual: diagrama de 3 estados (cerrado → abierto → semiabierto). |
| 10 | B·03 | 3 | Rama 04: cola y sesiones | Con playback-metrics caído responde 202 y no se pierde nada. La revocación de sesión pasa de 30 s a 0,04 s (cifra antes/después). |
| 11 | B·04 | 3 | Rama 05: mensajería | `track_published` con outbox, Redis Streams, consumidor idempotente y cola de mensajes muertos tras 5 intentos. Resultado: 132 publicados, 0 sin relevar. Visual: flujo de 4 pasos. |
| 12 | B·05 | 4 | Rama 06: caché | Caché de lectura separada del Redis durable. `GET /api/songs` 38/70 → 13/28 ms y top de métricas 31,6 → 7,1 ms. Visual: barras antes/después hechas con formas. |
| 13 | B·06 | 4 | Carga | 50 clientes durante 2 min, 0 fallos (5373 peticiones sin caché y 5203 con caché). Nota honesta: la búsqueda de la prueba usa solo 6 palabras y las cifras son optimistas. |
| 14 | B·07 | 4 | Aprendizajes y pendientes | 3 aprendizajes y lo que quedó fuera: saga, MongoDB, `track_hidden` y la sala sincronizada. |
| 15 | B·08 | 4 | Cierre | "Gracias", el logo y el casete. Espacio para preguntas. *(QR o demo: pendiente, ver abajo.)* |

Las cifras salen de `docs/ramas.md` y `docs/decisions/`, que son la fuente de verdad: si una cifra de esta tabla no coincide con el repo, manda el repo. La rama 01 no tiene cifras repetidas, por eso solo se usa como comparación en la lámina 6. Quien construya debe verificar cada cifra contra esos documentos antes de usarla.

**Comparar solo dentro de una misma corrida.** `GET /api/songs` aparece con valores distintos según la rama, y todos son correctos:

- 36/71 → 12/26 ms es monolito frente a rama 02 (`decisions/02-separacion.md:95`).
- 15/34 ms es la rama 03.
- 38/70 → 13/28 ms es sin y con caché en la rama 06 (`decisions/06-poliglota.md:57`).

La propia decisión 06 pide no cruzar corridas. En la lámina 6, `GET /api/playlists/{id}` va de 27/66 a 31/55 ms: el p50 sube y el p95 baja.

**Decisiones del revisor, resueltas por el líder:**

- **Tipografía:** Montserrat negrita en todos los títulos, el lema y las cifras. Unbounded desaparece del archivo, incluido lo heredado del prototipo.
- **Nota de pista:** si no cabe, se agranda la nota (hasta 2.8 × 0.9 in) y se recorta la pista a 3 ideas de 1–3 palabras. Nunca baja de Caveat 14 pt.
- **`build.js` en el repo:** usa rutas relativas a `docs/presentacion/`, con el logo copiado a esa carpeta.
- **Contingencia de Canva:** lo que se deforme al importar se corrige por la conexión, si es texto, posición o color. Si no se puede así, se simplifica en el generador y se reimporta.

## Animación (guía para Canva)

- **Transición entre láminas:** "Disolver", la misma en todas.
- **Dentro de la lámina:** solo "Aparecer al hacer clic" con el efecto **Desvanecer**, en el orden en que se narra. Por ejemplo:
  - En los diagramas aparece primero el emisor, luego la flecha y luego el receptor.
  - Las cifras de resultado aparecen al final, como remate.
- **Máximo 4 clics por lámina.** El título, el fondo y la nota de pista ya están visibles al entrar.
- **Sin animaciones** en la portada ni en el divisor.
- **Entregable:** `guia-animacion.md`, una tabla con la lámina, el elemento (por su nombre visible), el orden de clic y el efecto.

## Flujo de trabajo

1. **Sonnet** extiende `build.js` (scratchpad `deck/`) a las 15 láminas, con QA propia (validate y render).
2. **Haiku** hace una revisión visual independiente de los PNG renderizados contra una lista de comprobación.
3. **El líder** (Opus) revisa y corrige si algo se atora.
4. **El usuario** importa `meloxo.pptx` a Canva.
5. **El líder**, por la conexión: limpia el número suelto de las notas, comprueba las fuentes y le pone título al diseño.
6. **Sonnet** escribe `guion.md` y `guia-animacion.md`.

Los entregables finales se copian a `docs/presentacion/` en el repo: `meloxo.pptx`, `build.js`, `fondo-puntos.png`, `guion.md` y `guia-animacion.md`.

## Decisiones del usuario

- **Expositores, en el orden del README:**
  - Lado A·1 Christian Franco Ramírez: láminas 1–4.
  - Lado A·2 Miriam Amisadai López Hernández: láminas 5–7.
  - Lado B·1 Erick Nava Santiago: láminas 8–11.
  - Lado B·2 Brent Armando Pérez Paitán: láminas 12–15.
- **Cierre:** QR al repositorio público `https://github.com/zmd-brnt/MELOXO` (responde 200). Se genera como PNG con fondo papel y módulos tinta, y lleva la URL en texto debajo.
- **Demo: video corto** de 30–45 s, grabado con Playwright sobre la app levantada (`docker compose up -d` + semilla). Muestra el flujo de crear un casete, agregar pistas y reproducir.
  - Va en una lámina nueva, la **A·05 "Así se ve"**, al final del bloque del expositor 1. El expositor 1 pasa a tener las láminas 1–5, y la numeración de lo que sigue se recorre en uno, hasta 16 láminas.
  - En el .pptx va un marco con un fotograma del video y el rótulo "video". El video se sube a Canva por la conexión (la API sí acepta video) y se coloca en el marco.
- **Capturas reales** de la app para las láminas 3 y 4, con Playwright y la misma semilla: inicio con casetes, un casete abierto con dedicatorias y el reproductor. Van dentro de un marco de panel con la sombra rosa.
- Si la app no levanta, el respaldo es la maqueta `docs/design/maqueta-inicio.png` y se avisa al usuario.

## Decisiones del líder (revisables)

- Con la demo, el expositor 1 tiene 5 láminas ligeras, el 2 tiene 3 densas y el 3 y el 4 tienen 4 cada uno (contando el divisor y el cierre).
- La lámina 6 incluye la regresión de playlists en lugar de ocultarla.
- La lámina 13 incluye la advertencia de que las cifras son optimistas, porque así lo dice la documentación del proyecto.
