from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings
from app.shared.errors import error_response

_MULTIPART_OVERHEAD = 1024 * 1024
_UPLOAD_PATH = "/api/songs"


class UploadSizeGuard:
    """Rechaza POST /api/songs sin Content-Length o demasiado grande antes de leer el cuerpo."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"].rstrip("/") == _UPLOAD_PATH
        ):
            raw = dict(scope["headers"]).get(b"content-length", b"")
            limit = get_settings().max_upload_bytes + _MULTIPART_OVERHEAD
            if not raw.isdigit() or int(raw) > limit:
                response = error_response(
                    422, "file_too_large", "El archivo supera el tamaño máximo permitido."
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
