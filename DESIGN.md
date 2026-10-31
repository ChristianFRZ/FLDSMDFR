# DESIGN.md · FLDSMDFR

Fuente única de verdad del sistema visual de FLDSMDFR: concepto, distribución, temas,
tipografía, espaciado, componentes, accesibilidad y tono de los textos. Si un componente
de `ui/` contradice este documento, se corrige el componente o se actualiza este documento
en el mismo cambio; nunca se deja la contradicción.

Implementación de referencia:

| Qué | Dónde |
|---|---|
| Tokens de ambos temas | `ui/src/styles/tokens.css` |
| Estilos base (reset, tipografía, foco, movimiento) | `ui/src/styles/base.css` |
| Estado del tema (`useTheme`) | `ui/src/composables/useTheme.ts` |
| Interruptor Lado A / Lado B | `ui/src/components/InterruptorLado.vue` |
| Prototipo aprobado por el equipo | `.superpowers/brainstorm/43577-1793410204/content/casete-paletas-v3.html` |

---

## 1. Concepto: casete mixtape

La aplicación se presenta como **una casetera con su estante de casetes**. Cada playlist es
un casete que grabaste tú: tiene una etiqueta escrita a mano con su nombre, una ventanita
donde se ven los carretes y una lista de canciones. Del lado derecho está la tienda de
discos: el catálogo y lo más escuchado, desde donde "grabas" canciones en el casete activo.

Por qué este concepto:

- **Hace visible el modelo de datos.** Playlist = casete, agregar canción = grabar en el
  casete, playlist activa = el casete que está en la casetera. El usuario entiende qué
  pasa sin leer instrucciones.
- **Da identidad.** El equipo pidió alejarse del "clon de Spotify". Un objeto físico,
  cálido y setentero distingue al proyecto y conecta con el nombre (una máquina absurda
  de los 70).
- **Muestra el streaming.** La ventanita del casete y la barra de progreso enseñan lo que
  el backend hace: los carretes giran mientras suena y la barra dibuja los fragmentos ya
  descargados (`audio.buffered`) gracias a las peticiones HTTP Range.
- **Una sola pantalla.** Todo lo importante (qué suena, qué sigue, qué puedo agregar) cabe
  en dos columnas, sin navegar entre secciones.

### 1.1. Anti‑patrones (no hacer)

- **Barra lateral de navegación + reproductor fijo abajo.** Es la distribución que el
  equipo rechazó: fragmenta la pantalla en tres zonas y esconde el casete activo.
- **Paleta naranja/café plana del diseño anterior** (`#F4EFE6`, `#D36135`, `#5C3D2E`…).
  Se sustituye por los temas Lado A y Lado B de la sección 3.
- **Letra manuscrita fuera de la etiqueta del casete.** Caveat es un adorno; en títulos,
  botones o listas baja la legibilidad.
- **Emojis como iconos de interfaz.** Los glifos ⏮ ▶ ⏭ del prototipo son marcadores de
  posición; en la app se usan iconos SVG en línea con `aria-label`.
- **Colores escritos a mano en componentes.** Todo color sale de un token `var(--…)`.
- **Modales para todo.** Crear casete, renombrar o confirmar se resuelven en línea, junto
  al elemento afectado. Solo "Borrar casete" pide confirmación.
