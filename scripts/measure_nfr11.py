"""Medición de NFR-11 con procesos reales (01 §3; complementa TC-16, que usa TestClient).

Arranca el Controller (F-01) y el Router con una bitácora vacía en puertos libres; 4 clientes
concurrentes envían 25 POST /packets cada uno (pkt-000…pkt-099) y se comprueba que la bitácora
tiene exactamente 100 líneas JSONL parseables, sin mezclas y con 100 packet_id distintos.

Uso (desde la raíz del repositorio):
    python scripts/measure_nfr11.py --machine "descripción de la máquina" [--out demo-evidence/nfr11]
"""

import argparse
import json
import platform
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
CLIENTS, PER_CLIENT = 4, 25
LOG_FIELDS = ["recorded_at", "packet_id", "source", "destination", "metric", "status", "route", "trace",
              "topology_version", "error"]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait(url: str) -> None:
    deadline = time.monotonic() + 20
    while True:
        try:
            httpx.get(f"{url}/health", timeout=1.0)
            return
        except httpx.TransportError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--machine", required=True, help="descripción de la máquina donde se mide")
    parser.add_argument("--out", default="demo-evidence/nfr11", help="directorio de salida")
    args = parser.parse_args()
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    work = ROOT / "data" / "nfr11"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    log = work / "forwarding.jsonl"
    c_port, r_port = _free_port(), _free_port()
    controller = subprocess.Popen(
        [sys.executable, "-m", "controller.main", "--port", str(c_port), "--topology", "specs/fixtures/F-01.json"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    router = subprocess.Popen(
        [sys.executable, "-m", "router.main", "--port", str(r_port), "--controller-url", f"http://127.0.0.1:{c_port}",
         "--log-file", str(log)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    statuses: list[int] = []
    lock = threading.Lock()
    barrier = threading.Barrier(CLIENTS)
    try:
        _wait(f"http://127.0.0.1:{c_port}")
        _wait(f"http://127.0.0.1:{r_port}")

        def client(n: int) -> None:
            with httpx.Client(base_url=f"http://127.0.0.1:{r_port}", timeout=10.0) as http:
                barrier.wait()
                for i in range(n * PER_CLIENT, (n + 1) * PER_CLIENT):
                    response = http.post("/packets", json={"packet_id": f"pkt-{i:03d}", "source": "A",
                                                           "destination": "D", "metric": "delay"})
                    with lock:
                        statuses.append(response.status_code)

        t0 = time.perf_counter()
        threads = [threading.Thread(target=client, args=(n,)) for n in range(CLIENTS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        elapsed = time.perf_counter() - t0
    finally:
        router.terminate()
        controller.terminate()
        router.wait(timeout=10)
        controller.wait(timeout=10)

    lines = log.read_text(encoding="utf-8").splitlines()
    parsed, bad = [], 0
    for line in lines:
        try:
            record = json.loads(line)
            parsed.append(record if list(record) == LOG_FIELDS else None)
        except ValueError:
            bad += 1
    conforming = [r for r in parsed if r is not None]
    ids = {r["packet_id"] for r in conforming}
    ok = (
        statuses.count(200) == CLIENTS * PER_CLIENT
        and len(lines) == 100 and bad == 0 and len(conforming) == 100
        and ids == {f"pkt-{i:03d}" for i in range(100)}
        and all(r["status"] == "forwarded" for r in conforming)
    )
    shutil.copy(log, out / "nfr11-forwarding.jsonl")
    command = "python " + shlex.join([Path(sys.argv[0]).as_posix(), *sys.argv[1:]])
    summary = [
        f"NFR-11 — {started}",
        f"Comando: {command}",
        f"Máquina: {args.machine}",
        f"  os: {platform.platform()}  python: {platform.python_version()}",
        f"Procesos reales: Controller 127.0.0.1:{c_port} (F-01), Router 127.0.0.1:{r_port}, bitácora vacía al inicio",
        f"Clientes concurrentes: {CLIENTS} x {PER_CLIENT} POST /packets (pkt-000..pkt-099) en {elapsed:.3f} s",
        f"Respuestas 200: {statuses.count(200)} de {len(statuses)}",
        f"Líneas en la bitácora: {len(lines)}; no parseables: {bad}; conformes a 04 §6: {len(conforming)}",
        f"packet_id distintos: {len(ids)}",
        f"Veredicto (100 líneas parseables, sin mezclas, 100 IDs distintos): {'PASS' if ok else 'FAIL'}",
        "Bitácora cruda: nfr11-forwarding.jsonl",
        "El caso «un fallo de escritura produce 500 y nunca 200» se verifica en TC-33 (test-results.txt).",
    ]
    (out / "nfr11-summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
