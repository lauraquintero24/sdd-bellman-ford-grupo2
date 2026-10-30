"""Cliente HTTP del Controller (02 §3.2, §5, §9; 04 §4.2, §4.3; DEC-05, DEC-06).

Hace un ``GET /route`` por llamada, valida la respuesta por completo y convierte todo fallo
de red o respuesta no conforme en una subclase de ``AppError``. No recalcula costos ni
verifica optimalidad: confía en el Controller (frontera de confianza intencional).
"""

import json

import httpx

from router.ports import RouteClient
from shared.cost_format import is_canonical_cost
from shared.error_contract import (
    DETAILS_FIELD_RENAMES,
    ERROR_FIELDS,
    ERROR_KEY,
    NODE_NOT_FOUND,
    ROUTE_FIELDS,
    ROUTE_UNREACHABLE,
)
from shared.errors import (
    ControllerBadResponseError,
    ControllerTimeoutError,
    ControllerUnavailableError,
    NodeNotFoundError,
    RouteUnreachableError,
)
from shared.models import Route

_PROPAGATED = {NODE_NOT_FOUND: NodeNotFoundError, ROUTE_UNREACHABLE: RouteUnreachableError}
_BAD_RESPONSE = "La respuesta del Controller no cumple el contrato."


class _NonConforming(Exception):
    pass


def _reject_constant(name: str):
    raise _NonConforming(f"constante JSON no permitida: {name}")


def _parse_json(response: httpx.Response):
    try:
        return json.loads(response.content.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError) as exc:
        raise _NonConforming("cuerpo no JSON") from exc


def _is_text(value) -> bool:
    return isinstance(value, str) and value != ""


def _validate_route(body, src: str, dst: str, metric: str) -> Route:
    """Reglas 1–5 de 04 §4.3."""
    if not isinstance(body, dict) or set(body) != set(ROUTE_FIELDS):
        raise _NonConforming("campos de la respuesta")
    if (body["source"], body["destination"], body["metric"]) != (src, dst, metric):
        raise _NonConforming("source, destination o metric no coinciden con la petición")
    path = body["path"]
    if not isinstance(path, list) or not path or not all(_is_text(node) for node in path):
        raise _NonConforming("path no es una lista no vacía de cadenas no vacías")
    if len(set(path)) != len(path) or path[0] != src or path[-1] != dst:
        raise _NonConforming("path con repetidos o extremos incorrectos")
    total_cost = body["total_cost"]
    if not isinstance(total_cost, str) or not is_canonical_cost(total_cost):
        raise _NonConforming("total_cost no canónico")
    if src == dst and (path != [src] or total_cost != "0"):
        raise _NonConforming("ruta trivial incorrecta")
    version = body["topology_version"]
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise _NonConforming("topology_version inválida")
    return Route(
        source=src, destination=dst, metric=metric, path=tuple(path), total_cost=total_cost, topology_version=version
    )


def _propagated_error(body):
    """404 con sobre válido y código propagable → misma excepción con details.field renombrado."""
    if not isinstance(body, dict) or set(body) != {ERROR_KEY}:
        return None
    error = body[ERROR_KEY]
    if not isinstance(error, dict) or set(error) != set(ERROR_FIELDS):
        return None
    code, message, details = error["code"], error["message"], error["details"]
    if code not in _PROPAGATED or not isinstance(message, str) or not isinstance(details, dict):
        return None
    details = dict(details)
    if details.get("field") in DETAILS_FIELD_RENAMES:
        details["field"] = DETAILS_FIELD_RENAMES[details["field"]]
    return _PROPAGATED[code](message, details)


class HttpRouteClient(RouteClient):
    def __init__(
        self,
        base_url: str,
        connect_timeout_s: float,
        read_timeout_s: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._connect_timeout_s = connect_timeout_s
        self._read_timeout_s = read_timeout_s
        timeout = httpx.Timeout(connect=connect_timeout_s, read=read_timeout_s, write=read_timeout_s, pool=connect_timeout_s)
        self._http = httpx.Client(base_url=self._base_url, timeout=timeout, transport=transport)

    def fetch_route(self, src: str, dst: str, metric: str) -> Route:
        try:
            response = self._http.get("/route", params={"src": src, "dst": dst, "metric": metric})
        except httpx.ConnectError:
            raise ControllerUnavailableError("No fue posible conectar con el Controller.") from None
        except httpx.TimeoutException:
            raise ControllerTimeoutError("El Controller no respondió a tiempo.") from None
        except httpx.HTTPError:  # conexión cortada a mitad de respuesta, protocolo inválido, etc.
            raise ControllerBadResponseError(_BAD_RESPONSE) from None

        try:
            body = _parse_json(response)
            if response.status_code == 200:
                return _validate_route(body, src, dst, metric)
            if response.status_code == 404:
                error = _propagated_error(body)
                if error is not None:
                    raise error
            raise _NonConforming(f"estado HTTP no previsto: {response.status_code}")
        except _NonConforming:
            raise ControllerBadResponseError(_BAD_RESPONSE) from None
