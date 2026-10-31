"""Puertos (interfaces) del Router (02 §3.2, §5; DEC-05)."""

from abc import ABC, abstractmethod

from router.models import ForwardingResult, NodeTables
from shared.models import ForwardingTable, Route


class RouteClient(ABC):
    @abstractmethod
    def fetch_route(self, src: str, dst: str, metric: str) -> Route:
        """Ruta elegida por el Controller; los fallos se normalizan en subclases de ``AppError``."""


class ForwardingLogDAO(ABC):
    @abstractmethod
    def save(self, result: ForwardingResult) -> None:
        """Devuelve solo si la línea quedó escrita; los errores de E/S son ``LogPersistenceError``."""

    @abstractmethod
    def list_recent(self, limit: int) -> list[ForwardingResult]:
        """Los ``limit`` últimos resultados en orden de escritura."""


# --- Modo nodo (C-32, 02 §3.4) ---

class TableClient(ABC):
    @abstractmethod
    def fetch_topology_version(self) -> int:
        """Versión vigente de la topología en el Controller."""

    @abstractmethod
    def fetch_forwarding_table(self, router_id: str, metric: str) -> ForwardingTable:
        """Tabla calculada por el Controller; los fallos se normalizan en subclases de ``AppError``."""


class ForwardingTableDAO(ABC):
    @abstractmethod
    def load(self) -> NodeTables | None:
        """Última instantánea guardada, o ``None``."""

    @abstractmethod
    def save(self, tables: NodeTables) -> None:
        """Reemplaza la instantánea y anota el cambio; errores de E/S → ``LogPersistenceError``."""
