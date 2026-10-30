"""Dobles de prueba del Controller (02 §7: viven solo en tests/)."""

import dataclasses
import json
from decimal import Decimal
from pathlib import Path

from controller.models import Link, LinkChangeResult, Topology
from controller.ports import TopologyDAO
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
