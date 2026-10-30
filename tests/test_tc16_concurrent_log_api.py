"""TC-16 — Bitácora con peticiones concurrentes (FR-10, NFR-11).

Bitácora temporal vacía; pkt-000…pkt-099; create_router_app(settings, route_client=FakeRouteClient(E-01))
sin log_dao (se crea JsonlForwardingLogDAO de la configuración); 4 hilos cliente × 25 POST simultáneos.
"""

import json
import threading

from fastapi.testclient import TestClient

from router.app import create_router_app
from router.dao import JsonlForwardingLogDAO
from router.settings import RouterSettings
from shared.error_contract import LOG_RECORD_FIELDS
from shared.models import Route
from tests.fakes import FakeRouteClient

E01 = Route("A", "D", "delay", ("A", "B", "D"), "2", 1)


def test_tc16_four_concurrent_clients(tmp_path):
    path = tmp_path / "forwarding.jsonl"
    settings = RouterSettings("127.0.0.1", 8001, "http://127.0.0.1:9", 1.0, 2.0, path)
    app = create_router_app(settings, route_client=FakeRouteClient(E01))
    statuses, barrier = [], threading.Barrier(4)
    lock = threading.Lock()

    def worker(n):
        client = TestClient(app)
        barrier.wait()  # los 4 clientes empiezan a la vez
        for i in range(n * 25, n * 25 + 25):
            response = client.post("/packets", json={"packet_id": f"pkt-{i:03d}", "source": "A", "destination": "D",
                                                     "metric": "delay"})
            with lock:
                statuses.append(response.status_code)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert statuses.count(200) == 100
    lines = path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]  # toda línea es JSON parseable (sin mezclas)
    assert len(records) == 100
    assert all(tuple(r) == LOG_RECORD_FIELDS and r["status"] == "forwarded" for r in records)
    assert {r["packet_id"] for r in records} == {f"pkt-{i:03d}" for i in range(100)}
    assert len(JsonlForwardingLogDAO(path).list_recent(100)) == 100
