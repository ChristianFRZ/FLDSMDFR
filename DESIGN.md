# DESIGN.md · MELOXO

Fuente única de verdad del sistema visual de **MELOXO**: concepto, distribución, color,
tipografía, iconos, logo, componentes, accesibilidad y tono de los textos. Si un componente
de `ui/` contradice este documento, se corrige el componente o se actualiza este documento
en el mismo cambio; nunca se deja la contradicción.

MELOXO es el nombre visible del producto. El repositorio, los paquetes y los servicios de
Docker conservan el nombre técnico FLDSMDFR.

| Qué                               | Dónde                                                                                                                 |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Diseño de referencia (Figma)      | `cVr6xEoHkTZJyeDrngHxIL`, nodo `39:2` ("MELOXO · Tu casetera")                                                        |
| Tokens                            | `ui/src/styles/tokens.css`                                                                                            |
| Estilos base y piezas compartidas | `ui/src/styles/base.css`                                                                                              |
| Logo                              | `ui/src/assets/logo-meloxo.svg`, `logo-meloxo-pequeno.svg`, `ui/src/components/LogoMeloxo.vue`, `ui/public/favicon.*` |
| Iconos                            | `ui/src/components/icons/` (Lucide, licencia ISC)                                                                     |
| Diseño y plan del rediseño        | `docs/superpowers/specs/2026-10-31-meloxo-rediseno-design.md`                                                         |

---

## 1. Concepto: tu casetera

MELOXO es **una casetera de música en streaming** con identidad mexicana. Cada playlist es
un **casete**; agregar una canción es **grabarla**. La interfaz es oscura, cálida y sobria:
fondo oliva, texto y acentos en mostaza, una serif con carácter para los títulos y una sans
neutra para todo lo demás.

Por qué así:

- **Hace visible el modelo de datos.** Casete = playlist, grabar = agregar, colaborativo =
  casete compartido por enlace. La metáfora se mantiene en los textos.
- **Identidad propia.** El logo Sol‑carrete une la Piedra del Sol con un carrete de casete;
  la paleta mostaza/oliva evita el "clon de Spotify" aunque la distribución sea familiar.
- **Muestra el streaming.** La vista Streaming enseña los fragmentos descargados por HTTP
  Range, el bitrate y las métricas del sistema; los carretes giran mientras suena.

### 1.1. Anti‑patrones (no hacer)

- **Colores escritos a mano en componentes.** Todo color sale de un token `var(--…)`.
- **Emojis o glifos como iconos.** Solo iconos SVG de `Icono.vue` dentro de un botón o
  enlace con nombre accesible.
- **Botones que parecen activos y no hacen nada.** Lo único visible sin función son
  Letras, Dispositivos y Plus, siempre con `aria-disabled="true"` y "Próximamente".
- **Modales para todo.** Crear casete, renombrar, grabar en casete y compartir se
  resuelven en línea o en un popover junto al elemento. Solo "Borrar casete" pide
  confirmación.
- **Texto mostaza sobre `--surface-active`.** No llega a AA; ahí se usa `--ink-on-active`.
- **Mayúsculas sostenidas en frases.** Las versalitas solo en antetítulos cortos
  (`.antetitulo`); los mensajes van en *sentence case*.
- **Spinners de pantalla completa.** La carga se muestra con esqueletos en su lugar.
- **Tema claro o interruptor de tema.** MELOXO tiene un solo tema oscuro.

---

## 2. Distribución

### 2.1. Escritorio (≥ 900 px)

```text
┌──────────────┬─────────────────────────────────────────────────────┐
│ Logo MELOXO  │ ‹ ›  [ ¿Qué te apetece escuchar?   Ctrl K ]  Rol 🔔 AL │  80 px
│              ├─────────────────────────────────────────────────────┤
│ Inicio       │                                                     │
│ Catálogo     │                Vista activa (RouterView)            │
│ Streaming    │                                                     │
│ ──────────   │                                                     │
│ TUS CASETES +│                                                     │
│ (Casetes|Art)│                                                     │
│ lista…       │                                                     │
│              │                                                     │
│ [Cabina]     │                                                     │
├──────────────┴─────────────────────────────────────────────────────┤
│ Portada Título ♡ │ ⤨ ⏮ ⏯ ⏭ ⟲  ──●──────── │ 🎤 ☰ 🖥 🔊 ── ⤢       │  96 px
└────────────────────────────────────────────────────────────────────┘
```

