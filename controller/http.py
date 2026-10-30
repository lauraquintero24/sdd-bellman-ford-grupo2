"""Controller MVC del proceso Controller (02 §3.1; 04 §3).

Los handlers solo reciben esquemas ya validados por la View, invocan un método de
``RoutingService`` y serializan; no calculan rutas, no abren archivos y no conocen el DAO.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from controller.service import RoutingService
from controller.view import (
    ControllerHealthSchema,
    LinkRequestSchema,
    LinkSchema,
    LinkStatusSchema,
    Metric,
    NodeId,
    RouteResponseSchema,
    TopologyResponseSchema,
)


class ControllerHTTP:
    def __init__(self, service: RoutingService) -> None:
        self._service = service
        self.router = APIRouter()
        self.router.add_api_route("/health", self.health, methods=["GET"], response_model=ControllerHealthSchema)
        self.router.add_api_route("/topology", self.get_topology, methods=["GET"], response_model=TopologyResponseSchema)
        self.router.add_api_route("/route", self.get_route, methods=["GET"], response_model=RouteResponseSchema)
        self.router.add_api_route("/links/fail", self.fail_link, methods=["POST"], response_model=LinkStatusSchema)
        self.router.add_api_route("/links/restore", self.restore_link, methods=["POST"], response_model=LinkStatusSchema)

    def health(self) -> ControllerHealthSchema:
        return ControllerHealthSchema(status="ok", application="controller")

    def get_topology(self) -> TopologyResponseSchema:
        topology = self._service.read_topology()
        return TopologyResponseSchema(
            topology_version=topology.version,
            directed=topology.directed,
            nodes=list(topology.nodes),
            links=[
                LinkSchema(
                    source=link.source,
                    target=link.target,
                    delay_ms=link.delay_ms,
                    bandwidth_mbps=link.bandwidth_mbps,
                    loss_probability=link.loss_probability,
                    active=link.active,
                )
                for link in topology.links
            ],
        )

    def get_route(
        self, src: Annotated[NodeId, Query()], dst: Annotated[NodeId, Query()], metric: Annotated[Metric, Query()]
    ) -> RouteResponseSchema:
        route = self._service.compute_route(src, dst, metric)
        return RouteResponseSchema(
            source=route.source,
            destination=route.destination,
            metric=route.metric,
            path=list(route.path),
            total_cost=route.total_cost,
            topology_version=route.topology_version,
        )

    def fail_link(self, body: LinkRequestSchema) -> LinkStatusSchema:
        return self._link_status(self._service.set_link_status(body.source, body.target, False))

    def restore_link(self, body: LinkRequestSchema) -> LinkStatusSchema:
        return self._link_status(self._service.set_link_status(body.source, body.target, True))

    @staticmethod
    def _link_status(result) -> LinkStatusSchema:
        return LinkStatusSchema(
            source=result.source,
            target=result.target,
            active=result.active,
            changed=result.changed,
            topology_version=result.topology_version,
        )
