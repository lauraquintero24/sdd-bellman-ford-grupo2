"""TC-42 — Cada router mantiene y publica su propia tabla (FR-12; C-32).

Cuatro aplicaciones Router en modo nodo (una por nodo de F-20), cada una con su HttpTableClient real
conectado al Controller real por un puente HTTP en proceso, su directorio de datos y su hilo de
sincronización. El arranque con procesos reales y puertos propios se prueba en TC-40.
"""

import json
import shutil
import time

import pytest
from fastapi.testclient import TestClient

from controller.app import create_controller_app
from controller.settings import ControllerSettings
from router.app import create_router_app
from router.client import HttpTableClient
from router.settings import RouterSettings
from shared.models import RouterInfo
from tests.fakes import FIXTURES_DIR, asgi_bridge

REGISTRY = tuple(RouterInfo(n, f"http://127.0.0.1:{8001 + i}") for i, n in enumerate("ABCD"))
EXPECTED_DELAY = {  # 06 §3.1, T-07–T-10: (destino, siguiente salto, costo)
    "A": [("B", "B", "1"), ("C", "C", "2"), ("D", "B", "2")],
    "B": [("A", "A", "1"), ("C", "A", "3"), ("D", "D", "1")],
    "C": [("A", "A", "2"), ("B", "A", "3"), ("D", "D", "2")],
    "D": [("A", "B", "2"), ("B", "B", "1"), ("C", "C", "2")],
}


@pytest.fixture
def controller(tmp_path):
    topology = tmp_path / "F-20.json"
    shutil.copy(FIXTURES_DIR / "F-20.json", topology)
    return TestClient(create_controller_app(ControllerSettings("127.0.0.1", 8000, topology)))


def _router_app(tmp_path, router_id, controller, interval=0.05):
    folder = tmp_path / "routers" / router_id
    folder.mkdir(parents=True)
    settings = RouterSettings("127.0.0.1", 8001, "http://controller.test", 1.0, 2.0, folder / "forwarding.jsonl",
                              router_id=router_id, routers=REGISTRY, table_file=folder / "forwarding-table.json",
                              sync_interval_s=interval)
    client = HttpTableClient("http://controller.test", 1.0, 2.0, transport=asgi_bridge(controller))
    return create_router_app(settings, table_client=client)


def _wait_synced(client, version, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = client.get("/status").json()
        if status["sync_status"] == "ok" and status["topology_version"] == version:
            return status
        time.sleep(0.02)
    raise AssertionError(f"sin sincronizar: {client.get('/status').json()}")


def test_each_router_publishes_its_own_table(tmp_path, controller):
    apps = {n: _router_app(tmp_path, n, controller) for n in "ABCD"}
    clients = {n: TestClient(app) for n, app in apps.items()}
    for client in clients.values():
        client.__enter__()  # arranca el ciclo de vida: hilo de sincronización
    try:
        tables = {}
        for n, client in clients.items():
            status = _wait_synced(client, 1)
            assert (status["router_id"], status["url"], status["mode"]) == (n, f"http://127.0.0.1:{8001 + 'ABCD'.index(n)}", "node")
            body = client.get("/forwarding-table", params={"metric": "delay"}).json()
            assert body["router_id"] == n and body["url"] == status["url"] and body["topology_version"] == 1
            tables[n] = [(e["destination"], e["next_hop"], e["total_cost"]) for e in body["entries"]]
            assert tables[n] == EXPECTED_DELAY[n]
        assert len({tuple(t) for t in tables.values()}) == 4  # cuatro tablas distintas
        # Cada instancia escribe solo en su propio directorio
        for n in "ABCD":
            own = json.loads((tmp_path / "routers" / n / "forwarding-table.json").read_text(encoding="utf-8"))
            assert own["router_id"] == n
            assert sorted(p.name for p in (tmp_path / "routers" / n).iterdir()) == [
                "forwarding-table.json", "forwarding.jsonl", "table-events.jsonl"]
        # Fallo de B–D: las tablas se renuevan solas (hilo periódico) a la versión 2 (T-19–T-22)
        controller.post("/links/fail", json={"source": "B", "target": "D"})
        for client in clients.values():
            _wait_synced(client, 2)
        row = clients["B"].get("/forwarding-table", params={"metric": "delay"}).json()["entries"][2]
        assert (row["destination"], row["next_hop"], row["path"], row["total_cost"]) == ("D", "A", ["B", "A", "C", "D"], "5")
    finally:
        for client in clients.values():
            client.__exit__(None, None, None)


def test_table_unavailable_before_first_sync_and_errors(tmp_path, controller):
    client = TestClient(_router_app(tmp_path, "A", controller, interval=0))  # sin sincronización periódica
    response = client.get("/forwarding-table", params={"metric": "delay"})
    assert response.status_code == 503 and response.json()["error"]["code"] == "FORWARDING_TABLE_UNAVAILABLE"
    assert client.get("/status").json()["sync_status"] == "pending"
    assert client.get("/forwarding-table", params={"metric": "hops"}).status_code == 400
    assert client.get("/health").json() == {"status": "ok", "application": "router"}


def test_cors_allows_the_web_interface(tmp_path, controller):
    client = TestClient(_router_app(tmp_path, "A", controller, interval=0))
    response = client.get("/status", headers={"Origin": "http://127.0.0.1:8000"})
    assert response.headers.get("access-control-allow-origin") == "*"
