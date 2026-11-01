"""Utilidades para pruebas con procesos reales (TC-10, TC-14)."""

import locale
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def start(module: str, args: list[str], env: dict | None = None, log_file: Path | None = None) -> subprocess.Popen:
    """Arranca ``python -m module args``.

    Sin ``log_file``, stdout y stderr van a tuberías que nadie lee mientras el proceso vive. En Windows el búfer de
    una tubería anónima es de unos 4 KB (en Linux, 64 KB): cuando el registro de accesos de uvicorn lo llena, la
    escritura bloquea el bucle de eventos del servidor y deja de responder (504 CONTROLLER_TIMEOUT en las pruebas de
    5 procesos en Windows 11). Por eso las tuberías solo valen para procesos breves o que se leen con communicate().

    Con ``log_file``, ambas salidas van a ese archivo (como hace el lanzador) y ``stop()`` lo lee.
    """
    full_env = {**os.environ, **(env or {})}
    command = [sys.executable, "-m", module, *args]
    if log_file is None:
        return subprocess.Popen(command, cwd=ROOT, env=full_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("wb") as handle:  # el hijo hereda su propio descriptor
        process = subprocess.Popen(command, cwd=ROOT, env=full_env, stdout=handle, stderr=subprocess.STDOUT)
    process.log_file = log_file
    return process


def log_tail(log_file: Path, lines: int = 15) -> str:
    """Últimas líneas de la salida de un proceso arrancado con ``log_file`` (para diagnósticos)."""
    if not Path(log_file).exists():
        return "(sin archivo)"
    return "\n".join(read_output(log_file).splitlines()[-lines:])


def read_output(path: Path) -> str:
    """Salida de un proceso hijo guardada en archivo, con la codificación del sistema (la de ``text=True``)."""
    return Path(path).read_text(encoding=locale.getpreferredencoding(False), errors="replace")


def wait_health(port: int, timeout: float = 15.0) -> httpx.Response:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return httpx.get(f"http://127.0.0.1:{port}/health", timeout=1.0)
        except httpx.TransportError:
            time.sleep(0.1)
    raise TimeoutError(f"el proceso no respondió en el puerto {port}")


def stop(process: subprocess.Popen) -> None:
    """Detiene el proceso (idempotente) y conserva su salida en ``stdout_text`` / ``stderr_text``."""
    if hasattr(process, "stdout_text"):
        return
    process.terminate()
    try:
        out, err = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        out, err = process.communicate()
    if hasattr(process, "log_file"):  # salida combinada en archivo
        out, err = read_output(process.log_file), ""
    process.stdout_text, process.stderr_text = out or "", err or ""
