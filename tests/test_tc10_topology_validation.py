"""TC-10 — Validación de la topología al cargar (FR-01, FR-04; 01 §4).

Parte DAO: cada variante inválida de F-01 lanza TopologyLoadError con su regla.
La parte «el proceso no abre el puerto» se comprueba con controller.main (W-05/G5).
"""

import copy
import json
from decimal import Decimal

import pytest

import controller.dao as dao_module
from controller.dao import JsonTopologyDAO, TopologyLoadError
from tests.fakes import FIXTURES_DIR

F01 = json.loads((FIXTURES_DIR / "F-01.json").read_text(encoding="utf-8"))


def _write(tmp_path, doc=None, text=None):
    path = tmp_path / "topology.json"
    path.write_text(text if text is not None else json.dumps(doc), encoding="utf-8")
    return path


def _variant(mutate):
    doc = copy.deepcopy(F01)
    mutate(doc)
    return doc


def _set_link(index, field, value):
    return lambda doc: doc["links"][index].__setitem__(field, value)


F01_TEXT = (FIXTURES_DIR / "F-01.json").read_text(encoding="utf-8")

TEXT_CASES = [
    ("ilegible", '{"directed": true,', "TOPO-JSON"),
    ("nan", F01_TEXT.replace('"loss_probability": 0.01', '"loss_probability": NaN', 1), "TOPO-JSON"),
    ("infinity", F01_TEXT.replace('"delay_ms": 1.0', '"delay_ms": Infinity', 1), "TOPO-JSON"),
    ("clave-duplicada", F01_TEXT.replace('"directed": true', '"directed": true, "directed": true', 1), "TOPO-JSON"),
    ("utf8-invalido", None, "TOPO-JSON"),
    ("65-cifras", F01_TEXT.replace('"delay_ms": 1.0', '"delay_ms": 1.' + "1" * 64, 1), "TOPO-DOMAIN"),
    ("exponente-1001", F01_TEXT.replace('"delay_ms": 1.0', '"delay_ms": 1e1001', 1), "TOPO-DOMAIN"),
    ("exponente-menos-1001", F01_TEXT.replace('"delay_ms": 1.0', '"delay_ms": 1e-1001', 1), "TOPO-DOMAIN"),
]

DOC_CASES = [
    ("clave-desconocida", _variant(lambda d: d.__setitem__("x", 1)), "TOPO-KEYS"),
    ("falta-clave", _variant(lambda d: d.pop("links")), "TOPO-KEYS"),
    ("clave-desconocida-enlace", _variant(_set_link(0, "cost", 1)), "TOPO-KEYS"),
    ("falta-clave-enlace", _variant(lambda d: d["links"][0].pop("active")), "TOPO-KEYS"),
    ("nodes-vacio", _variant(lambda d: d.__setitem__("nodes", [])), "TOPO-NODES"),
    ("id-con-espacios", _variant(lambda d: d["nodes"].__setitem__(0, " A")), "TOPO-NODES"),
    ("id-vacio", _variant(lambda d: d["nodes"].append("")), "TOPO-NODES"),
    ("id-repetido", _variant(lambda d: d["nodes"].append("A")), "TOPO-DUP-NODE"),
    ("extremo-inexistente", _variant(_set_link(0, "target", "X")), "TOPO-ENDPOINT"),
    ("lazo", _variant(_set_link(0, "target", "A")), "TOPO-SELF-LOOP"),
    ("paralelo-dirigido", _variant(lambda d: d["links"].append(dict(d["links"][0]))), "TOPO-PARALLEL"),
    (
        "paralelo-no-dirigido",
        _variant(lambda d: (d.__setitem__("directed", False), d["links"].append({**d["links"][0], "source": "B", "target": "A"}))),
        "TOPO-PARALLEL",
    ),
    ("numero-como-cadena", _variant(_set_link(0, "delay_ms", "1.0")), "TOPO-TYPE"),
    ("cadena-fuera-de-rango", _variant(_set_link(0, "delay_ms", "-1")), "TOPO-TYPE"),
    ("numero-como-booleano", _variant(_set_link(0, "bandwidth_mbps", True)), "TOPO-TYPE"),
    ("directed-no-booleano", _variant(lambda d: d.__setitem__("directed", 1)), "TOPO-TYPE"),
    ("active-no-booleano", _variant(_set_link(0, "active", "true")), "TOPO-TYPE"),
    ("links-no-lista", _variant(lambda d: d.__setitem__("links", {})), "TOPO-TYPE"),
    ("enlace-no-objeto", _variant(lambda d: d["links"].append(5)), "TOPO-TYPE"),
    ("raiz-no-objeto", [1, 2], "TOPO-TYPE"),
    ("delay-negativo", _variant(_set_link(0, "delay_ms", -1)), "TOPO-RANGE"),
    ("bandwidth-cero", _variant(_set_link(0, "bandwidth_mbps", 0)), "TOPO-RANGE"),
    ("loss-1.5", _variant(_set_link(0, "loss_probability", 1.5)), "TOPO-RANGE"),
    ("loss-menos-0.1", _variant(_set_link(0, "loss_probability", -0.1)), "TOPO-RANGE"),
]


