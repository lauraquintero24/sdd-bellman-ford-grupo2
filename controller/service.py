"""Servicio de dominio del Controller (02 §3.1, §5).

Depende de la interfaz ``TopologyDAO`` y recibe todas sus dependencias por constructor,
sin valores por defecto (02 §7). No abre archivos ni conoce DAO concretos (NFR-02).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from controller.models import LinkChangeResult, Topology
from controller.ports import TopologyDAO
from shared.error_contract import ENTRY_ACTIVE, ENTRY_UNREACHABLE
from shared.errors import InvalidRequestError, NodeNotFoundError
from shared.models import ForwardingEntry, ForwardingTable, Route

if TYPE_CHECKING:
    from controller.engine import BellmanFordEngine
    from controller.presenter import CostPresenter

METRICS = ("delay", "inverse_bandwidth", "loss")


class RoutingService:
    def __init__(self, dao: TopologyDAO, engine: BellmanFordEngine, presenter: CostPresenter) -> None:
        self._dao = dao
        self._engine = engine
        self._presenter = presenter

    def read_topology(self) -> Topology:
        return self._dao.get_topology()

    def compute_route(self, src: str, dst: str, metric: str) -> Route:
        if metric not in METRICS:
            raise InvalidRequestError(f"La métrica {metric} no está admitida.", {"fields": ["metric"]})
        snapshot = self._dao.get_topology()
        for field, value in (("src", src), ("dst", dst)):
            if not snapshot.has_node(value):
                raise NodeNotFoundError(f"El nodo {value} no existe en la topología.", {"field": field, "value": value})
        result = self._engine.find_path(snapshot, src, dst, metric)
        total_cost = self._presenter.format_cost(result.score, metric)
        return Route(
            source=src,
            destination=dst,
            metric=metric,
            path=result.path,
            total_cost=total_cost,
            topology_version=snapshot.version,
        )

    def set_link_status(self, source: str, target: str, active: bool) -> LinkChangeResult:
        return self._dao.set_link_status(source, target, active)

    def topology_version(self) -> int:
        return self._dao.get_topology().version

    def compute_forwarding_table(self, router_id: str, metric: str) -> ForwardingTable:
        """Tabla de forwarding de ``router_id`` (02 §5, §6.4): una fila por cada otro nodo, en el orden de ``nodes``."""
        if metric not in METRICS:
            raise InvalidRequestError(f"La métrica {metric} no está admitida.", {"fields": ["metric"]})
        snapshot = self._dao.get_topology()
        if not snapshot.has_node(router_id):
            raise NodeNotFoundError(
                f"El nodo {router_id} no existe en la topología.", {"field": "router_id", "value": router_id}
            )
        best = self._engine.find_all_paths(snapshot, router_id, metric)
        entries = []
        for node in snapshot.nodes:
            if node == router_id:
                continue
            result = best.get(node)
            if result is None:
                entries.append(ForwardingEntry(node, None, None, None, ENTRY_UNREACHABLE))
            else:
                cost = self._presenter.format_cost(result.score, metric)
                entries.append(ForwardingEntry(node, result.path[1], result.path, cost, ENTRY_ACTIVE))
        return ForwardingTable(
            router_id=router_id, metric=metric, topology_version=snapshot.version, entries=tuple(entries)
        )
