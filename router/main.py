"""Punto de entrada del Router:
``python -m router.main [--host] [--port] [--controller-url] [--log-file] [--connect-timeout] [--read-timeout]``.

Una configuración inválida impide el arranque con un diagnóstico (02 §7, TC-14).
"""

import sys

import uvicorn

from router.app import create_router_app
from router.settings import load_router_settings
from shared.errors import LogPersistenceError


def main(argv: list[str] | None = None) -> int:
    try:
        settings = load_router_settings(argv)
        app = create_router_app(settings)
    except ValueError as exc:
        print(f"Router no arrancado: configuración inválida: {exc}", file=sys.stderr)
        return 2
    except LogPersistenceError as exc:
        print(f"Router no arrancado: {exc.message}", file=sys.stderr)
        return 2
    uvicorn.run(app, host=settings.host, port=settings.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
