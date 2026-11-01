"""Demostración en modo nodo (C-32): Controller + routers A–D como procesos reales y los 5 escenarios del profesor.

Uso (desde la raíz del repositorio; Linux, o Windows con PowerShell o Git Bash):
    python scripts/demo_nodes.py --machine "descripción de la máquina" [--screenshots]

Arranca los procesos con las mismas líneas de comandos que el lanzador (scripts/start_all.py), con la topología
config/topology-demo.json (F-20) y el registro config/routers.json (puertos 8000–8004), y guarda en
demo-evidence/c32-modo-nodo/ un archivo por escenario con la fecha, la máquina, cada petición y su respuesta
literal. Los datos de cada router van a data/demo-c32/<id>/ (se vacía al empezar). Con --screenshots, además,
ejecuta scripts/capture_ui.js (Node.js + Playwright, opcional) contra la interfaz /ui.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from start_all import check_inputs, controller_command, default_connect_timeout, router_command  # noqa: E402

OUT = ROOT / "demo-evidence" / "c32-modo-nodo"
DATA = ROOT / "data" / "demo-c32"


class Evidence:
    """Escribe un archivo por escenario con cada petición y su respuesta literal."""

    def __init__(self, machine: str) -> None:
        self.machine = machine
        self.path: Path | None = None

    def step(self, name: str, title: str) -> None:
        self.path = OUT / name
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.path.write_text(f"# {title}\nFecha (UTC): {now}\nMáquina: {self.machine}\n\n", encoding="utf-8")
        print(f"== {title}")

    def note(self, text: str) -> None:
        self._write(f"## {text}\n")

    def request(self, method: str, url: str, body: dict | None = None, timeout: float = 15.0) -> httpx.Response | None:
        line = f"$ {method} {url}" + (f"  {json.dumps(body, ensure_ascii=False)}" if body is not None else "")
        try:
            response = httpx.request(method, url, json=body, timeout=timeout)
            text = f"{line}\n{response.text}\nHTTP {response.status_code}\n\n"
        except httpx.HTTPError as exc:
            response, text = None, f"{line}\n(sin respuesta: {type(exc).__name__})\n\n"
        self._write(text)
        return response

    def _write(self, text: str) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(text)


def wait_health(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            httpx.get(url + "/health", timeout=1.0)
            return
        except httpx.TransportError:
            time.sleep(0.2)
    raise RuntimeError(f"{url} no respondió")


def wait_version(urls: dict[str, str], version: int, timeout: float = 15.0) -> float:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            if all(httpx.get(u + "/status", timeout=2).json().get("topology_version") == version for u in urls.values()):
                return time.monotonic() - start
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError(f"los routers no alcanzaron la versión {version}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--machine", required=True)
    parser.add_argument("--topology", default="config/topology-demo.json")
    parser.add_argument("--routers", default="config/routers.json")
    parser.add_argument("--controller-port", type=int, default=8000)
    parser.add_argument("--screenshots", action="store_true", help="capturas de /ui con scripts/capture_ui.js")
    args = parser.parse_args()

    topology, registry_file = Path(args.topology), Path(args.routers)  # relativas a la raíz (cwd de los procesos)
    nodes, registry = check_inputs(ROOT / topology, ROOT / registry_file)
    urls = {info.router_id: info.url for info in registry}
    controller = f"http://127.0.0.1:{args.controller_port}"
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.rmtree(DATA, ignore_errors=True)
    OUT.mkdir(parents=True)
    (OUT / "logs").mkdir()
    ev = Evidence(args.machine)
    procs: dict[str, subprocess.Popen] = {}
    logs = {}

    def launch(name: str, command: list[str]) -> None:
        logs[name] = (OUT / "logs" / f"{name}.log").open("w", encoding="utf-8")
        procs[name] = subprocess.Popen([sys.executable, "-m", *command], cwd=ROOT, stdout=logs[name],
                                       stderr=subprocess.STDOUT, env={**os.environ, "ROUTERS_FILE": str(registry_file)})

    try:
        # --- 0. Arranque ------------------------------------------------------------------------------------
        ev.step("00-arranque.txt", "Escenario 0 — Arranque: Controller y una instancia Router por nodo")
        command = controller_command("127.0.0.1", args.controller_port, topology.as_posix())
        ev.note("python -m " + " ".join(command) + "   (ROUTERS_FILE=" + args.routers + ")")
        launch("controller", command)
        wait_health(controller)
        for info in registry:
            folder = DATA / info.router_id
            folder.mkdir(parents=True)
            relative = folder.relative_to(ROOT).as_posix()
            command = router_command(info.router_id, registry_file.as_posix(), controller,
                                     connect_timeout=default_connect_timeout(),
                                     extra=("--log-file", f"{relative}/forwarding.jsonl",
                                            "--table-file", f"{relative}/forwarding-table.json"))
            ev.note("python -m " + " ".join(command))
            launch(f"router-{info.router_id}", command)
        for url in urls.values():
            wait_health(url)
        ev.note(f"PID de los procesos: {json.dumps({n: p.pid for n, p in procs.items()})}")
        ev.request("GET", controller + "/health")
        ev.request("GET", controller + "/routers")
        for url in urls.values():
            ev.request("GET", url + "/health")
        waited = wait_version(urls, 1)
        ev.note(f"Las cuatro tablas sincronizadas en versión 1 tras {waited:.2f} s")

        # --- 1. Funcionamiento normal ---------------------------------------------------------------------
        ev.step("01-funcionamiento-normal.txt", "Escenario 1 — Cada router responde en su dirección con su propia tabla")
        for url in urls.values():
            ev.request("GET", url + "/status")
        for url in urls.values():
            ev.request("GET", url + "/forwarding-table?metric=delay")
        for metric in ("inverse_bandwidth", "loss"):
            ev.request("GET", urls[registry[0].router_id] + f"/forwarding-table?metric={metric}")

        # --- 2. Envío de un paquete ------------------------------------------------------------------------
        ev.step("02-envio-A-D.txt", "Escenario 2 — Paquete A→D reenviado salto a salto por HTTP")
        ev.request("GET", controller + "/route?src=A&dst=D&metric=delay")
        ev.request("POST", urls["A"] + "/packets",
                   {"packet_id": "pkt-1", "source": "A", "destination": "D", "metric": "delay", "payload": "demo"})
        ev.request("POST", urls["B"] + "/packets",
                   {"packet_id": "pkt-2", "source": "B", "destination": "C", "metric": "delay", "payload": "demo"})
        ev.note("B→C: empate exacto entre B-A-C y B-D-C (costo 3); DEC-08 elige B-A-C")

        # --- 3. Fallo de enlace ---------------------------------------------------------------------------
        ev.step("03-fallo-B-D.txt", "Escenario 3 — Fallo del enlace B–D: nueva versión, tablas y ruta")
        ev.request("POST", controller + "/links/fail", {"source": "B", "target": "D"})
        waited = wait_version(urls, 2)
        ev.note(f"Las cuatro tablas pasaron solas a la versión 2 en {waited:.2f} s (sincronización periódica, 1 s)")
        for url in urls.values():
            ev.request("GET", url + "/forwarding-table?metric=delay")
        ev.request("POST", urls["A"] + "/packets",
                   {"packet_id": "pkt-3", "source": "A", "destination": "D", "metric": "delay", "payload": "demo"})

        # --- 4. Restauración ------------------------------------------------------------------------------
        ev.step("04-restauracion.txt", "Escenario 4 — Restauración de B–D: las tablas vuelven a las mejores rutas")
        ev.request("POST", controller + "/links/restore", {"source": "B", "target": "D"})
        waited = wait_version(urls, 3)
        ev.note(f"Las cuatro tablas pasaron a la versión 3 en {waited:.2f} s")
        for url in urls.values():
            ev.request("GET", url + "/forwarding-table?metric=delay")
        ev.request("POST", urls["A"] + "/packets",
                   {"packet_id": "pkt-4", "source": "A", "destination": "D", "metric": "delay", "payload": "demo"})

        if args.screenshots:
            ev.step("06-interfaz.txt", "Interfaz web /ui en un navegador (scripts/capture_ui.js)")
            result = subprocess.run(["node", str(ROOT / "scripts" / "capture_ui.js"), controller + "/ui", str(OUT)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=180)
            ev.note("$ node scripts/capture_ui.js " + controller + "/ui demo-evidence/c32-modo-nodo")
            ev._write(result.stdout + result.stderr + f"\n(código de salida {result.returncode})\n")

        # --- 5. Router y Controller no disponibles -------------------------------------------------------
        ev.step("05-no-disponible.txt", "Escenario 5 — Router B detenido y Controller detenido: errores controlados")
        procs["router-B"].terminate()
        procs["router-B"].wait(timeout=10)
        ev.note(f"Se detiene el proceso Router B (PID {procs['router-B'].pid})")
        ev.request("POST", urls["A"] + "/packets",
                   {"packet_id": "pkt-5", "source": "A", "destination": "D", "metric": "delay", "payload": "demo"})
        for n in ("A", "C", "D"):
            ev.request("GET", urls[n] + "/health")
        procs["controller"].terminate()
        procs["controller"].wait(timeout=10)
        ev.note(f"Se detiene el proceso Controller (PID {procs['controller'].pid})")
        ev.request("POST", urls["C"] + "/packets",
                   {"packet_id": "pkt-6", "source": "C", "destination": "D", "metric": "delay", "payload": "demo"})
        ev.request("GET", urls["C"] + "/status")
        ev.request("GET", urls["C"] + "/health")
    finally:
        for process in procs.values():
            if process.poll() is None:
                process.terminate()
        for process in procs.values():
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        for handle in logs.values():
            handle.close()

    # --- Bitácoras y eventos de tabla de cada router (archivos propios de cada instancia) -------------------
    ev.step("07-bitacoras-y-eventos.txt", "Bitácora JSONL y eventos de tabla de cada router (data/demo-c32/<id>/)")
    for n in nodes:
        for name in ("forwarding.jsonl", "table-events.jsonl"):
            path = DATA / n / name
            ev.note(f"{path.relative_to(ROOT).as_posix()}")
            ev._write((path.read_text(encoding="utf-8") if path.exists() else "(no existe)\n") + "\n")
    print(f"Evidencias en {OUT.relative_to(ROOT).as_posix()}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
