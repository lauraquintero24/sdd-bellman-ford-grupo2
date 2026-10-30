"""TC-03 — Los enlaces fallados se excluyen de las rutas siguientes (FR-06).
TC-04 — Restaurar un enlace actualiza las rutas siguientes (FR-06, DEC-04).

TC-04 continúa el estado de TC-03 dentro de la misma prueba (06 §4).
"""

BD = {"source": "B", "target": "D"}
ROUTE = {"src": "A", "dst": "D", "metric": "delay"}


def test_tc03_then_tc04(controller_client):
    client = controller_client("F-01")

    # TC-03
    failed = client.post("/links/fail", json=BD)
    assert failed.status_code == 200
    assert failed.json() == {"source": "B", "target": "D", "active": False, "changed": True, "topology_version": 2}
    route = client.get("/route", params=ROUTE)
    assert route.status_code == 200
    assert route.json() == {
        "source": "A", "destination": "D", "metric": "delay",
        "path": ["A", "C", "D"], "total_cost": "4", "topology_version": 2,
    }
    path = route.json()["path"]
    assert ("B", "D") not in zip(path, path[1:])

    # TC-04
    restored = client.post("/links/restore", json=BD)
    assert restored.status_code == 200
    assert restored.json() == {"source": "B", "target": "D", "active": True, "changed": True, "topology_version": 3}
    route = client.get("/route", params=ROUTE)
    assert route.status_code == 200
    assert route.json()["path"] == ["A", "B", "D"]
    assert route.json()["total_cost"] == "2" and route.json()["topology_version"] == 3
    again = client.post("/links/restore", json=BD)
    assert again.status_code == 200
    assert again.json() == {"source": "B", "target": "D", "active": True, "changed": False, "topology_version": 3}
