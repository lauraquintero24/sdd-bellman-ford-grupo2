"""TC-40, TC-45, TC-46 y TC-47 con 5 PROCESOS REALES (FR-11–FR-13; C-32).

Controller (F-20) y routers A, B, C y D, cada uno un proceso del sistema operativo en su propio puerto, arrancados
con la misma línea de comandos que usa el lanzador (`python -m router.main --router-id X --routers …`). Comprueba:
cuatro servidores independientes, tablas distintas, un paquete A→D reenviado por HTTP real salto a salto, fallo y
restauración de B–D con las tablas actualizadas, y un router y el Controller detenidos con error controlado.
"""

import json
import shutil
import time

import httpx

from tests.fakes import FIXTURES_DIR
from tests.process_utils import free_port, start, stop, wait_health

DELAY_V1 = {  # 06 §3.1, T-07–T-10: siguiente salto por destino
    "A": {"B": "B", "C": "C", "D": "B"}, "B": {"A": "A", "C": "A", "D": "D"},
    "C": {"A": "A", "B": "A", "D": "D"}, "D": {"A": "B", "B": "B", "C": "C"},
}
DELAY_V2 = {  # T-19–T-22 (B–D fallado)
    "A": {"B": "B", "C": "C", "D": "C"}, "B": {"A": "A", "C": "A", "D": "A"},
    "C": {"A": "A", "B": "A", "D": "D"}, "D": {"A": "C", "B": "C", "C": "C"},
}


def _get(url, path, **params):
    return httpx.get(url + path, params=params, timeout=5)