- **Texto en mayúsculas sostenidas o en voz pasiva** ("CANCIÓN AGREGADA", "La canción fue
  agregada"). Ver sección 9.
- **Spinners de pantalla completa.** La carga se muestra en el lugar donde aparecerá el
  contenido (sección 6.0).

---

## 2. Distribución

### 2.1. Escritorio (≥ 900 px): dos columnas

La columna izquierda ("casetera", fondo `--deck`) mide `minmax(360px, 1fr)`; la derecha
("tienda", fondo `--bg`) `1.15fr`. Ambas ocupan el alto de la ventana y cada lista hace
scroll por dentro de su columna; la página no hace scroll.

```text
┌─────────────────────────────────┬──────────────────────────────────────────┐
│ CASETERA (--deck)               │ TIENDA (--bg)            [Lado A|Lado B] │
│ ┌─────────────────────────────┐ │                                          │
│ │▔▔▔▔▔▔▔ franja --accent ▔▔▔▔▔│ │ Catálogo                  (Fraunces 28)  │
│ │ Para la tarde lluviosa      │ │                                          │
│ │               (Caveat 22)   │ │ ( Catálogo ) ( Lo más escuchado )        │
│ │   ( ✺ )━━━━━━━────( ✺ )     │ │                                          │
│ └─────────────────────────────┘ │ ╭──────────────────────────────────╮     │
│ CaseteActivo (--tape)           │ │ Buscar canción, artista o álbum  │     │
│                                 │ ╰──────────────────────────────────╯     │
│ (|<) ( > ) (>|) Nubes de… (vol) │ Ana        Cabina de grabación  (Salir)  │
│                Los Meteoros     │ Granizo                     3:12  (+)    │
│ ━━━━━━━━░░░░──────── 1:12/3:41  │ Los Meteoros · Pronóstico                │
│ BarraProgreso                   │ ──────────────────────────────────────── │
│                                 │ Monzón                      4:20  (+)    │
│ ▶ Nubes de agosto        3:41   │ Tormenta Norte · Isobaras                │
│   Lluvia ligera          4:05   │ ──────────────────────────────────────── │
│   Frente frío            2:58   │ Neblina                     2:44  (+)    │
│ ListaCasete (scroll)            │ Calma Chicha · Barlovento                │
│                                 │                                          │
│ [Tarde lluv.][+ Nuevo casete]   │ PanelCatalogo / PanelTop (scroll)        │
│ EstanteCasetes (al pie)         │                                          │
└─────────────────────────────────┴──────────────────────────────────────────┘
```

Orden de lectura y de tabulación: casete activo → controles → barra de progreso → lista
del casete → estante → encabezado de la tienda (cabina, "Salir", interruptor de lado) →
pestañas → buscador → resultados. El interruptor queda en el encabezado de la tienda (columna
derecha), por eso llega después de la casetera.

### 2.2. Pantallas angostas (< 900 px): se apila

La casetera se compacta arriba (etiqueta del casete en una línea, sin ventanita de
carretes, controles y barra de progreso) y queda **fija** mientras el resto hace scroll.
Debajo, tres pestañas reparten el contenido:

```text
┌──────────────────────────────────────┐
│ CASETERA COMPACTA (--deck, sticky)   │
│ Para la tarde lluviosa   [Lado A|B]  │
│ (|<) ( > ) (>|) Nubes de agosto (vol)│
│ ━━━━━━━░░░────────────── 1:12 / 3:41 │
├──────────────────────────────────────┤
│ (Catálogo)(Mi casete)(Lo más escuch.)│
├──────────────────────────────────────┤
│ ╭──────────────────────────────────╮ │
│ │ Buscar canción, artista o álbum  │ │
│ ╰──────────────────────────────────╯ │
│ Granizo                   3:12  (+)  │
│ Los Meteoros · Pronóstico            │
│ ──────────────────────────────────── │
│ Monzón                    4:20  (+)  │
│ …                                    │
└──────────────────────────────────────┘
```

- **Catálogo:** `PanelCatalogo`.
- **Mi casete:** `ListaCasete` seguida de `EstanteCasetes` (el estante pasa a una rejilla
  de 2 columnas). El panel conserva el fondo `--deck` para mantener los contrastes de la
  casetera.
- **Lo más escuchado:** `PanelTop`.

Entre la casetera compacta y las pestañas va una fila con el nombre del usuario, "Cabina de
grabación" (solo admin) y "Salir"; esa fila no es fija. Las pestañas pasan a otra línea si no
caben. En < 480 px el control de volumen de `ControlesReproductor` se oculta: en teléfonos el
volumen lo controlan los botones del equipo y el deslizador provocaría scroll horizontal.

Margen lateral 16 px (`--space-4`). Ningún elemento provoca scroll horizontal; los
títulos largos se cortan con elipsis y el texto completo va en `title`.

---

## 3. Temas: Lado A y Lado B

Dos temas con **los mismos nombres de token**. El tema activo se fija en
`<html data-lado="A">` o `<html data-lado="B">`; los componentes solo leen `var(--…)`.

- **Lado A · Mostaza y oliva** (claro): una sala setentera, mostaza, oliva y naranja quemado.
- **Lado B · Ámbar nocturno** (oscuro): cacao, ladrillo y luz ámbar de bulbo, para escuchar
  de noche.

### 3.1. Tokens de color

| Token | Uso | Lado A | Lado B |
|---|---|---|---|
| `--bg` | Fondo de la tienda (columna derecha) y de la página | `#F5D7A1` | `#2A1B1D` |
| `--ink` | Texto principal sobre `--bg` y `--paper` | `#33210F` | `#FCE9D8` |
| `--paper` | Etiqueta del casete, buscador, tarjetas, campos | `#FFF3DC` | `#3A2629` |
| `--deck` | Fondo de la casetera (columna izquierda) | `#5B5A24` | `#1D1213` |
| `--deck-ink` | Texto e iconos sobre `--deck` y `--tape` | `#FFF3DC` | `#FCE9D8` |
| `--tape` | Cuerpo del casete y casetes del estante | `#8A3A16` | `#B4452F` |
| `--accent` | Relleno de botón principal (play, +), franja de la etiqueta | `#C4501E` | `#F2A541` |
| `--on-accent` | Texto e iconos sobre `--accent` | `#FFF3DC` | `#2A1B1D` |
| `--accent2` | Foco, canción que suena, casete activo, progreso | `#F2B33D` | `#F2A541` |
| `--rule` | Separadores sobre `--bg` / `--paper` | `#E3BC7E` | `#4A3236` |
| `--rule-deck` | Separadores sobre `--deck` | `#76753A` | `#3A2629` |
| `--danger` | Errores y acciones destructivas | `#9E2A1C` | `#FF8A6B` |

Estos valores son los aprobados por el equipo. **No se cambian** para arreglar un
contraste: se restringe el uso (sección 3.2).

### 3.2. Contraste medido (WCAG 2.2)

Razones calculadas con la fórmula de luminancia relativa de WCAG. Umbrales: texto normal
4.5:1, texto grande (≥ 24 px, o ≥ 18.66 px en negrita) 3:1, componentes no textuales
(bordes, iconos, indicadores de foco, barras) 3:1.

| Par | Lado A | Lado B | Resultado |
|---|---|---|---|
| `--ink` sobre `--bg` | 11.07 | 13.97 | AA texto normal en ambos |
| `--ink` sobre `--paper` | 13.99 | 11.94 | AA texto normal en ambos |
| `--bg` sobre `--ink` (pestaña activa) | 11.07 | 13.97 | AA texto normal en ambos |
| `--deck-ink` sobre `--deck` | 6.51 | 15.49 | AA texto normal en ambos |
| `--deck-ink` sobre `--tape` | 7.08 | 4.64 | AA texto normal en ambos |
| `--on-accent` sobre `--accent` | **4.23** | 8.04 | **Lado A: falla AA texto normal**; pasa texto grande y no textual |
| `--accent2` sobre `--deck` | **3.85** | 8.91 | **Lado A: falla AA texto normal**; pasa texto grande y no textual |
| `--accent` sobre `--bg` | **3.35** | 8.04 | **Lado A: falla AA texto normal**; pasa no textual |
| `--accent` sobre `--deck` | **1.54** | 8.91 | **Lado A: falla incluso no textual** |
| `--accent2` sobre `--bg` | **1.34** | 8.04 | **Lado A: falla incluso no textual** |
| `--danger` sobre `--bg` | 5.40 | 7.15 | AA texto normal en ambos |
| `--danger` sobre `--paper` | 6.82 | 6.11 | AA texto normal en ambos |
| `--ink` al 75 % de opacidad sobre `--bg` | 5.64 | 8.42 | AA texto normal |
| `--deck-ink` al 80 % de opacidad sobre `--deck` | 4.84 | 10.15 | AA texto normal (al 75 % el Lado A queda en 4.50, al límite) |

Restricciones que se derivan (aplican a los dos lados para no tener reglas por tema):

1. **Texto sobre `--accent`** (botón play, botón +, botón principal de formularios): solo
   iconos o texto **grande** — 18.66 px en negrita (peso ≥ 700) o 24 px. Los botones
   principales con texto usan Figtree 700 a 19 px. Nunca texto de 15 o 13 px sobre `--accent`.
2. **`--accent2` no es color de texto pequeño sobre `--deck`.** En la canción que suena
   (`ListaCasete`) el icono ▶ y la barra lateral de 3 px van en `--accent2` (elementos no
   textuales, 3.85:1) y el título va en `--deck-ink` 700. Como texto, `--accent2` sobre
   `--deck` solo se permite en tamaño grande (≥ 18.66 px negrita).
3. **`--accent` nunca es color de texto** sobre `--bg`, `--paper` ni `--deck`. Los enlaces
   y textos destacados usan `--ink` subrayado.
4. **Barra de progreso:** el tramo reproducido usa `--accent2`, no `--accent` (Lado A:
   3.85:1 sobre `--deck`; `--accent` tendría 1.54:1).
5. **Indicador de foco sobre fondos claros:** `--accent2` sobre `--bg` tiene 1.34:1 en el
   Lado A. Por eso el foco es un anillo doble: 3 px de `--accent2` por fuera y 2 px de
   `--ink` por dentro (sección 8.2). El anillo interior da ≥ 11:1 sobre `--bg`/`--paper`
   y el exterior ≥ 3.85:1 sobre `--deck`.
6. **Texto secundario** (artista, álbum, duración): opacidad mínima 0.8 sobre `--deck` y
   0.75 sobre `--bg`/`--paper`. En código se usa `opacity: .8` en ambos casos.
7. `--tape` es superficie, no texto. Sobre `--tape` solo va `--deck-ink`.

### 3.3. Cambio de tema

- Inicial: `localStorage['fldsmdfr-lado']` si vale `"A"` o `"B"`; si no,
  `prefers-color-scheme: dark` → Lado B, si no → Lado A.
- El interruptor `InterruptorLado` alterna y guarda la elección en `localStorage`.
- Si `localStorage` no está disponible (navegación privada, bloqueado) la app no falla:
  usa la preferencia del sistema y no recuerda la elección.
- El cambio es instantáneo, sin transición de colores (evita parpadeos en listas largas).

---

## 4. Tipografía

Tres familias, servidas localmente con `@fontsource-variable` (sin peticiones a Google):

| Token | Familia | Uso |
|---|---|---|
| `--font-display` | Fraunces (variable, eje `SOFT` = 100) | Títulos de vista y de panel |
| `--font-body` | Figtree (variable) | Todo el texto de interfaz |
| `--font-hand` | Caveat (variable) | **Solo** la etiqueta del casete (activo y del estante en escritorio) |

### 4.1. Escala

| Rol | Familia | Tamaño | Peso | Interlineado |
|---|---|---|---|---|
| Título de vista (h1) | Fraunces SOFT 100 | 28 px | 800 | 1.15, `letter-spacing: -0.01em` |
| Título de panel (h2) | Fraunces SOFT 100 | 22 px | 800 | 1.2 |
| Subtítulo (h3) | Fraunces SOFT 100 | 18 px | 800 | 1.25 |
| Texto | Figtree | 15 px | 400 (500 en botones, 700 en títulos de canción) | 1.5 |
| Texto pequeño (metadatos, tiempos) | Figtree | 13 px | 400 | 1.5 |
| Botón principal con texto (sobre `--accent`) | Figtree | 19 px | 700 | 1.2 |
| Etiqueta de casete | Caveat | 22 px | 700 | 1.1 |

- Los tiempos (`1:12 / 3:41`, duraciones) usan `font-variant-numeric: tabular-nums` para
  que no "bailen" al avanzar.
- Nada por debajo de 13 px.
- Sentence case en todo: "Lo más escuchado", no "Lo Más Escuchado".

---

## 5. Espaciado, tamaños y forma

| Token | Valor | Uso típico |
|---|---|---|
| `--space-1` | 4 px | Separación icono‑texto, ajustes finos |
| `--space-2` | 8 px | Entre botones del estante, entre pestañas |
| `--space-3` | 12 px | Entre controles del reproductor, columnas de una fila |
| `--space-4` | 16 px | Relleno de paneles en móvil, entre bloques pequeños |
| `--space-5` | 24 px | Relleno de columnas en escritorio, entre bloques grandes |
| `--radius-s` | 6 px | Etiqueta, casetes del estante, campos pequeños |
| `--radius-m` | 12 px | Casete activo, tarjetas, paneles |

- Solo se usan estos cinco espacios. Nada de 10, 14 o 18 px.
- **Área táctil mínima 40 × 40 px** para todo botón o control; el botón play mide 52 px.
- Píldoras (pestañas, buscador, botones de icono) con `border-radius: 999px`.
- Separación mínima de 8 px entre dos objetivos táctiles contiguos.
- Bordes de 2 px para controles en reposo (botones de icono, buscador); 1 px para
  separadores de lista.

---

## 6. Componentes

### 6.0. Estados comunes

Todos los componentes interactivos cumplen estas reglas, salvo que su ficha diga otra cosa:

| Estado | Tratamiento |
|---|---|
| Hover | Fondo o borde se oscurece/aclara con `filter: brightness(1.08)` en rellenos de `--accent`; en botones de contorno el fondo pasa a `color-mix(in srgb, currentColor 12%, transparent)`. Cursor `pointer`. Solo en dispositivos con `hover: hover`. |
| Foco | Anillo doble visible (sección 8.2) con `:focus-visible`. Nunca `outline: none` sin reemplazo. |
| Activo (pulsado) | `transform: scale(.96)` 80 ms (sin animación con reduced motion). |
| Deshabilitado | Opacidad 0.45, `cursor: not-allowed`, atributo `disabled` (o `aria-disabled="true"` si debe seguir siendo enfocable para explicar por qué). Sin hover. |
| Cargando | Esqueleto en el lugar del contenido: barras de `--rule` (o `--rule-deck`) con la forma de las filas, 3 filas. En botones, el texto cambia ("Grabando…") y el botón queda `aria-busy="true"` y deshabilitado. |
| Vacío | Mensaje de una o dos frases que dice qué hacer a continuación (sección 9) y, si aplica, el botón para hacerlo. |
| Error | `Aviso` tipo error en el lugar del contenido, con el mensaje del backend (`error.message`) y un botón "Reintentar". |
| Degradado | El servidor respondió con datos de respaldo (p. ej. `status: "degraded"` en canciones de un casete o `/api/health` con `degraded`). Se muestra el contenido con un `Aviso` tipo aviso arriba: "Mostramos la última versión guardada; algunos datos pueden estar desactualizados." |
| No disponible | Elemento que existe pero no se puede usar (canción desactivada: `status: "unavailable"`). Se ve atenuado (opacidad 0.6, sin tachar), con la etiqueta "No disponible" en texto pequeño y sin botón de reproducir. Se puede quitar del casete. |

### 6.1. `CaseteActivo`

El casete en la casetera: el elemento que da identidad a la app.

- Cuerpo `--tape`, `--radius-m`, relleno 12/16 px, sombra interior `inset 0 0 0 2px rgb(0 0 0 / .18)`.
- **Etiqueta:** fondo `--paper`, texto `--ink`, Caveat 22 px 700, `--radius-s`, franja
  superior de 6 px en `--accent`. Muestra el nombre del casete (playlist); corta con
  elipsis en una línea.
- **Ventanita:** píldora `rgb(0 0 0 / .35)` al 78 % del ancho, alto 46 px, con dos carretes
  (círculos de 32 px con rayos de `--paper`) y la cinta entre ellos (4 px, tramo
  reproducido en `--accent2`).
- **Estados:**
  - Sonando: los carretes giran (1 vuelta cada 2 s, `linear`, infinito). Con
    `prefers-reduced-motion: reduce` no giran.
  - En pausa / detenido: carretes quietos.
  - Cargando el casete: etiqueta con esqueleto.
  - Sin casete seleccionado: etiqueta en blanco con el texto "Elige un casete del estante"
    en Figtree 15 px (no Caveat), carretes quietos.
  - Degradado: icono de aviso pequeño junto a la etiqueta con `title` explicativo.
- Accesible: `role="img"` en la ventanita con `aria-label="Carretes del casete"`; el nombre
  del casete es un `h2` real.
- En < 900 px: solo la etiqueta en una línea, sin ventanita.

### 6.2. `ControlesReproductor`

Fila con ⏮ anterior, ▶/⏸ reproducir‑pausar, ⏭ siguiente, título/artista/tiempo y volumen.

- Botones de icono: círculo de 40 px, borde 2 px `currentColor`, fondo transparente,
  icono 18 px en `--deck-ink`. Separación `--space-3`.
- Play/pausa: círculo de 52 px, fondo `--accent`, icono `--on-accent` 22 px, sin borde.
- Metadatos: título Figtree 15 px 700 en `--deck-ink`; debajo "Artista · 1:12 / 3:41" en
  13 px, opacidad 0.8, `tabular-nums`. Una línea cada uno, con elipsis.
- Volumen: botón de icono que abre un deslizador horizontal (`input type="range"`,
  0–100) junto al botón; con flechas de teclado cambia de 5 en 5. Clic largo o tecla M
  silencia. `aria-label="Volumen"` en el deslizador y "Silenciar"/"Activar sonido" en el botón.
- `aria-label` obligatorios: "Anterior", "Reproducir"/"Pausar" (cambia con el estado),
  "Siguiente".
- En < 480 px el volumen se oculta (sección 2.2).
- **Estados:**
  - Sin canción: play deshabilitado; metadatos "Nada suena todavía".
  - Primera / última canción: ⏮ / ⏭ deshabilitados.
  - Cargando audio (antes de `canplay`): el icono de play se sustituye por un anillo
    girando (estático con reduced motion) y `aria-busy="true"`.
  - Error de audio (404, red): `Aviso` en línea bajo los controles: "No pudimos reproducir
    esta canción." y se salta a la siguiente disponible tras 3 s.

### 6.3. `BarraProgreso`

- Pista de 6 px de alto (área de clic de 40 px de alto, centrada), color `rgb(255 255 255 / .2)`
  sobre `--deck`.
- Tramos descargados (`audio.buffered`) en `--deck-ink` al 35 %: varios segmentos si hay
  saltos. Muestra el streaming por fragmentos.
- Tramo reproducido en `--accent2` (ver restricción 4 de la sección 3.2) y tirador
  circular de 16 px en `--accent2` con borde 2 px `--deck`.
- Clic o arrastre salta a esa posición. Teclado: `role="slider"`, flechas ±5 s,
  Re Pág/Av Pág ±30 s, Inicio/Fin. `aria-valuetext="1:12 de 3:41"`.
- **Estados:** deshabilitada sin canción (pista vacía, sin tirador); cargando (pista
  con esqueleto); foco con anillo doble alrededor de toda la barra.

### 6.4. `ListaCasete`

Canciones del casete activo, sobre `--deck`.

- Fila: posición implícita, título 15 px, duración 13 px a la derecha (`tabular-nums`),
  separador 1 px `--rule-deck`, alto mínimo 44 px. Acciones "Subir", "Bajar" y "Quitar del
  casete" (botones de icono de 40 px con `aria-label` que nombra la canción, p. ej.
  "Subir «Monzón»") visibles al hover/foco de la fila y siempre en pantallas táctiles.
  "Subir" se deshabilita en la primera fila y "Bajar" en la última.
