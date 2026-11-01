"""TC-45 / TC-46 — Paquetes enviados INMEDIATAMENTE después de fallar o restaurar un enlace (C-32).

Cubre la carrera observada en Windows 11 (paquete justo tras el cambio → respuesta de error con trace []):
1. Procesos reales: sin esperar a la sincronización periódica, el router de ingreso debe sincronizar dentro de
   handle() (escritura de forwarding-table.json en el camino del paquete) y reenviar por la ruta nueva.
2. Reintento acotado ante PermissionError transitorio (Windows) en os.replace y al abrir los archivos anexados.
3. Las sincronizaciones concurrentes de una instancia (hilo periódico + peticiones) nunca escriben a la vez.
"""

import json
import os
import shutil
import threading
import time

import httpx
import pytest

import router.dao as dao_module
from controller.engine import BellmanFordEngine
from controller.presenter import CostPresenter
from controller.service import RoutingService
from router.dao import JsonForwardingTableDAO, JsonlForwardingLogDAO
from router.models import Packet
from router.service import NodeForwardingService
from shared.errors import LogPersistenceError
from shared.models import RouterInfo
from tests.fakes import FIXTURES_DIR, FakeForwardingLogDAO, FakeTopologyDAO, SpyTableClient, load_fixture_topology
from tests.process_utils import free_port, start, stop, wait_health
from tests.test_tc40_tc45_tc46_five_processes import _diagnosis, _send_expect

ROUNDS = 6


def test_packets_right_after_each_link_change(tmp_path):
    topology = tmp_path / "topology-demo.json"
    shutil.copy(FIXTURES_DIR / "F-20.json", topology)
    c_port, ports = free_port(), {n: free_port() for n in "ABCD"}
    urls = {n: f"http://127.0.0.1:{p}" for n, p in ports.items()}
    registry = tmp_path / "routers.json"
    registry.write_text(json.dumps({"routers": [{"router_id": n, "url": u} for n, u in urls.items()]}), encoding="utf-8")
    controller = f"http://127.0.0.1:{c_port}"
    procs = {"controller": start("controller.main", ["--port", str(c_port), "--topology", str(topology)])}
    for n in "ABCD":
        (tmp_path / n).mkdir()
        # --connect-timeout 3 como en el lanzador en Windows (rechazo de conexión lento, limitación 10 del README)
        procs[n] = start("router.main", ["--router-id", n, "--routers", str(registry), "--controller-url", controller,
                                         "--log-file", str(tmp_path / n / "forwarding.jsonl"),
                                         "--table-file", str(tmp_path / n / "forwarding-table.json"),
                                         "--connect-timeout", "3"])
    try:
        wait_health(c_port)
        for port in ports.values():
            wait_health(port)
        _send_expect(urls, tmp_path, "A", "D", "warmup", ["A", "B", "D"])
        expected = {"fail": ["A", "C", "D"], "restore": ["A", "B", "D"]}
        for round_index in range(ROUNDS):
            for action in ("fail", "restore"):
                httpx.post(f"{controller}/links/{action}", json={"source": "B", "target": "D"}, timeout=5)
                # Sin esperar: el router de ingreso debe sincronizar dentro de handle()
                body = _send_expect(urls, tmp_path, "A", "D", f"r{round_index}-{action}-0", expected[action])
                assert body["topology_version"] == 2 + 2 * round_index + (action == "restore")
                # Y varios paquetes concurrentes desde orígenes distintos mientras el hilo periódico sincroniza
                errors = []

                def send(src, dst, packet_id):
                    try:
                        response = httpx.post(f"{urls[src]}/packets", timeout=15, json={
                            "packet_id": packet_id, "source": src, "destination": dst, "metric": "delay"})
                        if response.status_code != 200:
                            errors.append(f"{packet_id}: HTTP {response.status_code} {response.text}")
                    except httpx.HTTPError as exc:
                        errors.append(f"{packet_id}: {exc!r}")

                threads = [threading.Thread(target=send, args=(s, d, f"r{round_index}-{action}-{s}{d}"))
                           for s, d in (("A", "D"), ("D", "A"), ("C", "B"), ("B", "C"))]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
                assert not errors, "\n".join(errors) + "\n" + _diagnosis(urls, tmp_path)
    finally:
        for process in procs.values():
            stop(process)
    for n in "ABCD":  # ninguna línea failed en ninguna bitácora
        records = [json.loads(l) for l in (tmp_path / n / "forwarding.jsonl").read_text(encoding="utf-8").splitlines()]
        assert all(r["status"] == "forwarded" for r in records), [r for r in records if r["status"] != "forwarded"]


# --- Reintento acotado ante PermissionError transitorio (Windows) ---

def _tables(version=1):
    service = RoutingService(dao=FakeTopologyDAO(load_fixture_topology("F-20")), engine=BellmanFordEngine(),
                             presenter=CostPresenter())
    node = NodeForwardingService("A", (RouterInfo("A", "http://127.0.0.1:8001"),), SpyTableClient(service),
                                 _MemoryDAO(), None, FakeForwardingLogDAO())
    return node.sync_if_changed()


