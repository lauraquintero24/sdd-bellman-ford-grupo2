"""Punto de entrada del Controller: ``python -m controller.main [--host] [--port] [--topology]``.

Una configuración o topología inválida impide el arranque con un diagnóstico (02 §7, TC-10, TC-14).
"""

import sys

import uvicorn

from controller.app import create_controller_app
from controller.dao import TopologyLoadError
from controller.settings import load_controller_settings


def main(argv: list[str] | None = None) -> int:
    try:
        settings = load_controller_settings(argv)
        app = create_controller_app(settings)
    except ValueError as exc:
        print(f"Controller no arrancado: configuración inválida: {exc}", file=sys.stderr)
        return 2
    except TopologyLoadError as exc:
        print(f"Controller no arrancado: topología inválida [{exc.rule}]: {exc.detail}", file=sys.stderr)
        return 2
    uvicorn.run(app, host=settings.host, port=settings.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