def _wait_tables(urls, version, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all(_get(u, "/status").json()["topology_version"] == version for u in urls.values()):
            return
        time.sleep(0.2)
    raise AssertionError({n: _get(u, "/status").json() for n, u in urls.items()})


def _next_hops(url):
    entries = _get(url, "/forwarding-table", metric="delay").json()["entries"]
    return {e["destination"]: e["next_hop"] for e in entries}


def _send(url, src, dst, packet_id):
    return httpx.post(url + "/packets", json={"packet_id": packet_id, "source": src, "destination": dst,
                                              "metric": "delay"}, timeout=15)


def _diagnosis(urls, tmp_path) -> str:
    """Estado de cada router y última línea de su bitácora, para dejar constancia de la causa de un fallo."""
    lines = []
    for n, url in urls.items():
        try:
            status = _get(url, "/status").json()
        except httpx.HTTPError as exc:
            status = f"sin respuesta ({type(exc).__name__})"
        log = tmp_path / n / "forwarding.jsonl"
        last = log.read_text(encoding="utf-8").splitlines()[-1:] if log.exists() else []
        lines.append(f"  {n}: /status={status} · última línea de bitácora={last}")
    return "\n".join(lines)


def _send_expect(urls, tmp_path, src, dst, packet_id, expected_path):
    """Envía y comprueba la traza; si falla, el mensaje incluye el estado HTTP, el cuerpo completo y el diagnóstico."""
    response = _send(urls[src], src, dst, packet_id)
    nodes = [h["node"] for h in response.json().get("trace", [])] if response.headers.get("content-type", "").startswith(
        "application/json") else None
    assert response.status_code == 200 and nodes == expected_path, (
        f"{packet_id} {src}→{dst}: esperado {expected_path}; HTTP {response.status_code}; cuerpo: {response.text}\n"
        + _diagnosis(urls, tmp_path))
    return response.json()


def test_five_real_processes(tmp_path):
    topology = tmp_path / "topology-demo.json"
    shutil.copy(FIXTURES_DIR / "F-20.json", topology)
    c_port = free_port()
    ports = {n: free_port() for n in "ABCD"}
    urls = {n: f"http://127.0.0.1:{p}" for n, p in ports.items()}
    registry = tmp_path / "routers.json"
    registry.write_text(json.dumps({"routers": [{"router_id": n, "url": u} for n, u in urls.items()]}), encoding="utf-8")
    controller_url = f"http://127.0.0.1:{c_port}"

    procs = {"controller": start("controller.main", ["--port", str(c_port), "--topology", str(topology)])}
    for n in "ABCD":
        (tmp_path / n).mkdir()
        # --connect-timeout 3: en Windows una conexión rechazada a 127.0.0.1 tarda ~2 s (127.0.0.1:9 →
        # «ConnectionRefusedError 2.03 s», medido por el equipo); con 1.0 s un router detenido daría 504 y no 503.
        procs[n] = start("router.main", ["--router-id", n, "--routers", str(registry), "--controller-url", controller_url,
                                         "--log-file", str(tmp_path / n / "forwarding.jsonl"),
                                         "--table-file", str(tmp_path / n / "forwarding-table.json"),
                                         "--connect-timeout", "3"])
    try:
        # 1. Cuatro servidores independientes, cada uno en su puerto y con su identidad
        wait_health(c_port)
        for n in "ABCD":
            wait_health(ports[n])
        assert len({p.pid for p in procs.values()}) == 5
        for n, url in urls.items():
            status = _get(url, "/status").json()
            assert (status["router_id"], status["url"], status["mode"]) == (n, url, "node")
        # 2. Tablas distintas (versión 1)
        _wait_tables(urls, 1)
        assert {n: _next_hops(u) for n, u in urls.items()} == DELAY_V1
        # 3. Paquete A→D salto a salto por HTTP real, igual a la ruta del Controller
        body = _send_expect(urls, tmp_path, "A", "D", "pkt-1", ["A", "B", "D"])
        route = _get(controller_url, "/route", src="A", dst="D", metric="delay").json()
        assert [h["node"] for h in body["trace"]] == route["path"] == ["A", "B", "D"]
        assert [h["router_url"] for h in body["trace"]] == [urls["A"], urls["B"], urls["D"]]
        # 4. Fallo de B–D: tablas actualizadas solas (versión 2) y nueva ruta; restauración (versión 3)
        httpx.post(controller_url + "/links/fail", json={"source": "B", "target": "D"}, timeout=5)
        _wait_tables(urls, 2)
        assert {n: _next_hops(u) for n, u in urls.items()} == DELAY_V2
        _send_expect(urls, tmp_path, "A", "D", "pkt-2", ["A", "C", "D"])
        httpx.post(controller_url + "/links/restore", json={"source": "B", "target": "D"}, timeout=5)
        _wait_tables(urls, 3)
        assert {n: _next_hops(u) for n, u in urls.items()} == DELAY_V1
        _send_expect(urls, tmp_path, "A", "D", "pkt-3", ["A", "B", "D"])
        # 5. Router B detenido: error controlado en A; los demás siguen vivos
        stop(procs["B"])
        response = _send(urls["A"], "A", "D", "pkt-4")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "NEXT_HOP_UNAVAILABLE"
        assert response.json()["error"]["details"]["at_router"] == "A"
        for n in "ACD":
            assert _get(urls[n], "/health").status_code == 200
        # 6. Controller detenido: el reenvío se bloquea con 503 (DEC-06) sin bloquear el router
        stop(procs["controller"])
        response = _send(urls["C"], "C", "D", "pkt-5")
        assert response.status_code == 503 and response.json()["error"]["code"] == "CONTROLLER_UNAVAILABLE"
        assert _get(urls["C"], "/health").status_code == 200
    finally:
        for proc in procs.values():
            stop(proc)
    # Registros de accesos reales: B y D recibieron POST /forward del paquete 1; A no recibió ninguno
    outputs = {n: procs[n].stdout_text + procs[n].stderr_text for n in "ABCD"}
    assert "POST /forward" in outputs["B"] and "POST /forward" in outputs["D"]
    assert "POST /forward" not in outputs["A"]
    # Cada router escribió solo en sus archivos
    for n in "ABD":
        records = [json.loads(l) for l in (tmp_path / n / "forwarding.jsonl").read_text(encoding="utf-8").splitlines()]
        assert {r["router_id"] for r in records} == {n}
