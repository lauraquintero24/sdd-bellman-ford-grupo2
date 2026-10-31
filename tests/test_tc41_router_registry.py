"""TC-41 — Registro de routers: identidad, direcciones y puertos únicos (FR-11, NFR-05; C-32)."""

import json
from pathlib import Path

import pytest

from router.settings import load_router_settings
from shared.models import RouterInfo
from shared.registry import parse_router_registry

REGISTRY = {"routers": [{"router_id": n, "url": f"http://127.0.0.1:{8001 + i}"} for i, n in enumerate("ABCD")]}


def test_valid_registry_has_unique_ids_urls_and_ports():
    routers = parse_router_registry(json.dumps(REGISTRY))
    assert routers == tuple(RouterInfo(n, f"http://127.0.0.1:{8001 + i}") for i, n in enumerate("ABCD"))
    assert len({r.router_id for r in routers}) == len({r.url for r in routers}) == 4


INVALID = {
    "no-json": "{",
    "sin-clave": json.dumps({"nodes": []}),
    "clave-extra": json.dumps({**REGISTRY, "x": 1}),
    "vacio": json.dumps({"routers": []}),
    "id-repetido": json.dumps({"routers": [{"router_id": "A", "url": "http://127.0.0.1:8001"},
                                           {"router_id": "A", "url": "http://127.0.0.1:8002"}]}),
    "id-vacio": json.dumps({"routers": [{"router_id": "", "url": "http://127.0.0.1:8001"}]}),
    "id-espacios": json.dumps({"routers": [{"router_id": " A", "url": "http://127.0.0.1:8001"}]}),
    "url-repetida": json.dumps({"routers": [{"router_id": "A", "url": "http://127.0.0.1:8001"},
                                            {"router_id": "B", "url": "http://127.0.0.1:8001/"}]}),
    "puerto-repetido": json.dumps({"routers": [{"router_id": "A", "url": "http://127.0.0.1:8001"},
                                               {"router_id": "B", "url": "http://localhost:8001"}]}),
    "sin-puerto": json.dumps({"routers": [{"router_id": "A", "url": "http://127.0.0.1"}]}),
    "sin-http": json.dumps({"routers": [{"router_id": "A", "url": "127.0.0.1:8001"}]}),
    "con-ruta": json.dumps({"routers": [{"router_id": "A", "url": "http://127.0.0.1:8001/x"}]}),
    "campo-extra": json.dumps({"routers": [{"router_id": "A", "url": "http://127.0.0.1:8001", "port": 1}]}),
}


@pytest.mark.parametrize("text", list(INVALID.values()), ids=list(INVALID))
def test_invalid_registries_are_rejected(text):
    with pytest.raises(ValueError):
        parse_router_registry(text)


@pytest.fixture
def registry_file(tmp_path):
    path = tmp_path / "routers.json"
    path.write_text(json.dumps(REGISTRY), encoding="utf-8")
    return path


def test_node_mode_takes_host_port_and_paths_from_registry(monkeypatch, tmp_path, registry_file):
    monkeypatch.chdir(tmp_path)
    s = load_router_settings(["--router-id", "C", "--routers", str(registry_file)], {})
    assert (s.router_id, s.host, s.port) == ("C", "127.0.0.1", 8003)
    assert s.log_file == Path("data/routers/C/forwarding.jsonl")
    assert s.table_file == Path("data/routers/C/forwarding-table.json")
    assert (tmp_path / "data" / "routers" / "C").is_dir()
    assert [r.router_id for r in s.routers] == ["A", "B", "C", "D"] and s.sync_interval_s == 1.0


def test_each_router_gets_its_own_directory(monkeypatch, tmp_path, registry_file):
    monkeypatch.chdir(tmp_path)
    settings = [load_router_settings(["--router-id", n, "--routers", str(registry_file)], {}) for n in "ABCD"]
    assert len({s.port for s in settings}) == 4
    assert len({s.log_file for s in settings}) == len({s.table_file for s in settings}) == 4


def test_environment_variables(monkeypatch, tmp_path, registry_file):
    monkeypatch.chdir(tmp_path)
    s = load_router_settings([], {"ROUTER_ID": "B", "ROUTERS_FILE": str(registry_file),
                                  "TABLE_SYNC_INTERVAL_SECONDS": "0"})
    assert (s.router_id, s.port, s.sync_interval_s) == ("B", 8002, 0.0)


@pytest.mark.parametrize(
    "argv, message",
    [
        (["--router-id", "X"], "no está en ROUTERS_FILE"),
        (["--router-id", "A", "--port", "9999"], "no coincide"),
        (["--router-id", "A", "--host", "0.0.0.0"], "no coincide"),
        (["--router-id", "A", "--sync-interval", "-1"], "TABLE_SYNC_INTERVAL_SECONDS"),
        (["--router-id", "A", "--table-file", "no-existe/t.json"], "FORWARDING_TABLE_FILE"),
    ],
)
def test_invalid_node_configuration_prevents_start(monkeypatch, tmp_path, registry_file, argv, message):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match=message):
        load_router_settings(argv + ["--routers", str(registry_file)], {})


def test_missing_registry_file(tmp_path):
    with pytest.raises(ValueError, match="ROUTERS_FILE"):
        load_router_settings(["--router-id", "A", "--routers", str(tmp_path / "no.json")], {})


def test_legacy_mode_unchanged(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    s = load_router_settings([], {})
    assert (s.router_id, s.routers, s.table_file, s.port) == (None, (), None, 8001)
