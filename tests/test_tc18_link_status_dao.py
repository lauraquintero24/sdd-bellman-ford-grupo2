"""TC-18 (parte DAO) — idempotencia, versiones y errores de enlace (FR-06, DEC-01, DEC-02, DEC-04).

La consulta de ruta E-08 y la parte HTTP se prueban cuando existan el motor y la API (W-04/W-05).
"""

import shutil

import pytest

from controller.dao import JsonTopologyDAO
from shared.errors import LinkNotFoundError, NodeNotFoundError
from tests.fakes import FIXTURES_DIR


@pytest.fixture
def dao_for(tmp_path):
    def make(name):
        path = tmp_path / f"{name}.json"
        shutil.copy(FIXTURES_DIR / f"{name}.json", path)
        return JsonTopologyDAO(path), path

    return make


def _state(result):
    return (result.source, result.target, result.active, result.changed, result.topology_version)


def test_fail_and_restore_are_idempotent_with_versions(dao_for):
    dao, path = dao_for("F-01")
    original = path.read_bytes()
    assert _state(dao.set_link_status("B", "D", False)) == ("B", "D", False, True, 2)
    assert _state(dao.set_link_status("B", "D", False)) == ("B", "D", False, False, 2)
    assert _state(dao.set_link_status("B", "D", True)) == ("B", "D", True, True, 3)
    assert _state(dao.set_link_status("B", "D", True)) == ("B", "D", True, False, 3)
    assert path.read_bytes() == original  # el archivo fuente nunca se modifica


def test_link_errors_do_not_change_version(dao_for):
    dao, _ = dao_for("F-01")
    with pytest.raises(LinkNotFoundError) as info:
        dao.set_link_status("D", "B", False)  # dirigido: solo existe B->D
    assert info.value.code == "LINK_NOT_FOUND"
    with pytest.raises(NodeNotFoundError) as info:
        dao.set_link_status("A", "X", False)
    assert info.value.details == {"field": "target", "value": "X"}
    with pytest.raises(NodeNotFoundError) as info:
        dao.set_link_status("X", "Y", False)  # se comprueba source primero
    assert info.value.details == {"field": "source", "value": "X"}
    assert dao.get_topology().version == 1


def test_snapshots_are_immutable(dao_for):
    dao, _ = dao_for("F-01")
    before = dao.get_topology()
    dao.set_link_status("B", "D", False)
    after = dao.get_topology()
    assert before.version == 1 and before.find_link("B", "D").active
    assert after.version == 2 and not after.find_link("B", "D").active


def test_directed_links_are_independent(dao_for):
    dao, _ = dao_for("F-06")
    dao.set_link_status("A", "B", False)
    topology = dao.get_topology()
    assert not topology.find_link("A", "B").active
    assert topology.find_link("B", "A").active


def test_undirected_link_is_the_same_in_both_directions(dao_for):
    dao, _ = dao_for("F-11")
    assert _state(dao.set_link_status("A", "B", False)) == ("A", "B", False, True, 2)
    assert _state(dao.set_link_status("B", "A", False)) == ("B", "A", False, False, 2)


def test_restoring_p1_link_keeps_it_unusable(dao_for):
    dao, _ = dao_for("F-13")
    assert _state(dao.set_link_status("A", "B", True)) == ("A", "B", True, False, 1)
    assert not dao.get_topology().find_link("A", "B").is_usable()
