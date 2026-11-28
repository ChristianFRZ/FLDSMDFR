# Presentación de MELOXO: plan de construcción

> **Para agentes:** sub-skill obligatoria: superpowers:subagent-driven-development. Haiku lee y revisa, Sonnet escribe y el líder supervisa. Los pasos usan casillas `- [ ]`.

**Objetivo:** dejar en el Canva del usuario una presentación de 16 láminas de MELOXO, con notas del orador, video de demo y QR. En el repo quedan el generador, el guion y la guía de animación.

**Arquitectura:**
- Un generador Node con pptxgenjs, modular: tema y motivos, una pieza por expositor y el ensamblado. Produce `meloxo.pptx`.
- Un verificador Python con python-pptx comprueba las reglas del diseño antes del render visual.
- El usuario importa el .pptx a Canva. El líder termina el diseño por la conexión de Canva: notas, video y título.

**Pila:** Node 24, pptxgenjs, sharp, qrcode, Playwright (el de `frontend/`), Python 3 con python-pptx y LibreOffice para el render de QA.

**Diseño:** `docs/superpowers/specs/2026-11-24-presentacion-meloxo-design.md`. Quien ejecute debe leerlo completo. Referencia visual aprobada: el prototipo `build.js` en el scratchpad (`…/scratchpad/deck/`).

## Restricciones globales

- Fuentes: solo `Montserrat` (bold) en títulos, lema y cifras; `Roboto` en el cuerpo; `Caveat` en la pista, las etiquetas de casete y los "lados". Ninguna otra, y nunca `Unbounded`.
- Colores: solo `141317 201F25 4A4852 F4F1EA BDB9AF FF3D8B 00D1BE FFD233 4A5CFF`. El rosa, en 1–2 palabras clave por lámina; el turquesa, en las cifras de resultado.
- Fondo: `assets/fondo-puntos.png` (1920×1080, tinta con puntos `34323B` cada 32 px) en todas las láminas.
- Lienzo `LAYOUT_16x9`. Márgenes ≥ 0.5 in. Cuerpo ≥ 12 pt; Caveat ≥ 14 pt; títulos de 30–36 pt, con mayúscula solo al inicio.
- Cada idea va en su propio cuadro de texto, con `objectName` legible. Prohibido: barras, franjas, líneas bajo los títulos, degradados y viñetas `•` literales.
- Cada lámina lleva una nota de pista (`objectName` `pista`) con el formato `Lado X · NN — idea → idea → idea` y notas del orador de 30–75 s.
- Las cifras salen de `docs/decisions/*.md`. Solo se comparan cifras de una misma corrida.
- Expositores: A·1 Christian Franco Ramírez (láminas 1–5), A·2 Miriam Amisadai López Hernández (6–8), B·1 Erick Nava Santiago (9–12), B·2 Brent Armando Pérez Paitán (13–16).
- Commits sin línea `Co-Authored-By`.

## Puntos de atención en la revisión

1. **Desborde en Canva:** Montserrat y Roboto miden distinto que la fuente que use LibreOffice si no las tiene. La QA debe renderizar con los TTF reales de Montserrat, Roboto y Caveat en `.qa/fonts`. Los cuadros llevan un 10 % de holgura (lo comprueba `verificar.py` con `test_holgura_titulos`).
2. **La pista tapa contenido:** ningún elemento puede cruzarse con el rectángulo de la pista (`test_pista_sin_solape`).
3. **Notas del orador:** Canva les agrega un número de lámina suelto. Se limpian en la tarea 8 y se comprueban leyendo el diseño.
4. **QR ilegible al proyectar:** mínimo 1.6 in de lado, módulos tinta sobre papel, margen de 2 módulos. Se comprueba decodificándolo (`test_qr_decodifica`).
5. **Video rechazado por Canva:** MP4 H.264, ≤ 45 s, ≤ 25 MB. Se comprueba con `ffprobe` en la tarea 2.

---

## Estructura de archivos (todo en `docs/presentacion/`)

| Archivo | Responsabilidad |
|---|---|
| `package.json` | Dependencias: pptxgenjs, sharp y qrcode. Script `build`. |
| `build/tema.js` | Constantes de color y fuente, más los ayudantes de motivo: `fondo(slide)`, `titulo(slide, texto)`, `panel(slide, {x,y,w,h})`, `pista(slide, texto)`, `casete(slide, {x,y,w,rot,color,etiqueta})`, `textoRico(partes)`. |
| `build/fondo.js` | Genera `assets/fondo-puntos.png` con sharp. |
| `build/lado-a1.js` … `lado-b2.js` | Exportan `agregar(pres)`, que añade las láminas de cada expositor con sus notas. |
| `build/build.js` | Ensambla todo en orden y escribe `meloxo.pptx`. |
| `verificar.py` | Pruebas pytest sobre `meloxo.pptx`. |
| `capturas/capturar.spec.ts` | Spec de Playwright para las capturas y el video. Se corre con la configuración de `frontend/`. |
| `assets/` | Logo, fondo, capturas, fotograma del video, `demo.mp4` y `qr-repo.png`. |
| `guion.md`, `guia-animacion.md` | Entregables para el equipo. |
| `.gitignore` | `node_modules/`, `.qa/` (fuentes, venv, renders). |

