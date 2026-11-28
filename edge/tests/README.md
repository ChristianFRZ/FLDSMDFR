# Pruebas de edge

- `test_routes.py`: no necesita el stack. Importa la aplicación de cada servicio, lista sus rutas públicas `/api/*` y resuelve cada una con las reglas de `location` de nginx sobre `edge/nginx.conf`. Falla si una ruta no llega a su servicio dueño, si llega a dos o a ninguno. También comprueba la sesión en el gateway: `auth_request` activo por defecto, que las rutas sin sesión sean exactamente las que los servicios dejan sin `security` (más el stream), el mapa de roles, las cabeceras de identidad y los JSON de 401/403.
- `test_stack.py`: marcada `stack`, necesita el stack arriba en `http://localhost:8080`. Comprueba que `/internal/*` da 404, las peticiones `Range` (206/206/416), el error JSON con un servicio caído, los 401 y 403 del gateway, que las cabeceras de identidad falsas no dan acceso, que con `gateway-auth` caído las rutas protegidas dan 503, que con una réplica de catálogo detenida se pierde a lo sumo una petición, y que `POST /api/playbacks` da `202` (lo encola catálogo). Las pruebas de caída detienen `meloxo-playback-metrics-1`, `meloxo-gateway-auth-1` o una réplica de catálogo, y siempre los vuelven a arrancar.

```bash
.venv/bin/pytest edge/tests -q -m "not stack"          # sin stack
docker compose up -d --build
.venv/bin/pytest edge/tests -q -m stack                # con stack
```
