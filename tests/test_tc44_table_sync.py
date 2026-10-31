"""TC-44 — Sincronización por versión sin recálculos innecesarios (FR-12, NFR-12; C-32).

También: JsonForwardingTableDAO (instantánea atómica y eventos) y validación de HttpTableClient.
"""

import json

import httpx
import pytest

from controller.engine import BellmanFordEngine
from controller.presenter import CostPresenter
from controller.service import RoutingService
from router.client import HttpTableClient
from router.dao import JsonForwardingTableDAO
from router.service import NodeForwardingService
from shared.errors import (
    ControllerBadResponseError,
    ControllerTimeoutError,
    ControllerUnavailableError,
    ForwardingTableUnavailableError,
    NodeNotFoundError,
)
from shared.models import RouterInfo
from tests.fakes import FakeForwardingLogDAO, FakeForwardingTableDAO, FakeTopologyDAO, SpyTableClient, load_fixture_topology

REGISTRY = tuple(RouterInfo(n, f"http://127.0.0.1:{8001 + i}") for i, n in enumerate("ABCD"))


def _controller(fixture="F-20"):
    return RoutingService(dao=FakeTopologyDAO(load_fixture_topology(fixture)), engine=BellmanFordEngine(),
                          presenter=CostPresenter())


def _node(router_id, client, table_dao=None):
    return NodeForwardingService(router_id=router_id, registry=REGISTRY, table_client=client,
                                 table_dao=table_dao or FakeForwardingTableDAO(), next_hop_client=None,
                                 log_dao=FakeForwardingLogDAO())


def test_no_table_requests_while_version_is_unchanged():
    controller = _controller()
    spy = SpyTableClient(controller)
    node = _node("A", spy)
    with pytest.raises(ForwardingTableUnavailableError):
        node.current_table("delay")
    assert node.status()["sync_status"] == "pending"

    first = node.sync_if_changed()
    assert first.topology_version == 1 and len(spy.table_calls) == 3  # una por métrica
    for _ in range(5):
        node.sync_if_changed()
    assert len(spy.table_calls) == 3 and spy.version_calls == 6  # solo la versión, sin tablas
    assert node.status()["sync_status"] == "ok"

    controller.set_link_status("B", "D", False)
    second = node.sync_if_changed()
    assert second.topology_version == 2 and len(spy.table_calls) == 6
    row_d = second.tables["delay"].entries[2]
    assert (row_d.destination, row_d.next_hop, row_d.total_cost) == ("D", "C", "4")  # T-19
    assert node.current_table("delay").topology_version == 2


def test_sync_error_keeps_last_table_and_reports_status():
    spy = SpyTableClient(_controller())
    node = _node("B", spy)
    node.sync_if_changed()
    spy.error = ControllerUnavailableError("No fue posible conectar con el Controller.")
    with pytest.raises(ControllerUnavailableError):
        node.sync_if_changed()
    status = node.status()
    assert status["sync_status"] == "error" and status["sync_error"]["code"] == "CONTROLLER_UNAVAILABLE"
    assert node.current_table("delay").entries[0].next_hop == "A"  # tabla anterior conservada (T-08)
    spy.error = None
    node.sync_if_changed()
    assert node.status()["sync_status"] == "ok"


def test_stored_table_is_shown_but_refreshed_on_first_sync():
    controller = _controller()
    dao = FakeForwardingTableDAO()
    _node("A", SpyTableClient(controller), dao).sync_if_changed()
    spy = SpyTableClient(controller)
    restarted = _node("A", spy, FakeForwardingTableDAO(stored=dao.stored))
    assert restarted.current_table("delay").topology_version == 1  # visible antes de sincronizar
    restarted.sync_if_changed()
    assert len(spy.table_calls) == 3  # la primera sincronización siempre la renueva


def test_router_not_in_registry_is_rejected():
    with pytest.raises(ValueError):
        _node("X", SpyTableClient(_controller()))