---

### Task 1 (Tarea): andamiaje, tema y verificador (con las 2 láminas aprobadas)

**Archivos:** crear `package.json`, `.gitignore`, `build/tema.js`, `build/fondo.js`, `build/build.js`, `build/lado-a1.js` (solo la portada), `build/lado-a2.js` (solo la lámina de la rama 03) y `verificar.py`. Copiar el logo `docs/brand/png/meloxo-horizontal-color-dark.png` a `assets/`.

**Interfaces:**
- Produce `tema.js`: `C` (colores), `F = {titulo:'Montserrat', cuerpo:'Roboto', mano:'Caveat'}` y los ayudantes de motivo de la tabla. Todas las medidas van en pulgadas. `pista()` siempre usa `objectName: 'pista'`.
- Produce `build.js`: `node build/build.js` escribe `meloxo.pptx`; luego ejecuta `zip -dq meloxo.pptx '*/'`.
- Produce `verificar.py`: `MELOXO_PPTX` (ruta) y `ESPERADAS` (número de láminas, que empieza en 2 y la tarea 6 deja en 16).

- [ ] **Paso 1. Escribir `verificar.py` con estas pruebas.** Usa python-pptx y recorre también las formas agrupadas.
  - `test_numero_laminas`: el número de láminas es igual a `ESPERADAS`.
  - `test_fuentes_permitidas`: toda fuente de cada run está en {Montserrat, Roboto, Caveat}.
  - `test_colores_permitidos`: todo color sólido de texto y relleno está en la paleta.
  - `test_tamanos_minimos`: Roboto ≥ 12 pt, Caveat ≥ 14 pt y título ≥ 30 pt.
  - `test_cada_lamina_tiene_pista_y_notas`: hay exactamente una forma `pista` y las notas tienen ≥ 250 caracteres.
  - `test_pista_sin_solape`: el rectángulo de `pista` no se cruza con ninguna otra forma, salvo `pista-papel` y `pista-cinta`.
  - `test_margenes`: todas las formas quedan dentro de 0.4–9.6 × 0.3–5.35 in (no aplica a la imagen de fondo).
  - `test_holgura_titulos`: longitud del título × 0.62 × tamaño en pt / 72 ≤ 0.9 × ancho del cuadro.
  - `test_sin_unbounded`: no aparece `Unbounded` en el XML.
- [ ] **Paso 2.** Ejecutar `pytest verificar.py`. Resultado esperado: FALLA, porque `meloxo.pptx` no existe todavía.
- [ ] **Paso 3. Implementar `tema.js`, `fondo.js`, `build.js`, la portada y la lámina de la rama 03.**
  - Portar el prototipo cambiando Unbounded por Montserrat bold y respetando la nueva distribución aprobada.
  - La lámina de la rama 03 pasa a ser la lámina 8, A·08. La portada es A·01.
- [ ] **Paso 4. Instalar dependencias y comprobar.** `npm i`, `node build/build.js` y `pytest verificar.py -q`: todas las pruebas PASAN. Además, `validate.py` del skill pptx no da errores.
- [ ] **Paso 5. Render de QA.**
  - Descargar los TTF de Montserrat, Roboto y Caveat (google/fonts) a `.qa/fonts` y escribir `.qa/fonts.conf`.
  - Renderizar con `FONTCONFIG_FILE=.qa/fonts.conf` a `.qa/render/`.
  - Revisar los PNG con Read: sin desbordes y con aspecto equivalente al prototipo aprobado.
- [ ] **Paso 6. Commit:** `feat(presentacion): generador y verificador con portada y rama 03`.

### Task 2 (Tarea): capturas reales y video de demo

**Archivos:** crear `capturas/capturar.spec.ts` y `capturas/README.md` (cómo regenerarlas). Salida en `assets/`: `cap-inicio.png`, `cap-casete.png`, `cap-reproductor.png`, `demo.mp4` y `demo-fotograma.png`.

