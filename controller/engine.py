"""Motor de rutas del Controller: Bellman-Ford exacto (02 §6; 01 §5; DEC-07, DEC-08, DEC-09).

NetworkX se usa solo como estructura de grafo; la ruta la elige el núcleo de relajación
propio, no ``nx.bellman_ford_path`` (02 §6.1, «Por qué no se usa directamente»).
No se usa ``float``: los pesos son ``Fraction`` exactos.
"""

from dataclasses import dataclass
from fractions import Fraction

import networkx as nx

from controller.models import Link, Topology
from shared.errors import InvalidRequestError, NegativeCycleError, RouteUnreachableError

ADDITIVE = "additive"
PRODUCT = "product"
METRIC_MODES = {"delay": ADDITIVE, "inverse_bandwidth": ADDITIVE, "loss": PRODUCT}


@dataclass(frozen=True)
class RouteLabel:
    """Mejor caminata conocida hacia un nodo: puntuación exacta, saltos y ruta."""

    score: Fraction
    hops: int
    path: tuple[str, ...]


@dataclass(frozen=True)
class PathScore:
    path: tuple[str, ...]
    score: Fraction


class LinkCostPolicy:
    """Peso exacto de un enlace (01 §5.1): ``d``, ``1/b`` o el factor de supervivencia ``1 − p``."""

    def weight(self, link: Link, metric: str) -> Fraction:
        if metric == "delay":
            return Fraction(link.delay_ms)
        if metric == "inverse_bandwidth":
            return 1 / Fraction(link.bandwidth_mbps)
        if metric == "loss":
            return 1 - Fraction(link.loss_probability)
        raise InvalidRequestError(f"La métrica {metric} no está admitida.", {"fields": ["metric"]})


class BellmanFordEngine:
    def __init__(self) -> None:
        self._policy = LinkCostPolicy()

    def find_path(self, topology: Topology, src: str, dst: str, metric: str) -> PathScore:
        mode = METRIC_MODES.get(metric)
        if mode is None:
            raise InvalidRequestError(f"La métrica {metric} no está admitida.", {"fields": ["metric"]})
        if src == dst:
            return PathScore(path=(src,), score=Fraction(0) if mode == ADDITIVE else Fraction(1))

        graph = nx.DiGraph() if topology.directed else nx.Graph()
        graph.add_nodes_from(topology.nodes)
        for link in topology.links:
            if link.is_usable():
                graph.add_edge(link.source, link.target, weight=self._policy.weight(link, metric))

        labels = self.run_bellman_ford_on_weighted_graph(graph, src, mode)
        label = labels.get(dst)
        if label is None:
            raise RouteUnreachableError(
                f"No existe una ruta utilizable de {src} a {dst}.",
                {"source": src, "destination": dst, "metric": metric},
            )
        return PathScore(path=label.path, score=label.score)

    def run_bellman_ford_on_weighted_graph(self, graph: nx.Graph, src: str, mode: str) -> dict[str, RouteLabel]:
        """Núcleo común de relajación, desempate DEC-08 y detección de ciclo negativo (02 §6.2).

        Rondas síncronas: cada ronda solo extiende etiquetas de la ronda anterior, de modo
        que el resultado no depende del orden de los arcos.
        """
        if mode not in (ADDITIVE, PRODUCT):
            raise ValueError(f"modo desconocido: {mode}")
        additive = mode == ADDITIVE
        arcs = [(u, v, data["weight"]) for u, v, data in graph.edges(data=True)]
        if not graph.is_directed():
            arcs += [(v, u, weight) for u, v, weight in arcs]

        label = {src: RouteLabel(score=Fraction(0) if additive else Fraction(1), hops=0, path=(src,))}
        for _ in range(graph.number_of_nodes() - 1):
            new = dict(label)
            changed = False
            for u, v, weight in arcs:
                current = label.get(u)
                if current is None:
                    continue
                score = current.score + weight if additive else current.score * weight
                hops = current.hops + 1
                best = new.get(v)
                if best is not None and not _better(additive, score, hops, current.path, v, best):
                    continue
                new[v] = RouteLabel(score=score, hops=hops, path=current.path + (v,))
                changed = True
            if not changed:
                break
            label = new

        # Pasada de detección (ambos modos): solo compara la magnitud primaria.
        for u, v, weight in arcs:
            current = label.get(u)
            target = label.get(v)
            if current is None or target is None:  # target siempre existe si current existe (02 §6.2)
                continue
            score = current.score + weight if additive else current.score * weight
            if (score < target.score) if additive else (score > target.score):
                raise NegativeCycleError(
                    f"Se detectó un ciclo negativo alcanzable desde {src}.", {"source": src}
                )
        return label


def _better(additive: bool, score: Fraction, hops: int, prefix: tuple[str, ...], node: str, best: RouteLabel) -> bool:
    """``clave(candidato) < clave(best)`` con clave = (score, hops, path) o (−score, hops, path).

    La ruta del candidato (``prefix + (node,)``) solo se construye si hay empate en lo demás.
    """
    if score != best.score:
        return score < best.score if additive else score > best.score
    if hops != best.hops:
        return hops < best.hops
    return prefix + (node,) < best.path
