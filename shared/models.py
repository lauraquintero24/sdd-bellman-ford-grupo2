"""Contratos de datos compartidos entre el Controller y el Router (02 §3.1).

Solo biblioteca estándar (02 §8).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    """Ruta elegida por el Controller; es el contrato que viaja al Router.

    ``total_cost`` es la cadena canónica de presentación (01 §5.3); nunca se usa
    para comparar rutas.
    """

    source: str
    destination: str
    metric: str
    path: tuple[str, ...]
    total_cost: str
    topology_version: int
