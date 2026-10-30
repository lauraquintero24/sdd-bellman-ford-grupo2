"""Jerarquía de excepciones de dominio (02 §3.3).

Las excepciones llevan ``error.code`` pero no un estado HTTP: la correspondencia
código -> estado vive solo en ``controller/http_errors.py`` y
``router/http_errors.py`` (02 §1.6). Solo biblioteca estándar (02 §8).
"""


class AppError(Exception):
    """Error de dominio con el sobre normalizado de 04 §1."""

    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details) if details else {}

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "details": dict(self.details)}


# --- Errores del Controller (Estudiante A) ---

class InvalidRequestError(AppError):
    code = "INVALID_REQUEST"


class NodeNotFoundError(AppError):
    code = "NODE_NOT_FOUND"


class LinkNotFoundError(AppError):
    code = "LINK_NOT_FOUND"


class RouteUnreachableError(AppError):
    code = "ROUTE_UNREACHABLE"


class NegativeCycleError(AppError):
    code = "NEGATIVE_CYCLE"


# --- Errores del Router (Estudiante B) ---

class LogPersistenceError(AppError):
    code = "LOG_PERSISTENCE_ERROR"


class ControllerBadResponseError(AppError):
    code = "CONTROLLER_BAD_RESPONSE"


class ControllerUnavailableError(AppError):
    code = "CONTROLLER_UNAVAILABLE"


class ControllerTimeoutError(AppError):
    code = "CONTROLLER_TIMEOUT"