- Canción que suena: icono ▶ y barra izquierda de 3 px en `--accent2`, título en
  `--deck-ink` 700 (restricción 2) y `aria-current="true"`.
- Clic (o Enter / Espacio: la fila es un botón) reproduce desde esa canción; la cola son
  las canciones del casete que no están "No disponible".
- Reordenar: con los botones "Subir"/"Bajar" de la fila (no se depende de arrastrar).
- Canción con datos de respaldo (`status: "degraded"`): marca discreta "Datos guardados" en
  13 px con `title` que lo explica.
- Pie: "3 canciones · 10:44" en 13 px.
- **Estados:** cargando (esqueleto de 3 filas); vacío ("Este casete está vacío. Busca una
  canción y pulsa + para grabarla."); error (`Aviso` + "Reintentar"); degradado (`Aviso`
  arriba, filas normales); fila no disponible (sección 6.0).

### 6.5. `EstanteCasetes`

Los casetes del usuario al pie de la casetera.

- Casete: rectángulo de 40 px de alto mínimo, `--tape`, `--radius-s`, sombra inferior
  `inset 0 -4px 0 rgb(0 0 0 / .2)`, nombre en Figtree 13 px 500 `--deck-ink` con elipsis.
  Separación `--space-2`. En escritorio fila con scroll horizontal interno; en < 900 px
  rejilla de 2 columnas.
