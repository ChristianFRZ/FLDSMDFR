# Estilos

[`tokens.css`](tokens.css) tiene los colores y fuentes de la [guía de marca](../../../docs/brand/README.md), y [`app.css`](app.css) los estilos de la app.

## Temas

Hay dos temas, oscuro (el de siempre) y claro. Los elige cada persona en su perfil, o sigue al sistema; [`theme.ts`](../theme.ts) pone `data-theme` en `<html>` y [`tokens.css`](tokens.css) define los colores de cada uno.

- `--ink` y `--paper` son colores fijos de la marca: la tinta de lo que va sobre rosa, amarillo o teal, y el papel de las notas. No cambian con el tema.
- `--bg`, `--panel`, `--panel-2`, `--line`, `--text`, `--mute` y `--edge` (el color de los bordes) sí cambian. Usa estos en estilos nuevos, no `--paper` ni `--ink`.
- `--yellow-ink`, `--teal-ink`, `--pink-ink` y `--danger` son los acentos para texto, íconos y bordes sobre un panel. En claro son más oscuros para que se lean (más de 4.5:1 sobre los paneles). El amarillo, el rosa y el teal de siempre son para rellenos.
- Las tarjetas de gráficas (`.chart`) siguen el tema. En claro usan `--panel`; la paleta de series se validó sobre las dos superficies y los colores de ejes, rejilla y tooltip se fijan en [`charts/index.ts`](../charts/README.md) según el tema vigente.

Las animaciones del logo (`.logo-anim*` en [`app.css`](app.css)) repiten las duraciones de `DURATIONS` en [`motion.ts`](../components/motion.ts): si cambias una, cambia la otra. Con `prefers-reduced-motion: reduce` se anulan y se muestra el logo quieto.

El diseño cambia a teléfono a los 900 px. [`useCompact.ts`](../player/useCompact.ts) repite ese valor, así que si lo cambias aquí, cámbialo también allá.

La caída del casete al crearlo (`.tape-drop` y `.tape-drop-overlay` en [`app.css`](app.css)) dura lo mismo que `DURATIONS.drop` en [`motion.ts`](../components/motion.ts) (900 ms): si cambias una, cambia la otra. Usa la misma capa (`z-index: 70`) que las animaciones del logo y con `prefers-reduced-motion: reduce` el casete aparece quieto.
