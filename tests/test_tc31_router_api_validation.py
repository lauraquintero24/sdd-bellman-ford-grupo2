"""TC-31 (parte API) — validación de entrada y de respuestas en el Router (FR-08, FR-09, NFR-04, NFR-06).

create_router_app(settings, route_client=HttpRouteClient(…, transport=MockTransport), log_dao=FakeForwardingLogDAO()).
"""

import json

import httpx
import pytest

from router.client import HttpRouteClient
from tests.fakes import FakeForwardingLogDAO

VALID = {"source": "A", "destination": "D", "metric": "delay", "path": ["A", "B", "D"], "total_cost": "2",
         "topology_version": 1}
PACKET = {"packet_id": "pkt-001", "source": "A", "destination": "D", "metric": "delay"}
JSON = {"content-type": "application/json"}


def make(router_client, status=200, body=None, content=None):
    calls = []

    def handler(request):
        calls.append(request)
        if content is not None:
            return httpx.Response(status, content=content)
        return httpx.Response(status, json=body)

    client = HttpRouteClient("http://controller.test", 1.0, 2.0, transport=httpx.MockTransport(handler))
    log_dao = FakeForwardingLogDAO()
    return router_client(route_client=client, log_dao=log_dao), log_dao, calls


INPUT_CASES = {
    "cuerpo-ilegible": ('{"packet_id": "p",', "MALFORMED_JSON"),
    "campo-adicional": (json.dumps({**PACKET, "x": 1}), "INVALID_REQUEST"),
    "sin-metric": (json.dumps({k: v for k, v in PACKET.items() if k != "metric"}), "INVALID_REQUEST"),
    "metric-invalida": (json.dumps({**PACKET, "metric": "hops"}), "INVALID_REQUEST"),
    "packet-id-vacio": (json.dumps({**PACKET, "packet_id": ""}), "INVALID_REQUEST"),
    "source-con-espacios": (json.dumps({**PACKET, "source": " A"}), "INVALID_REQUEST"),
    "source-numero": (json.dumps({**PACKET, "source": 1}), "INVALID_REQUEST"),
    "payload-no-texto": (json.dumps({**PACKET, "payload": 5}), "INVALID_REQUEST"),
    "no-objeto": ("[]", "INVALID_REQUEST"),
}


@pytest.mark.parametrize("body, code", list(INPUT_CASES.values()), ids=list(INPUT_CASES))
def test_invalid_input_is_400_without_record(router_client, body, code):
    client, log_dao, calls = make(router_client, body=VALID)
    response = client.post("/packets", content=body, headers=JSON)
    assert response.status_code == 400
    assert set(response.json()) == {"error"} and response.json()["error"]["code"] == code
    assert log_dao.saved == [] and calls == []  # ni registro ni petición al Controller
    assert client.get("/health").status_code == 200


RESPONSE_DEFECTS = {
    "sin-json": dict(content=b"no-json"),
    "path-vacio": dict(body={**VALID, "path": []}),
    "path-X-D": dict(body={**VALID, "path": ["X", "D"]}),
    "path-A-B-A-D": dict(body={**VALID, "path": ["A", "B", "A", "D"]}),
    "cost-numero": dict(body={**VALID, "total_cost": 2}),
    "cost-NaN": dict(body={**VALID, "total_cost": "NaN"}),
    "cost--0": dict(body={**VALID, "total_cost": "-0"}),
    "cost--1": dict(body={**VALID, "total_cost": "-1"}),
    "cost-vacio": dict(body={**VALID, "total_cost": ""}),
    "cost-2.0": dict(body={**VALID, "total_cost": "2.0"}),
    "cost-1e-07": dict(body={**VALID, "total_cost": "1e-07"}),
    "cost-true": dict(body={**VALID, "total_cost": True}),
    "version-0": dict(body={**VALID, "topology_version": 0}),
    "version-true": dict(body={**VALID, "topology_version": True}),
    "metric-distinta": dict(body={**VALID, "metric": "loss"}),
}


@pytest.mark.parametrize("kwargs", list(RESPONSE_DEFECTS.values()), ids=list(RESPONSE_DEFECTS))
def test_non_conforming_controller_response_is_502_and_logged(router_client, kwargs):
    client, log_dao, _ = make(router_client, **kwargs)
    response = client.post("/packets", json=PACKET)
    assert response.status_code == 502
    assert response.json() == {
        "packet_id": "pkt-001", "status": "failed", "trace": [],
        "error": {"code": "CONTROLLER_BAD_RESPONSE", "message": "La respuesta del Controller no cumple el contrato.",
                  "details": {}},
    }
    assert [(r.status, r.trace, r.route) for r in log_dao.saved] == [("failed", (), None)]
    assert client.get("/health").status_code == 200


def test_404_is_propagated_with_source_field(router_client):
    body = {"error": {"code": "NODE_NOT_FOUND", "message": "El nodo X no existe en la topología.",
                      "details": {"field": "src", "value": "X"}}}
    client, log_dao, _ = make(router_client, status=404, body=body)
    response = client.post("/packets", json={**PACKET, "source": "X"})
    assert response.status_code == 404
    assert response.json() == {"packet_id": "pkt-001", "status": "failed", "trace": [],
                               "error": {"code": "NODE_NOT_FOUND", "message": "El nodo X no existe en la topología.",
                                         "details": {"field": "source", "value": "X"}}}
    assert log_dao.saved[0].status == "failed" and log_dao.saved[0].error["details"]["field"] == "source"


def test_router_health_unknown_endpoint_and_method(router_client):
    client, _, _ = make(router_client, body=VALID)
    assert client.get("/health").json() == {"status": "ok", "application": "router"}
    assert client.get("/rutas").status_code == 404 and client.get("/rutas").json()["error"]["code"] == "UNKNOWN_ENDPOINT"
    response = client.get("/packets")
    assert response.status_code == 405 and response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_valid_packet_with_default_payload_is_forwarded(router_client):
    client, log_dao, calls = make(router_client, body=VALID)
    response = client.post("/packets", json=PACKET)
    assert response.status_code == 200 and response.json()["status"] == "forwarded"
    assert len(calls) == 1 and [r.status for r in log_dao.saved] == ["forwarded"]
