"""Raíz de composición del Controller (02 §7): crea las implementaciones y las inyecta."""

import logging
import time

from fastapi import FastAPI, Request

from controller.dao import JsonTopologyDAO
from controller.engine import BellmanFordEngine
from controller.http import ControllerHTTP
from controller.http_errors import install_error_handlers
from controller.ports import TopologyDAO
from controller.presenter import CostPresenter
from controller.service import RoutingService
from controller.settings import ControllerSettings

logger = logging.getLogger("controller")
# Peticiones cuya duración se registra (diagnóstico de la sincronización de tablas en modo nodo, C-32)
TIMED_PATHS = frozenset({"/links/fail", "/links/restore", "/topology/version", "/forwarding-table"})


def create_controller_app(settings: ControllerSettings, dao: TopologyDAO | None = None) -> FastAPI:
    """``dao`` es el punto de inyección de las pruebas de API; si no se pasa, se crea
    ``JsonTopologyDAO(settings.topology_file)`` (que lanza ``TopologyLoadError`` si es inválida)."""
    topology_dao = dao if dao is not None else JsonTopologyDAO(settings.topology_file)
    service = RoutingService(dao=topology_dao, engine=BellmanFordEngine(), presenter=CostPresenter())
    app = FastAPI(title="Controller SDN — Grupo 2 (Bellman-Ford)", version="1.1")
    app.include_router(ControllerHTTP(service, routers=settings.routers).router)
    install_error_handlers(app)

    @app.middleware("http")
    async def log_duration(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        if request.url.path in TIMED_PATHS:
            logger.info("%s %s → %d en %.1f ms", request.method, request.url.path, response.status_code,
                        (time.perf_counter() - started) * 1000)
        return response

    return app
