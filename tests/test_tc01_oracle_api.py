"""Las 48 filas del oráculo de 06 §3 por HTTP (TestClient sobre create_controller_app).

Operaciones previas con POST /links/fail|restore; en las filas 404 la versión se comprueba
con GET /topology (nota de 06 §3).
"""

import pytest

from tests.oracle import IDS, ROWS, assert_cost
from tests.fakes import load_fixture_topology


@pytest.mark.parametrize("case, tc, fixture, ops, src, dst, metric, expected, version", ROWS, ids=IDS)
def test_oracle_row_api(controller_client, case, tc, fixture, ops, src, dst, metric, expected, version):
    client = controller_client(fixture)
    for action, source, target in ops:
        response = client.post(f"/links/{action}", json={"source": source, "target": target})
        assert response.status_code == 200

    response = client.get("/route", params={"src": src, "dst": dst, "metric": metric})
    if expected[0] == "ok":
        _, exp_path, exp_cost = expected
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"source", "destination", "metric", "path", "total_cost", "topology_version"}
        assert (body["source"], body["destination"], body["metric"]) == (src, dst, metric)
        assert body["path"] == exp_path and body["topology_version"] == version
        assert_cost(metric, body["total_cost"], exp_cost, load_fixture_topology(fixture), body["path"])
    else:
        assert response.status_code == 404
        assert response.json()["error"]["code"] == expected[1]
        assert client.get("/topology").json()["topology_version"] == version