- Barra lateral de 232 px (`--sidebar-width`) con borde derecho `--rule`.
- Encabezado de 80 px con borde inferior; contenido con 32 px de margen lateral.
- Reproductor fijo de 96 px con borde superior.
- La tarjeta "Cabina de grabación · Administrador" solo aparece a administradores.

### 2.2. Pantallas angostas (< 900 px)

La barra lateral desaparece. Abajo, encima del reproductor compacto (portada, título,
play/pausa, corazón y barra de progreso fina), aparece una barra de navegación con
Inicio, Catálogo, Biblioteca y Streaming. La biblioteca vive en `/biblioteca`. El
encabezado conserva búsqueda, campana y avatar. Sin scroll horizontal a 320 px.

---

## 3. Color

Un solo tema oscuro, tomado del Figma y ajustado para cumplir WCAG 2.2 AA.

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#3b3932` | Fondo general, tarjetas |
| `--surface` | `#6e6547` | Bordes, separadores, pistas de barras |
| `--surface-active` | `#6e6547` | Destino/fila activa, tarjeta de la Cabina, botón play |
| `--accent` | `#d4ae35` | Mostaza: iconos, progreso, badge, botón principal |
| `--accent-strong` | `#e2c050` | Hover del botón principal |
| `--on-accent` | `#3b3932` | Texto sobre `--accent` |
| `--ink` | `#d4ae35` | Texto principal sobre `--bg` |
| `--ink-muted` | `#b8a35e` | Texto secundario (artista, detalles, tiempos) |
| `--ink-on-active` | `#f8e9b5` | Texto e iconos sobre `--surface-active` |
| `--chip-ink` | `#f5e8f1` | Texto de las pastillas Casetes / Artistas |
| `--danger` | `#ff8a6b` | Errores y "Borrar" |
| `--focus` | `#f8e9b5` | Anillo de foco |

### 3.1. Contraste medido

| Par | Contraste | Uso permitido |
|---|---|---|
| `--ink` / `--bg` | 5.45:1 | Todo texto |
| `--ink-muted` / `--bg` | 4.64:1 | Todo texto (el `#a18c48` del Figma daba 3.5:1 y se aclaró) |
| `--on-accent` / `--accent` | 5.45:1 | Texto de botones principales y badges |
| `--ink-on-active` / `--surface-active` | 4.79:1 | Texto sobre filas y destinos activos |
| `--chip-ink` / `--surface-active` | 4.89:1 | Pastilla seleccionada |
| `--accent` / `--surface-active` | 2.74:1 | **Solo** iconos y elementos no textuales grandes |

---

## 4. Tipografía

- **Display:** Lora Variable (`--font-display`), peso 400. Marca, saludo, títulos de
  sección y de la tarjeta de la Cabina.
- **Texto:** Inter Variable (`--font-body`). Todo lo demás.

| Elemento | Fuente | Tamaño | Peso | Otros |
|---|---|---|---|---|
| Marca MELOXO | Lora | 24 px | 400 | `letter-spacing: -1.5px` |
| Saludo (`h1`) | Lora | 30 px | 400 | |
| Título de sección (`h2`) | Lora | 28 px | 400 | "Vuelve a lo que te gusta" |
| Tarjeta Cabina (`h3`) | Lora | 20 px | 400 | `line-height: 1.2` |
| Antetítulo | Inter | 10–12 px | 600 | Versalitas, `letter-spacing: 1.2–1.6px` |
| Navegación | Inter | 14 px | 400 (600 activo) | |
| Título de canción | Inter | 13 px | 500–600 | |
| Artista, detalles | Inter | 11 px | 400 | `--ink-muted` |
| Tiempos del reproductor | Inter | 9 px | 400 | `--ink-muted`, cifras tabulares |

---

## 5. Logo: Sol‑carrete

El sol de la Piedra del Sol (disco con ocho rayos triangulares) cuya ventana central es el
carrete de un casete (anillo con seis dientes). Une la cultura mexicana con la música en
una sola forma de una tinta.

- **Construcción:** lienzo 256 × 256; disco r = 65 con ventana r = 38; ocho rayos de base
  26° a r = 73 y punta a r = 118 (ligero rebase óptico); carrete: anillo r = 26/17 con seis
  dientes hacia dentro.
- **Corte pequeño** (`logo-meloxo-pequeno.svg`): bajo 24 px se quitan los dientes y se
  engrosan los anillos para que no se empasten. `LogoMeloxo.vue` lo elige solo.
- **Color:** mostaza `--accent` sobre `--bg`. A una tinta en negro o blanco cuando el
  fondo lo pida. Nunca con degradados, sombras ni contorno.
