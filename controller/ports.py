"""Puerto (interfaz) del DAO de topología (02 §3.1, §5)."""

from abc import ABC, abstractmethod

from controller.models import LinkChangeResult, Topology


class TopologyDAO(ABC):
    @abstractmethod
    def get_topology(self) -> Topology:
        """Instantánea inmutable y consistente con su ``version``."""

    @abstractmethod
    def set_link_status(self, source: str, target: str, active: bool) -> LinkChangeResult:
        """Cambio atómico; ``version += 1`` solo si ``active`` cambia.

        Lanza ``NodeNotFoundError`` si un extremo no existe (se comprueba ``source`` primero)
        y ``LinkNotFoundError`` si no hay enlace.
        """
