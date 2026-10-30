"""Medición de NFR-10 / TC-15: latencia p95 de GET /route (01 §3; 06 TC-15).

Por cada fixture arranca el Controller como proceso real en un puerto libre de loopback,
hace 10 peticiones de calentamiento y 100 secuenciales (metric=delay) medidas con
time.perf_counter_ns en el cliente, y calcula p95 = 95.º valor de las 100 latencias ordenadas.
PASS solo si las 200 respuestas son 200 con la ruta esperada y p95 <= 300 ms en ambos fixtures.

Uso (desde la raíz del repositorio):
    python scripts/measure_nfr10.py --machine "descripción de la máquina" [--out demo-evidence/nfr10]
"""

import argparse
import json
import os
import platform
import shlex
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
THRESHOLD_MS = 300.0
CASES = [
    {"fixture": "F-01", "src": "A", "dst": "D", "hops": 2, "total_cost": "2"},
    {"fixture": "F-19", "src": "N100", "dst": "N001", "hops": 99, "total_cost": "99"},
]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _environment(machine: str) -> dict:
    cpu = platform.processor() or "no disponible"
    ram = "no disponible"
    if Path("/proc/cpuinfo").is_file():
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    if Path("/proc/meminfo").is_file():
        ram = Path("/proc/meminfo").read_text().splitlines()[0].split(":", 1)[1].strip()
    return {
        "machine": machine,
        "os": platform.platform(),
        "cpu": cpu,
        "cpu_count": os.cpu_count(),
        "ram": ram,
        "python": platform.python_version(),
        "fastapi": version("fastapi"),
        "uvicorn": version("uvicorn"),
        "networkx": version("networkx"),
        "httpx": version("httpx"),
    }


def measure_case(case: dict, warmup: int = 10, samples: int = 100) -> dict:
    port = _free_port()
    topology = ROOT / "specs" / "fixtures" / f"{case['fixture']}.json"
    process = subprocess.Popen(
        [sys.executable, "-m", "controller.main", "--port", str(port), "--topology", str(topology)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}/route"
    params = {"src": case["src"], "dst": case["dst"], "metric": "delay"}
    try:
        with httpx.Client(timeout=10.0) as client:
            deadline = time.monotonic() + 20
            while True:
                try:
                    client.get(f"http://127.0.0.1:{port}/health")
                    break
                except httpx.TransportError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.1)
            statuses, valid, latencies_ns = [], [], []
            for i in range(warmup + samples):
                start = time.perf_counter_ns()
                response = client.get(url, params=params)
                elapsed = time.perf_counter_ns() - start
                body = response.json() if response.status_code == 200 else {}
                statuses.append(response.status_code)
                valid.append(
                    response.status_code == 200
                    and len(body.get("path", [])) - 1 == case["hops"]
                    and body.get("total_cost") == case["total_cost"]
                )
                if i >= warmup:
                    latencies_ns.append(elapsed)
    finally:
        process.terminate()
        process.wait(timeout=10)
    latencies_ms = [ns / 1e6 for ns in latencies_ns]
    ordered = sorted(latencies_ms)
    p95 = ordered[94]
    return {
        **case,
        "port": port,
        "warmup": warmup,
        "samples": samples,
        "all_200": all(s == 200 for s in statuses),
        "all_valid": all(valid),
        "p50_ms": ordered[49],
        "p95_ms": p95,
        "max_ms": ordered[-1],
        "pass": all(valid) and p95 <= THRESHOLD_MS,
        "latencies_ms": latencies_ms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--machine", required=True, help="descripción de la máquina donde se mide")
    parser.add_argument("--out", default="demo-evidence/nfr10", help="directorio de salida")
    args = parser.parse_args()

    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = [measure_case(case) for case in CASES]
    report = {
        "requirement": "NFR-10 / TC-15",
        "date_utc": started,
        "command": "python " + shlex.join([Path(sys.argv[0]).as_posix(), *sys.argv[1:]]),
        "threshold_ms": THRESHOLD_MS,
        "environment": _environment(args.machine),
        "results": results,
        "verdict": "PASS" if all(r["pass"] for r in results) else "FAIL",
    }
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "nfr10-raw.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [f"NFR-10 / TC-15 — {started}", f"Comando: {report['command']}", f"Máquina: {args.machine}"]
    lines += [f"  {k}: {v}" for k, v in report["environment"].items() if k != "machine"]
    for r in results:
        lines.append(
            f"{r['fixture']} {r['src']}->{r['dst']} (puerto {r['port']}): 10 calentamiento + 100 muestras; "
            f"todas 200 y ruta esperada: {r['all_valid']}; p50={r['p50_ms']:.3f} ms; "
            f"p95={r['p95_ms']:.3f} ms; max={r['max_ms']:.3f} ms; {'PASS' if r['pass'] else 'FAIL'}"
        )
    lines.append(f"Veredicto (p95 <= {THRESHOLD_MS:.0f} ms en ambos): {report['verdict']}")
    lines.append("Latencias crudas: nfr10-raw.json")
    (out / "nfr10-summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
