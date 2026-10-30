"""Configuración del proceso Router (02 §7, NFR-05).

Precedencia: opción CLI > variable de entorno > valor por defecto.
"""

import argparse
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8001
DEFAULT_CONTROLLER_URL = "http://127.0.0.1:8000"
DEFAULT_LOG_FILE = "data/forwarding.jsonl"
DEFAULT_CONNECT_TIMEOUT = 1.0
DEFAULT_READ_TIMEOUT = 2.0


@dataclass(frozen=True)
class RouterSettings:
    host: str
    port: int
    controller_url: str
    connect_timeout_s: float
    read_timeout_s: float
    log_file: Path


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
    args = parser.parse_args(argv)

    def pick(cli, env_name, default):
        return cli if cli is not None else env.get(env_name, default)

    host = pick(args.host, "ROUTER_HOST", DEFAULT_HOST)
    port = _parse_port(pick(args.port, "ROUTER_PORT", str(DEFAULT_PORT)))
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
    raw_log = pick(args.log_file, "FORWARDING_LOG_FILE", None)
    log_file = Path(raw_log if raw_log is not None else DEFAULT_LOG_FILE)
    directory = log_file.parent
    if raw_log is None:
        directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir():
        raise ValueError(f"El directorio de FORWARDING_LOG_FILE no existe: {directory}")
    if not os.access(directory, os.W_OK) or (log_file.exists() and not os.access(log_file, os.W_OK)):
        raise ValueError(f"FORWARDING_LOG_FILE no admite escritura: {log_file}")
    return RouterSettings(
        host=host,
        port=port,
        controller_url=controller_url,
        connect_timeout_s=connect_timeout,
        read_timeout_s=read_timeout,
        log_file=log_file,
    )
