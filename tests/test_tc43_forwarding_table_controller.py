"""TC-43 — Siguiente salto y costo de las tablas de forwarding según Bellman-Ford (FR-12, FR-03; C-32).

El Controller calcula cada tabla con una sola ejecución del núcleo (find_all_paths). Se contrasta con
dos fuentes independientes: las filas T-01–T-22 de 06 §3.1 (copiadas literalmente) y el oráculo de
enumeración exhaustiva de tests/oracle_tables.py.
"""

import shutil
from decimal import Decimal, localcontext

import pytest

from controller.dao import JsonTopologyDAO
from controller.engine import BellmanFordEngine
from controller.presenter import CostPresenter
from controller.service import RoutingService
from shared.errors import InvalidRequestError, NodeNotFoundError
from tests.fakes import FIXTURES_DIR, FakeTopologyDAO, load_fixture_topology
from tests.oracle_tables import METRICS, expected_table, rounded

# 06 §3.1: (caso, fixture, enlace fallado, métrica, router) -> "destino: siguiente, costo [ruta]" ; "—" = inalcanzable
SPEC = {
    ("T-01", "F-01", None, "delay", "A"): "B:B,1,AB C:C,2,AC D:B,2,ABD",
    ("T-02", "F-01", None, "delay", "B"): "A:— C:— D:D,1,BD",
    ("T-03", "F-01", None, "delay", "C"): "A:— B:— D:D,2,CD",
    ("T-04", "F-01", None, "delay", "D"): "A:— B:— C:—",
    ("T-05", "F-01", None, "inverse_bandwidth", "A"): "B:B,0.1,AB C:C,0.01,AC D:C,0.02,ACD",
    ("T-06", "F-01", None, "loss", "A"): "B:B,0.0100503358535,AB C:C,0.0202027073175,AC D:B,0.020100671707,ABD",
    ("T-07", "F-20", None, "delay", "A"): "B:B,1,AB C:C,2,AC D:B,2,ABD",
    ("T-08", "F-20", None, "delay", "B"): "A:A,1,BA C:A,3,BAC D:D,1,BD",
    ("T-09", "F-20", None, "delay", "C"): "A:A,2,CA B:A,3,CAB D:D,2,CD",
    ("T-10", "F-20", None, "delay", "D"): "A:B,2,DBA B:B,1,DB C:C,2,DC",
    ("T-11", "F-20", None, "inverse_bandwidth", "A"): "B:B,0.1,AB C:C,0.01,AC D:C,0.02,ACD",
    ("T-12", "F-20", None, "inverse_bandwidth", "B"): "A:A,0.1,BA C:A,0.11,BAC D:D,0.1,BD",
    ("T-13", "F-20", None, "inverse_bandwidth", "C"): "A:A,0.01,CA B:A,0.11,CAB D:D,0.01,CD",
    ("T-14", "F-20", None, "inverse_bandwidth", "D"): "A:C,0.02,DCA B:B,0.1,DB C:C,0.01,DC",
    ("T-15", "F-20", None, "loss", "A"): "B:B,0.0100503358535,AB C:C,0.0202027073175,AC D:B,0.020100671707,ABD",
    ("T-16", "F-20", None, "loss", "B"): "A:A,0.0100503358535,BA C:A,0.030253043171,BAC D:D,0.0100503358535,BD",
    ("T-17", "F-20", None, "loss", "C"): "A:A,0.0202027073175,CA B:A,0.030253043171,CAB D:D,0.0202027073175,CD",
    ("T-18", "F-20", None, "loss", "D"): "A:B,0.020100671707,DBA B:B,0.0100503358535,DB C:C,0.0202027073175,DC",
    ("T-19", "F-20", ("B", "D"), "delay", "A"): "B:B,1,AB C:C,2,AC D:C,4,ACD",
    ("T-20", "F-20", ("B", "D"), "delay", "B"): "A:A,1,BA C:A,3,BAC D:A,5,BACD",
    ("T-21", "F-20", ("B", "D"), "delay", "C"): "A:A,2,CA B:A,3,CAB D:D,2,CD",
    ("T-22", "F-20", ("B", "D"), "delay", "D"): "A:C,4,DCA B:C,5,DCAB C:C,2,DC",
}


def _parse(spec):
    rows = []
    for item in spec.split():
        dest, rest = item.split(":")
        if rest == "—":
            rows.append((dest, None, None, None))
        else:
            hop, cost, path = rest.split(",")
            rows.append((dest, hop, tuple(path), cost))
    return rows


def _service(fixture, failed=None, tmp_path=None):
    if failed is None:
        dao = FakeTopologyDAO(load_fixture_topology(fixture))
    else:
        path = tmp_path / f"{fixture}.json"
        shutil.copy(FIXTURES_DIR / f"{fixture}.json", path)
        dao = JsonTopologyDAO(path)
        dao.set_link_status(*failed, False)
    return RoutingService(dao=dao, engine=BellmanFordEngine(), presenter=CostPresenter())


