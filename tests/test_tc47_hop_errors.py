"""TC-47 — Errores de comunicación entre routers (FR-13, FR-09, NFR-06; C-32).

Nunca 200 ante un fallo; registro failed en el router que procesó el paquete; /health 200 después.
"""

import json
import shutil

import httpx
import pytest
from fastapi.testclient import TestClient

from controller.app import create_controller_app
from controller.settings import ControllerSettings
from router.app import create_router_app
from router.client import HttpNextHopClient, HttpTableClient
from router.settings import RouterSettings
from shared.models import RouterInfo
from tests.fakes import FIXTURES_DIR, asgi_bridge
from tests.test_tc46_hop_by_hop import build_network, send

REGISTRY = tuple(RouterInfo(n, f"http://127.0.0.1:{8001 + i}") for i, n in enumerate("ABCD"))
PACKET = {"packet_id": "pkt-e", "source": "A", "destination": "D", "metric": "delay"}


def router_a(tmp_path, next_hop_handler, table_transport=None):
    topology = tmp_path / "F-20.json"
    shutil.copy(FIXTURES_DIR / "F-20.json", topology)
    controller = TestClient(create_controller_app(ControllerSettings("127.0.0.1", 8000, topology)))
    folder = tmp_path / "A"
    folder.mkdir()
    settings = RouterSettings("127.0.0.1", 8001, "http://controller.test", 1.0, 2.0, folder / "forwarding.jsonl",
                              router_id="A", routers=REGISTRY, table_file=folder / "forwarding-table.json",
                              sync_interval_s=0)
    app = create_router_app(
        settings,
        table_client=HttpTableClient("http://controller.test", 1.0, 2.0,
                                     transport=table_transport or asgi_bridge(controller)),
        next_hop_client=HttpNextHopClient(1.0, 2.0, transport=httpx.MockTransport(next_hop_handler)),
    )
    return TestClient(app, raise_server_exceptions=False), folder / "forwarding.jsonl"


def raising(exc):
    def handler(request):
        raise exc("fallo simulado", request=request)
    return handler


def good_body(request):
    return {"packet_id": "pkt-e", "status": "forwarded", "topology_version": 1, "forwarding_mode": "hop_by_hop",
            "route": {"source": "A", "destination": "D", "metric": "delay", "path": ["A", "B", "D"], "total_cost": "1",
                      "topology_version": 1},
            "trace": [{"hop_index": 0, "node": "A", "router_url": "http://127.0.0.1:8001"},
                      {"hop_index": 1, "node": "B", "router_url": "http://127.0.0.1:8002"},
                      {"hop_index": 2, "node": "D", "router_url": "http://127.0.0.1:8004"}]}


def respond(mutate):
    def handler(request):
        body = good_body(request)
        mutate(body)
        return httpx.Response(200, json=body)
    return handler


CASES = {
    "siguiente-caido": (raising(httpx.ConnectError), 503, "NEXT_HOP_UNAVAILABLE"),
    "siguiente-connect-timeout": (raising(httpx.ConnectTimeout), 504, "NEXT_HOP_TIMEOUT"),
    "siguiente-read-timeout": (raising(httpx.ReadTimeout), 504, "NEXT_HOP_TIMEOUT"),
    "conexion-cortada": (raising(httpx.RemoteProtocolError), 502, "NEXT_HOP_BAD_RESPONSE"),
    "sin-json": (lambda r: httpx.Response(200, content=b"<html>"), 502, "NEXT_HOP_BAD_RESPONSE"),
    "estado-500-sin-sobre": (lambda r: httpx.Response(500, json={"detail": "x"}), 502, "NEXT_HOP_BAD_RESPONSE"),
    "traza-no-empieza-por-la-enviada": (respond(lambda b: b["trace"].__setitem__(0, {**b["trace"][0], "node": "X"})),
                                        502, "NEXT_HOP_BAD_RESPONSE"),
    "no-termina-en-destino": (respond(lambda b: (b["trace"].pop(), b["route"]["path"].pop())), 502, "NEXT_HOP_BAD_RESPONSE"),
    "otra-version": (respond(lambda b: (b.__setitem__("topology_version", 2), b["route"].__setitem__("topology_version", 2))),
                     502, "NEXT_HOP_BAD_RESPONSE"),
    "nodo-repetido": (respond(lambda b: (b["trace"].insert(2, {"hop_index": 2, "node": "A", "router_url": "u"}),
                                         [h.__setitem__("hop_index", i) for i, h in enumerate(b["trace"])],
                                         b["route"].__setitem__("path", [h["node"] for h in b["trace"]]))),
                      502, "NEXT_HOP_BAD_RESPONSE"),
    "estado-failed-con-200": (respond(lambda b: b.__setitem__("status", "failed")), 502, "NEXT_HOP_BAD_RESPONSE"),
    "error-propagado-404": (lambda r: httpx.Response(404, json={"packet_id": "pkt-e", "status": "failed", "trace": [], "error": {
        "code": "ROUTE_UNREACHABLE", "message": "No existe una ruta utilizable de B a D.",
        "details": {"at_router": "B", "source": "B", "destination": "D", "metric": "delay"}}}), 404, "ROUTE_UNREACHABLE"),
    "error-propagado-508": (lambda r: httpx.Response(508, json={"packet_id": "pkt-e", "status": "failed", "trace": [], "error": {
        "code": "FORWARDING_LOOP", "message": "bucle", "details": {"at_router": "B"}}}), 508, "FORWARDING_LOOP"),
}