- Casete activo: contorno 2 px `--accent2` con 2 px de separación, `aria-pressed="true"`.
- "Nuevo casete" (con icono +): mismo tamaño, fondo transparente, borde 2 px discontinuo `--deck-ink`. Al
  pulsarlo se convierte en un campo en línea ("Nombre del casete") con botones "Crear
  casete" y "Cancelar"; Enter crea, Escape cancela. Nombre de 1 a 60 caracteres.
- Renombrar / borrar: menú del casete activo ("Renombrar", "Borrar casete"). Borrar pide
  confirmación en línea: "¿Borrar «Correr»? Esta acción no se puede deshacer." con
  "Borrar casete" (`--danger`) y "Cancelar".
- **Estados:** cargando (3 casetes esqueleto); vacío ("Aún no tienes casetes. Crea el
  primero con «Nuevo casete»."); error al crear (mensaje bajo el campo, en `--danger` sobre
  `--paper`); creando ("Creando…", botón deshabilitado).

### 6.6. `PanelCatalogo`

Columna derecha, pestaña "Catálogo".

- Título h2 "Catálogo".
- Buscador: píldora `--paper`, borde 2 px `--ink`, alto 44 px, icono de lupa,
  placeholder "Buscar canción, artista o álbum" (placeholder con opacidad 0.75, cumple
  AA). Busca al escribir con 250 ms de espera; `aria-label="Buscar canción, artista o álbum"`.
