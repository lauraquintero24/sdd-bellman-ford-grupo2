"""TC-34 — Independencia de procesos (FR-07; 02 §1.1).

Dos directorios, cada uno con solo su aplicación y su copia de shared/: el Router no tiene el
paquete controller (si lo importara, no arrancaría) ni el Controller el paquete router. Se comunican
solo por HTTP; al detener el Controller el Router sigue vivo; no hay archivos de estado comunes.
"""

import os
import shutil
import subprocess
import sys

import httpx

from tests.process_utils import ROOT, free_port, stop, wait_health


def _start(cwd, module, args):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.Popen([sys.executable, "-m", module, *args], cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def test_tc34_two_separate_directories(tmp_path):
    ctrl_dir, rtr_dir = tmp_path / "controller-app", tmp_path / "router-app"
    for target, package in ((ctrl_dir, "controller"), (rtr_dir, "router")):
        target.mkdir()
        ignore = shutil.ignore_patterns("__pycache__")
        shutil.copytree(ROOT / package, target / package, ignore=ignore)
        shutil.copytree(ROOT / "shared", target / "shared", ignore=ignore)
    shutil.copy(ROOT / "specs" / "fixtures" / "F-01.json", ctrl_dir / "topology.json")
    assert not (rtr_dir / "controller").exists() and not (ctrl_dir / "router").exists()

    c_port, r_port = free_port(), free_port()
    controller = _start(ctrl_dir, "controller.main", ["--port", str(c_port), "--topology", "topology.json"])
    # --connect-timeout 3: en Windows una conexión rechazada a 127.0.0.1 no falla al instante (el equipo midió
    # socket.connect a 127.0.0.1:9, puerto cerrado → «ConnectionRefusedError 2.03 s»); con el valor por defecto
    # de 1.0 s (02 §7) httpx lanzaría ConnectTimeout (504) antes que ConnectError (503) con el Controller detenido.
    router = _start(rtr_dir, "router.main", ["--port", str(r_port), "--controller-url", f"http://127.0.0.1:{c_port}",
                                             "--log-file", "forwarding.jsonl", "--connect-timeout", "3"])
    try:
        wait_health(c_port), wait_health(r_port)
        response = httpx.post(f"http://127.0.0.1:{r_port}/packets", timeout=10,
                              json={"packet_id": "pkt-34", "source": "A", "destination": "D", "metric": "delay"})
        assert response.status_code == 200 and response.json()["trace"][-1]["node"] == "D"
        stop(controller)
        assert httpx.get(f"http://127.0.0.1:{r_port}/health", timeout=5).status_code == 200
        response = httpx.post(f"http://127.0.0.1:{r_port}/packets", timeout=10,
                              json={"packet_id": "pkt-35", "source": "A", "destination": "D", "metric": "delay"})
        assert response.status_code == 503
    finally:
        stop(router)
        stop(controller)
    # Ningún archivo de estado común: la bitácora solo existe en el directorio del Router
    assert (rtr_dir / "forwarding.jsonl").is_file() and not (ctrl_dir / "forwarding.jsonl").exists()
    assert len((rtr_dir / "forwarding.jsonl").read_text(encoding="utf-8").splitlines()) == 2