**Interfaces:**
- Produce las 5 rutas anteriores, que consumen las tareas 3 y 8.
- Consume el stack: `docker compose up -d --build`, la semilla `docker compose run --rm seed python -m seed all` (o `activity` si no hay `JAMENDO_CLIENT_ID`) y el `.env` del usuario. No imprimir ni escribir contraseñas.

- [ ] **Paso 1. Levantar el stack y la semilla.** Comprobar que `curl -s -o /dev/null -w '%{http_code}' http://localhost:8080` responde `200`. Si no levanta, PARAR y avisar al líder. El respaldo es la maqueta.
- [ ] **Paso 2. Escribir la spec.**
  - Viewport 1600×900 con `deviceScaleFactor` 2.
  - Iniciar sesión como `oyente00@demo.meloxo.dev`, con la contraseña de `DEMO_PASSWORD` leída del entorno.
  - Captura del inicio con los casetes, de un casete abierto con dedicatorias y del reproductor en marcha.
  - Una segunda prueba con `video: on` a 1280×720 que crea un casete "Para el profe", agrega 2 pistas, escribe una dedicatoria y reproduce. Dura ≤ 45 s.
- [ ] **Paso 3. Grabar.** Correr `npx playwright test ../docs/presentacion/capturas` desde `frontend/`. Convertir el .webm con `ffmpeg -c:v libx264 -pix_fmt yuv420p -an` a `demo.mp4` y extraer el fotograma del segundo 3 a `demo-fotograma.png`.
- [ ] **Paso 4. Comprobar el video.** `ffprobe` debe dar códec h264, duración ≤ 45 s y tamaño ≤ 25 MB. Revisar las 3 capturas con Read: sin datos sensibles, en tema oscuro y con contenido de la semilla.
- [ ] **Paso 5. Commit:** `feat(presentacion): capturas y video de demo` (con el .mp4 incluido si pesa ≤ 25 MB).

### Task 3 (Tarea): lado A·1, Christian (láminas 1–5)

**Archivos:** modificar `build/lado-a1.js`.
**Interfaces:** consume `tema.js` y los assets de la tarea 2.

- [ ] **Paso 1.** Subir `ESPERADAS` a 6 y añadir `test_textos_a1`. Comprueba los textos que deben aparecer:
  - Lámina 3: "12 pistas", "8", "140".
  - Lámina 4: "Oyente", "Compositor", "Administrador".
  - Lámina 5: "Así se ve".
  - Ejecutar: FALLA.
- [ ] **Paso 2. Implementar las láminas 2–5 según la tabla del diseño** (A·02 a A·05).
  - La 3 y la 4 llevan capturas dentro del panel con sombra rosa.
  - La 5 lleva `demo-fotograma.png` en un marco de panel, con `objectName` `video-demo`, y la etiqueta Caveat "video".
- [ ] **Paso 3.** `pytest` PASA. Render de QA y revisión con Read de las láminas 1–5.
- [ ] **Paso 4. Commit:** `feat(presentacion): lado A·1`.

### Task 4 (Tarea): lado A·2, Miriam (láminas 6–8)

- [ ] **Paso 1.** `ESPERADAS` pasa a 8 y se añade `test_textos_a2`. Comprueba:
  - Lámina 6: los 9 contenedores por nombre.
  - Lámina 7: "12 / 26", "36 / 71", "31 / 55", "27 / 66".
  - Lámina 8: "0 / 293".
  - Ejecutar: FALLA.
- [ ] **Paso 2. Implementar la lámina 6 (arquitectura) y la lámina 7 (rama 01→02).**
  - La 6 lleva un diagrama con formas nativas: el edge arriba, los servicios en fila, los datos abajo y las flechas etiquetadas `HTTP /internal` y `Redis Streams`.
  - La 7 lleva una comparativa antes/después en columnas, con la nota de playlists.
  - Verificar cada cifra contra `docs/decisions/02-separacion.md:94-96`.
- [ ] **Paso 3.** `pytest` PASA, más render de QA. **Paso 4.** Commit: `feat(presentacion): lado A·2`.

### Task 5 (Tarea): lado B·1, Erick (láminas 9–12)

- [ ] **Paso 1.** `ESPERADAS` pasa a 12 y se añade `test_textos_b1`. Comprueba:
  - Lámina 10: "5 fallos", "30 s", "15 s".
  - Lámina 11: "202", "0,04 s".
  - Lámina 12: "132", "0 sin relevar".
  - Ejecutar: FALLA.
- [ ] **Paso 2. Implementar las láminas 9–12.**
  - La 9 es el divisor "Lado B: cuando algo falla", con un casete cobalto volteado.
  - La 10 lleva un diagrama de 3 estados.
  - La 11 lleva dos cifras antes/después.
  - La 12 lleva un flujo de outbox de 4 pasos.
  - Verificar las cifras contra `docs/decisions/04-*.md` y `05-*.md`.
