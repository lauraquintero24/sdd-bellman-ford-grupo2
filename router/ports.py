"""Puertos (interfaces) del Router (02 §3.2, §5; DEC-05)."""

from abc import ABC, abstractmethod

from router.models import ForwardingResult
from shared.models import Route


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