- Clic en una fila (es un botón) reproduce esa canción; la cola son los resultados cargados.
- Fila: rejilla `1fr auto 40px`, separación `--space-3`, título 15 px 700, debajo
  "Artista · Álbum" 13 px opacidad 0.8, duración 13 px, y botón **+** (40 px, círculo
  `--accent`, icono `--on-accent`) con `aria-label="Grabar «Granizo» en el casete"`.
  Separador 1 px `--rule`.
- Paginación: botón "Cargar más" al final (no scroll infinito).
- **Estados:**
  - Cargando: esqueleto de 5 filas.
  - Vacío por búsqueda: "No encontramos canciones con «xyz»."
  - Catálogo vacío: "Todavía no hay canciones en el catálogo."
  - Error: `Aviso` + "Reintentar". Si falla una búsqueda se quitan los resultados
    anteriores y "Reintentar" repite esa búsqueda.
  - **+** sin casete activo: atenuado con `aria-disabled="true"` y `title` "Elige o crea un
    casete para grabar"; sigue enfocable y al pulsarlo avisa "Crea un casete primero."
  - **+** grabando: icono de carga, `aria-busy`. Al terminar, el icono pasa a ✓ durante
    1.5 s y se anuncia "Grabada en «Tarde lluviosa»" por la región viva.
  - **+** si la canción ya está en el casete: icono ✓, deshabilitado, `aria-label`
    "Ya está en el casete".