def _check_cost(metric, actual, expected_text, reference):
    if metric != "loss":
        assert actual == expected_text
        return
    if reference == 0:
        assert actual == "0"
        return
    with localcontext() as ctx:
        ctx.prec = 120
        assert abs(Decimal(actual) - reference) / reference <= Decimal("1e-10")


@pytest.mark.parametrize("key", list(SPEC), ids=[k[0] for k in SPEC])
def test_tables_match_06_section_3_1(tmp_path, key):
    case, fixture, failed, metric, router = key
    table = _service(fixture, failed, tmp_path).compute_forwarding_table(router, metric)
    oracle = expected_table(fixture, router, metric, disabled=(failed,) if failed else ())
    assert table.router_id == router and table.metric == metric
    assert table.topology_version == (2 if failed else 1)
    assert len(table.entries) == len(_parse(SPEC[key]))
    for entry, (dest, hop, path, cost), (o_dest, o_hop, o_path, _, o_ref) in zip(table.entries, _parse(SPEC[key]), oracle):
        assert entry.destination == dest == o_dest
        assert entry.next_hop == hop == o_hop
        assert entry.path == path == o_path
        if hop is None:
            assert (entry.total_cost, entry.status) == (None, "unreachable")
        else:
            assert entry.status == "active"
            _check_cost(metric, entry.total_cost, cost, o_ref)
            if metric != "loss":
                assert cost == rounded(o_ref)


@pytest.mark.parametrize("fixture", ["F-01", "F-20"])
@pytest.mark.parametrize("metric", METRICS)
def test_every_router_matches_bruteforce_oracle(fixture, metric):
    service = _service(fixture)
    for router in load_fixture_topology(fixture).nodes:
        table = service.compute_forwarding_table(router, metric)
        for entry, (dest, hop, path, _, ref) in zip(table.entries, expected_table(fixture, router, metric)):
            assert (entry.destination, entry.next_hop, entry.path) == (dest, hop, path)
            if hop is not None:
                assert entry.next_hop == entry.path[1] and entry.path[0] == router and entry.path[-1] == dest
                _check_cost(metric, entry.total_cost, rounded(ref), ref)


def test_one_core_run_per_table(monkeypatch):
    calls = []
    original = BellmanFordEngine.run_bellman_ford_on_weighted_graph

    def spy(self, graph, src, mode):
        calls.append(src)
        return original(self, graph, src, mode)

    monkeypatch.setattr(BellmanFordEngine, "run_bellman_ford_on_weighted_graph", spy)
    _service("F-20").compute_forwarding_table("B", "delay")
    assert calls == ["B"]


def test_service_errors():
    service = _service("F-20")
    with pytest.raises(InvalidRequestError):
        service.compute_forwarding_table("A", "hops")
    with pytest.raises(NodeNotFoundError) as info:
        service.compute_forwarding_table("X", "delay")
    assert info.value.details == {"field": "router_id", "value": "X"}


def test_api_matches_04_example(controller_client):
    response = controller_client("F-20").get("/forwarding-table", params={"router_id": "A", "metric": "delay"})
    assert response.status_code == 200
    assert response.json() == {"router_id": "A", "metric": "delay", "topology_version": 1, "entries": [
        {"destination": "B", "next_hop": "B", "path": ["A", "B"], "total_cost": "1", "status": "active"},
        {"destination": "C", "next_hop": "C", "path": ["A", "C"], "total_cost": "2", "status": "active"},
        {"destination": "D", "next_hop": "B", "path": ["A", "B", "D"], "total_cost": "2", "status": "active"}]}


def test_api_unreachable_row_has_no_next_hop(controller_client):
    body = controller_client("F-01").get("/forwarding-table", params={"router_id": "B", "metric": "delay"}).json()
    assert body["entries"][0] == {"destination": "A", "next_hop": None, "path": None, "total_cost": None,
                                  "status": "unreachable"}


@pytest.mark.parametrize(
    "params, status, code",
    [({"router_id": "A"}, 400, "INVALID_REQUEST"), ({"metric": "delay"}, 400, "INVALID_REQUEST"),
     ({"router_id": "A", "metric": "hops"}, 400, "INVALID_REQUEST"),
     ({"router_id": " A", "metric": "delay"}, 400, "INVALID_REQUEST"),
     ({"router_id": "X", "metric": "delay"}, 404, "NODE_NOT_FOUND")],
)
def test_api_errors(controller_client, params, status, code):
    response = controller_client("F-20").get("/forwarding-table", params=params)
    assert response.status_code == status and response.json()["error"]["code"] == code


def test_topology_version_endpoint_and_table_after_fail(controller_client):
    client = controller_client("F-20")
    assert client.get("/topology/version").json() == {"topology_version": 1}
    client.post("/links/fail", json={"source": "B", "target": "D"})
    assert client.get("/topology/version").json() == {"topology_version": 2}
    body = client.get("/forwarding-table", params={"router_id": "A", "metric": "delay"}).json()
    assert body["topology_version"] == 2
    assert body["entries"][2] == {"destination": "D", "next_hop": "C", "path": ["A", "C", "D"], "total_cost": "4",
                                  "status": "active"}
