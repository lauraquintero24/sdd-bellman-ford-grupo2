"""Cliente HTTP del Controller (02 §3.2, §5, §9; 04 §4.2, §4.3; DEC-05, DEC-06).

Hace un ``GET /route`` por llamada, valida la respuesta por completo y convierte todo fallo
de red o respuesta no conforme en una subclase de ``AppError``. No recalcula costos ni
verifica optimalidad: confía en el Controller (frontera de confianza intencional).
"""

import json

import httpx

from router.ports import RouteClient, TableClient
from shared.cost_format import is_canonical_cost
from shared.error_contract import (
    DETAILS_FIELD_RENAMES,
    ERROR_FIELDS,
    ERROR_KEY,
    NODE_NOT_FOUND,
    ENTRY_ACTIVE,
    ENTRY_UNREACHABLE,
    METRICS,
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
from shared.models import ForwardingEntry, ForwardingTable, Route

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
        self._timeout = httpx.Timeout(
            connect=connect_timeout_s, read=read_timeout_s, write=read_timeout_s, pool=connect_timeout_s
        )
        self._transport = transport
        # Contexto SSL creado una vez: cada httpx.Client() recargaría los certificados raíz (~51 ms por llamada).
        # p95 de POST /packets medido (F-01, procesos reales): 8,554 ms antes; 81,746 ms creando el cliente por
        # llamada sin este contexto (variante A); 8,440 ms con él (variante A′). No es una conexión abierta.
        self._ssl_context = httpx.create_ssl_context()

    def fetch_route(self, src: str, dst: str, metric: str) -> Route:
        response = _controller_get(self, "/route", {"src": src, "dst": dst, "metric": metric})
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


def _controller_get(client, path: str, params: dict | None) -> httpx.Response:
    """Un GET al Controller con un httpx.Client por llamada y el mapeo de errores de red de 02 §9."""
    try:
        # Un httpx.Client por llamada: no queda ningún cliente abierto durante la vida del proceso.
        with httpx.Client(
            base_url=client._base_url, timeout=client._timeout, transport=client._transport, verify=client._ssl_context
        ) as http:
            return http.get(path, params=params)
    except httpx.ConnectError:
        raise ControllerUnavailableError("No fue posible conectar con el Controller.") from None
    except httpx.TimeoutException:
        raise ControllerTimeoutError("El Controller no respondió a tiempo.") from None
    except httpx.HTTPError:  # conexión cortada a mitad de respuesta, protocolo inválido, etc.
        raise ControllerBadResponseError(_BAD_RESPONSE) from None


def _is_version(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _validate_entry(item, router_id: str) -> ForwardingEntry:
    if not isinstance(item, dict) or set(item) != {"destination", "next_hop", "path", "total_cost", "status"}:
        raise _NonConforming("campos de la fila")
    destination, next_hop, path, cost, status = (
        item["destination"], item["next_hop"], item["path"], item["total_cost"], item["status"])
    if not _is_text(destination) or destination == router_id:
        raise _NonConforming("destino inválido")
    if status == ENTRY_UNREACHABLE:
        if next_hop is not None or path is not None or cost is not None:
            raise _NonConforming("fila inalcanzable con siguiente salto, ruta o costo")
        return ForwardingEntry(destination, None, None, None, ENTRY_UNREACHABLE)
    if status != ENTRY_ACTIVE:
        raise _NonConforming("estado de fila desconocido")
    if not isinstance(path, list) or len(path) < 2 or not all(_is_text(node) for node in path):
        raise _NonConforming("ruta de la fila")
    if len(set(path)) != len(path) or path[0] != router_id or path[-1] != destination or next_hop != path[1]:
        raise _NonConforming("ruta o siguiente salto incoherentes")
    if not isinstance(cost, str) or not is_canonical_cost(cost):
        raise _NonConforming("total_cost no canónico")
    return ForwardingEntry(destination, next_hop, tuple(path), cost, ENTRY_ACTIVE)


def _validate_table(body, router_id: str, metric: str) -> ForwardingTable:
    """Respuesta de GET /forwarding-table (04 §3.7)."""
    if not isinstance(body, dict) or set(body) != {"router_id", "metric", "topology_version", "entries"}:
        raise _NonConforming("campos de la tabla")
    if (body["router_id"], body["metric"]) != (router_id, metric) or not _is_version(body["topology_version"]):
        raise _NonConforming("router_id, metric o versión incoherentes")
    if not isinstance(body["entries"], list):
        raise _NonConforming("entries no es una lista")
    entries = tuple(_validate_entry(item, router_id) for item in body["entries"])
    if len({entry.destination for entry in entries}) != len(entries):
        raise _NonConforming("destinos repetidos")
    return ForwardingTable(router_id=router_id, metric=metric, topology_version=body["topology_version"], entries=entries)


class HttpTableClient(TableClient):
    """Cliente del Controller para la sincronización de tablas en modo nodo (C-32, 04 §3.6–§3.7)."""

    def __init__(
        self,
        base_url: str,
        connect_timeout_s: float,
        read_timeout_s: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(
            connect=connect_timeout_s, read=read_timeout_s, write=read_timeout_s, pool=connect_timeout_s
        )
        self._transport = transport
        self._ssl_context = httpx.create_ssl_context()  # una vez por instancia (ver HttpRouteClient)

    def fetch_topology_version(self) -> int:
        response = _controller_get(self, "/topology/version", None)
        try:
            body = _parse_json(response)
            if response.status_code == 200 and isinstance(body, dict) and set(body) == {"topology_version"}:
                if _is_version(body["topology_version"]):
                    return body["topology_version"]
            raise _NonConforming("versión no conforme")
        except _NonConforming:
            raise ControllerBadResponseError(_BAD_RESPONSE) from None

    def fetch_forwarding_table(self, router_id: str, metric: str) -> ForwardingTable:
        if metric not in METRICS:
            raise ValueError(f"métrica no admitida: {metric}")
        response = _controller_get(self, "/forwarding-table", {"router_id": router_id, "metric": metric})
        try:
            body = _parse_json(response)
            if response.status_code == 200:
                return _validate_table(body, router_id, metric)
            if response.status_code == 404:
                error = _propagated_error(body)
                if error is not None:
                    raise error
            raise _NonConforming(f"estado HTTP no previsto: {response.status_code}")
        except _NonConforming:
            raise ControllerBadResponseError(_BAD_RESPONSE) from None