### 6.7. `PanelTop`

Pestaña "Lo más escuchado" (`GET /api/metrics/top`).

- Lista numerada (`<ol>`): número en Fraunces 22 px 800, título, artista, y "128
  reproducciones" en 13 px. Mismo botón **+** que el catálogo.
- **Estados:** cargando (esqueleto); vacío ("Nadie ha escuchado nada todavía. Pon play y
  estrena el ranking."); error (`Aviso` + "Reintentar").

### 6.8. `InterruptorLado`

Botón que alterna entre Lado A y Lado B.

- `<button role="switch">` con `aria-checked="true"` cuando está el Lado B.
- Texto visible "Lado A" o "Lado B" (el lado actual), Figtree 13 px 500, con un pequeño
  casete que se voltea. Alto 40 px, píldora con borde 2 px `currentColor`.
- Nombre accesible: el texto visible ("Lado A" / "Lado B"); no lleva `aria-label` que lo
  contradiga. El `title` dice "Cambiar a Lado B" / "Cambiar a Lado A".
- Ubicación: esquina superior derecha de la tienda en escritorio; en la casetera
  compacta en < 900 px. También en Acceso y Cabina.

### 6.9. `Aviso`

Mensaje en línea para información, éxito, degradado o error.

- Caja `--paper`, `--radius-m`, relleno `--space-3 --space-4`, borde izquierdo de 4 px
  según tipo: info `--ink`, éxito `--accent2` (con icono ✓), aviso/degradado `--accent2`
  (icono ⚠), error `--danger` (icono ✕). El texto siempre es `--ink`; el color nunca es
  el único indicador (hay icono y texto).
- Error y degradado usan `role="alert"`; info y éxito `role="status"`.
- Puede llevar una acción ("Reintentar") como botón de contorno.
- Los avisos de éxito desaparecen solos a los 4 s; los de error se quedan hasta que se
  resuelven o se cierran ("Cerrar", botón de icono de 40 px).

### 6.10. Botones y campos (genéricos)

| Variante | Aspecto |
|---|---|
| Principal | Fondo `--accent`, texto `--on-accent` Figtree 19 px 700, alto 44 px, píldora. Uno por vista o formulario. |
| Contorno | Transparente, borde 2 px `currentColor`, Figtree 15 px 500, alto 40 px. |
| Destructivo | Contorno en `--danger` con texto `--danger`. |
| Icono | Círculo de 40 px, `aria-label` obligatorio. |
| Campo de texto | `--paper`, borde 2 px `--ink` (o `--rule` en reposo dentro de tarjetas), alto 44 px, `--radius-s`, etiqueta visible arriba en 13 px 500. Error: borde `--danger` y mensaje debajo enlazado con `aria-describedby`. |

---

## 7. Vistas

### 7.1. Acceso (`/acceso`)

- Fondo `--bg`. Un casete grande centrado (máx. 420 px) cuya etiqueta dice "FLDSMDFR"
  en Caveat, y debajo una tarjeta `--paper` con pestañas "Entrar" / "Crear cuenta".
- Campos: Correo, Contraseña (mínimo 8 caracteres, con botón "Mostrar"), y en registro
  Nombre. Botón principal "Entrar" / "Crear cuenta".
- Errores del backend en `Aviso` arriba del formulario; errores de campo bajo cada campo.
- `InterruptorLado` arriba a la derecha.

### 7.2. Casetera (`/`)

La distribución de la sección 2. Requiere sesión. Una región viva `aria-live="polite"`
(oculta visualmente) anuncia "Grabada en …", "Casete creado", cambios de canción.

El único `<audio>` de la app vive en `App.vue`, fuera de las vistas: la música sigue al ir a
la cabina y volver. Al cerrar sesión (o si expira) el reproductor se detiene y se vacían los
casetes en memoria, para que el siguiente usuario no vea los del anterior.

### 7.3. Cabina de grabación (`/cabina`, solo admin)

El estudio donde se graban los masters del catálogo. Misma paleta, distribución de
dos columnas en escritorio:

```text
┌──────────────────────────────┬───────────────────────────────────────────┐
│ CABINA (--deck)              │ (--bg)                     [Lado A|Lado B]│
│ Cabina de grabación   (h1)   │ ( Canciones ) ( Usuarios )                │
│ ← Volver a la casetera       │                                           │
│                              │ ╭ Buscar canción ╮                        │
│ Resumen                      │ Granizo · Los Meteoros   Activa  [Editar] │
│ ┌──────┐┌──────┐┌──────┐     │ Monzón · Tormenta Norte  Activa  [Editar] │
│ │ 1 284││  37  ││  12  │     │ Neblina · Calma Chicha   Inactiva[Editar] │
│ │reprod.││canc. ││usuar.│     │                                           │
│ └──────┘└──────┘└──────┘     │                                           │
│                              │                                           │
│ Subir canción                │                                           │
│ ╭ Arrastra o elige archivo ╮ │                                           │
│ Título / Artista / Álbum     │                                           │
│ [ Subir canción ]            │                                           │
└──────────────────────────────┴───────────────────────────────────────────┘
```

- **Resumen** (`GET /api/metrics/summary`): tarjetas `--tape` con número en Fraunces
  28 px 800 y rótulo en 13 px. Estados: cargando (esqueleto), error (`Aviso`).
- **Subir canción:** zona de soltar con borde 2 px discontinuo `--deck-ink`, acepta
  `.mp3`, `.ogg`, `.wav` hasta 20 MB (se valida en el cliente antes de enviar y se
  muestra el error del servidor si lo rechaza). Campos Título, Artista, Álbum. Durante
  la subida: barra de progreso con porcentaje y botón "Subiendo…" deshabilitado. Éxito:
  `Aviso` "«Granizo» ya está en el catálogo."
- **Canciones:** tabla con título, artista, estado ("Activa" / "Inactiva", con texto,
  no solo color), y acciones "Editar" (edición en línea de título/artista/álbum) y
  "Desactivar" (confirmación en línea: "Los oyentes dejarán de verla en el catálogo.").
- **Usuarios:** buscador por correo y lista con rol; botón "Hacer admin" / "Quitar
  admin". El admin actual no puede quitarse su propio rol (botón deshabilitado con
  explicación "No puedes quitarte tu propio rol de admin.").
