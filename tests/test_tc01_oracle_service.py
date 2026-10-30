"""TC-01 a TC-04, TC-17 a TC-30, TC-36 a TC-39 (nivel servicio): las 48 filas del oráculo de 06 §3.

Cada fila usa un fixture nuevo (copia temporal) cargado por JsonTopologyDAO, y RoutingService
con el motor y el presentador reales; sin HTTP. La misma tabla se ejecuta por HTTP en W-05.
"""

import shutil

import pytest

from controller.dao import JsonTopologyDAO
from controller.engine import BellmanFordEngine
from controller.presenter import CostPresenter
from controller.service import RoutingService
from shared.errors import AppError
from tests.fakes import FIXTURES_DIR
from tests.oracle import IDS, ROWS, assert_cost


@pytest.mark.parametrize("case, tc, fixture, ops, src, dst, metric, expected, version", ROWS, ids=IDS)
def test_oracle_row(tmp_path, case, tc, fixture, ops, src, dst, metric, expected, version):
    path = tmp_path / f"{fixture}.json"
    shutil.copy(FIXTURES_DIR / f"{fixture}.json", path)
    service = RoutingService(dao=JsonTopologyDAO(path), engine=BellmanFordEngine(), presenter=CostPresenter())
    for action, source, target in ops:
        service.set_link_status(source, target, action == "restore")

    if expected[0] == "ok":
        _, exp_path, exp_cost = expected
        route = service.compute_route(src, dst, metric)
        assert (route.source, route.destination, route.metric) == (src, dst, metric)
        assert list(route.path) == exp_path
        assert route.topology_version == version
        assert_cost(metric, route.total_cost, exp_cost, service.read_topology(), route.path)
    else:
        with pytest.raises(AppError) as info:
            service.compute_route(src, dst, metric)
        assert info.value.code == expected[1]
        assert service.read_topology().version == version
