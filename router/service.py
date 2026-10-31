"""Servicio de dominio del Router (02 §3.2, §5; 03 S1–S3; DEC-06).

Pide cada ruta al Controller mediante ``RouteClient`` (nunca la calcula ni la guarda en
caché), construye la traza salto a salto y registra todo resultado mediante ``ForwardingLogDAO``.
"""

import threading
from datetime import datetime, timezone

from router.models import ForwardingResult, NodeTables, Packet, TraceHop
from router.ports import ForwardingLogDAO, ForwardingTableDAO, RouteClient, TableClient
from shared.error_contract import INTERNAL_ERROR, METRICS, STATUS_FAILED, STATUS_FORWARDED
from shared.errors import (
    AppError,
    ControllerBadResponseError,
    ForwardingTableUnavailableError,
    InvalidRequestError,
    LogPersistenceError,
)
from shared.models import ForwardingTable, RouterInfo


class ForwardingService:
    def __init__(self, client: RouteClient, log_dao: ForwardingLogDAO) -> None:
        self._client = client
        self._log_dao = log_dao

    def forward(self, packet: Packet) -> ForwardingResult:
        try:
            route = self._client.fetch_route(packet.source, packet.destination, packet.metric)
        except Exception as exc:
            error = (
                exc.to_dict()
                if isinstance(exc, AppError)
                else {"code": INTERNAL_ERROR, "message": "Error interno del Router.", "details": {}}
            )
            self._save(self._result(packet, STATUS_FAILED, (), None, None, error))
            raise
        trace = tuple(TraceHop(hop_index=index, node=node) for index, node in enumerate(route.path))
        result = self._result(packet, STATUS_FORWARDED, trace, route, route.topology_version, None)
        self._save(result)
        return result

    @staticmethod
    def _result(packet: Packet, status, trace, route, topology_version, error) -> ForwardingResult:
        return ForwardingResult(
            packet_id=packet.packet_id,
            source=packet.source,
            destination=packet.destination,
            metric=packet.metric,
            status=status,
            trace=trace,
            route=route,
            topology_version=topology_version,
            error=error,
        )

    def _save(self, result: ForwardingResult) -> None:
        """Si la bitácora falla, ``LogPersistenceError`` prevalece sobre cualquier error original."""
        try:
            self._log_dao.save(result)
        except LogPersistenceError:
            raise
        except Exception as exc:
            raise LogPersistenceError("No fue posible guardar el resultado.") from exc


# --- Modo nodo (C-32, 02 §5, §6.4) ---

SYNC_PENDING, SYNC_OK, SYNC_ERROR = "pending", "ok", "error"
_SYNC_ATTEMPTS = 3


def _now() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


class NodeForwardingService:
    """Una instancia Router por nodo: guarda la tabla que calcula el Controller y la renueva solo si cambia la versión.

    No calcula rutas: cada fila procede de ``TableClient.fetch_forwarding_table`` (DEC-06, DEC-10).
    """

    def __init__(
        self,
        router_id: str,
        registry: tuple[RouterInfo, ...],
        table_client: TableClient,
        table_dao: ForwardingTableDAO,
        log_dao: ForwardingLogDAO,
    ) -> None:
        self._registry = {info.router_id: info.url for info in registry}
        if router_id not in self._registry:
            raise ValueError(f"router_id {router_id!r} no está en el registro de routers")
        self._router_id = router_id
        self._url = self._registry[router_id]
        self._table_client = table_client
        self._table_dao = table_dao
        self._log_dao = log_dao
        self._lock = threading.Lock()
        stored = table_dao.load()
        # Una tabla guardada de una ejecución anterior se muestra, pero la primera sincronización siempre la renueva:
        # al reiniciar el Controller la versión vuelve a 1 aunque la topología pueda ser otra.
        self._tables = stored if stored is not None and stored.router_id == router_id else None
        self._confirmed = False
        self._sync_status = SYNC_PENDING
        self._sync_error: dict | None = None

    def sync_if_changed(self) -> NodeTables:
        with self._lock:
            try:
                version = self._table_client.fetch_topology_version()
                if self._confirmed and self._tables is not None and self._tables.topology_version == version:
                    self._set_ok()
                    return self._tables
                tables = self._fetch_tables()
                self._table_dao.save(tables)
                self._tables, self._confirmed = tables, True
                self._set_ok()
                return tables
            except AppError as exc:
                self._sync_status, self._sync_error = SYNC_ERROR, {"code": exc.code, "message": exc.message}
                raise

    def _fetch_tables(self) -> NodeTables:
        """Las tres tablas de una misma versión; si la versión cambia entre peticiones, se repite."""
        for _ in range(_SYNC_ATTEMPTS):
            tables = {metric: self._table_client.fetch_forwarding_table(self._router_id, metric) for metric in METRICS}
            versions = {table.topology_version for table in tables.values()}
            if len(versions) == 1:
                return NodeTables(self._router_id, self._url, versions.pop(), _now(), tables)
        raise ControllerBadResponseError("El Controller devolvió tablas de versiones distintas.")

    def _set_ok(self) -> None:
        self._sync_status, self._sync_error = SYNC_OK, None

    def current_table(self, metric: str) -> ForwardingTable:
        if metric not in METRICS:
            raise InvalidRequestError(f"La métrica {metric} no está admitida.", {"fields": ["metric"]})
        tables = self._tables
        if tables is None:
            raise ForwardingTableUnavailableError(
                f"El router {self._router_id} aún no tiene tabla de forwarding.", {"router_id": self._router_id}
            )
        return tables.tables[metric]

    def status(self) -> dict:
        tables = self._tables
        return {
            "router_id": self._router_id,
            "url": self._url,
            "mode": "node",
            "topology_version": tables.topology_version if tables is not None else None,
            "synced_at": tables.synced_at if tables is not None else None,
            "sync_status": self._sync_status,
            "sync_error": self._sync_error,
        }
