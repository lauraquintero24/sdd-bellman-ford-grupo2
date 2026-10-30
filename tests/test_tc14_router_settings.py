"""TC-14 (parte Router, unitaria): configuración por entorno y CLI (NFR-05, 02 §7)."""

from pathlib import Path

import pytest

from router.settings import RouterSettings, load_router_settings

ROOT = Path(__file__).resolve().parent.parent


def test_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # data/ se crea al arrancar, aquí en un directorio temporal
    settings = load_router_settings([], {})
    assert settings == RouterSettings("127.0.0.1", 8001, "http://127.0.0.1:8000", 1.0, 2.0, Path("data/forwarding.jsonl"))
    assert (tmp_path / "data").is_dir()


def test_environment(tmp_path):
    env = {
        "ROUTER_HOST": "0.0.0.0", "ROUTER_PORT": "18001", "CONTROLLER_URL": "http://127.0.0.1:18000",
        "FORWARDING_LOG_FILE": str(tmp_path / "log.jsonl"),
        "CONTROLLER_CONNECT_TIMEOUT_SECONDS": "0.3", "CONTROLLER_READ_TIMEOUT_SECONDS": "0.5",
    }
    s = load_router_settings([], env)
    assert (s.host, s.port, s.controller_url, s.connect_timeout_s, s.read_timeout_s, s.log_file) == (
        "0.0.0.0", 18001, "http://127.0.0.1:18000", 0.3, 0.5, tmp_path / "log.jsonl")


def test_cli_overrides_environment(tmp_path):
    env = {"ROUTER_PORT": "18001", "CONTROLLER_URL": "http://x:1", "CONTROLLER_READ_TIMEOUT_SECONDS": "9"}
    argv = ["--port", "18101", "--controller-url", "http://127.0.0.1:18100/", "--log-file", str(tmp_path / "f.jsonl"),
            "--connect-timeout", "0.25", "--read-timeout", "0.75", "--host", "127.0.0.2"]
    s = load_router_settings(argv, env)
    assert (s.host, s.port, s.controller_url, s.connect_timeout_s, s.read_timeout_s) == (
        "127.0.0.2", 18101, "http://127.0.0.1:18100", 0.25, 0.75)


@pytest.mark.parametrize(
    "argv, message",
    [
        (["--port", "70000"], "uerto"),
        (["--port", "0"], "uerto"),
        (["--connect-timeout", "0"], "CONTROLLER_CONNECT_TIMEOUT_SECONDS"),
        (["--read-timeout", "-1"], "CONTROLLER_READ_TIMEOUT_SECONDS"),
        (["--read-timeout", "nan"], "CONTROLLER_READ_TIMEOUT_SECONDS"),
        (["--read-timeout", "abc"], "CONTROLLER_READ_TIMEOUT_SECONDS"),
        (["--controller-url", "127.0.0.1:8000"], "CONTROLLER_URL"),
    ],
)
def test_invalid_values_prevent_start(tmp_path, argv, message):
    with pytest.raises(ValueError, match=message):
        load_router_settings(argv + ["--log-file", str(tmp_path / "f.jsonl")], {})


def test_explicit_log_directory_must_exist(tmp_path):
    with pytest.raises(ValueError, match="no existe"):
        load_router_settings(["--log-file", str(tmp_path / "no" / "f.jsonl")], {})
