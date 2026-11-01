"""Diagnóstico: un servidor cuya salida va a una tubería que nadie lee deja de responder cuando el búfer se llena.

Uso (desde la raíz del repositorio):
    python scripts/diagnose_pipe_block.py [--requests 300]

Arranca el Controller dos veces con la topología F-20 y le hace peticiones GET /topology/version seguidas
(connect 1 s, read 2 s, como los routers):
1. «tubería»: stdout y stderr a subprocess.PIPE sin leer (lo que hacían las pruebas de 5 procesos antes);
2. «archivo»: stdout y stderr a un archivo (lo que hacen ahora las pruebas y el lanzador).
Cada petición escribe una línea del registro de accesos de uvicorn (~70 bytes). Con un búfer de ~4 KB (Windows)
la variante «tubería» se bloquea hacia la petición 55–60; con 64 KB (Linux) tardaría ~900 peticiones.
"""

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.process_utils import free_port, start, stop, wait_health  # noqa: E402

TIMEOUT = httpx.Timeout(2.0, connect=1.0)


def run(mode: str, requests: int, log_file: Path | None) -> bool:
    port = free_port()
    process = start("controller.main", ["--port", str(port), "--topology", "specs/fixtures/F-20.json"],
                    log_file=log_file)
    wait_health(port)
    ok, failure = 0, None
    for index in range(1, requests + 1):
        started = time.perf_counter()
        try:
            httpx.get(f"http://127.0.0.1:{port}/topology/version", timeout=TIMEOUT)
            ok += 1
        except httpx.HTTPError as exc:
            failure = f"la petición {index} falló con {type(exc).__name__} tras {time.perf_counter() - started:.2f} s"
            break
    stop(process)
    output = process.stdout_text + process.stderr_text
    print(f"[{mode}] {ok} de {requests} correctas" + (f"; {failure}" if failure else ""))
    print(f"[{mode}] salida del Controller: {len(output.encode('utf-8'))} bytes; últimas líneas de peticiones:")
    for line in [l for l in output.splitlines() if "/topology/version" in l][-4:]:
        print(f"    {line}")
    return failure is None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--requests", type=int, default=300)
    args = parser.parse_args()
    print(f"Python {sys.version.split()[0]} en {sys.platform}")
    piped = run("tubería", args.requests, None)
    with tempfile.TemporaryDirectory() as folder:
        to_file = run("archivo", args.requests, Path(folder) / "controller.log")
    print("Conclusión:", "la tubería sin leer bloquea el servidor" if not piped and to_file else
          "sin bloqueo con tubería en esta máquina" if piped else "fallo también con archivo: la causa es otra")
    return 0


if __name__ == "__main__":
    sys.exit(main())
