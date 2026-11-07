# Interfaz web

La app que usa la gente: una SPA hecha con React, Vite y TypeScript. Como es una sola página, navegar no recarga nada y el audio sigue sonando. En producción, FastAPI sirve los archivos compilados, así que no hace falta un servidor aparte.

Usa Node 24, la misma versión del [`Dockerfile`](../Dockerfile).

## Comandos

Todos se corren dentro de `frontend/`:

| Comando | Qué hace |
| --- | --- |
| `npm install` | Instala las dependencias |
| `npm run dev` | Inicia el servidor de desarrollo, que redirige `/api` a `localhost:8080` |
| `npm test` | Corre las pruebas con Vitest |
| `npm run e2e` | Corre las [pruebas de navegador](e2e/README.md) con Playwright |
| `npm run build` | Revisa los tipos y compila en `dist/` |

`npm run dev` y `npm run e2e` necesitan el backend en marcha. Para levantarlo, corre `docker compose up -d` desde la raíz del repositorio.

## Carpetas

| Carpeta | Contenido |
| --- | --- |
| [`e2e/`](e2e/README.md) | Pruebas de navegador |
| [`public/`](public/README.md) | Favicons y manifiesto |
| [`src/`](src/README.md) | Código de la interfaz |
| [`src/api/`](src/api/README.md) | Cliente HTTP y tipos |
| [`src/assets/`](src/assets/README.md) | Logos |
| [`src/auth/`](src/auth/README.md) | Sesión |
| [`src/charts/`](src/charts/README.md) | Gráficas y exportación |
| [`src/components/`](src/components/README.md) | Piezas reutilizables |
| [`src/pages/`](src/pages/README.md) | Pantallas |
| [`src/player/`](src/player/README.md) | Reproductor |
| [`src/styles/`](src/styles/README.md) | Variables de diseño y estilos |
