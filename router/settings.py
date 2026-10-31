"""Configuración del proceso Router (02 §7, NFR-05).

Precedencia: opción CLI > variable de entorno > valor por defecto.
"""

import argparse
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from shared.models import RouterInfo
from shared.registry import parse_router_registry

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8001
DEFAULT_CONTROLLER_URL = "http://127.0.0.1:8000"
DEFAULT_LOG_FILE = "data/forwarding.jsonl"
DEFAULT_CONNECT_TIMEOUT = 1.0
DEFAULT_READ_TIMEOUT = 2.0
DEFAULT_ROUTERS_FILE = "config/routers.json"
DEFAULT_SYNC_INTERVAL = 1.0


@dataclass(frozen=True)
class RouterSettings:
    host: str
    port: int
    controller_url: str
    connect_timeout_s: float
    read_timeout_s: float
    log_file: Path
    # Modo nodo (C-32, 02 §7); con router_id = None la instancia funciona en modo legado.
    router_id: str | None = None
    routers: tuple[RouterInfo, ...] = ()
    table_file: Path | None = None
    sync_interval_s: float = DEFAULT_SYNC_INTERVAL


def _parse_port(raw: str) -> int:
    try:
        port = int(raw)
    except ValueError:
        raise ValueError(f"Puerto inválido: {raw!r} (debe ser un entero entre 1 y 65535).") from None
    if not 1 <= port <= 65535:
        raise ValueError(f"Puerto fuera de rango: {port} (debe estar entre 1 y 65535).")
    return port


def _parse_timeout(name: str, raw: str) -> float:
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name} inválido: {raw!r} (debe ser un número de segundos > 0).") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} debe ser un número de segundos finito y > 0: {raw!r}.")
    return value


def _parse_interval(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"TABLE_SYNC_INTERVAL_SECONDS inválido: {raw!r} (número de segundos ≥ 0).") from None
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"TABLE_SYNC_INTERVAL_SECONDS debe ser un número finito ≥ 0: {raw!r}.")
    return value


def _writable_file(name: str, raw: str | None, default: Path) -> Path:
    """Ruta por defecto: se crea su directorio; ruta explícita: su directorio debe existir y admitir escritura."""
    path = Path(raw if raw is not None else default)
    directory = path.parent
    if raw is None:
        directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir():
        raise ValueError(f"El directorio de {name} no existe: {directory}")
    if not os.access(directory, os.W_OK) or (path.exists() and not os.access(path, os.W_OK)):
        raise ValueError(f"{name} no admite escritura: {path}")
    return path