- **Bloque de marca:** símbolo 29 px + "MELOXO" en Lora 24 px + punto de 6 px, dentro de una
  píldora con borde `--rule` y radio 12 px (barra lateral). En Acceso, símbolo 56 px.
- **Zona de respeto:** la altura de un rayo alrededor del símbolo.
- **Tamaño mínimo:** 16 px (favicon) con el corte pequeño.
- **Favicon:** `favicon.svg` y `favicon.ico` (16/32/48) con el corte pequeño sobre un
  cuadrado `--bg` de esquinas redondeadas.
- **Usos indebidos:** deformarlo, rotarlo, cambiar el número de rayos, ponerlo sobre
  fotografías sin fondo, recolorearlo fuera de la paleta.

---

## 6. Espaciado, tamaños y forma

- Escala: 4, 8, 12, 16, 24, 32 px (`--space-1` … `--space-6`).
- Radios: 4 px portadas pequeñas, 6 px filas y portadas de la biblioteca, 12 px tarjetas,
  100 px píldoras y avatares.
- Portadas: 42 px biblioteca, 40 px tarjetas de Inicio, 44 px "Vuelve a lo que te gusta",
  58 px reproductor. Sin portada: marcador con iniciales sobre `--surface-active`.
- Objetivos táctiles de al menos 32 × 32 px (44 px en móvil).

---

## 7. Componentes

### 7.0. Estados comunes

| Estado | Tratamiento |
|---|---|
| Hover | Fondo `color-mix(--surface 45%)` en botones de icono, texto y contorno; `--accent-strong` en el principal. Solo con `hover: hover`. |
| Foco | Anillo de 2 px `--focus` separado 2 px (`:focus-visible`), definido en `base.css`. |
| Activo | Filas y destinos con fondo `--surface-active` y texto `--ink-on-active`, más un indicador no cromático (punto, icono `audio-lines` o `aria-current`). |
| Deshabilitado | Opacidad 0.45, `cursor: not-allowed`, `disabled` o `aria-disabled="true"`. |
| Próximamente | Igual que deshabilitado, enfocable, con `title`/tooltip "Próximamente". |
| Cargando | Esqueletos (`.esqueleto-fila`) con la forma del contenido; botones con texto en gerundio y `aria-busy`. |
| Vacío | Una o dos frases que dicen qué hacer y, si aplica, el botón para hacerlo. |
| Error | `AvisoEnLinea` en el lugar del contenido con el mensaje del backend y "Reintentar". |
| No disponible | Canción desactivada: opacidad 0.6, etiqueta "No disponible", sin reproducir. |

### 7.1. Barra lateral (`BarraLateral`)

Bloque de marca, navegación (icono 20 px + texto 14 px, alto 44 px, radio 6 px; el
destino activo lleva fondo `--surface-active`, texto `--ink-on-active`, peso 600 y un
punto de 5 px), separador, biblioteca y, para administradores, la tarjeta de la Cabina
(fondo `--surface-active`, icono `disc-3`, título en Lora 20 px, enlace "Abrir Cabina ↗").

### 7.2. Biblioteca (`Biblioteca`)

Cabecera "TUS CASETES" con botón `+` (crear en línea). Pastillas "Casetes" / "Artistas"
(patrón ARIA `tablist`). Filas de 42 px de portada, nombre 12 px y detalle 10 px
("Casete · 12 canciones", "Casete · Colaborativo"). "Tus favoritas" va primero.

### 7.3. Encabezado (`EncabezadoSuperior`)

Flechas atrás/adelante, buscador en píldora de 480 px con atajo "Ctrl K" (⌘K en macOS),
etiqueta de rol ("Administrador" u "Oyente"), etiqueta "Plus" deshabilitada, campana con
contador y avatar de 34 px con iniciales y menú "Cerrar sesión".

### 7.4. Reproductor (`Reproductor`)

Izquierda: portada 58 px, título, artista y corazón. Centro: aleatorio, anterior, botón
play/pausa redondo de 34 px en `--surface-active`, siguiente y repetir (icono `repeat-1`
en modo "una"); debajo la barra de progreso con tiempos. Derecha: Letras y Dispositivos
(Próximamente), Cola (`list-music`), volumen y pantalla completa (`maximize-2`). La barra
de progreso dibuja los fragmentos descargados (`audio.buffered`).

### 7.5. Fila de canción (`FilaCancion`)

Portada, título, artista, `audio-lines` si suena, duración `m:ss` y menú `…` (Grabar en
casete…, Añadir a favoritas/Quitar, Añadir a la cola, Reproducir a continuación). La fila
que suena usa el estado activo.

