"""TC-50 — Lanzador: una instancia Router por nodo (FR-11; C-32).

Ejecuta scripts/start_all.py como proceso real con un registro de puertos libres. La variante PowerShell
(scripts/start-all.ps1) solo envuelve este lanzador y se prueba en Windows (no hay PowerShell en este entorno).
"""

import json
import shutil
import subprocess
import sys
import time

import httpx

from tests.fakes import FIXTURES_DIR
from tests.process_utils import ROOT, free_port, port_open, read_output


def _registry(tmp_path, names):
    ports = {n: free_port() for n in names}
    path = tmp_path / "routers.json"
    path.write_text(json.dumps({"routers": [{"router_id": n, "url": f"http://127.0.0.1:{p}"} for n, p in ports.items()]}),
                    encoding="utf-8")
    return path, ports


def _launcher(tmp_path, registry, c_port, *extra):
    topology = tmp_path / "topology-demo.json"
    shutil.copy(FIXTURES_DIR / "F-20.json", topology)
    # Salida del lanzador a archivos, no a tuberías sin leer mientras vive (ver tests/process_utils.start)
    out_file, err_file = tmp_path / "launcher-stdout.txt", tmp_path / "launcher-stderr.txt"
    with out_file.open("wb") as out, err_file.open("wb") as err:
        process = subprocess.Popen(
            [sys.executable, "scripts/start_all.py", "--topology", str(topology), "--routers", str(registry),
             "--controller-port", str(c_port), "--logs", str(tmp_path / "logs"), *extra],
            cwd=ROOT, stdout=out, stderr=err,
        )
    process.output_files = (out_file, err_file)
    return process


def _output(process) -> tuple[str, str]:
    return tuple(read_output(path) for path in process.output_files)


def _finish(process, timeout: float) -> tuple[str, str]:
    process.wait(timeout=timeout)
    return _output(process)


def test_registry_that_does_not_match_nodes_starts_nothing(tmp_path):
    registry, ports = _registry(tmp_path, "ABC")  # falta D
    c_port = free_port()
    process = _launcher(tmp_path, registry, c_port)
    out, err = _finish(process, 30)
    assert process.returncode == 2 and "no coincide" in err
    assert not port_open(c_port) and not any(port_open(p) for p in ports.values())


def test_launcher_starts_one_router_per_node_and_stops_everything(tmp_path):
    registry, ports = _registry(tmp_path, "ABCD")
    c_port = free_port()
    stop_file = tmp_path / "stop"
    process = _launcher(tmp_path, registry, c_port, "--stop-file", str(stop_file))
    try:
        deadline = time.monotonic() + 60
        while not all(port_open(p) for p in [c_port, *ports.values()]):
            assert process.poll() is None, _output(process)
            assert time.monotonic() < deadline, "el lanzador no arrancó todo a tiempo"
            time.sleep(0.2)
        for n, port in ports.items():
            status = httpx.get(f"http://127.0.0.1:{port}/status", timeout=5).json()
            assert (status["router_id"], status["url"]) == (n, f"http://127.0.0.1:{port}")
        assert httpx.get(f"http://127.0.0.1:{c_port}/health", timeout=5).json()["application"] == "controller"
        assert sorted(p.name for p in (tmp_path / "logs").iterdir()) == [
            "controller.log", "router-A.log", "router-B.log", "router-C.log", "router-D.log"]
    finally:
        stop_file.write_text("stop", encoding="utf-8")
        out, err = _finish(process, 60)
    assert process.returncode == 0, err
    assert "Red en marcha: Controller + 4 routers" in out and "todos los procesos detenidos" in out
    for port in [c_port, *ports.values()]:
        assert not port_open(port)


def test_default_configuration_is_consistent():
    sys.path.insert(0, str(ROOT / "scripts"))
    from start_all import check_inputs

    nodes, registry = check_inputs(ROOT / "config/topology-demo.json", ROOT / "config/routers.json")
    assert nodes == ["A", "B", "C", "D"]
    assert [(r.router_id, r.url) for r in registry] == [(n, f"http://127.0.0.1:{8001 + i}") for i, n in enumerate("ABCD")]
    assert json.loads((ROOT / "config/topology-demo.json").read_text(encoding="utf-8")) == json.loads(
        (FIXTURES_DIR / "F-20.json").read_text(encoding="utf-8"))  # DEC-12: topología de demostración = F-20
