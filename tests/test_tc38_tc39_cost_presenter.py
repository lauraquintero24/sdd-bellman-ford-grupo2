"""TC-38 y TC-39 (parte presentador) — formato canónico, precisión de loss y separación
entre selección y presentación (FR-04, DEC-09; 01 §5.3; 02 §6.3).

Referencia de loss: −ln(S) con Decimal a 120 cifras (método independiente de la serie).
"""

import ast
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import pytest

import controller.presenter as presenter_module
from controller.engine import BellmanFordEngine
from controller.presenter import CostPresenter
from controller.service import RoutingService
from tests.fakes import FakeTopologyDAO, SpyCostPresenter, load_fixture_topology

ROOT = Path(__file__).resolve().parent.parent

EXACT = [
    (Fraction(0), "0"),
    (Fraction(2), "2"),
    (Fraction(20), "20"),
    (Fraction(4), "4"),
    (Fraction(1, 50), "0.02"),
    (Fraction(4, 5), "0.8"),
    (Fraction(1, 5), "0.2"),
    (Fraction(1, 10**6), "0.000001"),
    (Fraction(1, 10**7), "1e-7"),
    (Fraction(1, 10**60), "1e-60"),
    (Fraction(15 * 10**12), "1.5e+13"),
    (Fraction(10**12), "1e+12"),
    (Fraction(10**12 - 1), "999999999999"),
    (Fraction(1, 3), "0.333333333333"),
    (Fraction(2, 3), "0.666666666667"),
    (Fraction(2000000000001, 10**12), "2"),  # 2.000000000001 → 12 cifras: 2.00000000000
    (Fraction(1234567890125, 10), "123456789012"),  # empate exacto → par (half-even)
    (Fraction(1234567890135, 10), "123456789014"),  # empate exacto → par (half-even)
    (Fraction(19999999999995, 10), "2e+12"),  # 1999999999999.5 → 2.00000000000e12
    (Fraction(9999999999995, 10**19), "0.000001"),  # redondea a 1e-6: notación fija
    (Fraction(99, 1), "99"),
    (Fraction(10**1000), "1e+1000"),
]


@pytest.mark.parametrize("score, expected", EXACT, ids=[e for _, e in EXACT])
@pytest.mark.parametrize("metric", ["delay", "inverse_bandwidth"])
def test_exact_rounding_and_canonical_format(score, expected, metric):
    assert CostPresenter().format_cost(score, metric) == expected


def _reference(survival: Fraction) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 120
        if survival == 1:
            return Decimal(0)
        return -(Decimal(survival.numerator) / Decimal(survival.denominator)).ln()


LOSS = [
    ("E-03", Fraction(99, 100) ** 2, "0.020100671707"),
    ("E-36", Fraction(81, 100), "0.210721031316"),
    ("E-42", 1 - Fraction(1, 10**60), "1e-60"),
    ("E-43", Fraction(1, 10**12), "27.6310211159"),
    ("E-44", Fraction(1), "0"),
    ("E-45", Fraction(3, 4), "0.287682072452"),
    ("E-46", 1 - Fraction(250000000001, 10**12), "0.287682072453"),
]


@pytest.mark.parametrize("case, survival, oracle", LOSS, ids=[c[0] for c in LOSS])
def test_loss_relative_error_within_1e_10(case, survival, oracle):
    out = CostPresenter().format_cost(survival, "loss")
    ref = _reference(survival)
    if ref == 0:
        assert out == "0"
        return
    with localcontext() as ctx:
        ctx.prec = 120
        assert abs(Decimal(out) - ref) / ref <= Decimal("1e-10")
        assert abs(Decimal(oracle) - ref) / ref <= Decimal("1e-10")  # coherencia del oráculo de 06 §3
    assert out != "0"  # un costo positivo nunca se publica como "0"


@pytest.mark.parametrize(
    "fixture, branch, expected",
    [("F-17", "_loss_series", "0.287682072452"), ("F-17b", "_loss_ln", "0.287682072453")],
    ids=["E-45-serie", "E-46-ln"],
)
def test_tc39_series_boundary_branches(monkeypatch, fixture, branch, expected):
    used = []
    for name in ("_loss_series", "_loss_ln"):
        original = getattr(presenter_module, name)
        monkeypatch.setattr(presenter_module, name, lambda x, _o=original, _n=name: used.append(_n) or _o(x))
    score = BellmanFordEngine().find_path(load_fixture_topology(fixture), "A", "D", "loss").score
    out = CostPresenter().format_cost(score, "loss")
    assert used == [branch]
    with localcontext() as ctx:
        ctx.prec = 120
        ref = _reference(score)
        assert abs(Decimal(out) - ref) / ref <= Decimal("1e-10")
    assert out == expected


def test_tc39_spy_presenter_does_not_change_selection():
    spy = SpyCostPresenter(result="999")
    service = RoutingService(dao=FakeTopologyDAO(load_fixture_topology("F-01")), engine=BellmanFordEngine(), presenter=spy)
    route = service.compute_route("A", "D", "loss")
    assert route.path == ("A", "B", "D") and route.total_cost == "999"
    assert spy.calls == [(Fraction(99, 100) ** 2, "loss")]


@pytest.mark.parametrize("module", ["controller/engine.py", "controller/presenter.py"])
def test_tc39_no_float_in_engine_or_presenter(module):
    tree = ast.parse((ROOT / module).read_text(encoding="utf-8"))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    floats = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)]
    assert "float" not in names and not floats
    assert "isclose" not in ast.dump(tree) and "fsum" not in ast.dump(tree)


def test_unknown_metric_is_rejected():
    from shared.errors import InvalidRequestError

    with pytest.raises(InvalidRequestError):
        CostPresenter().format_cost(Fraction(1), "hops")


def test_tc39_real_outputs_are_canonical():
    """Usa shared.cost_format.is_canonical_cost (Estudiante B, W-02B)."""
    from shared.cost_format import is_canonical_cost

    outputs = [CostPresenter().format_cost(s, "delay") for s, _ in EXACT]
    outputs += [CostPresenter().format_cost(s, "loss") for _, s, _ in LOSS]
    assert all(is_canonical_cost(o) for o in outputs), [o for o in outputs if not is_canonical_cost(o)]
