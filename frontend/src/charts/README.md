# Gráficas

Base común de las estadísticas: Chart.js con los colores y estilos de MELOXO.

| Archivo | Para qué sirve |
| --- | --- |
| [`index.ts`](index.ts) | Registra Chart.js y fija la paleta `SERIES` y los estilos de barras y líneas |
| [`ChartCanvas.tsx`](ChartCanvas.tsx) | Crea y destruye la gráfica sobre un `<canvas>` |
| [`ChartCard.tsx`](ChartCard.tsx) | Tarjeta que carga los datos y muestra la gráfica, la tabla, el estado vacío o el error |
| [`definitions.ts`](definitions.ts) | Gráficas concretas, columnas de sus tablas y utilidades como `fillDays` |
| [`export.ts`](export.ts) | Guarda un reporte como CSV (desde el backend) o PNG (desde la gráfica) |

## Reglas

- Una gráfica que falla muestra "Datos no disponibles por ahora" y el resto de la página sigue funcionando (criterio F7.3 del [PRD](../../../docs/prd.md#f7-panel-web-y-gráficas)).
- Toda gráfica ofrece una tabla con los mismos datos.
- Los colores de `SERIES` van siempre en ese orden y son cuatro como máximo. Son tonos derivados de la marca, porque los colores puros quedan fuera de la banda de luminosidad que funciona sobre el panel oscuro.
- Una gráfica con una sola serie no lleva leyenda; con dos o más, siempre.
