"""TC-11 — Ciclo negativo alcanzable y no alcanzable (FR-03, DEC-07; 02 §6.2).

Parte del núcleo y de find_path. El subcaso API (500 NEGATIVE_CYCLE) se prueba en W-05.
"""

from decimal import Decimal
from fractions import Fraction

import networkx as nx
import pytest

from controller.engine import BellmanFordEngine, RouteLabel
from controller.models import Link, Topology
from shared.errors import NegativeCycleError

G1 = [("A", "B", 1), ("B", "C", -3), ("C", "A", 1), ("C", "D", 1)]
G2 = [("A", "D", 1), ("X", "Y", -2), ("Y", "X", 1)]
G3 = [("A", "B", 2), ("B", "A", 1), ("A", "D", Fraction(1, 2))]


def _digraph(arcs):
    graph = nx.DiGraph()
    for u, v, w in arcs:
        graph.add_edge(u, v, weight=Fraction(w))
    return graph


def test_g1_reachable_negative_cycle_is_detected():
    graph = _digraph(G1)
    with pytest.raises(NegativeCycleError) as info:
        BellmanFordEngine().run_bellman_ford_on_weighted_graph(graph, "A", "additive")
    assert info.value.code == "NEGATIVE_CYCLE"
    with pytest.raises(nx.NetworkXUnbounded):  # oráculo independiente
        nx.bellman_ford_predecessor_and_distance(graph, "A")


def test_g2_unreachable_negative_cycle_is_not_detected():
    graph = _digraph(G2)
    labels = BellmanFordEngine().run_bellman_ford_on_weighted_graph(graph, "A", "additive")
    assert labels["D"] == RouteLabel(score=Fraction(1), hops=1, path=("A", "D"))
    assert "X" not in labels and "Y" not in labels
    nx.bellman_ford_predecessor_and_distance(graph, "A")  # el oráculo tampoco lo detecta


def test_g3_gain_cycle_in_product_mode_is_detected():
    with pytest.raises(NegativeCycleError):
        BellmanFordEngine().run_bellman_ford_on_weighted_graph(_digraph(G3), "A", "product")


def test_find_path_detects_negative_cycle_in_artificial_topology():
    # El Model no valida (02 §4): se puede construir G1 como topología con delay_ms negativo.
    links = tuple(Link(u, v, Decimal(w), Decimal(10), Decimal(0), True) for u, v, w in G1)
    topology = Topology(directed=True, version=1, nodes=("A", "B", "C", "D"), links=links)
    with pytest.raises(NegativeCycleError):
        BellmanFordEngine().find_path(topology, "A", "D", "delay")


def test_find_path_uses_the_same_core(monkeypatch):
    from tests.fakes import load_fixture_topology

    calls = []
    original = BellmanFordEngine.run_bellman_ford_on_weighted_graph

    def spy(self, graph, src, mode):
        calls.append((src, mode))
        return original(self, graph, src, mode)

    monkeypatch.setattr(BellmanFordEngine, "run_bellman_ford_on_weighted_graph", spy)
    engine = BellmanFordEngine()
    topology = load_fixture_topology("F-01")
    engine.find_path(topology, "A", "D", "delay")
    engine.find_path(topology, "A", "D", "loss")
    engine.find_path(topology, "A", "A", "delay")  # caso trivial: no invoca el núcleo
    assert calls == [("A", "additive"), ("A", "product")]
