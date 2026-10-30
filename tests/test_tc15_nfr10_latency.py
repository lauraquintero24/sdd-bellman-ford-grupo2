"""TC-15 — Latencia p95 de GET /route (NFR-10): 10 + 100 peticiones por loopback a un proceso real.

Las mediciones con datos crudos y entorno se guardan con ``scripts/measure_nfr10.py``.
"""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "measure_nfr10.py"
spec = importlib.util.spec_from_file_location("measure_nfr10", SCRIPT)
measure_nfr10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure_nfr10)


@pytest.mark.parametrize("case", measure_nfr10.CASES, ids=[c["fixture"] for c in measure_nfr10.CASES])
def test_tc15_p95_under_300ms(case):
    result = measure_nfr10.measure_case(case)
    assert result["all_200"] and result["all_valid"]
    assert len(result["latencies_ms"]) == 100
    assert result["p95_ms"] <= measure_nfr10.THRESHOLD_MS, f"p95 = {result['p95_ms']:.3f} ms"
