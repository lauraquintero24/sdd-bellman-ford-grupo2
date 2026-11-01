"""Raíz de composición del Router (02 §7): crea las implementaciones y las inyecta."""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from router.client import HttpNextHopClient, HttpRouteClient, HttpTableClient
from router.dao import JsonForwardingTableDAO, JsonlForwardingLogDAO
from router.http import NodeHTTP, PacketHTTP
from router.http_errors import install_error_handlers
from router.ports import ForwardingLogDAO, ForwardingTableDAO, NextHopClient, RouteClient, TableClient
from router.service import ForwardingService, NodeForwardingService
from router.settings import RouterSettings
from shared.errors import AppError

logger = logging.getLogger("router")


def create_router_app(
    settings: RouterSettings,
    route_client: RouteClient | None = None,
    log_dao: ForwardingLogDAO | None = None,
    table_client: TableClient | None = None,
    table_dao: ForwardingTableDAO | None = None,
    next_hop_client: NextHopClient | None = None,
) -> FastAPI:
    """``route_client``, ``log_dao``, ``table_client``, ``table_dao`` y ``next_hop_client`` son puntos de inyección de pruebas.

    Sin ``settings.router_id`` la aplicación funciona en modo legado (1.0); con él, en modo nodo (C-32).
    """
    forwarding_log = log_dao if log_dao is not None else JsonlForwardingLogDAO(settings.log_file)
    if settings.router_id is None:
        client = route_client if route_client is not None else HttpRouteClient(
            settings.controller_url, settings.connect_timeout_s, settings.read_timeout_s
        )
        service = ForwardingService(client=client, log_dao=forwarding_log)
        app = FastAPI(title="Router SDN — Grupo 2 (plano de datos simulado)", version="1.0")
        app.include_router(PacketHTTP(service).router)
        install_error_handlers(app)
        return app

    tables = table_client if table_client is not None else HttpTableClient(
        settings.controller_url, settings.connect_timeout_s, settings.read_timeout_s
    )
    table_store = table_dao if table_dao is not None else JsonForwardingTableDAO(
        settings.table_file, settings.table_file.parent / "table-events.jsonl"
    )
    hops = next_hop_client if next_hop_client is not None else HttpNextHopClient(
        settings.connect_timeout_s, settings.read_timeout_s
    )
    node = NodeForwardingService(
        router_id=settings.router_id,
        registry=settings.routers,
        table_client=tables,
        table_dao=table_store,
        next_hop_client=hops,
        log_dao=forwarding_log,
    )
    sync_loop = TableSyncLoop(node, settings.sync_interval_s)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        sync_loop.start()
        try:
            yield
        finally:
            sync_loop.stop()

    app = FastAPI(title=f"Router SDN — Grupo 2 · nodo {settings.router_id}", version="1.1", lifespan=lifespan)
    # Laboratorio: la interfaz web del Controller consulta los routers desde el navegador (01 §9, C-32).
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
    app.include_router(NodeHTTP(node).router)
    install_error_handlers(app)
    return app


class TableSyncLoop:
    """Sincronización periódica de la tabla local (02 §6.4): un hilo que llama a ``sync_if_changed``."""

    def __init__(self, service: NodeForwardingService, interval_s: float) -> None:
        self._service = service
        self._interval_s = interval_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._interval_s <= 0 or self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="table-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._service.sync_if_changed()
            except AppError as exc:  # el estado queda en GET /status; se reintenta en el siguiente ciclo
                logger.warning("Sincronización de tabla fallida: %s (%s)", exc.code, exc.message)
            except Exception:  # noqa: BLE001 - el hilo no debe morir por un error inesperado
                logger.exception("Error inesperado en la sincronización de tabla")
            self._stop.wait(self._interval_s)
