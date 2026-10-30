"""Model del Controller (02 §3.1, §4): objetos de dominio inmutables, sin E/S y sin validación.

La validación de topologías la hace solo ``JsonTopologyDAO``; así una prueba puede
construir un ``Topology`` con pesos negativos (TC-11).
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Link:
    source: str
    target: str
    delay_ms: Decimal
    bandwidth_mbps: Decimal
    loss_probability: Decimal
    active: bool

    def is_usable(self) -> bool:
        """Un enlace inactivo o con ``loss_probability = 1`` no se usa en ninguna métrica (DEC-02)."""
        return self.active and self.loss_probability != 1


@dataclass(frozen=True)
class Topology:
    directed: bool
    version: int
    nodes: tuple[str, ...]
    links: tuple[Link, ...]

    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes

    def find_link(self, source: str, target: str) -> Link | None:
        """Enlace que une ``source`` con ``target``; en modo no dirigido, en cualquier sentido."""
        for link in self.links:
            if link.source == source and link.target == target:
                return link
            if not self.directed and link.source == target and link.target == source:
                return link
        return None


@dataclass(frozen=True)
class LinkChangeResult:
    source: str
    target: str
    active: bool
    changed: bool
    topology_version: int