- Usuarios no admin que entran a `/cabina` se redirigen a `/` con un `Aviso`: "La cabina
  de grabación es solo para administradores."
- En < 900 px: se apila; pestañas "Resumen / Subir / Canciones / Usuarios".

---

## 8. Accesibilidad

### 8.1. Objetivo

WCAG 2.2 nivel AA. Contrastes medidos y restricciones en la sección 3.2.

### 8.2. Foco visible

```css
:focus-visible {
  outline: 3px solid var(--accent2);
  outline-offset: 2px;
  box-shadow: 0 0 0 2px var(--ink);
}
```

Anillo de 3 px en `--accent2` separado 2 px del elemento, con un anillo interior de 2 px
en `--ink` que rellena esa separación. El doble anillo es necesario porque `--accent2`
sobre `--bg` en el Lado A no llega a 3:1. Implementado en `base.css`; los componentes no
lo redefinen.

### 8.3. Otras reglas

- **Botones de icono:** `aria-label` obligatorio, en español y con el objeto cuando
  aporta ("Grabar «Granizo» en el casete", "Quitar «Monzón» del casete").
- **Teclado:** todo se puede hacer sin ratón. Orden de tabulación de la sección 2.1.
  Pestañas con el patrón ARIA `tablist` (flechas para moverse, Tab para entrar al panel).
