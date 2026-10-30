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
