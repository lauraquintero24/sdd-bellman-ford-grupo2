"""Raíz de composición del Controller (02 §7): crea las implementaciones y las inyecta."""

from fastapi import FastAPI

from controller.dao import JsonTopologyDAO
from controller.engine import BellmanFordEngine
from controller.http import ControllerHTTP
from controller.http_errors import install_error_handlers
from controller.ports import TopologyDAO
from controller.presenter import CostPresenter
from controller.service import RoutingService
from controller.settings import ControllerSettings


def create_controller_app(settings: ControllerSettings, dao: TopologyDAO | None = None) -> FastAPI:
    """``dao`` es el punto de inyección de las pruebas de API; si no se pasa, se crea
    ``JsonTopologyDAO(settings.topology_file)`` (que lanza ``TopologyLoadError`` si es inválida)."""
    topology_dao = dao if dao is not None else JsonTopologyDAO(settings.topology_file)
    service = RoutingService(dao=topology_dao, engine=BellmanFordEngine(), presenter=CostPresenter())
    app = FastAPI(title="Controller SDN — Grupo 2 (Bellman-Ford)", version="1.0")
    app.include_router(ControllerHTTP(service).router)
    install_error_handlers(app)
    return app
