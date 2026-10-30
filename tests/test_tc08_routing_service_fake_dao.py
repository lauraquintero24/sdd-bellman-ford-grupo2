"""TC-08 — RoutingService funciona con un TopologyDAO falso y sin servidor HTTP (NFR-02, NFR-07, NFR-09).

Además, pruebas unitarias de la inyección de dependencias de RoutingService con un motor
de sustitución (W-03), independientes del motor real.
"""

import builtins
import io
import socket
from fractions import Fraction
from typing import NamedTuple

import pytest

from controller.service import RoutingService
from shared.errors import InvalidRequestError, LinkNotFoundError, NodeNotFoundError
from tests.fakes import FakeTopologyDAO, SpyCostPresenter, load_fixture_topology


def _forbid(*_args, **_kwargs):
    raise AssertionError("E/S prohibida en TC-08")


@pytest.fixture
def no_io_ready(monkeypatch):
    # Se importa el motor y se carga el fixture antes de prohibir la E/S.
    from controller.engine import BellmanFordEngine
    from controller.presenter import CostPresenter

    fake_dao = FakeTopologyDAO(topology=load_fixture_topology("F-01"))
    monkeypatch.setattr(builtins, "open", _forbid)
    monkeypatch.setattr(io, "open", _forbid)
    monkeypatch.setattr(socket, "socket", _forbid)
    return BellmanFordEngine, CostPresenter, fake_dao


def test_tc08_routing_service_with_fake_dao(no_io_ready):
    BellmanFordEngine, CostPresenter, fake_dao = no_io_ready
    service = RoutingService(dao=fake_dao, engine=BellmanFordEngine(), presenter=CostPresenter())

    first = service.compute_route(src="A", dst="D", metric="delay")
    service.set_link_status(source="B", target="D", active=False)
    second = service.compute_route(src="A", dst="D", metric="delay")

    assert (first.path, first.total_cost, first.topology_version) == (("A", "B", "D"), "2", 1)
    assert (second.path, second.total_cost, second.topology_version) == (("A", "C", "D"), "4", 2)
    assert fake_dao.get_topology_calls == 2
    assert fake_dao.set_link_status_calls == 1


def test_tc08_spy_presenter_called_once_per_query(no_io_ready):
    BellmanFordEngine, _, fake_dao = no_io_ready
    spy = SpyCostPresenter()
    service = RoutingService(dao=fake_dao, engine=BellmanFordEngine(), presenter=spy)

    service.compute_route(src="A", dst="D", metric="delay")
    service.set_link_status(source="B", target="D", active=False)
    service.compute_route(src="A", dst="D", metric="delay")

    assert spy.calls == [(Fraction(2), "delay"), (Fraction(4), "delay")]


# --- W-03: inyección de dependencias de RoutingService con un motor de sustitución ---

class _Score(NamedTuple):
    path: tuple
    score: Fraction


class _StubEngine:
    def __init__(self):
        self.calls = []

    def find_path(self, topology, src, dst, metric):
        self.calls.append((topology.version, src, dst, metric))
        return _Score((src, dst), Fraction(7, 2))


@pytest.fixture
def parts():
    dao = FakeTopologyDAO(topology=load_fixture_topology("F-01"))
    engine, presenter = _StubEngine(), SpyCostPresenter(result="3.5")
    return dao, engine, presenter, RoutingService(dao=dao, engine=engine, presenter=presenter)


def test_constructor_requires_all_dependencies():
    with pytest.raises(TypeError):
        RoutingService()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        RoutingService(dao=FakeTopologyDAO(load_fixture_topology("F-01")))  # type: ignore[call-arg]


def test_compute_route_builds_route_from_one_snapshot(parts):
    dao, engine, presenter, service = parts
    route = service.compute_route("A", "D", "loss")
    assert route.source == "A" and route.destination == "D" and route.metric == "loss"
    assert route.path == ("A", "D") and route.total_cost == "3.5" and route.topology_version == 1
    assert dao.get_topology_calls == 1
    assert engine.calls == [(1, "A", "D", "loss")]
    assert presenter.calls == [(Fraction(7, 2), "loss")]


def test_invalid_metric_is_rejected_before_reading_dao(parts):
    dao, engine, _, service = parts
    with pytest.raises(InvalidRequestError) as info:
        service.compute_route("A", "D", "hops")
    assert info.value.code == "INVALID_REQUEST"
    assert dao.get_topology_calls == 0 and engine.calls == []


@pytest.mark.parametrize("src, dst, field, value", [("X", "D", "src", "X"), ("X", "Y", "src", "X"), ("A", "Y", "dst", "Y")])
def test_node_not_found_checks_src_first(parts, src, dst, field, value):
    _, engine, _, service = parts
    with pytest.raises(NodeNotFoundError) as info:
        service.compute_route(src, dst, "delay")
    assert info.value.details == {"field": field, "value": value}
    assert engine.calls == []


def test_read_topology_and_set_link_status_delegate_to_dao(parts):
    dao, _, _, service = parts
    assert service.read_topology() is dao.topology
    result = service.set_link_status("B", "D", False)
    assert (result.active, result.changed, result.topology_version) == (False, True, 2)
    with pytest.raises(LinkNotFoundError):
        service.set_link_status("D", "A", False)
