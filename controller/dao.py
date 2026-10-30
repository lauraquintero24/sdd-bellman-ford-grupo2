"""DAO concreto de la topología (02 §3.1, §5; 01 §4).

Lee el archivo JSON una sola vez, lo valida con las reglas TOPO-* y conserva el estado
mutable (``active`` y ``version``) en memoria; el archivo fuente nunca se modifica.

Las reglas se evalúan en el orden de la tabla de 01 §4 y se informa la primera violada.
Cada regla solo examina los valores de su tipo y deja los demás a ``TOPO-TYPE``; un
elemento de ``links`` o una raíz que no son objetos se informan como ``TOPO-TYPE``.
"""

import dataclasses
import json
import threading
from decimal import Decimal
from pathlib import Path

from controller.models import Link, LinkChangeResult, Topology
from controller.ports import TopologyDAO
from shared.errors import LinkNotFoundError, NodeNotFoundError

TOPOLOGY_KEYS = frozenset({"directed", "nodes", "links"})
LINK_KEYS = frozenset({"source", "target", "delay_ms", "bandwidth_mbps", "loss_probability", "active"})
NUMERIC_FIELDS = ("delay_ms", "bandwidth_mbps", "loss_probability")
MAX_SIGNIFICANT_DIGITS = 64
MAX_ABS_EXPONENT = 1000


class TopologyLoadError(Exception):
    """La topología viola 01 §4: el proceso no arranca. Nunca se traduce a HTTP."""

    def __init__(self, rule: str, detail: str) -> None:
        super().__init__(f"{rule}: {detail}")
        self.rule = rule
        self.detail = detail


class _InvalidJson(ValueError):
    pass


def _reject_constant(name: str):
    raise _InvalidJson(f"constante no permitida: {name}")


def _reject_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise _InvalidJson(f"clave duplicada: {key!r}")
        obj[key] = value
    return obj


