"""Adaptador de errores HTTP del Router (02 §9; 04 §4.2, §5).

Única tabla error.code → estado HTTP del proceso. Para un paquete ya validado responde
``PacketErrorSchema`` (packet_id, status "failed", trace [], error); para errores de entrada,
solo el sobre ``{"error": ...}``. Ninguna respuesta expone trazas Python, rutas de archivo ni
la dirección del Controller.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from router.view import ErrorBodySchema, PacketErrorSchema
from shared.error_contract import STATUS_FAILED
from shared.errors import AppError

logger = logging.getLogger("router")

STATUS_BY_CODE = {
    "MALFORMED_JSON": 400,
    "INVALID_REQUEST": 400,
    "NODE_NOT_FOUND": 404,
    "ROUTE_UNREACHABLE": 404,
    "UNKNOWN_ENDPOINT": 404,
    "METHOD_NOT_ALLOWED": 405,
    "LOG_PERSISTENCE_ERROR": 500,
    "INTERNAL_ERROR": 500,
    "CONTROLLER_BAD_RESPONSE": 502,
    "CONTROLLER_UNAVAILABLE": 503,
    "CONTROLLER_TIMEOUT": 504,
}
INTERNAL_MESSAGE = "Error interno del Router."


def _response(code: str, message: str, details: dict | None, packet_id: str | None) -> JSONResponse:
    error = ErrorBodySchema(code=code, message=message, details=details or {})
    if packet_id is None:
        content = {"error": error.model_dump()}
    else:
        content = PacketErrorSchema(packet_id=packet_id, status=STATUS_FAILED, trace=[], error=error).model_dump()
    return JSONResponse(status_code=STATUS_BY_CODE[code], content=content)


async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
    code = exc.code if exc.code in STATUS_BY_CODE else "INTERNAL_ERROR"
    if code in ("LOG_PERSISTENCE_ERROR", "INTERNAL_ERROR"):
        logger.error("%s: %s", code, exc.message)
    return _response(code, exc.message, exc.details, getattr(exc, "packet_id", None))


async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(error.get("type") == "json_invalid" for error in errors):
        return _response("MALFORMED_JSON", "El cuerpo JSON es inválido.", None, None)
    fields = []
    for error in errors:
        loc = [str(part) for part in error.get("loc", ()) if part not in ("body", "query")]
        if loc and loc[0] not in fields:
            fields.append(loc[0])
    message = f"Solicitud inválida en: {', '.join(fields)}." if fields else "La solicitud no es válida."
    return _response("INVALID_REQUEST", message, {"fields": fields}, None)


async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 404:
        return _response("UNKNOWN_ENDPOINT", "El endpoint solicitado no existe.", None, None)
    if exc.status_code == 405:
        return _response("METHOD_NOT_ALLOWED", "Método no admitido en esta ruta.", None, None)
    if exc.status_code == 400:
        return _response("INVALID_REQUEST", "La solicitud no es válida.", None, None)
    return _response("INTERNAL_ERROR", INTERNAL_MESSAGE, None, None)


async def _unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error inesperado", exc_info=exc)
    return _response("INTERNAL_ERROR", INTERNAL_MESSAGE, None, getattr(exc, "packet_id", None))


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected_error)
