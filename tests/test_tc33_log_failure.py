"""TC-33 — Fallo de la bitácora (FR-10, NFR-06, NFR-11): 500 LOG_PERSISTENCE_ERROR, nunca 200 ni 503."""

import logging
import os

import pytest

from router.dao import JsonlForwardingLogDAO
from shared.errors import ControllerUnavailableError
from shared.models import Route
from tests.fakes import FakeForwardingLogDAO, FakeRouteClient

E01 = Route("A", "D", "delay", ("A", "B", "D"), "2", 1)
PACKET = {"packet_id": "pkt-004", "source": "A", "destination": "D", "metric": "delay"}
EXPECTED = {"packet_id": "pkt-004", "status": "failed", "trace": [],
            "error": {"code": "LOG_PERSISTENCE_ERROR", "message": "No fue posible guardar el resultado.", "details": {}}}


@pytest.mark.parametrize(
    "route_client",
    [FakeRouteClient(E01), FakeRouteClient(error=ControllerUnavailableError("No fue posible conectar con el Controller."))],
    ids=["ruta-valida", "controller-caido"],
)
def test_fake_dao_raising_oserror(router_client, caplog, route_client):
    client = router_client(route_client=route_client, log_dao=FakeForwardingLogDAO(fail_with=OSError("disco lleno")))
    with caplog.at_level(logging.ERROR, logger="router"):
        response = client.post("/packets", json=PACKET)
    assert response.status_code == 500 and response.json() == EXPECTED
    assert any("LOG_PERSISTENCE_ERROR" in record.getMessage() for record in caplog.records)  # diagnóstico del proceso
    assert client.get("/health").status_code == 200


def test_real_jsonl_without_write_permission(router_client, tmp_path):
    path = tmp_path / "forwarding.jsonl"
    log_dao = JsonlForwardingLogDAO(path)
    client = router_client(route_client=FakeRouteClient(E01), log_dao=log_dao)
    path.chmod(0o444)  # se retira el permiso de escritura después del arranque
    try:
        if os.access(path, os.W_OK):
            pytest.skip("NO EJECUTADO: el proceso tiene privilegios de administrador y los permisos no aplican (06 TC-33)")
        response = client.post("/packets", json=PACKET)
        assert response.status_code == 500 and response.json() == EXPECTED
        assert client.get("/health").status_code == 200
    finally:
        path.chmod(0o644)
