"""TC-31 (parte formato) — is_canonical_cost con ejemplos válidos e inválidos (01 §5.3; 04 §4.3)."""

import pytest

from shared.cost_format import is_canonical_cost

VALID = [
    "0", "2", "4", "20", "99", "0.02", "0.2", "0.8", "0.000001", "27.6310211159", "0.020100671707",
    "0.210721031316", "0.287682072452", "999999999999", "123456789012", "1e-7", "1e-60", "1.5e+13",
    "1e+12", "9.99999999999e-7", "1e+1000", "1.23456789012e-100",
]
INVALID = [
    "", "NaN", "-0", "-1", "2.0", "1e-07", "02", "00", "0.0", ".5", "5.", "+2", " 2", "2 ", "2\n",
    "1E-7", "1e7", "1e+07", "1.0e-7", "10e-7", "1e-0", "1e+0", "inf", "Infinity", "٢",
    "1e+5",              # < 10^12: debe ir en notación fija
    "0.0000001",         # < 10^-6: debe ir en notación científica
    "1000000000000",     # >= 10^12: debe ir en notación científica
    "1.234567890123",    # 13 cifras significativas
    "1.234567890123e-7", # 13 cifras significativas
    "1234567890123e+1",
]


@pytest.mark.parametrize("text", VALID)
def test_valid(text):
    assert is_canonical_cost(text)


@pytest.mark.parametrize("text", INVALID)
def test_invalid(text):
    assert not is_canonical_cost(text)


@pytest.mark.parametrize("value", [2, 2.0, True, None, b"2", ["2"]])
def test_non_strings_are_rejected(value):
    assert not is_canonical_cost(value)
