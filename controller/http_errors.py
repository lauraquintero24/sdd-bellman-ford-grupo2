"""Adaptador de errores HTTP del Controller (02 §9; 04 §1, §5).

Única tabla error.code → estado HTTP del proceso. Ninguna respuesta expone trazas
Python, rutas de archivo ni direcciones internas.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from controller.view import ErrorBodySchema
from shared.errors import AppError

logger = logging.getLogger("controller")

STATUS_BY_CODE = {
    "MALFORMED_JSON": 400,
    "INVALID_REQUEST": 400,
    "NODE_NOT_FOUND": 404,
    "LINK_NOT_FOUND": 404,
    "ROUTE_UNREACHABLE": 404,
    "UNKNOWN_ENDPOINT": 404,
    "METHOD_NOT_ALLOWED": 405,
    "NEGATIVE_CYCLE": 500,
    "INTERNAL_ERROR": 500,
}


def _error_response(code: str, message: str, details: dict | None = None) -> JSONResponse:
    body = ErrorBodySchema(code=code, message=message, details=details or {})
    return JSONResponse(status_code=STATUS_BY_CODE[code], content={"error": body.model_dump()})


async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
    code = exc.code if exc.code in STATUS_BY_CODE else "INTERNAL_ERROR"
    if code in ("NEGATIVE_CYCLE", "INTERNAL_ERROR"):
        logger.error("Error interno: %s (%s)", code, exc.message)
    return _error_response(code, exc.message, exc.details)


async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(error.get("type") == "json_invalid" for error in errors):
        return _error_response("MALFORMED_JSON", "El cuerpo JSON es inválido.")
    fields = []
    for error in errors:
        loc = [str(part) for part in error.get("loc", ()) if part not in ("body", "query")]
        if loc and loc[0] not in fields:
            fields.append(loc[0])
    message = f"Solicitud inválida en: {', '.join(fields)}." if fields else "La solicitud no es válida."
    return _error_response("INVALID_REQUEST", message, {"fields": fields})


async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 404:
        return _error_response("UNKNOWN_ENDPOINT", "El endpoint solicitado no existe.")
    if exc.status_code == 405:
        return _error_response("METHOD_NOT_ALLOWED", "Método no admitido en esta ruta.")
    if exc.status_code == 400:
        return _error_response("INVALID_REQUEST", "La solicitud no es válida.")
    return _error_response("INTERNAL_ERROR", "Error interno del Controller.")


async def _unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error inesperado", exc_info=exc)
    return _error_response("INTERNAL_ERROR", "Error interno del Controller.")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected_error)
