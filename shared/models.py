"""Contratos de datos compartidos entre el Controller y el Router (02 §3.1).

Solo biblioteca estándar (02 §8).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    """Ruta elegida por el Controller; es el contrato que viaja al Router.

    ``total_cost`` es la cadena canónica de presentación (01 §5.3); nunca se usa
    para comparar rutas.
    """

    source: str
    destination: str
    metric: str
    path: tuple[str, ...]
    total_cost: str
    topology_version: int


@dataclass(frozen=True)
class RouterInfo:
    """Entrada del registro de routers (C-32): identidad y dirección HTTP de una instancia."""

    router_id: str
    url: str


@dataclass(frozen=True)
class ForwardingEntry:
    """Fila de una tabla de forwarding (04 §3.7). Inalcanzable: ``next_hop``, ``path`` y ``total_cost`` en None."""

    destination: str
    next_hop: str | None
    path: tuple[str, ...] | None
    total_cost: str | None
    status: str


@dataclass(frozen=True)
class ForwardingTable:
    """Tabla de forwarding de un router para una métrica, calculada por el Controller sobre una versión."""

    router_id: str
    metric: str
    topology_version: int
    entries: tuple[ForwardingEntry, ...]
