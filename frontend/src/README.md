# Código de la interfaz

Código en React y TypeScript. Cada carpeta tiene su propio README.

| Carpeta o archivo | Contenido |
| --- | --- |
| [`main.tsx`](main.tsx) | Arranque de la app y carga de las fuentes, instaladas con Fontsource |
| [`App.tsx`](App.tsx) | Rutas |
| [`api/`](api/README.md) | Cliente HTTP y tipos |
| [`auth/`](auth/README.md) | Sesión y rutas por rol |
| [`pages/`](pages/README.md) | Una pantalla por ruta |
| [`components/`](components/README.md) | Piezas compartidas |
| [`player/`](player/README.md) | Reproductor |
| [`charts/`](charts/README.md) | Gráficas |
| [`styles/`](styles/README.md) | Colores y estilos |
| [`assets/`](assets/README.md) | Logos |
| [`test-setup.ts`](test-setup.ts), [`test-utils.tsx`](test-utils.tsx) | Base de las pruebas con Vitest |

Las pruebas viven junto a lo que prueban, como [`queue.test.ts`](player/queue.test.ts) al lado de [`queue.ts`](player/queue.ts).
