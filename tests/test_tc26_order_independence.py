"""TC-26 — Independencia del orden del JSON (FR-03, DEC-08).

Todas las permutaciones de ``links`` (24 de F-05, 120 de F-05b), cada una con ``nodes``
en orden original e inverso, dan E-13 y E-14.
"""

import dataclasses
import itertools
from fractions import Fraction

import pytest

from controller.engine import BellmanFordEngine
from tests.fakes import load_fixture_topology


@pytest.mark.parametrize(
    "fixture, expected, count",
    [("F-05", ("A", "B", "D"), 24), ("F-05b", ("A", "B", "E", "D"), 120)],
    ids=["E-13", "E-14"],
)
def test_all_permutations_give_the_same_route(fixture, expected, count):
    base = load_fixture_topology(fixture)
    engine = BellmanFordEngine()
    results = set()
    runs = 0
    for links in itertools.permutations(base.links):
        for nodes in (base.nodes, tuple(reversed(base.nodes))):
            topology = dataclasses.replace(base, links=links, nodes=nodes)
            result = engine.find_path(topology, "A", "D", "delay")
            results.add((result.path, result.score))
            runs += 1
    assert runs == 2 * count
    assert results == {(expected, Fraction(4) if fixture == "F-05" else Fraction(3))}
