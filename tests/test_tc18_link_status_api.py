"""TC-18 (parte API) — idempotencia y errores de enlace (FR-06, DEC-04)."""


def _post(client, action, source, target):
    return client.post(f"/links/{action}", json={"source": source, "target": target})


def test_tc18_api(controller_client):
    client = controller_client("F-01")
    steps = [("fail", True, 2), ("fail", False, 2), ("restore", True, 3), ("restore", False, 3)]
    for action, changed, version in steps:
        response = _post(client, action, "B", "D")
        assert response.status_code == 200
        assert (response.json()["changed"], response.json()["topology_version"]) == (changed, version)

    response = _post(client, "fail", "D", "B")
    assert response.status_code == 404 and response.json()["error"]["code"] == "LINK_NOT_FOUND"
    response = _post(client, "fail", "A", "X")
    assert response.status_code == 404 and response.json()["error"]["code"] == "NODE_NOT_FOUND"
    assert response.json()["error"]["details"]["field"] == "target"
    assert client.get("/topology").json()["topology_version"] == 3


def test_e08_route_after_repeated_fail(controller_client):
    client = controller_client("F-01")
    _post(client, "fail", "B", "D")
    _post(client, "fail", "B", "D")
    body = client.get("/route", params={"src": "A", "dst": "D", "metric": "delay"}).json()
    assert (body["path"], body["total_cost"], body["topology_version"]) == (["A", "C", "D"], "4", 2)
