"""Controller MVC del proceso Router (02 §3.2; 04 §4).

Los handlers solo reciben esquemas ya validados por la View, invocan ``ForwardingService``
y serializan; no calculan rutas, no construyen trazas, no abren archivos y no conocen el
cliente HTTP ni el DAO.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from router.models import Packet
from router.service import ForwardingService, NodeForwardingService
from router.view import (
    ForwardingEntrySchema,
    ForwardingResponseSchema,
    Metric,
    NodeForwardingTableSchema,
    PacketRequestSchema,
    RouteSchema,
    RouterHealthSchema,
    RouterStatusSchema,
    TraceHopSchema,
)


class PacketHTTP:
    def __init__(self, service: ForwardingService) -> None:
        self._service = service
        self.router = APIRouter()
        self.router.add_api_route("/health", self.health, methods=["GET"], response_model=RouterHealthSchema)
        self.router.add_api_route("/packets", self.post_packet, methods=["POST"], response_model=ForwardingResponseSchema)

    def health(self) -> RouterHealthSchema:
        return RouterHealthSchema(status="ok", application="router")

    def post_packet(self, body: PacketRequestSchema) -> ForwardingResponseSchema:
        packet = Packet(
            packet_id=body.packet_id,
            source=body.source,
            destination=body.destination,
            payload=body.payload,
            metric=body.metric,
        )
        try:
            result = self._service.forward(packet)
        except Exception as exc:
            exc.packet_id = body.packet_id  # http_errors.py construye PacketErrorSchema (02 §9)
            raise
        route = result.route
        return ForwardingResponseSchema(
            packet_id=result.packet_id,
            status=result.status,
            route=RouteSchema(
                source=route.source,
                destination=route.destination,
                metric=route.metric,
                path=list(route.path),
                total_cost=route.total_cost,
                topology_version=route.topology_version,
            ),
            trace=[TraceHopSchema(hop_index=hop.hop_index, node=hop.node) for hop in result.trace],
            topology_version=result.topology_version,
        )


class NodeHTTP:
    """Controller MVC de una instancia Router en modo nodo (C-32, 04 §4.4).

    Solo valida con la View, delega en ``NodeForwardingService`` y serializa.
    """

    def __init__(self, service: NodeForwardingService) -> None:
        self._service = service
        self.router = APIRouter()
        self.router.add_api_route("/health", self.health, methods=["GET"], response_model=RouterHealthSchema)
        self.router.add_api_route("/status", self.status, methods=["GET"], response_model=RouterStatusSchema)
        self.router.add_api_route(
            "/forwarding-table", self.get_forwarding_table, methods=["GET"], response_model=NodeForwardingTableSchema
        )

    def health(self) -> RouterHealthSchema:
        return RouterHealthSchema(status="ok", application="router")

    def status(self) -> RouterStatusSchema:
        return RouterStatusSchema(**self._service.status())

    def get_forwarding_table(self, metric: Annotated[Metric, Query()]) -> NodeForwardingTableSchema:
        table = self._service.current_table(metric)
        status = self._service.status()
        return NodeForwardingTableSchema(
            router_id=table.router_id,
            url=status["url"],
            metric=table.metric,
            topology_version=table.topology_version,
            synced_at=status["synced_at"],
            entries=[
                ForwardingEntrySchema(
                    destination=entry.destination,
                    next_hop=entry.next_hop,
                    path=list(entry.path) if entry.path is not None else None,
                    total_cost=entry.total_cost,
                    status=entry.status,
                )
                for entry in table.entries
            ],
        )
