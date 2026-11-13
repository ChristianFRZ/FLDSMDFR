# Pruebas de edge

- `test_routes.py`: no necesita el stack. Importa la aplicación de cada servicio, lista sus rutas públicas `/api/*` y resuelve cada una con las reglas de `location` de nginx sobre `edge/nginx.conf`. Falla si una ruta no llega a su servicio dueño, si llega a dos o a ninguno.
- `test_stack.py`: marcada `stack`, necesita el stack arriba en `http://localhost:8080`. Comprueba que `/internal/*` da 404, las peticiones `Range` (206/206/416) y el error JSON con un servicio caído. Esa prueba detiene `meloxo-playback-metrics-1` y siempre lo vuelve a arrancar.

```bash
.venv/bin/pytest edge/tests -q -m "not stack"          # sin stack
docker compose up -d --build
.venv/bin/pytest edge/tests -q -m stack                # con stack
```
