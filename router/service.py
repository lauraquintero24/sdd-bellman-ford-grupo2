"""Servicio de dominio del Router (02 §3.2, §5; 03 S1–S3; DEC-06).

Pide cada ruta al Controller mediante ``RouteClient`` (nunca la calcula ni la guarda en
caché), construye la traza salto a salto y registra todo resultado mediante ``ForwardingLogDAO``.
"""

from router.models import ForwardingResult, Packet, TraceHop
from router.ports import ForwardingLogDAO, RouteClient
from shared.error_contract import INTERNAL_ERROR, STATUS_FAILED, STATUS_FORWARDED
from shared.errors import AppError, LogPersistenceError


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
