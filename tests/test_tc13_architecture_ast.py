"""TC-13 (parte automática) — reglas de importación de 02 §8 y separación MVC (NFR-01, NFR-02, NFR-03).

Analiza el AST de cada módulo, incluidas las importaciones dentro de funciones. Las reglas
del Router se aplican a los módulos de ``router/`` que existan en el árbol.
La parte manual (06 §6) la completan y firman ambas estudiantes en test-results.txt.
"""

import ast
import inspect
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Prefijos de módulo prohibidos por archivo (02 §8). "open" = llamada a open() o E/S de pathlib.
FRAMEWORKS = ("fastapi", "starlette", "pydantic")
RULES = {
    "controller/models.py": FRAMEWORKS + ("networkx", "router", "controller.dao", "httpx", "open"),
    "controller/ports.py": FRAMEWORKS + ("networkx", "router", "controller.dao", "httpx", "open"),
    "controller/service.py": FRAMEWORKS + ("networkx", "router", "controller.dao", "httpx", "open"),
    "controller/engine.py": FRAMEWORKS + ("router", "controller.dao", "httpx", "open"),
    "controller/presenter.py": FRAMEWORKS + ("networkx", "router", "controller.dao", "httpx", "open"),
    # Los adaptadores HTTP pueden usar FastAPI (Starlette es su base) y Pydantic.
    "controller/http.py": ("controller.dao", "controller.engine", "networkx", "router", "httpx", "open"),
    "controller/http_errors.py": ("controller.dao", "controller.engine", "networkx", "router", "httpx", "open"),
    "controller/view.py": ("controller.dao", "controller.engine", "networkx", "router", "httpx", "open"),
    "controller/dao.py": FRAMEWORKS + ("networkx", "router", "httpx"),
    "controller/app.py": ("router",),
    "controller/main.py": ("router",),
    "controller/settings.py": FRAMEWORKS + ("networkx", "router", "httpx"),
    "router/models.py": FRAMEWORKS + ("networkx", "httpx", "controller", "router.dao", "router.client", "open"),
    "router/ports.py": FRAMEWORKS + ("networkx", "httpx", "controller", "router.dao", "router.client", "open"),
    "router/service.py": FRAMEWORKS + ("networkx", "httpx", "controller", "router.dao", "router.client", "open"),
    "router/http.py": ("router.dao", "router.client", "networkx", "controller", "httpx", "open"),
    "router/http_errors.py": ("router.dao", "router.client", "networkx", "controller", "httpx", "open"),
    "router/view.py": ("router.dao", "router.client", "networkx", "controller", "httpx", "open"),
    "router/dao.py": FRAMEWORKS + ("networkx", "httpx", "controller"),
    "router/client.py": FRAMEWORKS + ("networkx", "controller"),
    "router/app.py": ("controller", "networkx"),
    "router/main.py": ("controller", "networkx"),
    "router/settings.py": FRAMEWORKS + ("networkx", "httpx", "controller"),
}
PATHLIB_IO = {"read_text", "write_text", "read_bytes", "write_bytes", "open"}
CONCRETE = {"JsonTopologyDAO": {"controller/dao.py", "controller/app.py"},
            "JsonlForwardingLogDAO": {"router/dao.py", "router/app.py"},
            "HttpRouteClient": {"router/client.py", "router/app.py"}}
EXISTING = sorted(m for m in RULES if (ROOT / m).is_file())


def _tree(module: str) -> ast.Module:
    return ast.parse((ROOT / module).read_text(encoding="utf-8"))


def _imports(tree: ast.Module) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def _calls(tree: ast.Module) -> list[ast.Call]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call)]


@pytest.mark.parametrize("module", EXISTING)
def test_import_rules(module):
    tree = _tree(module)
    banned = [b for b in RULES[module] if b != "open"]
    violations = sorted(
        name for name in _imports(tree) for b in banned if name == b or name.startswith(b + ".")
    )
    assert not violations, f"{module} importa {violations}"
    if "open" in RULES[module]:
        opens = [c for c in _calls(tree) if isinstance(c.func, ast.Name) and c.func.id == "open"]
        io = [c for c in _calls(tree) if isinstance(c.func, ast.Attribute) and c.func.attr in PATHLIB_IO]
        assert not opens and not io, f"{module} hace E/S de archivos"


@pytest.mark.parametrize("module", [m for m in ("controller/http.py", "router/http.py") if m in EXISTING])
def test_http_handlers_have_no_loops(module):
    """Los handlers no contienen bucles de relajación ni de reenvío (NFR-03)."""
    loops = [n for n in ast.walk(_tree(module)) if isinstance(n, (ast.For, ast.While, ast.AsyncFor))]
    assert not loops, f"{module} contiene {len(loops)} bucles"


def test_networkx_only_in_engine():
    users = [m for m in EXISTING if any(n.split(".")[0] == "networkx" for n in _imports(_tree(m)))]
    assert users == ["controller/engine.py"]


def test_concrete_implementations_only_in_composition_roots():
    for module in EXISTING:
        for call in _calls(_tree(module)):
            name = call.func.id if isinstance(call.func, ast.Name) else None
            if name in CONCRETE:
                assert module in CONCRETE[name], f"{name} instanciado en {module}"


def test_services_require_all_dependencies():
    from controller.service import RoutingService

    params = list(inspect.signature(RoutingService.__init__).parameters.values())[1:]
    assert [p.name for p in params] == ["dao", "engine", "presenter"]
    assert all(p.default is inspect.Parameter.empty for p in params)
    if (ROOT / "router/service.py").is_file():
        from router.service import ForwardingService

        params = list(inspect.signature(ForwardingService.__init__).parameters.values())[1:]
        assert [p.name for p in params] == ["client", "log_dao"]
        assert all(p.default is inspect.Parameter.empty for p in params)
