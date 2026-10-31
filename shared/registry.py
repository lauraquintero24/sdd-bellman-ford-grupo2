"""Registro de routers en modo nodo (C-32, 02 §7): ``{"routers": [{"router_id": "A", "url": "http://127.0.0.1:8001"}, …]}``.

Función pura sobre el texto del archivo; la lectura del archivo la hace cada ``settings.py``.
Solo biblioteca estándar (02 §8).
"""

import json
from urllib.parse import urlsplit

from shared.models import RouterInfo


def parse_router_registry(text: str) -> tuple[RouterInfo, ...]:
    """Valida el registro y devuelve sus entradas en orden; lanza ``ValueError`` con un diagnóstico."""
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"el registro de routers no es JSON válido ({exc})") from None
    if not isinstance(doc, dict) or set(doc) != {"routers"} or not isinstance(doc["routers"], list):
        raise ValueError('el registro debe ser un objeto con exactamente la clave "routers" (lista)')
    if not doc["routers"]:
        raise ValueError("el registro de routers está vacío")
    entries, ids, urls, endpoints = [], set(), set(), set()
    for index, item in enumerate(doc["routers"]):
        if not isinstance(item, dict) or set(item) != {"router_id", "url"}:
            raise ValueError(f'entrada {index}: debe tener exactamente "router_id" y "url"')
        router_id, url = item["router_id"], item["url"]
        if not isinstance(router_id, str) or router_id == "" or router_id != router_id.strip():
            raise ValueError(f"entrada {index}: router_id vacío o con espacios en los extremos: {router_id!r}")
        if not isinstance(url, str):
            raise ValueError(f"entrada {index}: url debe ser texto")
        parts = urlsplit(url)
        try:
            port = parts.port
        except ValueError:
            port = None
        if parts.scheme not in ("http", "https") or not parts.hostname or port is None:
            raise ValueError(f"entrada {index}: url debe ser http:// o https:// con host y puerto explícito: {url!r}")
        if parts.path not in ("", "/") or parts.query or parts.fragment:
            raise ValueError(f"entrada {index}: url no debe tener ruta, consulta ni fragmento: {url!r}")
        normalized = url.rstrip("/")
        if router_id in ids:
            raise ValueError(f"router_id repetido: {router_id!r}")
        if normalized in urls or (parts.hostname, port) in endpoints:
            raise ValueError(f"url o puerto repetido: {url!r}")
        ids.add(router_id)
        urls.add(normalized)
        endpoints.add((parts.hostname, port))
        entries.append(RouterInfo(router_id=router_id, url=normalized))
    ports = [urlsplit(e.url).port for e in entries]
    if len(set(ports)) != len(ports):
        raise ValueError("cada router debe tener un puerto distinto")
    return tuple(entries)
