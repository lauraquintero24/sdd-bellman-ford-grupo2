"""Comprobación del formato canónico de ``total_cost`` (01 §5.3, punto 4).

Función pura usada por el Router (04 §4.3) y por las pruebas. Solo biblioteca estándar.
"""

import re
from decimal import Decimal

_GRAMMAR = re.compile(
    r"0|[1-9][0-9]*(\.[0-9]*[1-9])?|0\.[0-9]*[1-9]|[1-9](\.[0-9]*[1-9])?e[+-][1-9][0-9]*",
    re.ASCII,
)
MAX_SIGNIFICANT_DIGITS = 12
FIXED_MIN_EXPONENT = -6  # 10^-6 <= r
FIXED_MAX_EXPONENT = 11  # r < 10^12


def is_canonical_cost(text: object) -> bool:
    """``True`` si ``text`` es una cadena con la gramática, el rango de notación y ≤ 12 cifras de 01 §5.3."""
    if not isinstance(text, str) or _GRAMMAR.fullmatch(text) is None:
        return False
    if text == "0":
        return True
    value = Decimal(text)
    if len(value.as_tuple().digits) > MAX_SIGNIFICANT_DIGITS:
        return False
    fixed_range = FIXED_MIN_EXPONENT <= value.adjusted() <= FIXED_MAX_EXPONENT
    return fixed_range if "e" not in text else not fixed_range