def load_router_settings(
    argv: Sequence[str] | None = None, environ: Mapping[str, str] | None = None
) -> RouterSettings:
    """Lee CLI y entorno; lanza ``ValueError`` con un diagnóstico si la configuración impide arrancar.

    El directorio por defecto ``data/`` se crea al arrancar; el de una ruta indicada
    explícitamente debe existir y admitir escritura.
    """
    env = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(prog="python -m router.main", description="Router SDN (plano de datos simulado)")
    parser.add_argument("--host", help="ROUTER_HOST; por defecto 127.0.0.1")
    parser.add_argument("--port", help="ROUTER_PORT; por defecto 8001")
    parser.add_argument("--controller-url", help="CONTROLLER_URL; por defecto http://127.0.0.1:8000")
    parser.add_argument("--log-file", help="FORWARDING_LOG_FILE; por defecto data/forwarding.jsonl")
    parser.add_argument("--connect-timeout", help="CONTROLLER_CONNECT_TIMEOUT_SECONDS; por defecto 1.0")
    parser.add_argument("--read-timeout", help="CONTROLLER_READ_TIMEOUT_SECONDS; por defecto 2.0")
    parser.add_argument("--router-id", help="ROUTER_ID; sin valor: modo legado (C-32)")
    parser.add_argument("--routers", help="ROUTERS_FILE; por defecto config/routers.json (modo nodo)")
    parser.add_argument("--table-file", help="FORWARDING_TABLE_FILE; por defecto data/routers/<id>/forwarding-table.json")
    parser.add_argument("--sync-interval", help="TABLE_SYNC_INTERVAL_SECONDS; por defecto 1.0 (0 la desactiva)")
    args = parser.parse_args(argv)

    def pick(cli, env_name, default):
        return cli if cli is not None else env.get(env_name, default)

    router_id = pick(args.router_id, "ROUTER_ID", None)
    routers: tuple[RouterInfo, ...] = ()
    if router_id is None:
        host = pick(args.host, "ROUTER_HOST", DEFAULT_HOST)
        port = _parse_port(pick(args.port, "ROUTER_PORT", str(DEFAULT_PORT)))
    else:
        routers_file = Path(pick(args.routers, "ROUTERS_FILE", DEFAULT_ROUTERS_FILE))
        if not routers_file.is_file():
            raise ValueError(f"ROUTERS_FILE no existe o no es un archivo: {routers_file}")
        routers = parse_router_registry(routers_file.read_text(encoding="utf-8"))
        own = next((info for info in routers if info.router_id == router_id), None)
        if own is None:
            raise ValueError(f"ROUTER_ID {router_id!r} no está en ROUTERS_FILE ({routers_file})")
        parts = urlsplit(own.url)
        host, port = parts.hostname, parts.port
        explicit_host = pick(args.host, "ROUTER_HOST", None)
        explicit_port = pick(args.port, "ROUTER_PORT", None)
        if explicit_host is not None and explicit_host != host:
            raise ValueError(f"--host {explicit_host!r} no coincide con la URL de {router_id} en el registro ({own.url})")
        if explicit_port is not None and _parse_port(explicit_port) != port:
            raise ValueError(f"--port {explicit_port} no coincide con la URL de {router_id} en el registro ({own.url})")
    controller_url = pick(args.controller_url, "CONTROLLER_URL", DEFAULT_CONTROLLER_URL).rstrip("/")
    if not controller_url.startswith(("http://", "https://")):
        raise ValueError(f"CONTROLLER_URL debe empezar por http:// o https://: {controller_url!r}")
    connect_timeout = _parse_timeout(
        "CONTROLLER_CONNECT_TIMEOUT_SECONDS",
        pick(args.connect_timeout, "CONTROLLER_CONNECT_TIMEOUT_SECONDS", str(DEFAULT_CONNECT_TIMEOUT)),
    )
    read_timeout = _parse_timeout(
        "CONTROLLER_READ_TIMEOUT_SECONDS",
        pick(args.read_timeout, "CONTROLLER_READ_TIMEOUT_SECONDS", str(DEFAULT_READ_TIMEOUT)),
    )
    sync_interval = _parse_interval(pick(args.sync_interval, "TABLE_SYNC_INTERVAL_SECONDS", str(DEFAULT_SYNC_INTERVAL)))
    node_dir = Path("data/routers") / router_id if router_id is not None else None
    log_default = node_dir / "forwarding.jsonl" if node_dir is not None else Path(DEFAULT_LOG_FILE)
    log_file = _writable_file("FORWARDING_LOG_FILE", pick(args.log_file, "FORWARDING_LOG_FILE", None), log_default)
    table_file = None
    if node_dir is not None:
        table_file = _writable_file(
            "FORWARDING_TABLE_FILE", pick(args.table_file, "FORWARDING_TABLE_FILE", None), node_dir / "forwarding-table.json"
        )
    return RouterSettings(
        host=host,
        port=port,
        controller_url=controller_url,
        connect_timeout_s=connect_timeout,
        read_timeout_s=read_timeout,
        log_file=log_file,
        router_id=router_id,
        routers=routers,
        table_file=table_file,
        sync_interval_s=sync_interval,
    )
