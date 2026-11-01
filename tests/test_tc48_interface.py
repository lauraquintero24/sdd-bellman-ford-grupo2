"""TC-48 — Tablas consultables por HTTP y visibles en la interfaz (FR-14; C-32).

Parte HTTP: GET /routers, GET /ui y configuración ROUTERS_FILE del Controller. La cabecera CORS de los routers
está en TC-42; la comprobación en un navegador real con procesos reales se guarda como evidencia en W-19.
"""

import json
import re
import shutil

import pytest
from fastapi.testclient import TestClient

from controller.app import create_controller_app
from controller.settings import ControllerSettings, load_controller_settings
from shared.models import RouterInfo
from tests.fakes import FIXTURES_DIR

REGISTRY = tuple(RouterInfo(n, f"http://127.0.0.1:{8001 + i}") for i, n in enumerate("ABCD"))


def _client(tmp_path, routers=REGISTRY):
    topology = tmp_path / "F-20.json"
    shutil.copy(FIXTURES_DIR / "F-20.json", topology)
    return TestClient(create_controller_app(ControllerSettings("127.0.0.1", 8000, topology, routers=routers)))


def test_routers_endpoint_returns_the_registry(tmp_path):
    response = _client(tmp_path).get("/routers")
    assert response.status_code == 200
    assert response.json() == {"routers": [{"router_id": n, "url": f"http://127.0.0.1:{8001 + i}"}
                                           for i, n in enumerate("ABCD")]}
    empty = tmp_path / "sin-registro"
    empty.mkdir()
    assert _client(empty, routers=()).get("/routers").json() == {"routers": []}


def test_ui_is_html_and_obtains_everything_over_http(tmp_path):
    response = _client(tmp_path).get("/ui")
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/html")
    html = response.text
    for element in ('id="routers"', 'id="forwarding-table"', 'id="send-form"', 'id="links"', 'id="table-metric"',
                    'id="history"', 'id="topology-version"'):
        assert element in html
    for call in ('"/routers"', '"/topology"', '"/topology/version"', '"/status"', '"/forwarding-table?metric="',
                 '"/packets"', '"/links/"'):
        assert call in html
    # Sin datos de la red incrustados: nada de rutas, costos ni URL de routers en el HTML
    assert "127.0.0.1:800" not in html and not re.search(r'"total_cost"\s*:', html) and "A → B" not in html
    # La tabla solo se redibuja cuando cambia (router, métrica, versión)
    assert "if (key === state.tableKey) return;" in html


def test_controller_reads_routers_file_from_cli_and_environment(tmp_path):
    registry = tmp_path / "routers.json"
    registry.write_text(json.dumps({"routers": [{"router_id": "A", "url": "http://127.0.0.1:9001"}]}), encoding="utf-8")
    topology = FIXTURES_DIR / "F-20.json"
    by_cli = load_controller_settings(["--topology", str(topology), "--routers", str(registry)], {})
    by_env = load_controller_settings(["--topology", str(topology)], {"ROUTERS_FILE": str(registry)})
    assert by_cli.routers == by_env.routers == (RouterInfo("A", "http://127.0.0.1:9001"),)
    assert load_controller_settings(["--topology", str(topology)], {}).routers == ()


@pytest.mark.parametrize("content", ['{"routers": []}', "{", '{"routers": [{"router_id": "A", "url": "x"}]}'])
def test_invalid_routers_file_prevents_start(tmp_path, content):
    registry = tmp_path / "routers.json"
    registry.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_controller_settings(["--topology", str(FIXTURES_DIR / "F-20.json"), "--routers", str(registry)], {})
    with pytest.raises(ValueError, match="ROUTERS_FILE"):
        load_controller_settings(["--topology", str(FIXTURES_DIR / "F-20.json"), "--routers", str(tmp_path / "no.json")], {})
