"""Raíz de composición del Router (02 §7): crea las implementaciones y las inyecta."""

from fastapi import FastAPI

from router.client import HttpRouteClient
from router.dao import JsonlForwardingLogDAO
from router.http import PacketHTTP
from router.http_errors import install_error_handlers
from router.ports import ForwardingLogDAO, RouteClient
from router.service import ForwardingService
from router.settings import RouterSettings


def create_router_app(
    settings: RouterSettings, route_client: RouteClient | None = None, log_dao: ForwardingLogDAO | None = None
) -> FastAPI:
    """``route_client`` y ``log_dao`` son los puntos de inyección de las pruebas de API."""
    client = route_client if route_client is not None else HttpRouteClient(
        settings.controller_url, settings.connect_timeout_s, settings.read_timeout_s
    )
    forwarding_log = log_dao if log_dao is not None else JsonlForwardingLogDAO(settings.log_file)
    service = ForwardingService(client=client, log_dao=forwarding_log)
    app = FastAPI(title="Router SDN — Grupo 2 (plano de datos simulado)", version="1.0")
    app.include_router(PacketHTTP(service).router)
    install_error_handlers(app)
    return app
