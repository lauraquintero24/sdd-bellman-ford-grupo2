"""TC-07 — La caída del Controller y el destino inalcanzable se gestionan limpiamente (FR-09, NFR-06).
TC-14 — Configuración por entorno y CLI con ambos procesos en puertos no predeterminados (NFR-05).

Procesos reales: Controller y Router como dos procesos del sistema operativo comunicados por HTTP.
"""

import json
import shutil
import socket
import threading

import httpx

from tests.fakes import FIXTURES_DIR
from tests.process_utils import free_port, start, stop, wait_health

PACKET = {"source": "A", "destination": "D", "metric": "delay"}


def _post(port, packet_id):
    return httpx.post(f"http://127.0.0.1:{port}/packets", json={"packet_id": packet_id, **PACKET}, timeout=10)


def _health(port):
    return httpx.get(f"http://127.0.0.1:{port}/health", timeout=5).status_code


def _lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _silent_server():
    """Servidor de prueba que acepta la conexión y nunca responde."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen()
    held = []

    def accept():
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return
            held.append(conn)

    threading.Thread(target=accept, daemon=True).start()
    return server, held


def test_tc07_unreachable_controller_down_and_timeout(tmp_path):
    topology = tmp_path / "F-01.json"
    shutil.copy(FIXTURES_DIR / "F-01.json", topology)
    log = tmp_path / "forwarding.jsonl"
    c_port, r_port = free_port(), free_port()
    controller = start("controller.main", ["--port", str(c_port), "--topology", str(topology)])
    router = start("router.main", ["--port", str(r_port), "--controller-url", f"http://127.0.0.1:{c_port}",
                                   "--log-file", str(log)])
    try:
        wait_health(c_port), wait_health(r_port)
        # a. Fallar B→D y C→D → 404 ROUTE_UNREACHABLE (E-06)
        for target in ("B", "C"):
            httpx.post(f"http://127.0.0.1:{c_port}/links/fail", json={"source": target, "target": "D"}, timeout=5)
        response = _post(r_port, "pkt-a")
        assert response.status_code == 404
        assert (response.json()["status"], response.json()["trace"], response.json()["error"]["code"]) == (
            "failed", [], "ROUTE_UNREACHABLE")
        assert _health(r_port) == 200
        # b. Detener el Controller → 503 CONTROLLER_UNAVAILABLE
        stop(controller)
        response = _post(r_port, "pkt-b")
        assert response.status_code == 503 and response.json()["error"]["code"] == "CONTROLLER_UNAVAILABLE"
        assert response.json()["status"] == "failed" and response.json()["trace"] == []
        assert str(c_port) not in response.text  # no expone la dirección del Controller
        assert _health(r_port) == 200
    finally:
        stop(router)
        stop(controller)

    # c. Router apuntando a un servidor que acepta la conexión y no responde; lectura 0.5 s → 504
    server, held = _silent_server()
    r2_port = free_port()
    router2 = start("router.main", ["--port", str(r2_port), "--controller-url",
                                    f"http://127.0.0.1:{server.getsockname()[1]}", "--log-file", str(log),
                                    "--read-timeout", "0.5"])
    try:
        wait_health(r2_port)
        response = _post(r2_port, "pkt-c")
        assert response.status_code == 504 and response.json()["error"]["code"] == "CONTROLLER_TIMEOUT"
        assert response.json()["status"] == "failed" and response.json()["trace"] == []
        assert _health(r2_port) == 200
    finally:
        stop(router2)
        server.close()
        for conn in held:
            conn.close()

    records = _lines(log)
    assert [(r["packet_id"], r["status"], r["error"]["code"]) for r in records] == [
        ("pkt-a", "failed", "ROUTE_UNREACHABLE"),
        ("pkt-b", "failed", "CONTROLLER_UNAVAILABLE"),
        ("pkt-c", "failed", "CONTROLLER_TIMEOUT"),
    ]


def test_tc14_both_processes_by_environment_and_cli(tmp_path):
    topology = tmp_path / "topo.json"
    shutil.copy(FIXTURES_DIR / "F-01.json", topology)
    log = tmp_path / "log.jsonl"
    c_port, r_port = free_port(), free_port()
    controller = start("controller.main", [], env={"CONTROLLER_PORT": str(c_port), "TOPOLOGY_FILE": str(topology)})
    router = start("router.main", ["--port", str(r_port)],  # CLI para el puerto, entorno para el resto
                   env={"ROUTER_PORT": "1", "CONTROLLER_URL": f"http://127.0.0.1:{c_port}", "FORWARDING_LOG_FILE": str(log)})
    try:
        assert wait_health(c_port).status_code == 200 and wait_health(r_port).status_code == 200
        response = _post(r_port, "pkt-env")
        assert response.status_code == 200 and response.json()["status"] == "forwarded"
        assert response.json()["route"]["path"] == ["A", "B", "D"]
        assert [r["packet_id"] for r in _lines(log)] == ["pkt-env"]
    finally:
        stop(router)
        stop(controller)


def test_tc14_router_invalid_port_prevents_start(tmp_path):
    process = start("router.main", ["--port", "70000", "--log-file", str(tmp_path / "f.jsonl")])
    _, stderr = process.communicate(timeout=30)
    assert process.returncode != 0 and "70000" in stderr
