"""TC-31 (parte cliente) — validación de la respuesta del Controller (04 §4.3).

Cada respuesta no conforme → ControllerBadResponseError (502); el 404 con sobre válido se
propaga con details.field renombrado. La parte HTTP del Router (400 sin registro) va en W-08.
"""

import httpx
import pytest

from router.client import HttpRouteClient
from shared.errors import ControllerBadResponseError, NodeNotFoundError, RouteUnreachableError

VALID = {"source": "A", "destination": "D", "metric": "delay", "path": ["A", "B", "D"], "total_cost": "2",
         "topology_version": 1}


def fetch(status, body=None, content=None, src="A", dst="D", metric="delay"):
    def handler(request):
        if content is not None:
            return httpx.Response(status, content=content)
        return httpx.Response(status, json=body)

    client = HttpRouteClient("http://controller.test", 1.0, 2.0, transport=httpx.MockTransport(handler))
    return client.fetch_route(src, dst, metric)


DEFECTS = {
    "sin-json": dict(content=b"<html>no</html>"),
    "nan-literal": dict(content=b'{"source":"A","destination":"D","metric":"delay","path":["A","D"],"total_cost":NaN,"topology_version":1}'),
    "lista": dict(body=[VALID]),
    "path-vacio": dict(body={**VALID, "path": []}),
    "path-X-D": dict(body={**VALID, "path": ["X", "D"]}),
    "path-A-B-A-D": dict(body={**VALID, "path": ["A", "B", "A", "D"]}),
    "path-sin-destino": dict(body={**VALID, "path": ["A", "B"]}),
    "path-nodo-vacio": dict(body={**VALID, "path": ["A", "", "D"]}),
    "path-no-texto": dict(body={**VALID, "path": ["A", 1, "D"]}),
    "path-no-lista": dict(body={**VALID, "path": "ABD"}),
    "cost-numero-2": dict(body={**VALID, "total_cost": 2}),
    "cost-NaN": dict(body={**VALID, "total_cost": "NaN"}),
    "cost--0": dict(body={**VALID, "total_cost": "-0"}),
    "cost--1": dict(body={**VALID, "total_cost": "-1"}),
    "cost-vacio": dict(body={**VALID, "total_cost": ""}),
    "cost-2.0": dict(body={**VALID, "total_cost": "2.0"}),
    "cost-1e-07": dict(body={**VALID, "total_cost": "1e-07"}),
    "cost-true": dict(body={**VALID, "total_cost": True}),
    "version-0": dict(body={**VALID, "topology_version": 0}),
    "version-true": dict(body={**VALID, "topology_version": True}),
    "version-texto": dict(body={**VALID, "topology_version": "1"}),
    "metric-distinta": dict(body={**VALID, "metric": "loss"}),
    "source-X": dict(body={**VALID, "source": "X"}),
    "campo-extra": dict(body={**VALID, "extra": 1}),
    "falta-campo": dict(body={k: v for k, v in VALID.items() if k != "topology_version"}),
    "404-codigo-desconocido": dict(status=404, body={"error": {"code": "LINK_NOT_FOUND", "message": "x", "details": {}}}),
    "404-sin-sobre": dict(status=404, body={"detail": "Not Found"}),
    "404-sobre-incompleto": dict(status=404, body={"error": {"code": "NODE_NOT_FOUND", "message": "x"}}),
    "201": dict(status=201, body=VALID),
    "503": dict(status=503, body={"error": {"code": "X", "message": "x", "details": {}}}),
}


@pytest.mark.parametrize("kwargs", list(DEFECTS.values()), ids=list(DEFECTS))
def test_non_conforming_response_is_bad_response(kwargs):
    with pytest.raises(ControllerBadResponseError) as info:
        fetch(kwargs.get("status", 200), **{k: v for k, v in kwargs.items() if k != "status"})
    assert info.value.code == "CONTROLLER_BAD_RESPONSE"


def test_same_node_route_must_be_trivial():
    trivial = {**VALID, "destination": "A", "path": ["A"], "total_cost": "0"}
    assert fetch(200, trivial, dst="A").path == ("A",)
    with pytest.raises(ControllerBadResponseError):
        fetch(200, {**trivial, "total_cost": "1"}, dst="A")


def test_404_node_not_found_is_propagated_with_renamed_field():
    body = {"error": {"code": "NODE_NOT_FOUND", "message": "El nodo X no existe en la topología.",
                      "details": {"field": "src", "value": "X"}}}
    with pytest.raises(NodeNotFoundError) as info:
        fetch(404, body, src="X")
    assert info.value.message == "El nodo X no existe en la topología."
    assert info.value.details == {"field": "source", "value": "X"}


def test_404_route_unreachable_is_propagated():
    details = {"source": "A", "destination": "D", "metric": "delay"}
    body = {"error": {"code": "ROUTE_UNREACHABLE", "message": "No existe una ruta utilizable de A a D.", "details": details}}
    with pytest.raises(RouteUnreachableError) as info:
        fetch(404, body)
    assert info.value.details == details
