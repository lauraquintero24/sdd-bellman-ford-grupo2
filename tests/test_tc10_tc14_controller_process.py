"""TC-10 (parte proceso) y TC-14 (parte Controller) con procesos reales (FR-01, NFR-05).

TC-10: con una topología inválida el proceso termina con diagnóstico y no abre el puerto.
TC-14: arranque por entorno y por CLI en puertos no predeterminados; puerto 70000 rechazado.
La parte Router de TC-14 se ejecuta en la integración (G5).
"""

import json
import shutil

import pytest

from tests.fakes import FIXTURES_DIR
from tests.process_utils import free_port, port_open, start, stop, wait_health


@pytest.mark.parametrize(
    "content, rule",
    [('{"directed": true,', "TOPO-JSON"), (json.dumps({"directed": True, "nodes": [], "links": []}), "TOPO-NODES")],
    ids=["TOPO-JSON", "TOPO-NODES"],
)
def test_tc10_invalid_topology_prevents_start(tmp_path, content, rule):
    path = tmp_path / "bad.json"
    path.write_text(content, encoding="utf-8")
    port = free_port()
    process = start("controller.main", ["--port", str(port), "--topology", str(path)])
    _, stderr = process.communicate(timeout=30)
    assert process.returncode != 0
    assert rule in stderr
    assert not port_open(port)


def test_tc14_controller_by_environment(tmp_path):
    topology = tmp_path / "topo.json"
    shutil.copy(FIXTURES_DIR / "F-01.json", topology)
    port = free_port()
    process = start("controller.main", [], env={"CONTROLLER_PORT": str(port), "TOPOLOGY_FILE": str(topology)})
    try:
        assert wait_health(port).json() == {"status": "ok", "application": "controller"}
    finally:
        stop(process)


def test_tc14_controller_by_cli(tmp_path):
    topology = tmp_path / "topo.json"
    shutil.copy(FIXTURES_DIR / "F-01.json", topology)
    port = free_port()
    process = start("controller.main", ["--host", "127.0.0.1", "--port", str(port), "--topology", str(topology)],
                    env={"CONTROLLER_PORT": "1"})  # la CLI prevalece sobre el entorno
    try:
        assert wait_health(port).status_code == 200
    finally:
        stop(process)


def test_tc14_invalid_port_prevents_start():
    process = start("controller.main", ["--port", "70000", "--topology", str(FIXTURES_DIR / "F-01.json")])
    _, stderr = process.communicate(timeout=30)
    assert process.returncode != 0 and "70000" in stderr
