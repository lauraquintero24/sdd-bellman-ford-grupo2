"""TC-14 (parte Controller, unitaria): configuración por entorno y CLI (NFR-05, 02 §7).

El arranque de procesos reales en puertos 18000/18001 se hace en la integración (G5).
"""

from pathlib import Path

import pytest

from controller.settings import ControllerSettings, load_controller_settings


@pytest.fixture
def topo(tmp_path):
    path = tmp_path / "topo.json"
    path.write_text("{}", encoding="utf-8")
    return path


def test_defaults(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parent.parent)
    settings = load_controller_settings([], {})
    assert settings == ControllerSettings(host="127.0.0.1", port=8000, topology_file=settings.topology_file)
    assert settings.topology_file.as_posix() == "config/topology.json"


def test_environment_overrides_defaults(topo):
    env = {"CONTROLLER_HOST": "0.0.0.0", "CONTROLLER_PORT": "18000", "TOPOLOGY_FILE": str(topo)}
    settings = load_controller_settings([], env)
    assert (settings.host, settings.port, settings.topology_file) == ("0.0.0.0", 18000, topo)


def test_cli_overrides_environment(topo, tmp_path):
    other = tmp_path / "other.json"
    other.write_text("{}", encoding="utf-8")
    env = {"CONTROLLER_HOST": "0.0.0.0", "CONTROLLER_PORT": "18000", "TOPOLOGY_FILE": str(other)}
    settings = load_controller_settings(["--host", "127.0.0.2", "--port", "18100", "--topology", str(topo)], env)
    assert (settings.host, settings.port, settings.topology_file) == ("127.0.0.2", 18100, topo)


@pytest.mark.parametrize("port", ["70000", "0", "-1", "abc", "80.5"])
def test_invalid_port_prevents_start(topo, port):
    with pytest.raises(ValueError, match="[Pp]uerto"):
        load_controller_settings(["--port", port, "--topology", str(topo)], {})


def test_missing_topology_file_prevents_start(tmp_path):
    with pytest.raises(ValueError, match="TOPOLOGY_FILE"):
        load_controller_settings(["--topology", str(tmp_path / "no-existe.json")], {})
