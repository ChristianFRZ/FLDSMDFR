# Capturas y video de demo

Generan las imágenes reales de la app que usa la presentación. Salida en [`../assets/`](../assets): `cap-inicio.png`, `cap-casete.png`, `cap-reproductor.png` (1600×900 a doble densidad), `demo.mp4` (1280×720, sin audio) y `demo-fotograma.png` (segundo 3 del video).

## Requisitos

- El stack arriba y la semilla corrida, desde la raíz del repositorio: `docker compose up -d --build` y `docker compose run --rm seed python -m seed all`.
- `DEMO_PASSWORD` en `.env`: la spec la lee del entorno y nunca la escribe en ningún archivo. Inicia sesión como `oyente00@demo.meloxo.dev`.
- `npm install` en `docs/presentacion/` y `npx playwright install chromium` en `frontend/`.

## Regenerar

```bash
cd frontend
set -a; . ../.env; set +a
npx playwright test --config ../docs/presentacion/capturas/playwright.config.ts
```

La spec usa el Playwright de `frontend/` y su propia configuración, sin tocar `frontend/playwright.config.ts`. Al empezar borra los casetes "Para el profe" de corridas anteriores de ese oyente; la segunda prueba crea uno nuevo, así que cada corrida parte igual. Deja `assets/demo.webm`.

Después, desde `docs/presentacion/`, convierte con los binarios de `ffmpeg-static` y `ffprobe-static`:

```bash
F=$(node -p "require('ffmpeg-static')"); P=$(node -p "require('ffprobe-static').path")
$F -y -i assets/demo.webm -c:v libx264 -pix_fmt yuv420p -an assets/demo.mp4
$F -y -ss 3 -i assets/demo.mp4 -frames:v 1 assets/demo-fotograma.png
$P -v error -show_entries stream=codec_name:format=duration,size -of default=nw=1 assets/demo.mp4
```

El video debe ser h264, durar 45 s o menos y pesar 25 MB o menos. Tema oscuro en todo.