@pytest.mark.parametrize("text, rule", [(t, r) for _, t, r in TEXT_CASES], ids=[c[0] for c in TEXT_CASES])
def test_invalid_text_variants(tmp_path, text, rule):
    if text is None:
        path = tmp_path / "topology.json"
        path.write_bytes(b'{"directed": true, "nodes": ["\xff"], "links": []}')
    else:
        path = _write(tmp_path, text=text)
    with pytest.raises(TopologyLoadError) as info:
        JsonTopologyDAO(path)
    assert info.value.rule == rule


@pytest.mark.parametrize("doc, rule", [(d, r) for _, d, r in DOC_CASES], ids=[c[0] for c in DOC_CASES])
def test_invalid_document_variants(tmp_path, doc, rule):
    with pytest.raises(TopologyLoadError) as info:
        JsonTopologyDAO(_write(tmp_path, doc))
    assert info.value.rule == rule


def test_missing_file_is_a_load_error(tmp_path):
    with pytest.raises(TopologyLoadError):
        JsonTopologyDAO(tmp_path / "no-existe.json")


@pytest.mark.parametrize("path", sorted(FIXTURES_DIR.glob("*.json")), ids=lambda p: p.stem)
def test_all_fixtures_load(path):
    topology = JsonTopologyDAO(path).get_topology()
    assert topology.version == 1
    assert len(topology.nodes) >= 1


def test_f13_with_p_equal_1_loads_and_link_is_unusable():
    topology = JsonTopologyDAO(FIXTURES_DIR / "F-13.json").get_topology()
    link = topology.find_link("A", "B")
    assert link.loss_probability == 1 and link.active and not link.is_usable()


def test_f01_loaded_as_in_file():
    topology = JsonTopologyDAO(FIXTURES_DIR / "F-01.json").get_topology()
    assert topology.directed is True
    assert topology.nodes == ("A", "B", "C", "D")
    assert [(l.source, l.target) for l in topology.links] == [("A", "B"), ("B", "D"), ("A", "C"), ("C", "D")]
    assert all(l.active for l in topology.links)


def test_numbers_are_read_as_exact_decimals_never_float(monkeypatch):
    calls = []
    real_loads = dao_module.json.loads

    def spy_loads(*args, **kwargs):
        calls.append(kwargs)
        return real_loads(*args, **kwargs)

    monkeypatch.setattr(dao_module.json, "loads", spy_loads)
    f01 = JsonTopologyDAO(FIXTURES_DIR / "F-01.json").get_topology()
    f18 = JsonTopologyDAO(FIXTURES_DIR / "F-18.json").get_topology()
    f08 = JsonTopologyDAO(FIXTURES_DIR / "F-08.json").get_topology()

    assert calls and all(kw.get("parse_float") is Decimal and kw.get("parse_int") is Decimal for kw in calls)
    first = f01.links[0]
    assert str(first.delay_ms) == "1.0" and str(first.loss_probability) == "0.01"
    for topology in (f01, f18, f08):
        for link in topology.links:
            assert all(type(getattr(link, f)) is Decimal for f in ("delay_ms", "bandwidth_mbps", "loss_probability"))
    assert f18.find_link("A", "D").loss_probability == Decimal("1e-60")
    assert f08.find_link("A", "B").delay_ms == Decimal("0.1")
