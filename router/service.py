"""Servicio de dominio del Router (02 §3.2, §5; 03 S1–S3; DEC-06).

Pide cada ruta al Controller mediante ``RouteClient`` (nunca la calcula ni la guarda en
caché), construye la traza salto a salto y registra todo resultado mediante ``ForwardingLogDAO``.
"""

import threading
from datetime import datetime, timezone

from router.models import (
    ForwardingResult,
    HopPacket,
    NodeForwardingResult,
    NodeTables,
    NodeTraceHop,
    Packet,
    TraceHop,
)
from router.ports import ForwardingLogDAO, ForwardingTableDAO, NextHopClient, RouteClient, TableClient
from shared.error_contract import ENTRY_UNREACHABLE, INTERNAL_ERROR, METRICS, STATUS_FAILED, STATUS_FORWARDED
from shared.errors import (
    AppError,
    ControllerBadResponseError,
    ForwardingLoopError,
    ForwardingTableUnavailableError,
    HopLimitExceededError,
    InvalidRequestError,
    LogPersistenceError,
    NextHopBadResponseError,
    NextHopUnavailableError,
    NodeNotFoundError,
    RouteUnreachableError,
    TopologyChangedError,
)
from shared.models import ForwardingTable, Route, RouterInfo


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
        next_hop_client: NextHopClient,
        log_dao: ForwardingLogDAO,
    ) -> None:
        self._registry = {info.router_id: info.url for info in registry}
        if router_id not in self._registry:
            raise ValueError(f"router_id {router_id!r} no está en el registro de routers")
        self._router_id = router_id
        self._url = self._registry[router_id]
        self._table_client = table_client
        self._table_dao = table_dao
        self._next_hop_client = next_hop_client
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

    def handle(
        self, packet: Packet, trace: tuple[NodeTraceHop, ...] = (), topology_version: int | None = None
    ) -> NodeForwardingResult:
        """Procesa un paquete en este router (02 §6.4): ingreso con ``trace = ()``, tránsito con la traza recibida.

        Registra un resultado por paquete (éxito o fallo) y relanza la excepción en los fallos.
        """
        ingress = not trace
        if ingress and packet.source != self._router_id:
            raise InvalidRequestError(
                f"El paquete debe entrar por su router de origen; este es {self._router_id}.", {"fields": ["source"]}
            )
        role = "ingress" if ingress else "transit"
        try:
            full_trace, route, version = self._route_packet(packet, trace, topology_version)
        except Exception as exc:
            if isinstance(exc, AppError):
                # details.at_router = router donde se originó el error; los reproducidos de otro salto ya lo traen.
                exc.details.setdefault("at_router", self._router_id)
                error = exc.to_dict()
            else:
                error = {"code": INTERNAL_ERROR, "message": "Error interno del Router.", "details": {}}
            self._save(self._node_result(role, packet, STATUS_FAILED, (), None, None, error))
            raise
        if not ingress and packet.destination == self._router_id:
            role = "egress"
        result = self._node_result(role, packet, STATUS_FORWARDED, full_trace, route, version, None)
        self._save(result)
        return result

    def _route_packet(self, packet: Packet, trace: tuple[NodeTraceHop, ...], topology_version: int | None):
        here = {"at_router": self._router_id}
        if any(hop.node == self._router_id for hop in trace):
            raise ForwardingLoopError(f"El paquete ya pasó por {self._router_id}.", here)
        tables = self.sync_if_changed()  # GET /topology/version; tabla nueva solo si cambió (DEC-10)
        table = tables.tables[packet.metric]
        node_count = len(table.entries) + 1
        if len(trace) + 1 > node_count:  # más saltos que nodos
            raise HopLimitExceededError(f"La traza supera los {node_count} nodos de la topología.", here)
        version = tables.topology_version
        if topology_version is not None and topology_version != version:
            raise TopologyChangedError(
                "La topología cambió durante el reenvío.", {**here, "received": topology_version, "current": version}
            )
        full_trace = trace + (NodeTraceHop(len(trace), self._router_id, self._url),)
        nodes = tuple(hop.node for hop in full_trace)
        if packet.destination == self._router_id:
            # Costo desde este router hasta el destino: "0"; el router de ingreso pone el de su propia fila.
            return full_trace, Route(packet.source, packet.destination, packet.metric, nodes, "0", version), version
        entry = next((e for e in table.entries if e.destination == packet.destination), None)
        if entry is None:
            raise NodeNotFoundError(
                f"El nodo {packet.destination} no existe en la topología.",
                {**here, "field": "destination", "value": packet.destination},
            )
        if entry.status == ENTRY_UNREACHABLE:
            raise RouteUnreachableError(
                f"No existe una ruta utilizable de {self._router_id} a {packet.destination}.",
                {**here, "source": self._router_id, "destination": packet.destination, "metric": packet.metric},
            )
        next_url = self._registry.get(entry.next_hop)
        if next_url is None:
            raise NextHopUnavailableError(f"El router {entry.next_hop} no está en el registro.", here)
        downstream = self._next_hop_client.forward(next_url, HopPacket(packet, full_trace, version))
        self._check_downstream(downstream, full_trace, packet, version)
        route = Route(packet.source, packet.destination, packet.metric,
                      tuple(hop.node for hop in downstream.trace), entry.total_cost, version)
        return downstream.trace, route, version

    def _check_downstream(self, result: NodeForwardingResult, sent, packet: Packet, version: int) -> None:
        """La traza devuelta empieza por la enviada, termina en el destino, no repite nodos y es de la misma versión."""
        trace = result.trace
        nodes = [hop.node for hop in trace]
        if (
            tuple(trace[: len(sent)]) != tuple(sent)
            or not nodes
            or nodes[-1] != packet.destination
            or len(set(nodes)) != len(nodes)
            or result.topology_version != version
        ):
            raise NextHopBadResponseError(
                "La respuesta del siguiente router no cumple el contrato.", {"at_router": self._router_id}
            )

    def _node_result(self, role, packet: Packet, status, trace, route, version, error) -> NodeForwardingResult:
        return NodeForwardingResult(
            router_id=self._router_id,
            role=role,
            packet_id=packet.packet_id,
            source=packet.source,
            destination=packet.destination,
            metric=packet.metric,
            status=status,
            trace=trace,
            route=route,
            topology_version=version,
            error=error,
        )

    def _save(self, result: NodeForwardingResult) -> None:
        """Igual que ForwardingService: si la bitácora falla, ``LogPersistenceError`` prevalece."""
        try:
            self._log_dao.save(result)
        except LogPersistenceError:
            raise
        except Exception as exc:
            raise LogPersistenceError("No fue posible guardar el resultado.") from exc
