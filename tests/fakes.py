"""Dobles de prueba del Controller y del Router (02 §7: viven solo en tests/)."""

import dataclasses
import json
from decimal import Decimal
from pathlib import Path

import httpx

from controller.models import Link, LinkChangeResult, Topology
from controller.ports import TopologyDAO
from router.models import ForwardingResult
from router.ports import ForwardingLogDAO, ForwardingTableDAO, RouteClient, TableClient
from shared.errors import LinkNotFoundError, NodeNotFoundError

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "specs" / "fixtures"


def load_fixture_topology(name: str) -> Topology:
    """Copia en memoria de ``specs/fixtures/<name>.json`` (sin validar, versión 1)."""
    doc = json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"), parse_float=Decimal, parse_int=Decimal)
    links = tuple(Link(**link) for link in doc["links"])
    return Topology(directed=doc["directed"], version=1, nodes=tuple(doc["nodes"]), links=links)


class FakeTopologyDAO(TopologyDAO):
    """DAO en memoria con contadores de llamadas; misma semántica que 02 §5."""

    def __init__(self, topology: Topology) -> None:
        self.topology = topology
        self.get_topology_calls = 0
        self.set_link_status_calls = 0

    def get_topology(self) -> Topology:
        self.get_topology_calls += 1
        return self.topology

    def set_link_status(self, source: str, target: str, active: bool) -> LinkChangeResult:
        self.set_link_status_calls += 1
        for field, value in (("source", source), ("target", target)):
            if not self.topology.has_node(value):
                raise NodeNotFoundError(f"El nodo {value} no existe en la topología.", {"field": field, "value": value})
        link = self.topology.find_link(source, target)
        if link is None:
            raise LinkNotFoundError(f"No existe el enlace {source} -> {target}.", {"source": source, "target": target})
        changed = link.active != active
        if changed:
            links = tuple(dataclasses.replace(l, active=active) if l is link else l for l in self.topology.links)
            self.topology = dataclasses.replace(self.topology, links=links, version=self.topology.version + 1)
        return LinkChangeResult(source, target, active, changed, self.topology.version)


class SpyCostPresenter:
    """Registra cada llamada a ``format_cost`` y devuelve una cadena fija."""

    def __init__(self, result: str = "999") -> None:
        self.result = result
        self.calls: list[tuple] = []

    def format_cost(self, score, metric: str) -> str:
        self.calls.append((score, metric))
        return self.result


# --- Dobles del Router (Estudiante B) ---

class FakeRouteClient(RouteClient):
    """Devuelve una ruta fija o lanza la excepción indicada; cuenta las llamadas."""

    def __init__(self, route=None, error: Exception | None = None) -> None:
        self.route = route
        self.error = error
        self.calls: list[tuple[str, str, str]] = []

    def fetch_route(self, src: str, dst: str, metric: str):
        self.calls.append((src, dst, metric))
        if self.error is not None:
            raise self.error
        return self.route


class SpyRouteClient(FakeRouteClient):
    """Espía: registra cada petición y devuelve la ruta configurada sin modificarla."""


class FakeForwardingLogDAO(ForwardingLogDAO):
    """Bitácora en memoria; con ``fail_with`` su ``save`` lanza esa excepción."""

    def __init__(self, fail_with: Exception | None = None) -> None:
        self.fail_with = fail_with
        self.saved: list[ForwardingResult] = []
        self.save_calls = 0

    def save(self, result: ForwardingResult) -> None:
        self.save_calls += 1
        if self.fail_with is not None:
            raise self.fail_with
        self.saved.append(result)

    def list_recent(self, limit: int) -> list[ForwardingResult]:
        return self.saved[-limit:] if limit > 0 else []


# --- Dobles del modo nodo (C-32) ---

class SpyTableClient(TableClient):
    """Cliente de tablas que consulta un RoutingService real en memoria y cuenta cada petición."""

    def __init__(self, routing_service) -> None:
        self.routing_service = routing_service
        self.version_calls = 0
        self.table_calls: list[tuple[str, str]] = []
        self.error: Exception | None = None

    def fetch_topology_version(self) -> int:
        self.version_calls += 1
        if self.error is not None:
            raise self.error
        return self.routing_service.topology_version()

    def fetch_forwarding_table(self, router_id: str, metric: str):
        self.table_calls.append((router_id, metric))
        if self.error is not None:
            raise self.error
        return self.routing_service.compute_forwarding_table(router_id, metric)


class FakeForwardingTableDAO(ForwardingTableDAO):
    """Tabla local en memoria; registra cada instantánea guardada."""

    def __init__(self, stored=None) -> None:
        self.stored = stored
        self.saved: list = []

    def load(self):
        return self.stored

    def save(self, tables) -> None:
        self.saved.append(tables)
        self.stored = tables


def asgi_bridge(test_client) -> httpx.MockTransport:
    """Transporte httpx que entrega cada petición a una aplicación FastAPI en el mismo proceso (TestClient)."""

    def handler(request: httpx.Request) -> httpx.Response:
        response = test_client.request(
            request.method, request.url.path, params=dict(request.url.params), content=request.content,
            headers={"content-type": request.headers.get("content-type", "application/json")},
        )
        return httpx.Response(response.status_code, content=response.content,
                              headers={"content-type": response.headers.get("content-type", "application/json")})

    return httpx.MockTransport(handler)
