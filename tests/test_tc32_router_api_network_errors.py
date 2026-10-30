"""TC-32 (parte API) — POST /packets ante fallos de red del Controller (FR-07, FR-09, NFR-06)."""

import httpx
import pytest

from router.client import HttpRouteClient
from tests.fakes import FakeForwardingLogDAO

PACKET = {"packet_id": "pkt-002", "source": "A", "destination": "D", "metric": "delay"}


def raising(exc_type):
    def handler(request):
        raise exc_type("fallo simulado", request=request)
    return handler


@pytest.mark.parametrize(
    "handler, status, code",
    [
        (raising(httpx.ConnectError), 503, "CONTROLLER_UNAVAILABLE"),
        (raising(httpx.ConnectTimeout), 504, "CONTROLLER_TIMEOUT"),
        (raising(httpx.ReadTimeout), 504, "CONTROLLER_TIMEOUT"),
        (raising(httpx.WriteTimeout), 504, "CONTROLLER_TIMEOUT"),
        (raising(httpx.PoolTimeout), 504, "CONTROLLER_TIMEOUT"),
        (raising(httpx.ReadError), 502, "CONTROLLER_BAD_RESPONSE"),
        (raising(httpx.RemoteProtocolError), 502, "CONTROLLER_BAD_RESPONSE"),
        (lambda r: httpx.Response(500, json={"error": {"code": "NEGATIVE_CYCLE", "message": "x", "details": {}}}),
         502, "CONTROLLER_BAD_RESPONSE"),
        (lambda r: httpx.Response(400, json={"error": {"code": "INVALID_REQUEST", "message": "x", "details": {}}}),
         502, "CONTROLLER_BAD_RESPONSE"),
    ],
    ids=["ConnectError", "ConnectTimeout", "ReadTimeout", "WriteTimeout", "PoolTimeout", "ReadError",
         "RemoteProtocolError", "HTTP500", "HTTP400"],
)
def test_network_failures_through_api(router_client, handler, status, code):
    log_dao = FakeForwardingLogDAO()
    client = router_client(
        route_client=HttpRouteClient("http://controller.test", 1.0, 2.0, transport=httpx.MockTransport(handler)),
        log_dao=log_dao,
    )
    response = client.post("/packets", json=PACKET)
    assert response.status_code == status
    body = response.json()
    assert (body["packet_id"], body["status"], body["trace"], body["error"]["code"]) == ("pkt-002", "failed", [], code)
    assert "controller.test" not in response.text and "Traceback" not in response.text
    assert [(r.status, r.error["code"]) for r in log_dao.saved] == [("failed", code)]
    assert client.get("/health").status_code == 200
