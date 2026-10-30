"""Model del Router (02 §3.2, §4): objetos de dominio inmutables, sin E/S."""

from dataclasses import dataclass

from shared.models import Route


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
