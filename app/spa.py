"""Servido del SPA de Vue (ui/dist) desde el mismo proceso de FastAPI.

Las rutas de la API y de Swagger se registran antes y tienen prioridad. La ruta comodín
del SPA usa el convertidor `spa`, que **no** acepta rutas bajo `api/` ni `docs`: así esas
rutas, si no existen, siguen respondiendo el 404 JSON uniforme para cualquier método
(un comodín GET normal haría que `POST /api/nada` respondiera 405).
Cualquier otra ruta GET devuelve el archivo pedido si existe dentro de `dist_dir`, o
`index.html` para que el router de Vue resuelva la vista.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.convertors import PathConvertor, register_url_convertor


class SpaPathConvertor(PathConvertor):
    """Como `path`, pero excluye las rutas reservadas `api` y `docs` (y lo que cuelga de ellas)."""

    regex = r"(?!(?:api|docs)(?:/|$)).*"


register_url_convertor("spa", SpaPathConvertor())


def _file_inside(root: Path, full_path: str) -> Path | None:
    """Devuelve el archivo pedido solo si existe y no escapa de `root`."""
    if not full_path:
        return None
    try:
        candidate = (root / full_path).resolve()
        found = candidate.is_file() and candidate.is_relative_to(root)
    except (ValueError, OSError):
        # Ruta imposible (byte nulo, nombre demasiado largo…): se trata como inexistente.
        return None
    return candidate if found else None


def mount_spa(app: FastAPI, dist_dir: Path) -> None:
    if not (dist_dir / "index.html").is_file():
        # Sin build del frontend (p. ej. desarrollo solo de backend): solo API.
        return
    root = dist_dir.resolve()

    # Recursos con hash generados por Vite; un archivo inexistente responde 404 JSON.
    app.mount("/assets", StaticFiles(directory=root / "assets", check_dir=False), name="assets")

    @app.get("/{full_path:spa}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        file = _file_inside(root, full_path)
        if file is not None:
            return FileResponse(file)
        # index.html sin caché: tras un despliegue debe apuntar a los nuevos recursos.
        return FileResponse(root / "index.html", headers={"Cache-Control": "no-cache"})
