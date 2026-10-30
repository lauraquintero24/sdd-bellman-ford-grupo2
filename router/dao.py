"""DAO concreto de la bitácora de reenvío (02 §3.2, §5; 04 §6; NFR-11).

Anexa una línea JSON por resultado bajo un candado de proceso y las relee para consultas.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from router.models import ForwardingResult, TraceHop
from router.ports import ForwardingLogDAO
from shared.errors import LogPersistenceError
from shared.models import Route


def _recorded_at() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _route_to_dict(route: Route | None) -> dict | None:
    if route is None:
        return None
    return {
        "source": route.source,
        "destination": route.destination,
        "metric": route.metric,
        "path": list(route.path),
        "total_cost": route.total_cost,
        "topology_version": route.topology_version,
    }


def _record(result: ForwardingResult) -> dict:
    return {
        "recorded_at": _recorded_at(),
        "packet_id": result.packet_id,
        "source": result.source,
        "destination": result.destination,
        "metric": result.metric,
        "status": result.status,
        "route": _route_to_dict(result.route),
        "trace": [{"hop_index": hop.hop_index, "node": hop.node} for hop in result.trace],
        "topology_version": result.topology_version,
        "error": result.error,
    }


def _from_record(record: dict) -> ForwardingResult:
    route = record["route"]
    return ForwardingResult(
        packet_id=record["packet_id"],
        source=record["source"],
        destination=record["destination"],
        metric=record["metric"],
        status=record["status"],
        trace=tuple(TraceHop(hop["hop_index"], hop["node"]) for hop in record["trace"]),
        route=None if route is None else Route(**{**route, "path": tuple(route["path"])}),
        topology_version=record["topology_version"],
        error=record["error"],
    )


class JsonlForwardingLogDAO(ForwardingLogDAO):
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        try:
            self._path.touch(exist_ok=True)  # la bitácora se crea si no existe (02 §7)
        except OSError as exc:
            raise LogPersistenceError(f"No fue posible crear la bitácora ({exc.strerror}).") from None

    def save(self, result: ForwardingResult) -> None:
        line = json.dumps(_record(result), ensure_ascii=False) + "\n"
        with self._lock:
            try:
                with self._path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
                    handle.flush()
            except OSError:
                raise LogPersistenceError("No fue posible guardar el resultado.") from None

    def list_recent(self, limit: int) -> list[ForwardingResult]:
        with self._lock:
            try:
                lines = self._path.read_text(encoding="utf-8").splitlines()
            except OSError:
                raise LogPersistenceError("No fue posible leer la bitácora.") from None
        recent = lines[-limit:] if limit > 0 else []
        return [_from_record(json.loads(line)) for line in recent]
