# Marca MELOXO

Guía de uso del logo y de la identidad visual, pensada para todo el equipo y no solo para quien diseña.

## El logo

**Idea:** un casete hecho de papel rasgado, mitad cinta y mitad nota dedicada. El casete compartido es la unidad central de MELOXO, y las dedicatorias son lo que lo hacen personal. La X chueca de la palabra aporta el desorden ochentero.

| Versión | Archivo | Cuándo usarla |
| --- | --- | --- |
| Horizontal (principal) | [`meloxo-horizontal-color-dark.svg`](svg/meloxo-horizontal-color-dark.svg) | Encabezados y barra lateral de la app |
| Apilada | [`meloxo-stacked-color-dark.svg`](svg/meloxo-stacked-color-dark.svg) | Pantallas de acceso y espacios cuadrados |
| Símbolo | [`meloxo-symbol-color-dark.svg`](svg/meloxo-symbol-color-dark.svg) | Avatar, ícono y espacios reducidos |
| Símbolo pequeño | [`meloxo-symbol-small.svg`](svg/meloxo-symbol-small.svg) | Menos de 32 px, con un dibujo simplificado |
| Solo palabra | [`meloxo-wordmark-color-dark.svg`](svg/meloxo-wordmark-color-dark.svg) | Cuando el símbolo ya está cerca |

## Espacio libre

Deja alrededor del logo un margen igual al **diámetro de un agujero del símbolo**. Ese margen crece y se reduce junto con el logo.

## Tamaño mínimo

| Versión | Pantalla | Impresión |
| --- | --- | --- |
| Horizontal | 96 px de ancho | 25 mm de ancho |
| Símbolo | 32 px | 8 mm |
| Símbolo pequeño | 16 px | 5 mm |

## Color

| Nombre | HEX | RGB | CMYK aproximado | Rol |
| --- | --- | --- | --- | --- |
| Tinta | `#141317` | 20, 19, 23 | 13, 17, 0, 91 | Fondo principal |
| Papel | `#F4F1EA` | 244, 241, 234 | 0, 1, 4, 4 | Texto sobre tinta, notas |
| Rosa | `#FF3D8B` | 255, 61, 139 | 0, 76, 45, 0 | Color de marca, acción principal |
| Amarillo | `#FFD233` | 255, 210, 51 | 0, 18, 80, 0 | Cinta adhesiva, avance, filtros activos |
| Turquesa | `#00D1BE` | 0, 209, 190 | 100, 0, 9, 18 | Estados activos |
| Cobalto | `#4A5CFF` | 74, 92, 255 | 71, 64, 0, 0 | Solo en casetes y portadas |

Los valores CMYK son una conversión matemática, no una prueba de imprenta. No se definieron equivalentes Pantone.

### Combinaciones aprobadas

| Logo | Fondo | Contraste |
| --- | --- | --- |
| Rosa y papel (`-color-dark`) | Tinta | 5.5:1 en el símbolo |
| Papel (`-reversed`) | Tinta | 16.4:1 |
| Tinta (sin sufijo) | Papel o blanco | 16.4:1 |
| Rosa y tinta (`-color-light`) | Papel | 3.0:1 en el símbolo. Solo para usos decorativos o de gran tamaño |

Sobre fondo claro, prefiere la versión en tinta.

## Tipografía

- **Títulos:** Unbounded, peso 800. Licencia SIL Open Font.
- **Dedicatorias y etiquetas de casete:** Caveat, peso 600. Licencia SIL Open Font.
- **Texto e interfaz:** fuente del sistema (`-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif`), definida en [`tokens.css`](../../frontend/src/styles/tokens.css).

La palabra MELOXO del logo está dibujada a medida. No la escribas con una fuente: usa los [archivos SVG](svg/README.md).

## Qué no hacer

- No estires ni deformes el logo.
- No lo rotes: lo chueco ya está en el dibujo.
- No uses colores fuera de la paleta.
- No añadas sombras, contornos ni degradados.
- No separes ni reacomodes sus partes.
- No lo pongas sobre fondos cargados sin un contenedor liso.

## Carpetas

| Carpeta | Contenido |
| --- | --- |
| [`svg/`](svg/README.md) | Archivos maestros vectoriales |
| [`png/`](png/README.md) | Exportaciones listas para documentos |
| [`web/`](web/README.md) | Favicon, íconos y manifiesto para la app |
| [`presentation/`](presentation/README.md) | Presentación de la marca con ejemplos de uso |

## Licencia

La [licencia MIT](../../LICENSE) del repositorio cubre el código, no esta carpeta. El nombre, el logo y estos archivos no se pueden reutilizar sin permiso del equipo.

## Pendientes

- Buscar si la marca ya está registrada antes de usar el nombre o el logo fuera del ámbito universitario.
- Definir Pantone y hacer una prueba de color impresa, si algún día se imprime.
