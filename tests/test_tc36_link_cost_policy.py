"""TC-36 (parte motor) y pesos de LinkCostPolicy (FR-04, DEC-02; 01 §5.1).

Un enlace con p = 1 nunca forma parte de una ruta y nunca se evalúa ln(0).
"""

from decimal import Decimal
from fractions import Fraction

import pytest

from controller.engine import BellmanFordEngine, LinkCostPolicy
from controller.models import Link
from shared.errors import InvalidRequestError
from tests.fakes import load_fixture_topology

LINK = Link("A", "B", Decimal("1.0"), Decimal("10.0"), Decimal("0.01"), True)


@pytest.mark.parametrize(
    "metric, weight",
    [("delay", Fraction(1)), ("inverse_bandwidth", Fraction(1, 10)), ("loss", Fraction(99, 100))],
)
def test_weights_are_exact_fractions(metric, weight):
    result = LinkCostPolicy().weight(LINK, metric)
    assert result == weight and isinstance(result, Fraction)


def test_unknown_metric():
    with pytest.raises(InvalidRequestError):
        LinkCostPolicy().weight(LINK, "hops")


@pytest.mark.parametrize(
    "metric, path, score",
    [
        ("delay", ("A", "C", "D"), Fraction(4)),  # E-30
        ("inverse_bandwidth", ("A", "C", "D"), Fraction(1, 5)),  # E-31
        ("loss", ("A", "C", "D"), Fraction(1)),  # E-32: supervivencia 1 → costo "0"
    ],
)
def test_p1_link_is_never_used(metric, path, score):
    result = BellmanFordEngine().find_path(load_fixture_topology("F-13"), "A", "D", metric)
    assert (result.path, result.score) == (path, score)
