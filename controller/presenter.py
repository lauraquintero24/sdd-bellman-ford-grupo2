"""Presentación de ``total_cost`` (02 §6.3; 01 §5.3; DEC-09).

Solo presenta: la selección de rutas nunca usa esta cadena. No se usa ``float``.
"""

from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction

from shared.errors import InvalidRequestError

SIGNIFICANT_DIGITS = 12
SERIES_TERMS = 25
SERIES_LIMIT = Fraction(1, 4)


class CostPresenter:
    def format_cost(self, score: Fraction, metric: str) -> str:
        if metric not in ("delay", "inverse_bandwidth", "loss"):
            raise InvalidRequestError(f"La métrica {metric} no está admitida.", {"fields": ["metric"]})
        with localcontext() as ctx:
            ctx.prec = 60
            ctx.rounding = ROUND_HALF_EVEN
            if metric == "loss":
                if score == 1:
                    return "0"
                q = 1 - score
                cost = _loss_series(q) if 0 < q <= SERIES_LIMIT else _loss_ln(score)
                return _format_exact(Fraction(cost))
            return _format_exact(score)


def _loss_series(q: Fraction) -> Decimal:
    """``−ln(1 − q) = Σ q^j / j`` sin formar ``1 − S`` redondeado (evita la cancelación con p = 1e-60)."""
    q_dec = Decimal(q.numerator) / Decimal(q.denominator)
    total = Decimal(0)
    power = Decimal(1)
    for j in range(1, SERIES_TERMS + 1):
        power *= q_dec
        total += power / j
    return total


def _loss_ln(survival: Fraction) -> Decimal:
    return -(Decimal(survival.numerator) / Decimal(survival.denominator)).ln()


def _format_exact(value: Fraction) -> str:
    """Redondeo exacto half-even a 12 cifras significativas y formato canónico de 01 §5.3."""
    if value == 0:
        return "0"
    if value < 0:
        raise ValueError("costo negativo: invariante de pesos no negativos violado")
    exponent = len(str(value.numerator)) - len(str(value.denominator))
    if Fraction(10) ** exponent > value:
        exponent -= 1
    elif Fraction(10) ** (exponent + 1) <= value:
        exponent += 1
    mantissa = round(value / Fraction(10) ** (exponent - (SIGNIFICANT_DIGITS - 1)))
    if mantissa == 10**SIGNIFICANT_DIGITS:
        mantissa //= 10
        exponent += 1
    return _canonical(str(mantissa).rstrip("0"), exponent)


def _canonical(digits: str, exponent: int) -> str:
    """``digits`` sin ceros finales; valor = d1.d2d3… × 10^exponent."""
    if -6 <= exponent <= 11:
        if exponent < 0:
            return "0." + "0" * (-exponent - 1) + digits
        integer = digits[: exponent + 1].ljust(exponent + 1, "0")
        fraction = digits[exponent + 1 :]
        return integer + ("." + fraction if fraction else "")
    mantissa = digits[0] + ("." + digits[1:] if len(digits) > 1 else "")
    return f"{mantissa}e{'+' if exponent >= 0 else '-'}{abs(exponent)}"