def _parse_json(raw: bytes):
    """JSON -> objetos Python; todo número se lee como ``Decimal`` desde su texto (DEC-09)."""
    try:
        return json.loads(
            raw.decode("utf-8"),
            parse_float=Decimal,
            parse_int=Decimal,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise TopologyLoadError("TOPO-JSON", f"el archivo no es JSON válido ({exc})") from None


def _is_member(value, nodes: list) -> bool:
    return any(type(value) is type(node) and value == node for node in nodes)


def _validate(doc) -> None:
    root = doc if isinstance(doc, dict) else None
    nodes = root.get("nodes") if root is not None else None
    links = root.get("links") if root is not None else None
    node_list = nodes if isinstance(nodes, list) else []
    link_objs = [link for link in links if isinstance(link, dict)] if isinstance(links, list) else []

    # TOPO-KEYS
    if root is not None and set(root) != TOPOLOGY_KEYS:
        missing, unknown = sorted(TOPOLOGY_KEYS - set(root)), sorted(set(root) - TOPOLOGY_KEYS)
        raise TopologyLoadError("TOPO-KEYS", f"topología: faltan {missing}, desconocidas {unknown}")
    for index, link in enumerate(link_objs):
        if set(link) != LINK_KEYS:
            missing, unknown = sorted(LINK_KEYS - set(link)), sorted(set(link) - LINK_KEYS)
            raise TopologyLoadError("TOPO-KEYS", f"enlace {index}: faltan {missing}, desconocidas {unknown}")

    # TOPO-NODES
    if isinstance(nodes, list):
        if not nodes:
            raise TopologyLoadError("TOPO-NODES", "la lista 'nodes' está vacía")
        for node in nodes:
            if isinstance(node, str) and (node == "" or node != node.strip()):
                raise TopologyLoadError("TOPO-NODES", f"ID de nodo vacío o con espacios en los extremos: {node!r}")

    # TOPO-DUP-NODE
    seen: list = []
    for node in node_list:
        if _is_member(node, seen):
            raise TopologyLoadError("TOPO-DUP-NODE", f"ID de nodo repetido: {node!r}")
        seen.append(node)

    # TOPO-ENDPOINT
    for link in link_objs:
        for end in ("source", "target"):
            if not _is_member(link[end], node_list):
                raise TopologyLoadError("TOPO-ENDPOINT", f"{end} {link[end]!r} no existe en 'nodes'")

    # TOPO-SELF-LOOP
    for link in link_objs:
        if _is_member(link["source"], [link["target"]]):
            raise TopologyLoadError("TOPO-SELF-LOOP", f"lazo {link['source']!r} -> {link['target']!r}")

    # TOPO-PARALLEL (un 'directed' no booleano se trata como dirigido; lo rechaza TOPO-TYPE)
    directed = root.get("directed") if root is not None else None
    undirected = directed is False
    pairs: set = set()
    for link in link_objs:
        source, target = link["source"], link["target"]
        try:
            pair = frozenset((source, target)) if undirected else (source, target)
            duplicate = pair in pairs
        except TypeError:  # extremos no hashables: los rechaza TOPO-TYPE
            continue
        if duplicate:
            mode = "no dirigido" if undirected else "dirigido"
            raise TopologyLoadError("TOPO-PARALLEL", f"enlace paralelo ({mode}): {source!r} -> {target!r}")
        pairs.add(pair)

    # TOPO-TYPE
    if root is None:
        raise TopologyLoadError("TOPO-TYPE", "la raíz debe ser un objeto JSON")
    if not isinstance(directed, bool):
        raise TopologyLoadError("TOPO-TYPE", "'directed' debe ser booleano")
    if not isinstance(nodes, list):
        raise TopologyLoadError("TOPO-TYPE", "'nodes' debe ser una lista")
    if not isinstance(links, list):
        raise TopologyLoadError("TOPO-TYPE", "'links' debe ser una lista")
    for node in nodes:
        if not isinstance(node, str):
            raise TopologyLoadError("TOPO-TYPE", f"ID de nodo no textual: {node!r}")
    for index, link in enumerate(links):
        if not isinstance(link, dict):
            raise TopologyLoadError("TOPO-TYPE", f"enlace {index}: debe ser un objeto")
        for end in ("source", "target"):
            if not isinstance(link[end], str):
                raise TopologyLoadError("TOPO-TYPE", f"enlace {index}: '{end}' debe ser texto")
        if not isinstance(link["active"], bool):
            raise TopologyLoadError("TOPO-TYPE", f"enlace {index}: 'active' debe ser booleano")
        for field in NUMERIC_FIELDS:
            if not isinstance(link[field], Decimal):
                raise TopologyLoadError("TOPO-TYPE", f"enlace {index}: '{field}' debe ser un número JSON")

    # TOPO-RANGE
    for index, link in enumerate(links):
        if link["delay_ms"] < 0:
            raise TopologyLoadError("TOPO-RANGE", f"enlace {index}: delay_ms < 0")
        if link["bandwidth_mbps"] <= 0:
            raise TopologyLoadError("TOPO-RANGE", f"enlace {index}: bandwidth_mbps <= 0")
        if not 0 <= link["loss_probability"] <= 1:
            raise TopologyLoadError("TOPO-RANGE", f"enlace {index}: loss_probability fuera de [0, 1]")

    # TOPO-DOMAIN
    for index, link in enumerate(links):
        for field in NUMERIC_FIELDS:
            value: Decimal = link[field]
            if len(value.as_tuple().digits) > MAX_SIGNIFICANT_DIGITS:
                raise TopologyLoadError("TOPO-DOMAIN", f"enlace {index}: '{field}' tiene más de 64 cifras significativas")
            if not -MAX_ABS_EXPONENT <= value.adjusted() <= MAX_ABS_EXPONENT:
                raise TopologyLoadError("TOPO-DOMAIN", f"enlace {index}: '{field}' tiene exponente fuera de [-1000, 1000]")


def _build_topology(doc: dict) -> Topology:
    links = tuple(
        Link(
            source=link["source"],
            target=link["target"],
            delay_ms=link["delay_ms"],
            bandwidth_mbps=link["bandwidth_mbps"],
            loss_probability=link["loss_probability"],
            active=link["active"],
        )
        for link in doc["links"]
    )
    return Topology(directed=doc["directed"], version=1, nodes=tuple(doc["nodes"]), links=links)


class JsonTopologyDAO(TopologyDAO):
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        try:
            raw = self._path.read_bytes()
        except OSError as exc:
            raise TopologyLoadError("TOPO-JSON", f"no se pudo leer el archivo ({exc.strerror})") from None
        doc = _parse_json(raw)
        _validate(doc)
        self._state = _build_topology(doc)

    def get_topology(self) -> Topology:
        with self._lock:
            return self._state

    def set_link_status(self, source: str, target: str, active: bool) -> LinkChangeResult:
        with self._lock:
            state = self._state
            for field, value in (("source", source), ("target", target)):
                if not state.has_node(value):
                    raise NodeNotFoundError(f"El nodo {value} no existe en la topología.", {"field": field, "value": value})
            link = state.find_link(source, target)
            if link is None:
                raise LinkNotFoundError(
                    f"No existe el enlace {source} -> {target}.", {"source": source, "target": target}
                )
            changed = link.active != active
            if changed:
                links = tuple(dataclasses.replace(item, active=active) if item is link else item for item in state.links)
                state = dataclasses.replace(state, links=links, version=state.version + 1)
                self._state = state
            return LinkChangeResult(
                source=source, target=target, active=active, changed=changed, topology_version=state.version
            )
