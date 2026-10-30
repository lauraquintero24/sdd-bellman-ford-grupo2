"""TC-19 a TC-23, TC-27 a TC-30 (parte motor): selección exacta y desempate DEC-08.

Cada fila es una del oráculo de 06 §3 sin operaciones previas, con métrica delay; se
compara la ruta y la puntuación exacta (Fraction) y, como oráculo independiente, el costo
con ``nx.bellman_ford_path_length`` (pesos Fraction). La presentación de total_cost se
prueba con el presentador (W-04.2/W-04A).
"""

from decimal import Decimal
from fractions import Fraction

import networkx as nx
import pytest

from controller.engine import BellmanFordEngine
from shared.errors import RouteUnreachableError
from tests.fakes import load_fixture_topology

ROWS = [
    ("E-01", "F-01", "A", "D", ("A", "B", "D"), Fraction(2)),
    ("E-09", "F-02", "A", "D", ("A", "B", "D"), Fraction(4)),
    ("E-10", "F-03", "A", "D", ("A", "B", "D"), Fraction(2)),
    ("E-11", "F-04", "A", "D", ("A", "D"), Fraction(2)),
    ("E-12", "F-07", "A", "D", ("A", "D"), Fraction(1)),
    ("E-13", "F-05", "A", "D", ("A", "B", "D"), Fraction(4)),
    ("E-14", "F-05b", "A", "D", ("A", "B", "E", "D"), Fraction(3)),
    ("E-15", "F-15", "A", "D", ("A", "B", "D"), Fraction(2)),
    ("E-19", "F-08", "A", "D", ("A", "D"), Fraction(4, 5)),
    ("E-20", "F-08b", "A", "D", ("A", "B", "D"), Fraction(4, 5)),
    ("E-47", "F-08c", "A", "D", ("A", "D"), Fraction(4, 5)),
    ("E-48", "F-08d", "A", "D", ("A", "B", "D"), Fraction(4, 5)),
    ("E-21", "F-09", "A", "A", ("A",), Fraction(0)),
    ("E-25", "F-10", "C", "C", ("C",), Fraction(0)),
    ("E-26", "F-11", "D", "A", ("D", "B", "A"), Fraction(2)),
]

UNREACHABLE = [("E-23", "F-10", "A", "C"), ("E-24", "F-10", "A", "E"), ("E-29", "F-12", "D", "A")]


def _oracle_graph(topology):
    graph = nx.DiGraph() if topology.directed else nx.Graph()
    graph.add_nodes_from(topology.nodes)
    for link in topology.links:
        if link.active and link.loss_probability != 1:
            graph.add_edge(link.source, link.target, weight=Fraction(link.delay_ms))
    return graph


@pytest.mark.parametrize("case, fixture, src, dst, path, score", ROWS, ids=[r[0] for r in ROWS])
def test_delay_selection_matches_oracle(case, fixture, src, dst, path, score):
    topology = load_fixture_topology(fixture)
    result = BellmanFordEngine().find_path(topology, src, dst, "delay")
    assert result.path == path
    assert result.score == score and isinstance(result.score, Fraction)
    assert nx.bellman_ford_path_length(_oracle_graph(topology), src, dst) == score


@pytest.mark.parametrize("case, fixture, src, dst", UNREACHABLE, ids=[r[0] for r in UNREACHABLE])
def test_unreachable(case, fixture, src, dst):
    with pytest.raises(RouteUnreachableError) as info:
        BellmanFordEngine().find_path(load_fixture_topology(fixture), src, dst, "delay")
    assert info.value.details == {"source": src, "destination": dst, "metric": "delay"}


def test_tc27_exact_decimal_tie():
    assert Fraction(Decimal("0.1")) + Fraction(Decimal("0.7")) == Fraction(4, 5)
    assert 0.1 + 0.7 != 0.8  # por eso F-08 distingue la aritmética exacta de float


def test_tc21_zero_cost_cycle_not_in_path():
    result = BellmanFordEngine().find_path(load_fixture_topology("F-07"), "A", "D", "delay")
    assert len(set(result.path)) == len(result.path)