- [ ] **Paso 3.** `pytest` PASA, más render de QA. **Paso 4.** Commit: `feat(presentacion): lado B·1`.

### Task 6 (Tarea): lado B·2, Brent (láminas 13–16) y QR

- [ ] **Paso 1.** `ESPERADAS` pasa a 16 y se añaden dos pruebas:
  - `test_textos_b2`. Comprueba:
    - Lámina 13: "13 / 28", "38 / 70", "7,1".
    - Lámina 14: "50 clientes", "0 fallos", "6 palabras".
    - Lámina 16: "github.com/zmd-brnt/MELOXO".
  - `test_qr_decodifica`: decodifica `assets/qr-repo.png` con `zbarimg` u `opencv` y comprueba que da `https://github.com/zmd-brnt/MELOXO`; además, la imagen del QR en la lámina 16 mide ≥ 1.6 in.
  - Ejecutar: FALLA.
- [ ] **Paso 2. Generar el QR y las láminas 13–16.**
  - Generar `assets/qr-repo.png` con `qrcode` (oscuro `141317`, claro `F4F1EA`, margen 2, 1024 px).
  - La 13 lleva barras antes/después hechas con formas, a escala real de ms.
  - La 14 lleva la cifra grande "0 fallos" y la advertencia honesta de que son cifras optimistas.
  - La 15 son 3 aprendizajes y una lista de lo que quedó fuera.
  - La 16 es el cierre: "Gracias", el logo, el casete y el QR con la URL.
- [ ] **Paso 3.** `pytest` PASA (las 16 láminas), más render de QA de todo el deck. **Paso 4.** Commit: `feat(presentacion): lado B·2 y cierre con QR`.

### Task 7 (Tarea): revisión visual independiente (Haiku) y correcciones (Sonnet)

- [ ] **Paso 1. Revisión de Haiku.** Revisa los 16 PNG de `.qa/render/` contra la lista de QA visual del skill pptx y contra estos criterios del diseño:
  - el rosa en 1–2 palabras por lámina;
  - la pista parece una dedicatoria;
  - títulos a la misma altura;
  - sin huecos grandes.

  Entrega una lista de defectos con número de lámina y elemento.
- [ ] **Paso 2. Correcciones de Sonnet.** Corrige en el generador. Después `pytest`, render y nueva revisión solo de las láminas tocadas.
- [ ] **Paso 3. Commit:** `fix(presentacion): correcciones de QA visual`.

### Task 8 (Tarea): Canva (líder y usuario)

- [ ] **Paso 1.** El usuario arrastra `docs/presentacion/meloxo.pptx` a Canva. El líder lo localiza con `search-designs`.
- [ ] **Paso 2. Comprobación de fuentes con `read-design`.**
  - Ningún `fontRef` de Arimo (`YACgEZ1cb1Q`) en títulos ni cifras.
  - Las notas existen en las 16 láminas.
- [ ] **Paso 3. Ajustes con `edit-design`, en una transacción.**
  - `replace_speaker_notes` en cada lámina para quitar el número suelto del final.
  - `update_title` → "MELOXO — Sistemas Distribuidos".
  - Subir `demo.mp4` con `create-upload-url` y colocarlo con `update_fill` en `video-demo` (lámina 5).
  - Mostrar las miniaturas al usuario y hacer `commit` solo con su aprobación.
- [ ] **Paso 4.** Abrir el diseño en el navegador con `xdg-open <edit_url>`.

### Task 9 (Tarea): guion y guía de animación

**Archivos:** crear `guion.md` y `guia-animacion.md`.

- [ ] **Paso 1. `guion.md`.**
  - Una sección por expositor, con sus láminas, el tiempo objetivo y el guion de cada una, idéntico a las notas del orador.
  - Al inicio, una tabla de tiempos que sume entre 14 y 15 min.
  - Se comprueba con `node -e` que el texto de cada lámina coincide con sus notas en el pptx, usando un script en `.qa/`.
- [ ] **Paso 2. `guia-animacion.md`.**
  - Primero, cómo aplicar en Canva "Disolver" a todas las transiciones.
  - Luego, por lámina: una tabla con el orden de clic, el elemento por su texto visible, "Aparecer al hacer clic" y el efecto Desvanecer. Máximo 4 clics; ninguno en las láminas 1 y 9.
  - Se comprueba que ninguna lámina pase de 4 filas.
- [ ] **Paso 3. Commit:** `docs(presentacion): guion y guía de animación`, que incluye `meloxo.pptx` final.
