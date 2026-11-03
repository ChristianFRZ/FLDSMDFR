"""Errores de dominio y formato JSON uniforme: {"error": {"code", "message"}}."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class DomainError(Exception):
    status: int = 400
    code: str = "error"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class NotFound(DomainError):
    status = 404
    code = "not_found"


class Conflict(DomainError):
    status = 409
    code = "conflict"


class Forbidden(DomainError):
    status = 403
    code = "forbidden"


class Unauthorized(DomainError):
    status = 401
    code = "unauthorized"


class InvalidInput(DomainError):
    status = 422
    code = "invalid_input"


class PayloadTooLarge(DomainError):
    status = 413
    code = "payload_too_large"


class RangeNotSatisfiable(DomainError):
    status = 416
    code = "range_not_satisfiable"

    def __init__(self, message: str, code: str | None = None, size: int | None = None):
        super().__init__(message, code)
        self.size = size


_HTTP_ERRORS = {
    401: ("unauthorized", "Necesitas iniciar sesión."),
    403: ("forbidden", "No tienes permiso para hacer esto."),
    404: ("not_found", "No encontramos lo que buscas."),
    405: ("method_not_allowed", "Método no permitido."),
}


def error_response(
    status: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message}}, status_code=status, headers=headers
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(422, "invalid_input", "Los datos enviados no son válidos.")

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = _HTTP_ERRORS.get(exc.status_code, ("error", "No se pudo completar."))
        return error_response(exc.status_code, code, message, headers=exc.headers)
