"""Controller MVC del proceso Router (02 §3.2; 04 §4).

Los handlers solo reciben esquemas ya validados por la View, invocan ``ForwardingService``
y serializan; no calculan rutas, no construyen trazas, no abren archivos y no conocen el
cliente HTTP ni el DAO.
"""

from fastapi import APIRouter

from router.models import Packet
from router.service import ForwardingService
from router.view import (
    ForwardingResponseSchema,
    PacketRequestSchema,
    RouteSchema,
    RouterHealthSchema,
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