- **Semántica:** un `h1` por vista; listas como `<ul>`/`<ol>`; regiones `<main>`,
  `<section aria-labelledby>`.
- **Movimiento reducido:** con `prefers-reduced-motion: reduce` los carretes no giran,
  no hay `transform` al pulsar ni transiciones de más de 0 ms. Implementado de forma
  global en `base.css`.
- **El color nunca es el único indicador:** estado de canción, activo/inactivo, errores
  y casete activo llevan además texto, icono o contorno.
- **Zoom:** usable al 200 % y a 320 px de ancho sin scroll horizontal.
- **Idioma:** `<html lang="es">`.

---

## 9. Tono de los textos

Español de México, cercano y breve. **Voz activa**, segunda persona (tú), **sentence
case**, sin signos de exclamación salvo celebraciones reales. Los verbos de la metáfora
del casete se usan en las acciones principales.

| Situación | Sí | No |
|---|---|---|
| Agregar canción | "Grabar en el casete" | "Agregar a playlist", "Añadir" |
| Crear playlist | "Crear casete" | "Nueva playlist", "Guardar" |
| Casete vacío | "Este casete está vacío. Busca una canción y pulsa + para grabarla." | "No hay elementos." |
| Sin casetes | "Aún no tienes casetes. Crea el primero con «Nuevo casete»." | "Lista vacía" |
| Búsqueda sin resultados | "No encontramos canciones con «xyz»." | "0 resultados" |
| Error de red | "No pudimos cargar el catálogo. Revisa tu conexión y vuelve a intentarlo." | "Error 500" |
| Canción no disponible | "No disponible" | "ERROR: canción inactiva" |
| Modo degradado | "Mostramos la última versión guardada; algunos datos pueden estar desactualizados." | "Servicio degradado" |
| Éxito al grabar | "Grabada en «Tarde lluviosa»" | "¡La canción fue agregada exitosamente!" |
| Cargando | "Cargando canciones…", "Grabando…" | "Por favor espere" |
| Borrar | "¿Borrar «Correr»? Esta acción no se puede deshacer." | "¿Está seguro?" |
| Sesión expirada | "Tu sesión terminó. Entra de nuevo para seguir escuchando." | "401 Unauthorized" |

Reglas:

- Los errores dicen qué pasó y qué puede hacer el usuario; nunca muestran códigos
  HTTP ni trazas. Si el backend devuelve `error.message` (ya en español), se usa tal cual.
- Comillas latinas «» para nombres de casetes y canciones.
- Puntos suspensivos tipográficos (…) en estados de carga.
- Números con separador de miles en métricas ("1 284 reproducciones").
