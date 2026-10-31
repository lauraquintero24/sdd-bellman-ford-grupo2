"""Oráculo independiente de tablas de forwarding (06 §3.1, C-32).

Enumera todas las rutas simples de un fixture con Fraction, aplica DEC-08 y presenta el costo con
una referencia decimal propia (120 cifras para loss). No usa el motor ni el presentador del proyecto.
"""

import json
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction

from tests.fakes import FIXTURES_DIR

METRICS = ("delay", "inverse_bandwidth", "loss")


def _arcs(doc, disabled=()):
    arcs = {}
    for link in doc["links"]:
        key = (link["source"], link["target"])
        off = key in disabled or (not doc["directed"] and key[::-1] in disabled)
        if not link["active"] or off or link["loss_probability"] == 1:
            continue
        pairs = [key] + ([] if doc["directed"] else [key[::-1]])
        for u, v in pairs:
            arcs.setdefault(u, []).append((v, link))
    return arcs


def _paths(arcs, path, target):
    if path[-1] == target:
        yield tuple(path)
        return
    for v, _ in arcs.get(path[-1], []):
        if v not in path:
            yield from _paths(arcs, path + [v], target)


def _weight(link, metric):
    if metric == "delay":
        return Fraction(link["delay_ms"])
    if metric == "inverse_bandwidth":
        return 1 / Fraction(link["bandwidth_mbps"])
    return 1 - Fraction(link["loss_probability"])


def _score(arcs, path, metric):
    links = {(u, v): link for u in arcs for v, link in arcs[u]}
    weights = [_weight(links[(u, v)], metric) for u, v in zip(path, path[1:])]
    if metric == "loss":
        result = Fraction(1)
        for w in weights:
            result *= w
        return result
    return sum(weights, Fraction(0))


def reference_cost(score: Fraction, metric: str) -> Decimal:
    """Valor exacto (delay, inverse_bandwidth) o −ln(S) a 120 cifras (loss)."""
    with localcontext() as ctx:
        ctx.prec = 120
        value = Decimal(score.numerator) / Decimal(score.denominator)
        if metric == "loss":
            return Decimal(0) if score == 1 else -value.ln()
        return value


def rounded(value: Decimal) -> str:
    """Redondeo half-even a 12 cifras en notación fija (todos los costos del oráculo están en [1e-6, 1e12))."""
    if value == 0:
        return "0"
    with localcontext() as ctx:
        ctx.prec = 12
        ctx.rounding = ROUND_HALF_EVEN
        text = format(+value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def expected_table(fixture: str, router: str, metric: str, disabled=()):
    """Lista de filas (destino, next_hop, path, score, referencia) en el orden de ``nodes``."""
    doc = json.loads((FIXTURES_DIR / f"{fixture}.json").read_text(encoding="utf-8"),
                     parse_float=Decimal, parse_int=Decimal)
    arcs = _arcs(doc, disabled)
    rows = []
    for dest in doc["nodes"]:
        if dest == router:
            continue
        candidates = list(_paths(arcs, [router], dest))
        if not candidates:
            rows.append((dest, None, None, None, None))
            continue
        sign = -1 if metric == "loss" else 1
        best = min(candidates, key=lambda p: (sign * _score(arcs, p, metric), len(p), p))
        score = _score(arcs, best, metric)
        rows.append((dest, best[1], best, score, reference_cost(score, metric)))
    return rows
