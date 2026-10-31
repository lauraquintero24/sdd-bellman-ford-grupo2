"""Model del Router (02 §3.2, §4): objetos de dominio inmutables, sin E/S."""

from dataclasses import dataclass

from shared.models import ForwardingTable, Route


@dataclass(frozen=True)
class Packet:
    packet_id: str
    source: str
    destination: str
    payload: str
    metric: str


@dataclass(frozen=True)
class TraceHop:
    hop_index: int
    node: str


@dataclass(frozen=True)
class ForwardingResult:
    packet_id: str
    source: str
    destination: str
    metric: str
    status: str
    trace: tuple[TraceHop, ...]
    route: Route | None
    topology_version: int | None
    error: dict | None


# --- Modo nodo (C-32, 02 §3.4) ---

@dataclass(frozen=True)
class NodeTables:
    """Tablas de forwarding de una instancia (una por métrica), todas de la misma ``topology_version``."""

    router_id: str
    url: str
    topology_version: int
    synced_at: str
    tables: dict[str, ForwardingTable]


@dataclass(frozen=True)
class NodeTraceHop:
    hop_index: int
    node: str
    router_url: str


@dataclass(frozen=True)
class HopPacket:
    """Paquete en tránsito entre routers: traza hasta el router anterior y versión usada."""

    packet: Packet
    trace: tuple[NodeTraceHop, ...]
    topology_version: int


@dataclass(frozen=True)
class NodeForwardingResult:
    """Resultado de un paquete visto por una instancia (rol ``ingress``, ``transit`` o ``egress``)."""

    router_id: str
    role: str
    packet_id: str
    source: str
    destination: str
    metric: str
    status: str
    trace: tuple[NodeTraceHop, ...]
    route: Route | None
    topology_version: int | None
    error: dict | None
