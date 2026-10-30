"""TC-09 — ForwardingService usa su DAO de bitácora y se prueba de forma independiente
(FR-10, NFR-02, NFR-07, NFR-09). Sin servidores ni disco; cero llamadas HTTP."""

import builtins
import io
import socket

import pytest

from router.models import Packet, TraceHop
from router.service import ForwardingService
from shared.errors import ControllerUnavailableError, LogPersistenceError
from shared.models import Route
from tests.fakes import FakeForwardingLogDAO, FakeRouteClient

ROUTE = Route(source="A", destination="D", metric="delay", path=("A", "B", "D"), total_cost="2", topology_version=1)


def _packet(packet_id):
    return Packet(packet_id=packet_id, source="A", destination="D", payload="", metric="delay")


def _forbid(*_args, **_kwargs):
    raise AssertionError("E/S prohibida en TC-09")


@pytest.fixture(autouse=True)
def no_io(monkeypatch):
    monkeypatch.setattr(builtins, "open", _forbid)
    monkeypatch.setattr(io, "open", _forbid)
    monkeypatch.setattr(socket, "socket", _forbid)


def test_tc09_forwarded_failed_and_log_failure():
    log_dao = FakeForwardingLogDAO()

    # 1. Reenvío exitoso
    client = FakeRouteClient(ROUTE)
    result = ForwardingService(client=client, log_dao=log_dao).forward(_packet("pkt-1"))
    assert result.status == "forwarded"
    assert result.trace == (TraceHop(0, "A"), TraceHop(1, "B"), TraceHop(2, "D"))
    assert result.route is ROUTE and result.topology_version == 1 and result.error is None
    assert log_dao.saved == [result]

    # 2. Cliente que lanza ControllerUnavailableError
    failing = FakeRouteClient(error=ControllerUnavailableError("No fue posible conectar con el Controller."))
    with pytest.raises(ControllerUnavailableError):
        ForwardingService(client=failing, log_dao=log_dao).forward(_packet("pkt-2"))
    assert len(log_dao.saved) == 2
    failed = log_dao.saved[1]
    assert (failed.packet_id, failed.source, failed.destination, failed.metric) == ("pkt-2", "A", "D", "delay")
    assert (failed.status, failed.trace, failed.route, failed.topology_version) == ("failed", (), None, None)
    assert failed.error["code"] == "CONTROLLER_UNAVAILABLE"

    # 3. DAO cuyo save lanza OSError
    broken = FakeForwardingLogDAO(fail_with=OSError("disco lleno"))
    with pytest.raises(LogPersistenceError) as info:
        ForwardingService(client=FakeRouteClient(ROUTE), log_dao=broken).forward(_packet("pkt-3"))
    assert info.value.code == "LOG_PERSISTENCE_ERROR"
    assert broken.save_calls == 1 and broken.saved == []


def test_log_failure_prevails_over_client_error():
    broken = FakeForwardingLogDAO(fail_with=OSError("disco lleno"))
    failing = FakeRouteClient(error=ControllerUnavailableError("x"))
    with pytest.raises(LogPersistenceError):
        ForwardingService(client=failing, log_dao=broken).forward(_packet("pkt-4"))


def test_unexpected_client_exception_is_logged_as_internal_error():
    log_dao = FakeForwardingLogDAO()
    with pytest.raises(RuntimeError):
        ForwardingService(client=FakeRouteClient(error=RuntimeError("boom")), log_dao=log_dao).forward(_packet("p"))
    assert log_dao.saved[0].error == {"code": "INTERNAL_ERROR", "message": "Error interno del Router.", "details": {}}


def test_constructor_requires_all_dependencies():
    with pytest.raises(TypeError):
        ForwardingService()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        ForwardingService(client=FakeRouteClient(ROUTE))  # type: ignore[call-arg]


def test_exactly_one_fetch_per_packet():
    client = FakeRouteClient(ROUTE)
    service = ForwardingService(client=client, log_dao=FakeForwardingLogDAO())
    service.forward(_packet("a"))
    service.forward(_packet("b"))
    assert client.calls == [("A", "D", "delay"), ("A", "D", "delay")]  # sin caché (DEC-06)
