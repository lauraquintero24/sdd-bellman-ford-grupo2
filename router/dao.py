"""DAO concreto de la bitácora de reenvío (02 §3.2, §5; 04 §6; NFR-11).

Anexa una línea JSON por resultado bajo un candado de proceso y las relee para consultas.
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from router.models import ForwardingResult, NodeTables, TraceHop
from router.ports import ForwardingLogDAO, ForwardingTableDAO
from shared.errors import LogPersistenceError
from shared.models import ForwardingEntry, ForwardingTable, Route


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


# --- Modo nodo (C-32, 04 §6) ---

def _entry_to_dict(entry: ForwardingEntry) -> dict:
    return {
        "destination": entry.destination,
        "next_hop": entry.next_hop,
        "path": list(entry.path) if entry.path is not None else None,
        "total_cost": entry.total_cost,
        "status": entry.status,
    }


def _tables_to_dict(tables: NodeTables) -> dict:
    return {
        "router_id": tables.router_id,
        "url": tables.url,
        "topology_version": tables.topology_version,
        "synced_at": tables.synced_at,
        "tables": {metric: [_entry_to_dict(e) for e in table.entries] for metric, table in tables.tables.items()},
    }


def _tables_from_dict(doc: dict) -> NodeTables:
    tables = {}
    for metric, rows in doc["tables"].items():
        entries = tuple(
            ForwardingEntry(row["destination"], row["next_hop"], tuple(row["path"]) if row["path"] else None,
                            row["total_cost"], row["status"])
            for row in rows
        )
        tables[metric] = ForwardingTable(doc["router_id"], metric, doc["topology_version"], entries)
    return NodeTables(doc["router_id"], doc["url"], doc["topology_version"], doc["synced_at"], tables)


def _summary(entry: ForwardingEntry | None) -> dict | None:
    if entry is None:
        return None
    return {"next_hop": entry.next_hop, "total_cost": entry.total_cost, "status": entry.status}


def _changes(previous: NodeTables | None, current: NodeTables) -> list[dict]:
    changes = []
    for metric, table in current.tables.items():
        before_table = previous.tables.get(metric) if previous is not None else None
        before = {e.destination: e for e in before_table.entries} if before_table is not None else {}
        for entry in table.entries:
            old = _summary(before.get(entry.destination))
            new = _summary(entry)
            if old != new:
                changes.append({"metric": metric, "destination": entry.destination, "before": old, "after": new})
    return changes


class JsonForwardingTableDAO(ForwardingTableDAO):
    """Tabla local de una instancia: ``forwarding-table.json`` (reemplazo atómico) y ``table-events.jsonl``."""

    def __init__(self, path: Path, events_path: Path) -> None:
        self._path = Path(path)
        self._events_path = Path(events_path)
        self._lock = threading.Lock()

    def load(self) -> NodeTables | None:
        with self._lock:
            return self._load()

    def _load(self) -> NodeTables | None:
        if not self._path.exists():
            return None
        try:
            return _tables_from_dict(json.loads(self._path.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            raise LogPersistenceError("No fue posible leer la tabla de forwarding local.") from None

    def save(self, tables: NodeTables) -> None:
        with self._lock:
            try:
                previous = self._load()
            except LogPersistenceError:
                previous = None
            event = {
                "recorded_at": _recorded_at(),
                "router_id": tables.router_id,
                "previous_version": previous.topology_version if previous is not None else None,
                "topology_version": tables.topology_version,
                "changes": _changes(previous, tables),
            }
            tmp = self._path.with_name(self._path.name + ".tmp")
            try:
                tmp.write_text(json.dumps(_tables_to_dict(tables), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                os.replace(tmp, self._path)
                with self._events_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            except OSError:
                raise LogPersistenceError("No fue posible guardar la tabla de forwarding.") from None
