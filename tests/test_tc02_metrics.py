"""TC-02 — Se admiten las métricas de retardo, ancho de banda inverso y pérdida (FR-04).

Unitario (RoutingService con FakeTopologyDAO) + API. E-01, E-02, E-03; el costo de loss
se compara con −2·ln(0.99) calculado a 100 cifras (error relativo ≤ 1e-10).
"""

import shutil
from decimal import Decimal, localcontext

import pytest

from controller.engine import BellmanFordEngine
from controller.presenter import CostPresenter
from controller.service import RoutingService
from tests.fakes import FIXTURES_DIR, FakeTopologyDAO, load_fixture_topology

EXPECTED = {
    "delay": (["A", "B", "D"], "2"),
    "inverse_bandwidth": (["A", "C", "D"], "0.02"),
    "loss": (["A", "B", "D"], "0.020100671707"),
}


def _check_loss(total_cost: str) -> None:
    with localcontext() as ctx:
        ctx.prec = 100
        reference = -2 * Decimal("0.99").ln()
        assert abs(Decimal(total_cost) - reference) / reference <= Decimal("1e-10")


@pytest.mark.parametrize("metric", list(EXPECTED))
def test_tc02_service_three_metrics(metric):
    service = RoutingService(
        dao=FakeTopologyDAO(load_fixture_topology("F-01")), engine=BellmanFordEngine(), presenter=CostPresenter()
    )
    route = service.compute_route("A", "D", metric)
    path, cost = EXPECTED[metric]
    assert list(route.path) == path and route.topology_version == 1
    if metric == "loss":
        _check_loss(route.total_cost)
    else:
        assert route.total_cost == cost


@pytest.mark.parametrize("metric", list(EXPECTED))
def test_tc02_api_three_metrics(tmp_path, metric):
    from fastapi.testclient import TestClient

    from controller.app import create_controller_app
    from controller.settings import ControllerSettings

    topology = tmp_path / "F-01.json"
    shutil.copy(FIXTURES_DIR / "F-01.json", topology)
    client = TestClient(create_controller_app(ControllerSettings(host="127.0.0.1", port=8000, topology_file=topology)))
    response = client.get("/route", params={"src": "A", "dst": "D", "metric": metric})
    assert response.status_code == 200
    body = response.json()
    path, cost = EXPECTED[metric]
    assert body["path"] == path and body["metric"] == metric and body["topology_version"] == 1
    if metric == "loss":
        _check_loss(body["total_cost"])
    else:
        assert body["total_cost"] == cost
