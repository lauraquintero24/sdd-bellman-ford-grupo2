"""TC-32 — Normalización de errores de red en HttpRouteClient (FR-07, FR-09, NFR-06; 02 §9).

httpx.MockTransport: ConnectError → 503; ConnectTimeout, ReadTimeout, WriteTimeout, PoolTimeout → 504;
ReadError, RemoteProtocolError, HTTP 500, HTTP 400 → 502; HTTP 200 válido → Route.
La parte con POST /packets (registro failed por HTTP) se ejecuta en W-08.
"""

import httpx
import pytest

from router.client import HttpRouteClient
from router.models import Packet
from router.service import ForwardingService
from shared.errors import ControllerBadResponseError, ControllerTimeoutError, ControllerUnavailableError
from shared.models import Route
from tests.fakes import FakeForwardingLogDAO

VALID = {"source": "A", "destination": "D", "metric": "delay", "path": ["A", "B", "D"], "total_cost": "2",
         "topology_version": 1}


def client_for(handler, connect=1.0, read=2.0):
    return HttpRouteClient("http://controller.test", connect, read, transport=httpx.MockTransport(handler))


def raising(exc_type):
    def handler(request):
        raise exc_type("fallo simulado", request=request)
    return handler


@pytest.mark.parametrize(
    "handler, expected",
    [
        (raising(httpx.ConnectError), ControllerUnavailableError),
        (raising(httpx.ConnectTimeout), ControllerTimeoutError),
        (raising(httpx.ReadTimeout), ControllerTimeoutError),
        (raising(httpx.WriteTimeout), ControllerTimeoutError),
        (raising(httpx.PoolTimeout), ControllerTimeoutError),
        (raising(httpx.ReadError), ControllerBadResponseError),
        (raising(httpx.RemoteProtocolError), ControllerBadResponseError),
        (lambda r: httpx.Response(500, json={"error": {"code": "INTERNAL_ERROR", "message": "x", "details": {}}}),
         ControllerBadResponseError),
        (lambda r: httpx.Response(400, json={"error": {"code": "INVALID_REQUEST", "message": "x", "details": {}}}),
         ControllerBadResponseError),
    ],
    ids=["ConnectError-503", "ConnectTimeout-504", "ReadTimeout-504", "WriteTimeout-504", "PoolTimeout-504",
         "ReadError-502", "RemoteProtocolError-502", "HTTP500-502", "HTTP400-502"],
)
def test_network_errors_are_normalized_and_logged(handler, expected):
    client = client_for(handler)
    with pytest.raises(expected):
        client.fetch_route("A", "D", "delay")
    log_dao = FakeForwardingLogDAO()
    with pytest.raises(expected):
        ForwardingService(client=client, log_dao=log_dao).forward(Packet("p", "A", "D", "", "delay"))
    assert [r.status for r in log_dao.saved] == ["failed"]
    assert log_dao.saved[0].error["code"] == expected.code


def test_valid_200_returns_route_and_sends_one_request():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=VALID)

    route = client_for(handler).fetch_route("A", "D", "delay")
    assert route == Route("A", "D", "delay", ("A", "B", "D"), "2", 1)
    assert len(requests) == 1
    assert requests[0].method == "GET" and requests[0].url.path == "/route"
    assert dict(requests[0].url.params) == {"src": "A", "dst": "D", "metric": "delay"}


def test_configured_timeouts_are_used():
    seen = {}

    def handler(request):
        seen.update(request.extensions["timeout"])
        return httpx.Response(200, json=VALID)

    client_for(handler, connect=0.3, read=0.5).fetch_route("A", "D", "delay")
    assert seen == {"connect": 0.3, "read": 0.5, "write": 0.5, "pool": 0.3}


def test_errors_do_not_expose_internal_addresses():
    with pytest.raises(ControllerUnavailableError) as info:
        client_for(raising(httpx.ConnectError)).fetch_route("A", "D", "delay")
    assert "controller.test" not in str(info.value.to_dict())
