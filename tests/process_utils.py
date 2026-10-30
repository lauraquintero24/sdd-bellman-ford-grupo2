"""Utilidades para pruebas con procesos reales (TC-10, TC-14)."""

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


def start(module: str, args: list[str], env: dict | None = None) -> subprocess.Popen:
    full_env = {**os.environ, **(env or {})}
    return subprocess.Popen(
        [sys.executable, "-m", module, *args], cwd=ROOT, env=full_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def wait_health(port: int, timeout: float = 15.0) -> httpx.Response:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return httpx.get(f"http://127.0.0.1:{port}/health", timeout=1.0)
        except httpx.TransportError:
            time.sleep(0.1)
    raise TimeoutError(f"el proceso no respondió en el puerto {port}")


def stop(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