### 7.6. Avisos (`Campana`, `PanelAvisos`, `TarjetaAviso`)

Tarjetas de 12 px de radio con cabecera (icono o iniciales en círculo de 28 px, tipo en
versalitas y tiempo relativo), título, texto y acciones. Lanzamiento: "Escuchar ahora →".
Invitación: botón principal "Aceptar" y texto "Ignorar". Badge mostaza con el número de
no leídos.

### 7.7. Otros

- `SelectorGrabar`: popover con los casetes donde puedes grabar, el último usado primero.
- `PanelCola`: panel lateral derecho con lo que sigue; reordenar y quitar.
- `SonandoAhora`: vista de pantalla completa con portada grande y controles.
- `VentanaCarretes`: ventanita de casete con dos carretes que giran mientras suena.
- `Aviso` (toast) y `AvisoEnLinea`: mensajes efímeros y en el lugar del contenido.

---

## 8. Vistas

| Ruta | Vista | Contenido |
|---|---|---|
| `/` | Inicio | "TU CASETERA DIARIA", saludo, más escuchadas, artistas más escuchados, Crear casete, Avisos, "Vuelve a lo que te gusta" |
| `/catalogo` | Catálogo | Búsqueda, grabar, seguir artistas |
| `/streaming` | Streaming | Carretes, fragmentos, bitrate, métricas |
| `/casete/:id` | Casete | Lista, reordenar, portada, compartir, miembros |
| `/favoritas` | Tus favoritas | Canciones con corazón |
| `/historial` | Historial | Todo lo escuchado, paginado |
| `/biblioteca` | Biblioteca | Solo en móvil |
| `/invitacion/:token` | Invitación | Reclama el enlace y lleva a Avisos |
| `/cabina` | Cabina (admin) | Subir canciones y portadas, retirar temas, roles |
| `/acceso` | Acceso | Entrar o crear cuenta, con el logo |

---

## 9. Accesibilidad

- **Objetivo:** WCAG 2.2 AA (contrastes en §3.1).
- **Foco visible** siempre; nunca `outline: none` sin reemplazo.
- **Botones de icono** con `aria-label` en español y el objeto cuando aporta
  ("Grabar «Cariño» en un casete").
- **Teclado:** todo se puede hacer sin ratón. Pestañas con `tablist` y flechas. Ctrl K
  enfoca la búsqueda; la barra espaciadora reproduce o pausa si no estás escribiendo.
- **Semántica:** un `h1` por vista, listas como `<ul>`/`<ol>`, regiones `<nav>`, `<main>`,
  `<aside>` y `<section aria-labelledby>`; `aria-current="page"` en la navegación.
- **Movimiento reducido:** sin giro de carretes, sin transiciones (global en `base.css`).
- **El color nunca es el único indicador.**
- **Zoom:** usable al 200 % y a 320 px sin scroll horizontal. **Idioma:** `lang="es"`.

---

## 10. Tono de los textos

Español de México, cercano y breve. Voz activa, segunda persona (tú), *sentence case*, sin
signos de exclamación salvo celebraciones reales. Verbos del casete en las acciones.

| Situación | Sí | No |
|---|---|---|
| Agregar canción | "Grabar en casete" | "Agregar a playlist" |
| Crear playlist | "Crear casete" | "Nueva playlist" |
| Casete vacío | "Este casete está vacío. Busca una canción en el Catálogo y grábala." | "No hay elementos." |
| Sin historial | "Aún no escuchas nada. Empieza en el Catálogo." | "Lista vacía" |
| Búsqueda sin resultados | "No encontramos canciones con «xyz»." | "0 resultados" |
| Error de red | "No pudimos cargar el catálogo. Revisa tu conexión y vuelve a intentarlo." | "Error 500" |
| Éxito al grabar | "Grabada en «Tardes de verano»" | "¡Agregada exitosamente!" |
| Invitación ya aceptada | "Ya formas parte de este casete." | "409 Conflict" |
| Enlace inválido | "Este enlace ya no es válido." | "Token not found" |
| Sin acceso | "Ya no tienes acceso a este casete." | "Forbidden" |
| Próximamente | "Próximamente" | "No implementado" |
| Borrar | "¿Borrar «Correr»? Esta acción no se puede deshacer." | "¿Está seguro?" |

Reglas: los errores dicen qué pasó y qué hacer, sin códigos HTTP; se usa `error.message`
del backend tal cual. Comillas latinas «» para casetes y canciones. Puntos suspensivos
tipográficos (…) en cargas. Cifras compactas en métricas (1.2k) y tiempos relativos
("hace 2 h") con `Intl`.
