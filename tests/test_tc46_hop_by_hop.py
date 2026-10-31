"""TC-46 — El reenvío usa las decisiones de forwarding vigentes, salto a salto por HTTP (FR-13, FR-07; C-32).

En proceso: Controller real y cuatro aplicaciones Router en modo nodo; cada salto es un POST /forward real
(HttpNextHopClient) entregado a la aplicación del siguiente router. La prueba con 5 procesos reales está en
test_tc40_tc45_tc46_five_processes.py.
"""

import json
import shutil

import pytest
from fastapi.testclient import TestClient

from controller.app import create_controller_app
from controller.settings import ControllerSettings
from router.app import create_router_app
from router.client import HttpNextHopClient, HttpTableClient
from router.settings import RouterSettings
from shared.models import RouterInfo
from tests.fakes import FIXTURES_DIR, RouterMesh, asgi_bridge

REGISTRY = tuple(RouterInfo(n, f"http://127.0.0.1:{8001 + i}") for i, n in enumerate("ABCD"))
METRICS = ("delay", "inverse_bandwidth", "loss")


def build_network(tmp_path, fixture="F-20"):
    topology = tmp_path / f"{fixture}.json"
    shutil.copy(FIXTURES_DIR / f"{fixture}.json", topology)
    controller = TestClient(create_controller_app(ControllerSettings("127.0.0.1", 8000, topology)))
    mesh = RouterMesh()
    routers = {}
    for info in REGISTRY:
        folder = tmp_path / "routers" / info.router_id
        folder.mkdir(parents=True)
        settings = RouterSettings("127.0.0.1", 8001, "http://controller.test", 1.0, 2.0, folder / "forwarding.jsonl",
                                  router_id=info.router_id, routers=REGISTRY, table_file=folder / "forwarding-table.json",
                                  sync_interval_s=0)
        app = create_router_app(
            settings,
            table_client=HttpTableClient("http://controller.test", 1.0, 2.0, transport=asgi_bridge(controller)),
            next_hop_client=HttpNextHopClient(1.0, 2.0, transport=mesh.transport()),
        )
        routers[info.router_id] = TestClient(app, raise_server_exceptions=False)
        mesh.add(info.url, routers[info.router_id])
    return controller, routers, mesh


def send(routers, src, dst, metric, packet_id="pkt"):
    return routers[src].post("/packets", json={"packet_id": packet_id, "source": src, "destination": dst, "metric": metric})


@pytest.mark.parametrize("fixture", ["F-20", "F-01"])
@pytest.mark.parametrize("metric", METRICS)
def test_every_pair_follows_the_controller_route(tmp_path, fixture, metric):
    controller, routers, mesh = build_network(tmp_path, fixture)
    for src in "ABCD":
        for dst in "ABCD":
            if src == dst:
                continue
            expected = controller.get("/route", params={"src": src, "dst": dst, "metric": metric})
            before = len(mesh.requests)
            response = send(routers, src, dst, metric)
            if expected.status_code == 404:
                assert response.status_code == 404
                assert response.json()["error"]["code"] == expected.json()["error"]["code"] == "ROUTE_UNREACHABLE"
                assert len(mesh.requests) == before  # sin vecino que contactar
                continue
            assert response.status_code == 200, response.text
            body, route = response.json(), expected.json()
            assert body["route"]["path"] == route["path"] and body["route"]["total_cost"] == route["total_cost"]
            assert [h["node"] for h in body["trace"]] == route["path"]
            assert [h["router_url"] for h in body["trace"]] == [
                f"http://127.0.0.1:{8001 + 'ABCD'.index(n)}" for n in route["path"]]
            hops = mesh.requests[before:]
            assert [path for _, path, _ in hops] == ["/forward"] * (len(route["path"]) - 1)  # un POST por salto
            assert [base for base, _, _ in hops] == [
                f"http://127.0.0.1:{8001 + 'ABCD'.index(n)}" for n in route["path"][1:]]


def test_failure_and_restoration_change_the_forwarding(tmp_path):
    controller, routers, _ = build_network(tmp_path)
    assert [h["node"] for h in send(routers, "A", "D", "delay", "p1").json()["trace"]] == ["A", "B", "D"]
    controller.post("/links/fail", json={"source": "B", "target": "D"})
    body = send(routers, "A", "D", "delay", "p2").json()
    assert [h["node"] for h in body["trace"]] == ["A", "C", "D"] and body["route"]["total_cost"] == "4"
    assert body["topology_version"] == 2
    controller.post("/links/restore", json={"source": "B", "target": "D"})
    body = send(routers, "A", "D", "delay", "p3").json()
    assert [h["node"] for h in body["trace"]] == ["A", "B", "D"] and body["topology_version"] == 3


def test_each_router_logs_its_own_role(tmp_path):
    _, routers, _ = build_network(tmp_path)
    assert send(routers, "A", "D", "delay", "pkt-log").status_code == 200
    roles = {}
    for n in "ABCD":
        lines = (tmp_path / "routers" / n / "forwarding.jsonl").read_text(encoding="utf-8").splitlines()
        roles[n] = [(json.loads(l)["router_id"], json.loads(l)["role"], json.loads(l)["status"]) for l in lines]
    assert roles == {"A": [("A", "ingress", "forwarded")], "B": [("B", "transit", "forwarded")],
                     "C": [], "D": [("D", "egress", "forwarded")]}
    record = json.loads((tmp_path / "routers" / "A" / "forwarding.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert list(record)[-2:] == ["router_id", "role"]
    assert record["trace"][1] == {"hop_index": 1, "node": "B", "router_url": "http://127.0.0.1:8002"}


def test_packet_to_itself(tmp_path):
    _, routers, mesh = build_network(tmp_path)
    body = send(routers, "C", "C", "loss").json()
    assert body["route"]["path"] == ["C"] and body["route"]["total_cost"] == "0" and mesh.requests == []
