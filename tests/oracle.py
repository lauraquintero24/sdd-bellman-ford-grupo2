"""Oráculo de 48 resultados esperados (06 §3), compartido por las pruebas de servicio y de API.

Cada fila: (caso, TC, fixture, operaciones previas, src, dst, metric, esperado, versión).
``esperado`` es ("ok", path, total_cost) o ("error", error.code).
Operaciones: ("fail" | "restore", source, target), aplicadas en orden sobre el fixture recién cargado.
"""

from decimal import Decimal, localcontext
from fractions import Fraction

FAIL_BD = ("fail", "B", "D")
FAIL_CD = ("fail", "C", "D")
ABD, ACD, AD = ["A", "B", "D"], ["A", "C", "D"], ["A", "D"]


def ok(path, cost):
    return ("ok", path, cost)


def error(code):
    return ("error", code)


ROWS = [
    ("E-01", "TC-01", "F-01", [], "A", "D", "delay", ok(ABD, "2"), 1),
    ("E-02", "TC-02", "F-01", [], "A", "D", "inverse_bandwidth", ok(ACD, "0.02"), 1),
    ("E-03", "TC-02", "F-01", [], "A", "D", "loss", ok(ABD, "0.020100671707"), 1),
    ("E-04", "TC-03", "F-01", [FAIL_BD], "A", "D", "delay", ok(ACD, "4"), 2),
    ("E-05", "TC-04", "F-01", [FAIL_BD, ("restore", "B", "D")], "A", "D", "delay", ok(ABD, "2"), 3),
    ("E-06", "TC-17", "F-01", [FAIL_BD, FAIL_CD], "A", "D", "delay", error("ROUTE_UNREACHABLE"), 3),
    ("E-07", "TC-17", "F-01", [FAIL_BD, FAIL_CD, ("restore", "C", "D")], "A", "D", "delay", ok(ACD, "4"), 4),
    ("E-08", "TC-18", "F-01", [FAIL_BD, FAIL_BD], "A", "D", "delay", ok(ACD, "4"), 2),
    ("E-09", "TC-19", "F-02", [], "A", "D", "delay", ok(ABD, "4"), 1),
    ("E-10", "TC-20", "F-03", [], "A", "D", "delay", ok(ABD, "2"), 1),
    ("E-11", "TC-21", "F-04", [], "A", "D", "delay", ok(AD, "2"), 1),
    ("E-12", "TC-21", "F-07", [], "A", "D", "delay", ok(AD, "1"), 1),
    ("E-13", "TC-22", "F-05", [], "A", "D", "delay", ok(ABD, "4"), 1),
    ("E-14", "TC-22", "F-05b", [], "A", "D", "delay", ok(["A", "B", "E", "D"], "3"), 1),
    ("E-15", "TC-23", "F-15", [], "A", "D", "delay", ok(ABD, "2"), 1),
    ("E-16", "TC-23", "F-15", [], "A", "D", "loss", ok(AD, "0"), 1),
    ("E-17", "TC-25", "F-06", [("fail", "A", "B")], "A", "B", "delay", error("ROUTE_UNREACHABLE"), 2),
    ("E-18", "TC-25", "F-06", [("fail", "A", "B")], "B", "A", "delay", ok(["B", "A"], "1"), 2),
    ("E-19", "TC-27", "F-08", [], "A", "D", "delay", ok(AD, "0.8"), 1),
    ("E-20", "TC-27", "F-08b", [], "A", "D", "delay", ok(ABD, "0.8"), 1),
    ("E-21", "TC-28", "F-09", [], "A", "A", "delay", ok(["A"], "0"), 1),
    ("E-22", "TC-28", "F-09", [], "A", "B", "delay", error("NODE_NOT_FOUND"), 1),
    ("E-23", "TC-29", "F-10", [], "A", "C", "delay", error("ROUTE_UNREACHABLE"), 1),
    ("E-24", "TC-29", "F-10", [], "A", "E", "delay", error("ROUTE_UNREACHABLE"), 1),
    ("E-25", "TC-29", "F-10", [], "C", "C", "delay", ok(["C"], "0"), 1),
    ("E-26", "TC-30", "F-11", [], "D", "A", "delay", ok(["D", "B", "A"], "2"), 1),
    ("E-27", "TC-30", "F-11", [("fail", "A", "B")], "D", "A", "delay", error("ROUTE_UNREACHABLE"), 2),
    ("E-28", "TC-30", "F-11", [("fail", "A", "B"), ("fail", "B", "A")], "A", "D", "delay", error("ROUTE_UNREACHABLE"), 2),
    ("E-29", "TC-30", "F-12", [], "D", "A", "delay", error("ROUTE_UNREACHABLE"), 1),
    ("E-30", "TC-36", "F-13", [], "A", "D", "delay", ok(ACD, "4"), 1),
    ("E-31", "TC-36", "F-13", [], "A", "D", "inverse_bandwidth", ok(ACD, "0.2"), 1),
    ("E-32", "TC-36", "F-13", [], "A", "D", "loss", ok(ACD, "0"), 1),
    ("E-33", "TC-36", "F-13", [("restore", "A", "B")], "A", "D", "delay", ok(ACD, "4"), 1),
    ("E-34", "TC-37", "F-14a", [], "A", "D", "delay", ok(AD, "0.8"), 1),
    ("E-35", "TC-37", "F-14a", [], "A", "D", "inverse_bandwidth", ok(AD, "0.2"), 1),
    ("E-36", "TC-37", "F-14a", [], "A", "D", "loss", ok(AD, "0.210721031316"), 1),
    ("E-37", "TC-37", "F-14a-near", [], "A", "D", "loss", ok(ABD, "0.210721031316"), 1),
    ("E-38", "TC-37", "F-14a-near", [], "A", "D", "delay", ok(AD, "0.8"), 1),
    ("E-39", "TC-37", "F-14b", [], "A", "D", "delay", ok(ABD, "2"), 1),
    ("E-40", "TC-37", "F-14b", [], "A", "D", "inverse_bandwidth", ok(ABD, "0.2"), 1),
    ("E-41", "TC-37", "F-14b", [], "A", "D", "loss", ok(ABD, "0.210721031316"), 1),
    ("E-42", "TC-38", "F-18", [], "A", "D", "loss", ok(AD, "1e-60"), 1),
    ("E-43", "TC-38", "F-16", [], "A", "D", "loss", ok(AD, "27.6310211159"), 1),
    ("E-44", "TC-38", "F-18b", [], "A", "D", "loss", ok(AD, "0"), 1),
    ("E-45", "TC-39", "F-17", [], "A", "D", "loss", ok(AD, "0.287682072452"), 1),
    ("E-46", "TC-39", "F-17b", [], "A", "D", "loss", ok(AD, "0.287682072453"), 1),
    ("E-47", "TC-27", "F-08c", [], "A", "D", "delay", ok(AD, "0.8"), 1),
    ("E-48", "TC-27", "F-08d", [], "A", "D", "delay", ok(ABD, "0.8"), 1),
]

IDS = [f"{row[0]}-{row[1]}" for row in ROWS]


def loss_reference(topology, path) -> Decimal:
    """−ln(Π(1 − p)) sobre ``path`` con Decimal a 120 cifras (referencia independiente)."""
    survival = Fraction(1)
    for u, v in zip(path, path[1:]):
        survival *= 1 - Fraction(topology.find_link(u, v).loss_probability)
    with localcontext() as ctx:
        ctx.prec = 120
        if survival == 1:
            return Decimal(0)
        return -(Decimal(survival.numerator) / Decimal(survival.denominator)).ln()


def assert_cost(metric, actual: str, expected: str, topology, path) -> None:
    """Comparación de 06 §1: literal en delay/inverse_bandwidth; tolerancia 1e-10 en loss."""
    if metric != "loss":
        assert actual == expected
        return
    ref = loss_reference(topology, path)
    if ref == 0:
        assert actual == "0"
        return
    with localcontext() as ctx:
        ctx.prec = 120
        assert abs(Decimal(actual) - ref) / ref <= Decimal("1e-10"), (actual, expected)
