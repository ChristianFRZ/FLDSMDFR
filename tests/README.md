# tests

Pruebas que miran el repositorio entero, no un servicio.

- `test_readmes.py`: exige un `README.md` en cada carpeta. Ignora carpetas ocultas, las carpetas cuyo contenido entero excluye `.gitignore` (por ejemplo `media`), `node_modules`, `dist`, `__pycache__`, `.venv`, `*.egg-info` y las subcarpetas de `docs/brand` (logos exportados, los explica `docs/brand/README.md`).

```bash
.venv/bin/pytest tests -q
```
