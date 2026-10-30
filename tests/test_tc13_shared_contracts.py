"""TC-13 (parte shared/): shared solo importa la biblioteca estándar (02 §8) y
contratos de Route y AppError (02 §3.1, §3.3; 04 §1, §5)."""

import ast
import dataclasses
import sys
from pathlib import Path

import pytest

from shared.errors import (
    AppError,
    InvalidRequestError,
    LinkNotFoundError,
    NegativeCycleError,
    NodeNotFoundError,
    RouteUnreachableError,
)
from shared.models import Route

SHARED_DIR = Path(__file__).resolve().parent.parent / "shared"


def _imported_top_modules(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("path", sorted(SHARED_DIR.glob("*.py")), ids=lambda p: p.name)
def test_shared_imports_only_stdlib(path):
    forbidden = _imported_top_modules(path) - set(sys.stdlib_module_names)
    assert not forbidden, f"{path.name} importa módulos no estándar: {forbidden}"


def test_route_is_immutable():
    route = Route(source="A", destination="D", metric="delay", path=("A", "B", "D"), total_cost="2", topology_version=1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        route.total_cost = "3"  # type: ignore[misc]


@pytest.mark.parametrize(
    "cls, code",
    [
        (InvalidRequestError, "INVALID_REQUEST"),
        (NodeNotFoundError, "NODE_NOT_FOUND"),
        (LinkNotFoundError, "LINK_NOT_FOUND"),
        (RouteUnreachableError, "ROUTE_UNREACHABLE"),
        (NegativeCycleError, "NEGATIVE_CYCLE"),
    ],
)
def test_controller_error_codes(cls, code):
    err = cls("mensaje", {"field": "src", "value": "X"})
    assert isinstance(err, AppError)
    assert err.to_dict() == {"code": code, "message": "mensaje", "details": {"field": "src", "value": "X"}}
    assert not hasattr(err, "status_code")


def test_details_default_to_empty_dict():
    assert NodeNotFoundError("m").to_dict()["details"] == {}
