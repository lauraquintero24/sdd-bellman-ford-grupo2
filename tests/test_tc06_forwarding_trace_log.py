"""TC-06 — La traza de reenvío informa un resultado válido (FR-08, FR-10).

API del Router (TestClient) con FakeRouteClient(ruta de E-01) y bitácora JSONL temporal real.
Además, la misma comprobación a nivel de servicio (sin HTTP).
"""

import json

from router.dao import JsonlForwardingLogDAO
from router.models import Packet, TraceHop
from router.service import ForwardingService
from shared.models import Route
from tests.fakes import FakeRouteClient

E01 = Route(source="A", destination="D", metric="delay", path=("A", "B", "D"), total_cost="2", topology_version=1)
E01_JSON = {"source": "A", "destination": "D", "metric": "delay", "path": ["A", "B", "D"], "total_cost": "2",
            "topology_version": 1}
TRACE_JSON = [{"hop_index": 0, "node": "A"}, {"hop_index": 1, "node": "B"}, {"hop_index": 2, "node": "D"}]


def _check_log(path, log_dao):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert (record["packet_id"], record["source"], record["destination"], record["metric"], record["status"]) == (
        "pkt-001", "A", "D", "delay", "forwarded")
    assert record["route"] == E01_JSON and record["trace"] == TRACE_JSON and record["topology_version"] == 1
    assert record["error"] is None
    (recent,) = log_dao.list_recent(10)
    assert recent.packet_id == "pkt-001" and recent.status == "forwarded" and recent.route == E01


def test_tc06_service_level(tmp_path):
    path = tmp_path / "forwarding.jsonl"
    log_dao = JsonlForwardingLogDAO(path)
    result = ForwardingService(client=FakeRouteClient(E01), log_dao=log_dao).forward(
        Packet("pkt-001", "A", "D", "", "delay"))
    assert result.trace == (TraceHop(0, "A"), TraceHop(1, "B"), TraceHop(2, "D"))
    for i, hop in enumerate(result.trace):
        assert hop.hop_index == i and hop.node == E01.path[i]
    _check_log(path, log_dao)


def test_tc06_api(tmp_path):
    from fastapi.testclient import TestClient

    from router.app import create_router_app
    from router.settings import RouterSettings

    path = tmp_path / "forwarding.jsonl"
    log_dao = JsonlForwardingLogDAO(path)
    settings = RouterSettings("127.0.0.1", 8001, "http://127.0.0.1:8000", 1.0, 2.0, path)
    client = TestClient(create_router_app(settings, route_client=FakeRouteClient(E01), log_dao=log_dao))
    response = client.post("/packets", json={"packet_id": "pkt-001", "source": "A", "destination": "D", "metric": "delay"})
    assert response.status_code == 200
    assert response.json() == {"packet_id": "pkt-001", "status": "forwarded", "route": E01_JSON, "trace": TRACE_JSON,
                               "topology_version": 1}
    _check_log(path, log_dao)