@pytest.mark.parametrize("handler, status, code", list(CASES.values()), ids=list(CASES))
def test_next_hop_failures_are_controlled(tmp_path, handler, status, code):
    client, log = router_a(tmp_path, handler)
    response = client.post("/packets", json=PACKET)
    assert response.status_code == status
    body = response.json()
    assert (body["packet_id"], body["status"], body["trace"], body["error"]["code"]) == ("pkt-e", "failed", [], code)
    assert "Traceback" not in response.text
    records = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
    assert [(r["role"], r["status"], r["error"]["code"]) for r in records] == [("ingress", "failed", code)]
    assert client.get("/health").status_code == 200


def test_controller_unavailable_blocks_forwarding(tmp_path):
    client, log = router_a(tmp_path, respond(lambda b: None), table_transport=httpx.MockTransport(raising(httpx.ConnectError)))
    response = client.post("/packets", json=PACKET)
    assert response.status_code == 503 and response.json()["error"]["code"] == "CONTROLLER_UNAVAILABLE"
    assert json.loads(log.read_text(encoding="utf-8"))["status"] == "failed"
    assert client.get("/status").json()["sync_status"] == "error"


def test_wrong_ingress_router_is_400_without_record(tmp_path):
    client, log = router_a(tmp_path, respond(lambda b: None))
    response = client.post("/packets", json={**PACKET, "source": "B"})
    assert response.status_code == 400 and response.json() == {"error": {
        "code": "INVALID_REQUEST", "message": "El paquete debe entrar por su router de origen; este es A.",
        "details": {"fields": ["source"]}}}
    assert log.read_text(encoding="utf-8") == ""


def _hop(trace_nodes, version=1, destination="D"):
    return {**PACKET, "destination": destination, "topology_version": version,
            "trace": [{"hop_index": i, "node": n, "router_url": f"http://h/{n}"} for i, n in enumerate(trace_nodes)]}


def test_loop_hop_limit_and_version_change_on_forward(tmp_path):
    _, routers, _ = build_network(tmp_path)
    b = routers["B"]
    loop = b.post("/forward", json=_hop(["A", "B"]))
    assert loop.status_code == 508 and loop.json()["error"]["code"] == "FORWARDING_LOOP"
    assert loop.json()["error"]["details"]["at_router"] == "B"
    limit = b.post("/forward", json=_hop(["A", "C", "D", "X"]))
    assert limit.status_code == 508 and limit.json()["error"]["code"] == "HOP_LIMIT_EXCEEDED"
    changed = b.post("/forward", json=_hop(["A"], version=7))
    assert changed.status_code == 409 and changed.json()["error"]["code"] == "TOPOLOGY_CHANGED"
    assert changed.json()["error"]["details"] == {"at_router": "B", "received": 7, "current": 1}
    bad = b.post("/forward", json={**_hop(["A"]), "extra": 1})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "INVALID_REQUEST"
    assert b.get("/health").status_code == 200


def test_error_from_a_later_hop_reaches_the_origin(tmp_path):
    controller, routers, mesh = build_network(tmp_path)
    send(routers, "A", "D", "delay", "warmup")
    del mesh.clients["http://127.0.0.1:8004"]  # D deja de responder: B no puede entregar
    response = send(routers, "A", "D", "delay", "pkt-d")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "NEXT_HOP_UNAVAILABLE" and error["details"]["at_router"] == "B"
    for n in "AB":
        last = json.loads((tmp_path / "routers" / n / "forwarding.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        assert (last["packet_id"], last["status"], last["error"]["code"]) == ("pkt-d", "failed", "NEXT_HOP_UNAVAILABLE")
