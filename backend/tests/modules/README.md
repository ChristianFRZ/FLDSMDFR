# Pruebas de los módulos

Hay una carpeta por cada módulo de [`app/modules/`](../../app/modules/README.md), con el mismo nombre. Todas corren contra un PostgreSQL real.

| Carpeta | Módulo que prueba |
| --- | --- |
| [`analytics/`](analytics/README.md) | [`analytics`](../../app/modules/analytics/README.md) |
| [`catalog/`](catalog/README.md) | [`catalog`](../../app/modules/catalog/README.md) |
| [`playback/`](playback/README.md) | [`playback`](../../app/modules/playback/README.md) |
| [`playlists/`](playlists/README.md) | [`playlists`](../../app/modules/playlists/README.md) |
| [`social/`](social/README.md) | [`social`](../../app/modules/social/README.md) |
| [`users/`](users/README.md) | [`users`](../../app/modules/users/README.md) |

Para probar un solo módulo, corre esto dentro de `backend/`:

```bash
.venv/bin/pytest tests/modules/social
```
