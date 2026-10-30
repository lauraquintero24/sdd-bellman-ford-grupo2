"""Fixtures comunes: cliente de la API del Controller sobre una copia temporal de un fixture (06 §1)."""

import shutil

import pytest
from fastapi.testclient import TestClient

from controller.app import create_controller_app
from controller.settings import ControllerSettings
from tests.fakes import FIXTURES_DIR


@pytest.fixture
def controller_client(tmp_path):
    """``controller_client("F-01")`` → TestClient con JsonTopologyDAO sobre una copia nueva."""

    def make(fixture: str = "F-01", dao=None) -> TestClient:
        path = tmp_path / f"{fixture}.json"
        shutil.copy(FIXTURES_DIR / f"{fixture}.json", path)
        settings = ControllerSettings(host="127.0.0.1", port=8000, topology_file=path)
        return TestClient(create_controller_app(settings, dao=dao), raise_server_exceptions=False)

    return make


@pytest.fixture
def router_client(tmp_path):
    """``router_client(route_client=…, log_dao=…)`` → TestClient sobre create_router_app.

    Sin ``log_dao`` se usa JsonlForwardingLogDAO sobre ``tmp_path / "forwarding.jsonl"``.
    """
    from router.app import create_router_app
    from router.settings import RouterSettings

    def make(route_client=None, log_dao=None, read_timeout: float = 2.0) -> TestClient:
        settings = RouterSettings("127.0.0.1", 8001, "http://127.0.0.1:9", 1.0, read_timeout, tmp_path / "forwarding.jsonl")
        app = create_router_app(settings, route_client=route_client, log_dao=log_dao)
        return TestClient(app, raise_server_exceptions=False)

    return make
