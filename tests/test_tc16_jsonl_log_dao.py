"""JsonlForwardingLogDAO (FR-10, NFR-11; 04 §6): formato de línea, list_recent, errores de E/S
y escritura concurrente a nivel DAO. La parte con 4 clientes HTTP de TC-16 se ejecuta en W-08."""

import json
import re
import threading

import pytest

from router.dao import JsonlForwardingLogDAO
from router.models import ForwardingResult, TraceHop
from shared.error_contract import LOG_RECORD_FIELDS
from shared.errors import LogPersistenceError
from shared.models import Route

ROUTE = Route(source="A", destination="D", metric="delay", path=("A", "B", "D"), total_cost="2", topology_version=1)
OK = ForwardingResult("pkt-001", "A", "D", "delay", "forwarded",
                      (TraceHop(0, "A"), TraceHop(1, "B"), TraceHop(2, "D")), ROUTE, 1, None)
FAILED = ForwardingResult("pkt-002", "A", "D", "delay", "failed", (), None, None,
                          {"code": "CONTROLLER_UNAVAILABLE", "message": "No fue posible conectar con el Controller.", "details": {}})
RECORDED_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def test_creates_file_and_writes_lines_as_in_04_section_6(tmp_path):
    path = tmp_path / "forwarding.jsonl"
    dao = JsonlForwardingLogDAO(path)
    assert path.is_file() and path.read_text() == ""
    dao.save(OK)
    dao.save(FAILED)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first, second = (json.loads(line) for line in lines)
    assert tuple(first) == LOG_RECORD_FIELDS
    assert RECORDED_AT.match(first["recorded_at"])
    assert {k: v for k, v in first.items() if k != "recorded_at"} == {
        "packet_id": "pkt-001", "source": "A", "destination": "D", "metric": "delay", "status": "forwarded",
        "route": {"source": "A", "destination": "D", "metric": "delay", "path": ["A", "B", "D"], "total_cost": "2",
                  "topology_version": 1},
        "trace": [{"hop_index": 0, "node": "A"}, {"hop_index": 1, "node": "B"}, {"hop_index": 2, "node": "D"}],
        "topology_version": 1, "error": None,
    }
    assert (second["status"], second["route"], second["trace"], second["topology_version"]) == ("failed", None, [], None)
    assert second["error"]["code"] == "CONTROLLER_UNAVAILABLE"
    assert "payload" not in first


def test_list_recent_returns_results_in_write_order(tmp_path):
    dao = JsonlForwardingLogDAO(tmp_path / "f.jsonl")
    dao.save(OK)
    dao.save(FAILED)
    assert dao.list_recent(10) == [OK, FAILED]
    assert dao.list_recent(1) == [FAILED]
    assert dao.list_recent(0) == []


def test_existing_file_is_appended_not_truncated(tmp_path):
    path = tmp_path / "f.jsonl"
    JsonlForwardingLogDAO(path).save(OK)
    JsonlForwardingLogDAO(path).save(FAILED)
    assert len(path.read_text().splitlines()) == 2


def test_write_failure_raises_log_persistence_error(tmp_path):
    path = tmp_path / "f.jsonl"
    dao = JsonlForwardingLogDAO(path)
    path.unlink()
    path.mkdir()  # ahora la ruta es un directorio: open("a") falla con OSError
    with pytest.raises(LogPersistenceError) as info:
        dao.save(OK)
    assert info.value.code == "LOG_PERSISTENCE_ERROR"


def test_concurrent_saves_do_not_lose_or_mix_lines(tmp_path):
    dao = JsonlForwardingLogDAO(tmp_path / "f.jsonl")

    def worker(base):
        for i in range(25):
            dao.save(ForwardingResult(f"pkt-{base + i:03d}", "A", "D", "delay", "forwarded", OK.trace, ROUTE, 1, None))

    threads = [threading.Thread(target=worker, args=(n * 25,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    lines = (tmp_path / "f.jsonl").read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert len(records) == 100 and len({r["packet_id"] for r in records}) == 100
    assert len(dao.list_recent(100)) == 100
