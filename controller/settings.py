"""Configuración del proceso Controller (02 §7, NFR-05).

Precedencia: opción CLI > variable de entorno > valor por defecto.
"""

import argparse
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from shared.models import RouterInfo
from shared.registry import parse_router_registry

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_TOPOLOGY_FILE = "config/topology.json"


@dataclass(frozen=True)
class ControllerSettings:
    host: str
    port: int
    topology_file: Path
    routers: tuple[RouterInfo, ...] = ()  # C-32: registro para GET /routers e /ui (vacío sin ROUTERS_FILE)


def _parse_port(raw: str) -> int:
    try:
        port = int(raw)
    except ValueError:
        raise ValueError(f"Puerto inválido: {raw!r} (debe ser un entero entre 1 y 65535).") from None
    if not 1 <= port <= 65535:
        raise ValueError(f"Puerto fuera de rango: {port} (debe estar entre 1 y 65535).")
    return port


def load_controller_settings(
    argv: Sequence[str] | None = None, environ: Mapping[str, str] | None = None
) -> ControllerSettings:
    """Lee CLI y entorno; lanza ``ValueError`` con un diagnóstico si la configuración impide arrancar.

    La validez del contenido de la topología la comprueba ``JsonTopologyDAO`` al cargarla.
    """
    env = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(prog="python -m controller.main", description="Controller SDN (Bellman-Ford)")
    parser.add_argument("--host", help="CONTROLLER_HOST; por defecto 127.0.0.1")
    parser.add_argument("--port", help="CONTROLLER_PORT; por defecto 8000")
    parser.add_argument("--topology", help="TOPOLOGY_FILE; por defecto config/topology.json")
    parser.add_argument("--routers", help="ROUTERS_FILE; registro de routers para la interfaz (C-32); sin valor por defecto")
    args = parser.parse_args(argv)

    host = args.host or env.get("CONTROLLER_HOST") or DEFAULT_HOST
    port = _parse_port(args.port if args.port is not None else env.get("CONTROLLER_PORT", str(DEFAULT_PORT)))
    topology_file = Path(args.topology or env.get("TOPOLOGY_FILE") or DEFAULT_TOPOLOGY_FILE)
    if not topology_file.is_file():
        raise ValueError(f"TOPOLOGY_FILE no existe o no es un archivo: {topology_file}")
    routers: tuple[RouterInfo, ...] = ()
    raw_routers = args.routers or env.get("ROUTERS_FILE")
    if raw_routers:
        routers_file = Path(raw_routers)
        if not routers_file.is_file():
            raise ValueError(f"ROUTERS_FILE no existe o no es un archivo: {routers_file}")
        routers = parse_router_registry(routers_file.read_text(encoding="utf-8"))
    return ControllerSettings(host=host, port=port, topology_file=topology_file, routers=routers)
