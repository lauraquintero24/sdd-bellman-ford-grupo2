"""TC-01 — Bellman-Ford devuelve la ruta de costo mínimo esperada (FR-01, FR-03, FR-05).

API (TestClient sobre create_controller_app con copia temporal de F-01) + oráculo NetworkX.
"""

import shutil
from fractions import Fraction

import networkx as nx
import pytest

from tests.fakes import FIXTURES_DIR, load_fixture_topology


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from controller.app import create_controller_app
    from controller.settings import ControllerSettings

    path = tmp_path / "F-01.json"
    shutil.copy(FIXTURES_DIR / "F-01.json", path)
    return TestClient(create_controller_app(ControllerSettings(host="127.0.0.1", port=8000, topology_file=path)))


def test_tc01_minimum_cost_route(client):
    topology = client.get("/topology")
    assert topology.status_code == 200
    body = topology.json()
    assert body["topology_version"] == 1
    assert len(body["nodes"]) == 4
    assert len(body["links"]) == 4 and all(link["active"] for link in body["links"])

    route = client.get("/route", params={"src": "A", "dst": "D", "metric": "delay"})
    assert route.status_code == 200
    assert route.json() == {
        "source": "A",
        "destination": "D",
        "metric": "delay",
        "path": ["A", "B", "D"],
        "total_cost": "2",
        "topology_version": 1,
    }


def test_tc01_networkx_oracle():
    f01 = load_fixture_topology("F-01")
    graph = nx.DiGraph()
    for link in f01.links:
        graph.add_edge(link.source, link.target, weight=Fraction(link.delay_ms))
    assert nx.bellman_ford_path_length(graph, "A", "D", weight="weight") == 2
