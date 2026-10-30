"""TC-12 — Contrato API del Controller (FR-05, FR-09, NFR-04, NFR-06; 06 §5.1; 04 §3, §5).

F-01 recién cargado; estados y error.code exactos; sin trazas; /health 200 al final.
"""

import json
from decimal import Decimal

import pytest

from controller.view import decimal_to_text

JSON = {"content-type": "application/json"}

CASES = [
    ("sin-metric", "GET", "/route?src=A&dst=D", None, 400, "INVALID_REQUEST", None),
    ("metric-foo", "GET", "/route?src=A&dst=D&metric=foo", None, 400, "INVALID_REQUEST", None),
    ("src-vacio", "GET", "/route?src=&dst=D&metric=delay", None, 400, "INVALID_REQUEST", None),
    ("src-X", "GET", "/route?src=X&dst=D&metric=delay", None, 404, "NODE_NOT_FOUND", {"field": "src"}),
    ("src-X-dst-Y", "GET", "/route?src=X&dst=Y&metric=delay", None, 404, "NODE_NOT_FOUND", {"field": "src"}),
    ("dst-Y", "GET", "/route?src=A&dst=Y&metric=delay", None, 404, "NODE_NOT_FOUND", {"field": "dst"}),
    ("espacio-inicial", "GET", "/route?src=%20A&dst=D&metric=delay", None, 400, "INVALID_REQUEST", None),
    ("rutas", "GET", "/rutas", None, 404, "UNKNOWN_ENDPOINT", None),
    ("delete-topology", "DELETE", "/topology", None, 405, "METHOD_NOT_ALLOWED", None),
    ("json-ilegible", "POST", "/links/fail", '{"source": "B",', 400, "MALFORMED_JSON", None),
    ("falta-target", "POST", "/links/fail", '{"source": "B"}', 400, "INVALID_REQUEST", {"fields": ["target"]}),
    ("campo-extra", "POST", "/links/fail", '{"source": "B", "target": "D", "x": 1}', 400, "INVALID_REQUEST", None),
    ("nodo-X", "POST", "/links/fail", '{"source": "X", "target": "D"}', 404, "NODE_NOT_FOUND", {"field": "source"}),
    ("enlace-D-A", "POST", "/links/fail", '{"source": "D", "target": "A"}', 404, "LINK_NOT_FOUND", None),
]


def _assert_error_envelope(body, code):
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and isinstance(body["error"]["details"], dict)
    text = json.dumps(body)
    assert "Traceback" not in text and ".py" not in text and "/home" not in text


@pytest.mark.parametrize("name, method, url, body, status, code, details", CASES, ids=[c[0] for c in CASES])
def test_tc12_error_cases(controller_client, name, method, url, body, status, code, details):
    client = controller_client("F-01")
    response = client.request(method, url, content=body, headers=JSON if body is not None else None)
    assert response.status_code == status
    _assert_error_envelope(response.json(), code)
    for key, value in (details or {}).items():
        assert response.json()["error"]["details"][key] == value
    assert client.get("/topology").json()["topology_version"] == 1  # los errores no cambian la versión
    assert client.get("/health").status_code == 200


def test_tc12_same_node_route(controller_client):
    response = controller_client("F-01").get("/route?src=A&dst=A&metric=loss")
    assert response.status_code == 200
    assert response.json()["path"] == ["A"] and response.json()["total_cost"] == "0"


def test_tc12_health(controller_client):
    response = controller_client("F-01").get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "application": "controller"}


def test_topology_matches_04_example(controller_client):
    response = controller_client("F-01").get("/topology")
    assert response.status_code == 200
    link = {"delay_ms": "1.0", "bandwidth_mbps": "10.0", "loss_probability": "0.01", "active": True}
    link2 = {"delay_ms": "2.0", "bandwidth_mbps": "100.0", "loss_probability": "0.02", "active": True}
    assert response.json() == {
        "topology_version": 1,
        "directed": True,
        "nodes": ["A", "B", "C", "D"],
        "links": [
            {"source": "A", "target": "B", **link},
            {"source": "B", "target": "D", **link},
            {"source": "A", "target": "C", **link2},
            {"source": "C", "target": "D", **link2},
        ],
    }


def test_topology_shows_inactive_links_and_exact_decimals(controller_client):
    client = controller_client("F-18")
    body = client.get("/topology").json()
    assert {l["loss_probability"] for l in body["links"]} >= {"1e-60"}
    client2 = controller_client("F-01")
    client2.post("/links/fail", json={"source": "B", "target": "D"})
    links = client2.get("/topology").json()["links"]
    assert [l["active"] for l in links] == [True, False, True, True]


@pytest.mark.parametrize(
    "literal, text",
    [("1.0", "1.0"), ("0.01", "0.01"), ("100.0", "100.0"), ("1e-60", "1e-60"), ("1.5e13", "1.5e+13"),
     ("0.000001", "0.000001"), ("1e-7", "1e-7"), ("1e2", "100"), ("0", "0"), ("123456789012", "123456789012"), ("1e12", "1e+12")],
)
def test_decimal_text_format(literal, text):
    assert decimal_to_text(Decimal(literal)) == text