def test_json_dao_writes_snapshot_and_one_event_per_version(tmp_path):
    controller = _controller()
    dao = JsonForwardingTableDAO(tmp_path / "forwarding-table.json", tmp_path / "table-events.jsonl")
    node = _node("A", SpyTableClient(controller), dao)
    node.sync_if_changed()
    node.sync_if_changed()  # misma versión: ningún evento nuevo
    controller.set_link_status("B", "D", False)
    node.sync_if_changed()

    snapshot = json.loads((tmp_path / "forwarding-table.json").read_text(encoding="utf-8"))
    assert snapshot["router_id"] == "A" and snapshot["topology_version"] == 2 and snapshot["url"] == "http://127.0.0.1:8001"
    assert set(snapshot["tables"]) == {"delay", "inverse_bandwidth", "loss"}
    events = [json.loads(line) for line in (tmp_path / "table-events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(e["previous_version"], e["topology_version"]) for e in events] == [(None, 1), (1, 2)]
    delay_changes = [c for c in events[1]["changes"] if c["metric"] == "delay"]
    assert delay_changes == [{"metric": "delay", "destination": "D",
                              "before": {"next_hop": "B", "total_cost": "2", "status": "active"},
                              "after": {"next_hop": "C", "total_cost": "4", "status": "active"}}]
    assert dao.load().topology_version == 2
    assert not (tmp_path / "forwarding-table.json.tmp").exists()


# --- HttpTableClient ---

TABLE = {"router_id": "A", "metric": "delay", "topology_version": 1, "entries": [
    {"destination": "B", "next_hop": "B", "path": ["A", "B"], "total_cost": "1", "status": "active"},
    {"destination": "C", "next_hop": None, "path": None, "total_cost": None, "status": "unreachable"}]}


def _client(handler):
    return HttpTableClient("http://controller.test", 1.0, 2.0, transport=httpx.MockTransport(handler))


def test_table_client_valid_responses():
    def handler(request):
        if request.url.path == "/topology/version":
            return httpx.Response(200, json={"topology_version": 3})
        assert dict(request.url.params) == {"router_id": "A", "metric": "delay"}
        return httpx.Response(200, json=TABLE)

    client = _client(handler)
    assert client.fetch_topology_version() == 3
    table = client.fetch_forwarding_table("A", "delay")
    assert table.entries[0].path == ("A", "B") and table.entries[1].status == "unreachable"


BAD_TABLES = {
    "otro-router": {**TABLE, "router_id": "B"},
    "otra-metrica": {**TABLE, "metric": "loss"},
    "version-0": {**TABLE, "topology_version": 0},
    "campo-extra": {**TABLE, "x": 1},
    "next-hop-incoherente": {**TABLE, "entries": [{**TABLE["entries"][0], "next_hop": "C"}]},
    "ruta-no-empieza-en-A": {**TABLE, "entries": [{**TABLE["entries"][0], "path": ["X", "B"]}]},
    "costo-no-canonico": {**TABLE, "entries": [{**TABLE["entries"][0], "total_cost": "1.0"}]},
    "inalcanzable-con-salto": {**TABLE, "entries": [{**TABLE["entries"][1], "next_hop": "B"}]},
    "estado-desconocido": {**TABLE, "entries": [{**TABLE["entries"][0], "status": "up"}]},
    "destino-propio": {**TABLE, "entries": [{**TABLE["entries"][1], "destination": "A"}]},
}


@pytest.mark.parametrize("body", list(BAD_TABLES.values()), ids=list(BAD_TABLES))
def test_table_client_rejects_non_conforming_tables(body):
    with pytest.raises(ControllerBadResponseError):
        _client(lambda r: httpx.Response(200, json=body)).fetch_forwarding_table("A", "delay")


@pytest.mark.parametrize("body", [{"topology_version": True}, {"topology_version": 1, "x": 1}, {"version": 1}])
def test_table_client_rejects_bad_versions(body):
    with pytest.raises(ControllerBadResponseError):
        _client(lambda r: httpx.Response(200, json=body)).fetch_topology_version()


def test_table_client_network_errors_and_404():
    def raising(exc):
        def handler(request):
            raise exc("fallo", request=request)
        return handler

    with pytest.raises(ControllerUnavailableError):
        _client(raising(httpx.ConnectError)).fetch_topology_version()
    with pytest.raises(ControllerTimeoutError):
        _client(raising(httpx.ReadTimeout)).fetch_forwarding_table("A", "delay")
    not_found = {"error": {"code": "NODE_NOT_FOUND", "message": "El nodo A no existe.", "details": {"field": "router_id", "value": "A"}}}
    with pytest.raises(NodeNotFoundError):
        _client(lambda r: httpx.Response(404, json=not_found)).fetch_forwarding_table("A", "delay")