class _MemoryDAO:
    def load(self):
        return None

    def save(self, tables):
        pass


@pytest.fixture
def windows_retry(monkeypatch):
    monkeypatch.setattr(dao_module, "RETRY_PERMISSION_ERRORS", True)
    monkeypatch.setattr(dao_module, "_RETRY_DELAY_S", 0)


def _flaky(monkeypatch, target, name, failures):
    calls = {"n": 0}
    original = getattr(target, name)

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] <= failures:
            raise PermissionError(13, "El proceso no tiene acceso al archivo porque está siendo utilizado por otro proceso")
        return original(*args, **kwargs)

    monkeypatch.setattr(target, name, flaky)
    return calls


def test_replace_is_retried_on_transient_permission_error(tmp_path, monkeypatch, windows_retry):
    calls = _flaky(monkeypatch, os, "replace", failures=3)
    dao = JsonForwardingTableDAO(tmp_path / "forwarding-table.json", tmp_path / "table-events.jsonl")
    dao.save(_tables())
    assert calls["n"] == 4 and dao.load().topology_version == 1


def test_persistent_permission_error_still_fails_controlled(tmp_path, monkeypatch, windows_retry):
    calls = _flaky(monkeypatch, os, "replace", failures=1000)
    dao = JsonForwardingTableDAO(tmp_path / "forwarding-table.json", tmp_path / "table-events.jsonl")
    with pytest.raises(LogPersistenceError):
        dao.save(_tables())
    assert calls["n"] == dao_module._RETRIES


def test_log_append_is_retried_on_transient_permission_error(tmp_path, monkeypatch, windows_retry):
    from pathlib import Path

    from router.models import ForwardingResult

    dao = JsonlForwardingLogDAO(tmp_path / "forwarding.jsonl")
    calls = _flaky(monkeypatch, Path, "open", failures=2)
    dao.save(ForwardingResult("p", "A", "D", "delay", "failed", (), None, None, {"code": "X", "message": "m", "details": {}}))
    assert calls["n"] == 3 and len((tmp_path / "forwarding.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_persistent_permission_error_gives_exact_tc33_response(router_client, monkeypatch, windows_retry):
    """Con reintento activo y PermissionError persistente, la respuesta HTTP es exactamente la de TC-33 (04 §5)."""
    from pathlib import Path

    from tests.test_tc33_log_failure import E01, EXPECTED, PACKET
    from tests.fakes import FakeRouteClient

    client = router_client(route_client=FakeRouteClient(E01))
    calls = _flaky(monkeypatch, Path, "open", failures=1000)
    response = client.post("/packets", json=PACKET)
    assert response.status_code == 500 and response.json() == EXPECTED
    assert calls["n"] == dao_module._RETRIES

def test_no_retry_outside_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(dao_module, "RETRY_PERMISSION_ERRORS", False)
    calls = _flaky(monkeypatch, os, "replace", failures=1)
    with pytest.raises(LogPersistenceError):
        JsonForwardingTableDAO(tmp_path / "t.json", tmp_path / "e.jsonl").save(_tables())
    assert calls["n"] == 1  # en Linux un PermissionError es real (TC-33): sin reintento


# --- Serialización de las escrituras de una instancia ---

class _OverlapDetectingDAO:
    """DAO que falla si dos save() se solapan en el tiempo."""

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.saves = 0
        self.guard = threading.Lock()

    def load(self):
        return None

    def save(self, tables) -> None:
        with self.guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.005)
        with self.guard:
            self.active -= 1
            self.saves += 1


def test_concurrent_syncs_never_write_at_the_same_time():
    service = RoutingService(dao=FakeTopologyDAO(load_fixture_topology("F-20")), engine=BellmanFordEngine(),
                             presenter=CostPresenter())
    dao = _OverlapDetectingDAO()
    registry = tuple(RouterInfo(n, f"http://127.0.0.1:{8001 + i}") for i, n in enumerate("ABCD"))
    node = NodeForwardingService("C", registry, SpyTableClient(service), dao, None, FakeForwardingLogDAO())
    stop_flag = threading.Event()

    def flip_links():
        active = False
        while not stop_flag.is_set():
            service.set_link_status("B", "D", active)
            active = not active
            time.sleep(0.002)

    def sync_many():
        for _ in range(50):
            node.sync_if_changed()

    def handle_many():  # C→D es directo: no necesita vecinos
        for i in range(50):
            node.handle(Packet(f"p{i}", "C", "C", "", "delay"))

    workers = [threading.Thread(target=flip_links)] + [threading.Thread(target=f) for f in (sync_many, sync_many, handle_many)]
    for worker in workers:
        worker.start()
    for worker in workers[1:]:
        worker.join()
    stop_flag.set()
    workers[0].join()
    assert dao.saves > 1 and dao.max_active == 1
