"""Lanzador de la red en modo nodo (C-32, 02 §7): Controller + una instancia Router por nodo de la topología.

Uso (desde la raíz del repositorio; en Windows, también con scripts/start-all.ps1):
    python scripts/start_all.py [--topology config/topology-demo.json] [--routers config/routers.json]
                                [--controller-port 8000] [--sync-interval 1.0] [--connect-timeout S]

No arranca nada si el conjunto de router_id del registro difiere del de ``nodes``. Cada router usa la misma
aplicación ``router`` con su ``--router-id`` y escribe en data/routers/<id>/. Ctrl+C detiene todos los procesos.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.registry import parse_router_registry  # noqa: E402


def _arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--topology", default="config/topology-demo.json")
    parser.add_argument("--routers", default="config/routers.json")
    parser.add_argument("--controller-host", default="127.0.0.1")
    parser.add_argument("--controller-port", type=int, default=8000)
    parser.add_argument("--sync-interval", help="TABLE_SYNC_INTERVAL_SECONDS de los routers (por defecto 1.0)")
    parser.add_argument("--connect-timeout", help="por defecto 3 en Windows (rechazo de conexión lento) y 1.0 en otros")
    parser.add_argument("--logs", default="data/logs", help="directorio de la salida de cada proceso")
    parser.add_argument("--stop-file", help="si aparece este archivo, el lanzador detiene todo (uso en pruebas)")
    return parser.parse_args(argv)


def check_inputs(topology: Path, routers: Path):
    """Devuelve (nodos, registro) o lanza ValueError si no coinciden (FR-11, TC-50)."""
    nodes = json.loads(topology.read_text(encoding="utf-8"))["nodes"]
    registry = parse_router_registry(routers.read_text(encoding="utf-8"))
    ids = [info.router_id for info in registry]
    if sorted(ids) != sorted(nodes):
        raise ValueError(f"el registro {sorted(ids)} no coincide con los nodos de la topología {sorted(nodes)}")
    return nodes, registry


def _wait(url: str, process: subprocess.Popen, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{url} terminó al arrancar (código {process.returncode})")
        try:
            httpx.get(url + "/health", timeout=1.0)
            return
        except httpx.TransportError:
            time.sleep(0.2)
    raise RuntimeError(f"{url} no respondió en {timeout:.0f} s")


def main(argv=None) -> int:
    args = _arguments(argv)
    topology, routers = (ROOT / args.topology).resolve(), (ROOT / args.routers).resolve()
    try:
        nodes, registry = check_inputs(topology, routers)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Lanzador: no se arranca nada: {exc}", file=sys.stderr)
        return 2
    connect_timeout = args.connect_timeout or ("3" if sys.platform == "win32" else None)
    logs = ROOT / args.logs
    logs.mkdir(parents=True, exist_ok=True)
    controller_url = f"http://{args.controller_host}:{args.controller_port}"
    env = {**os.environ, "ROUTERS_FILE": str(routers)}  # el Controller lo usa para GET /routers e /ui
    processes: list[tuple[str, str, subprocess.Popen]] = []

    def launch(name: str, url: str, command: list[str]) -> None:
        log = (logs / f"{name}.log").open("w", encoding="utf-8")
        process = subprocess.Popen([sys.executable, "-m", *command], cwd=ROOT, env=env, stdout=log,
                                   stderr=subprocess.STDOUT)
        processes.append((name, url, process))

    def stop_all() -> None:
        for _, _, process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for _, _, process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

    stopping = []
    signal.signal(signal.SIGINT, lambda *_: stopping.append(True))
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: stopping.append(True))
    try:
        launch("controller", controller_url, ["controller.main", "--host", args.controller_host,
                                              "--port", str(args.controller_port), "--topology", str(topology)])
        _wait(controller_url, processes[-1][2])
        for info in registry:
            command = ["router.main", "--router-id", info.router_id, "--routers", str(routers),
                       "--controller-url", controller_url]
            if args.sync_interval is not None:
                command += ["--sync-interval", args.sync_interval]
            if connect_timeout is not None:
                command += ["--connect-timeout", connect_timeout]
            launch(f"router-{info.router_id}", info.url, command)
        for name, url, process in processes[1:]:
            _wait(url, process)
    except RuntimeError as exc:
        print(f"Lanzador: {exc}; se detiene todo (ver {logs})", file=sys.stderr)
        stop_all()
        return 1

    print(f"Red en marcha: Controller + {len(registry)} routers ({len(nodes)} nodos en {topology.name})")
    print(f"  Controller   {controller_url}    interfaz: {controller_url}/ui")
    for info in registry:
        port = urlsplit(info.url).port
        print(f"  Router {info.router_id:<5} {info.url}   (puerto {port}, datos en data/routers/{info.router_id}/)")
    print(f"Salida de cada proceso en {logs}. Ctrl+C para detener todo.", flush=True)
    stop_file = Path(args.stop_file) if args.stop_file else None
    try:
        while not stopping:
            if stop_file is not None and stop_file.exists():
                break
            dead = [(name, p.returncode) for name, _, p in processes if p.poll() is not None]
            if dead:
                print(f"Lanzador: proceso terminado inesperadamente: {dead}; se detiene todo", file=sys.stderr)
                stop_all()
                return 1
            time.sleep(0.3)
    finally:
        stop_all()
    print("Lanzador: todos los procesos detenidos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
