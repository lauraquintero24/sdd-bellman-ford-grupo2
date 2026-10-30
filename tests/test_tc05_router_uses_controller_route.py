"""TC-05 — El Router obtiene la ruta por HTTP en lugar de calcularla (FR-07, DEC-06).

1. Espía que devuelve una ruta NO óptima de F-01 ([A, C, D]): el Router la usa sin recalcular.
2. AST: ningún módulo de router/ importa networkx ni controller.
3. La parte con procesos reales (un GET /route por paquete en el registro de accesos) va en G5.
"""

import ast
from pathlib import Path

import pytest

from router.models import Packet, TraceHop
from router.service import ForwardingService
from shared.models import Route
from tests.fakes import FakeForwardingLogDAO, SpyRouteClient

ROUTER_DIR = Path(__file__).resolve().parent.parent / "router"


def test_tc05_router_uses_route_from_spy_without_recalculating():
    spy = SpyRouteClient(Route("A", "D", "delay", ("A", "C", "D"), "4", 1))
    service = ForwardingService(client=spy, log_dao=FakeForwardingLogDAO())
    result = service.forward(Packet(packet_id="pkt-1", source="A", destination="D", payload="", metric="delay"))
    assert spy.calls == [("A", "D", "delay")]
    assert result.trace == (TraceHop(0, "A"), TraceHop(1, "C"), TraceHop(2, "D"))
    assert result.route.path == ("A", "C", "D") and result.route.total_cost == "4"


@pytest.mark.parametrize("path", sorted(ROUTER_DIR.glob("*.py")), ids=lambda p: p.name)
def test_tc05_router_modules_do_not_import_networkx_or_controller(path):
    imported = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {"networkx", "controller"}, f"{path.name}: {imported & {'networkx', 'controller'}}"
