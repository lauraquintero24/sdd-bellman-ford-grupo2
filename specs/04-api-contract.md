# 04 — Contrato REST/HTTP + JSON

| Campo | Valor |
|---|---|
| Versión | **1.1** (borrador con C-32, aprobado por ambas el 31/10/2026; candidata a `spec-1.1`) · 2026-10-31 |
| Estado de aprobación | Ver `REVIEW-AND-BASELINE.md` |
| Bases por defecto | Controller `http://127.0.0.1:8000` · Router legado `http://127.0.0.1:8001` · Routers en modo nodo: URL de cada `router_id` en `config/routers.json` (A–D → 8001–8004) (configurables, `02` §7) |

## 1. Convenciones

- Cuerpos `application/json` en UTF-8; nombres `snake_case`; sin `NaN` ni `Infinity`. Los identificadores (`src`, `dst`, `source`, `target`, `destination`, `packet_id`) son cadenas no vacías y sin espacios en los extremos (un ID con espacios en los extremos es entrada inválida: 400 `INVALID_REQUEST`, antes de buscarlo en la topología); `metric` es obligatoria y vale `delay`, `inverse_bandwidth` o `loss`. No existen opciones de desempate en la petición: DEC-08 se aplica siempre. Los cuerpos de petición no admiten campos adicionales (`extra="forbid"`: 400 `INVALID_REQUEST`); los parámetros de consulta desconocidos se ignoran.
- **Errores:** sobre normalizado `{"error": {"code": "...", "message": "...", "details": {...}}}`. `code` y la estructura son estables; `message` es informativo y puede variar. Ninguna respuesta incluye trazas Python, rutas de archivo ni direcciones internas. El Router añade `packet_id`, `status: "failed"` y `trace: []` cuando el paquete ya fue validado.
- **Códigos HTTP (DEC-03, conforme al ejemplo del PDF p. 4):** 400 para toda entrada inválida; 404 para nodo, enlace o camino ausente, distinguidos por `error.code`; 502/503/504 para fallos del Controller —o, en modo nodo, del siguiente router— vistos por el Router; 500 para fallos internos, de la bitácora o del invariante `NEGATIVE_CYCLE`. Solo en modo nodo (C-32): 409 `TOPOLOGY_CHANGED` y 508 `FORWARDING_LOOP` / `HOP_LIMIT_EXCEEDED`. Fuera del contrato, una ruta o un método inexistentes reciben 404 `UNKNOWN_ENDPOINT` o 405 `METHOD_NOT_ALLOWED` con el mismo sobre `error`. No se usa ningún otro código de error.
- **`total_cost`** es siempre una cadena con el formato canónico y la precisión de `01` §5.3 (`"2"`, `"0.02"`, `"27.6310211159"`, `"1e-7"`, `"1e-60"`); nunca un número JSON. Es solo de presentación.
- FastAPI publica además la documentación OpenAPI en `/docs`; si difiere, prevalece este contrato.

| Aplicación | Método y ruta | Propósito (PDF p. 3) | Éxito |
|---|---|---|---|
| Controller | `GET /health` | Disponibilidad del proceso | 200 |
| Controller | `GET /topology` | Topología activa con estado de enlaces y versión | 200 |
| Controller | `GET /route?src=A&dst=D&metric=delay` | Ruta seleccionada, métrica, costo total y versión | 200 |
| Controller | `POST /links/fail` | Desactivar un enlace existente | 200 |
| Controller | `POST /links/restore` | Restaurar un enlace existente | 200 |
| Router | `GET /health` | Disponibilidad del proceso | 200 |
| Router | `POST /packets` | Simular el reenvío; devolver traza y estado | 200 |
| Controller *(C-32)* | `GET /topology/version` | Versión vigente de la topología (sincronización de tablas) | 200 |
| Controller *(C-32)* | `GET /forwarding-table?router_id=A&metric=delay` | Tabla de forwarding calculada para un router | 200 |
| Controller *(C-32)* | `GET /routers` | Registro de routers (para la interfaz) | 200 |
| Controller *(C-32)* | `GET /ui` | Interfaz web (HTML) | 200 |
| Router, modo nodo *(C-32)* | `GET /status` | Identidad, URL y estado de sincronización de la instancia | 200 |
| Router, modo nodo *(C-32)* | `GET /forwarding-table?metric=delay` | Tabla local de esa instancia | 200 |
| Router, modo nodo *(C-32)* | `POST /forward` | Recibir un paquete de otro router (salto) | 200 |

## 2. Archivo de topología (entrada del Controller)

Reglas completas en `01` §4. Ejemplo normativo (fixture F-01, `specs/fixtures/F-01.json`):

```json
{
  "directed": true,
  "nodes": ["A", "B", "C", "D"],
  "links": [
    {"source": "A", "target": "B", "delay_ms": 1.0, "bandwidth_mbps": 10.0, "loss_probability": 0.01, "active": true},
    {"source": "B", "target": "D", "delay_ms": 1.0, "bandwidth_mbps": 10.0, "loss_probability": 0.01, "active": true},
    {"source": "A", "target": "C", "delay_ms": 2.0, "bandwidth_mbps": 100.0, "loss_probability": 0.02, "active": true},
    {"source": "C", "target": "D", "delay_ms": 2.0, "bandwidth_mbps": 100.0, "loss_probability": 0.02, "active": true}
  ]
}
```

Un archivo que viola `01` §4 no produce respuestas HTTP: el Controller no arranca y emite un diagnóstico (TC-10).

## 3. Endpoints del Controller

### 3.1 `GET /health`

**200:** `{"status": "ok", "application": "controller"}`. Solo informa que el proceso responde.

### 3.2 `GET /topology`

Sin parámetros. **200** (`TopologyResponseSchema`):

| Campo | Tipo | Descripción |
|---|---|---|
| `topology_version` | entero ≥ 1 | Versión vigente |
| `directed` | booleano | Modo del grafo |
| `nodes` | lista de cadenas | IDs en el orden del archivo |
| `links` | lista de objetos | Todos los enlaces, incluidos los inactivos, con `source`, `target`, `delay_ms`, `bandwidth_mbps`, `loss_probability` (cadenas decimales) y `active` |

```json
{
  "topology_version": 1,
  "directed": true,
  "nodes": ["A", "B", "C", "D"],
  "links": [
    {"source": "A", "target": "B", "delay_ms": "1.0", "bandwidth_mbps": "10.0", "loss_probability": "0.01", "active": true},
    {"source": "B", "target": "D", "delay_ms": "1.0", "bandwidth_mbps": "10.0", "loss_probability": "0.01", "active": true},
    {"source": "A", "target": "C", "delay_ms": "2.0", "bandwidth_mbps": "100.0", "loss_probability": "0.02", "active": true},
    {"source": "C", "target": "D", "delay_ms": "2.0", "bandwidth_mbps": "100.0", "loss_probability": "0.02", "active": true}
  ]
}
```

Los atributos numéricos se devuelven como **cadenas decimales exactas** del valor leído, conservando sus cifras: notación fija si el exponente decimal ajustado está entre −6 y 11 (`"1.0"`, `"0.01"`, `"100.0"`) y, si no, notación científica con `e` minúscula y signo (`"1e-60"`, `"1.5e+13"`); al igual que `total_cost`, viajan como cadena: así se conserva la exactitud en todo el dominio de `01` §4 (exponentes de −1000 a 1000) sin pasar por `float`. El archivo de entrada usa números JSON; la salida usa cadenas a propósito. **Errores:** 500 `INTERNAL_ERROR`.

### 3.3 `GET /route`

| Parámetro de consulta | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `src` | cadena | sí | ID de nodo |
| `dst` | cadena | sí | ID de nodo |
| `metric` | enumeración | sí | `delay`, `inverse_bandwidth` o `loss` |

**200** (`RouteResponseSchema`): `source`, `destination` y `metric` repiten la petición; `path` es la ruta simple elegida (lista de IDs desde `src` hasta `dst`); `total_cost` es la cadena canónica; `topology_version` es la versión de la instantánea usada.

```json
{"source": "A", "destination": "D", "metric": "delay", "path": ["A", "B", "D"], "total_cost": "2", "topology_version": 1}
```

Con F-01: `metric=inverse_bandwidth` → `["A", "C", "D"]`, `"0.02"`; `metric=loss` → `["A", "B", "D"]`, `"0.020100671707"`; `src=dst=A` → `["A"]`, `"0"`.

| Estado | `error.code` | Cuándo |
|---|---|---|
| 400 | `INVALID_REQUEST` | Falta un parámetro, está vacío o `metric` no es admitida |
| 404 | `NODE_NOT_FOUND` | `src` o `dst` no existe (se valida `src` primero); `details` incluye el campo y el valor |
| 404 | `ROUTE_UNREACHABLE` | Ambos nodos existen y no hay ruta utilizable |
| 500 | `NEGATIVE_CYCLE` | Invariante violado (pesos negativos); imposible con una topología validada, comprobable con un DAO falso (TC-11) |
| 500 | `INTERNAL_ERROR` | Error inesperado |

```json
{"error": {"code": "ROUTE_UNREACHABLE", "message": "No existe una ruta utilizable de A a D.", "details": {"source": "A", "destination": "D", "metric": "delay"}}}
```

```json
{"error": {"code": "NODE_NOT_FOUND", "message": "El nodo X no existe en la topología.", "details": {"field": "src", "value": "X"}}}
```

### 3.4 `POST /links/fail`

**Cuerpo** (`LinkRequestSchema`): `{"source": "B", "target": "D"}` (ambos obligatorios). **200** (`LinkStatusSchema`), primera vez sobre F-01:

```json
{"source": "B", "target": "D", "active": false, "changed": true, "topology_version": 2}
```

Repetido: `{"source": "B", "target": "D", "active": false, "changed": false, "topology_version": 2}`. En modo dirigido solo se modifica el arco B→D; en modo no dirigido `{"source": "D", "target": "B"}` designa el mismo enlace. La respuesta repite siempre `source` y `target` tal como llegaron en la petición.

| Estado | `error.code` | Cuándo |
|---|---|---|
| 400 | `MALFORMED_JSON` | El cuerpo no es JSON válido |
| 400 | `INVALID_REQUEST` | Falta un campo, tipo erróneo, cadena vacía o campo adicional; `details.fields` lista los campos afectados |
| 404 | `NODE_NOT_FOUND` | `source` o `target` no existe (se comprueba `source` primero; `details.field` indica cuál) |
| 404 | `LINK_NOT_FOUND` | Ambos nodos existen y no hay enlace entre ellos (en ese sentido, si es dirigido) |

```json
{"error": {"code": "INVALID_REQUEST", "message": "Falta el campo target.", "details": {"fields": ["target"]}}}
```

```json
{"error": {"code": "MALFORMED_JSON", "message": "El cuerpo JSON es inválido.", "details": {}}}
```

### 3.5 `POST /links/restore`

Mismo cuerpo y errores que §3.4. **200**, primera restauración tras el fallo anterior:

```json
{"source": "B", "target": "D", "active": true, "changed": true, "topology_version": 3}
```

Repetido: `active: true, changed: false, topology_version: 3`. Restaurar un enlace con `loss_probability=1` lo marca activo, pero sigue sin poder usarse en rutas (DEC-02).

### 3.6 `GET /topology/version` *(C-32)*

Sin parámetros. **200:** `{"topology_version": 1}`. Lo consultan los routers en modo nodo antes de cada paquete y cada `TABLE_SYNC_INTERVAL_SECONDS`. **Errores:** 500 `INTERNAL_ERROR`.

### 3.7 `GET /forwarding-table` *(C-32)*

| Parámetro de consulta | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `router_id` | cadena | sí | ID de nodo (mismas reglas que `src`) |
| `metric` | enumeración | sí | `delay`, `inverse_bandwidth` o `loss` |

**200** (`ForwardingTableResponseSchema`): `router_id`, `metric`, `topology_version` de la instantánea usada y `entries`, **una fila por cada otro nodo** en el orden de `nodes`. Fila alcanzable: `destination`, `next_hop` (= `path[1]`), `path` (ruta completa elegida por DEC-08), `total_cost` (cadena canónica de `01` §5.3) y `status: "active"`. Fila inalcanzable: `next_hop`, `path` y `total_cost` en `null` y `status: "unreachable"`. Ejemplo con F-20 (no dirigida), versión 1:

```json
{"router_id": "A", "metric": "delay", "topology_version": 1, "entries": [
  {"destination": "B", "next_hop": "B", "path": ["A", "B"], "total_cost": "1", "status": "active"},
  {"destination": "C", "next_hop": "C", "path": ["A", "C"], "total_cost": "2", "status": "active"},
  {"destination": "D", "next_hop": "B", "path": ["A", "B", "D"], "total_cost": "2", "status": "active"}]}
```

Con F-01 (dirigida), la fila A de la tabla del router B es `{"destination": "A", "next_hop": null, "path": null, "total_cost": null, "status": "unreachable"}`.

| Estado | `error.code` | Cuándo |
|---|---|---|
| 400 | `INVALID_REQUEST` | Falta un parámetro, está vacío o `metric` no es admitida |
| 404 | `NODE_NOT_FOUND` | `router_id` no existe; `details: {"field": "router_id", "value": …}` |
| 500 | `NEGATIVE_CYCLE` / `INTERNAL_ERROR` | Como en §3.3 |

### 3.8 `GET /routers` y `GET /ui` *(C-32)*

`GET /routers` → **200** `{"routers": [{"router_id": "A", "url": "http://127.0.0.1:8001"}, …]}` con el contenido de `ROUTERS_FILE` en su orden (lista vacía si no se configuró). `GET /ui` → **200** `text/html`: página que, desde el navegador, consulta `GET /routers`, `GET /topology` y `GET /topology/version` del Controller y `GET /health`, `GET /status` y `GET /forwarding-table` de cada router; envía `POST /packets` al router de origen y `POST /links/fail|restore` al Controller. Refresca el estado cada 2 s; redibuja la tabla del router seleccionado solo si cambió su `topology_version`; el resultado del último envío se muestra al enviar.

## 4. Endpoints del Router

### 4.1 `GET /health`

**200:** `{"status": "ok", "application": "router"}`, también cuando el Controller no responde.

### 4.2 `POST /packets`

**Cuerpo** (`PacketRequestSchema`):

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `packet_id` | cadena | sí | No vacía; identifica el paquete en la bitácora. No se exige unicidad: un `packet_id` repetido se procesa y registra como un paquete más |
| `source` | cadena | sí | ID de nodo (lo valida el Controller) |
| `destination` | cadena | sí | ID de nodo (lo valida el Controller) |
| `metric` | enumeración | sí | `delay`, `inverse_bandwidth` o `loss` |
| `payload` | cadena | no | Por defecto `""`; no se interpreta |

```json
{"packet_id": "pkt-001", "source": "A", "destination": "D", "metric": "delay", "payload": "hola"}
```

El Router **no** calcula la ruta: hace un `GET /route` al Controller, recorre la ruta recibida y registra el resultado antes de responder. **200** (`ForwardingResponseSchema`):

```json
{
  "packet_id": "pkt-001",
  "status": "forwarded",
  "route": {"source": "A", "destination": "D", "metric": "delay", "path": ["A", "B", "D"], "total_cost": "2", "topology_version": 1},
  "trace": [{"hop_index": 0, "node": "A"}, {"hop_index": 1, "node": "B"}, {"hop_index": 2, "node": "D"}],
  "topology_version": 1
}
```

`trace` enumera exactamente `route.path` en orden (`trace[i].node == path[i]`, `trace[i].hop_index == i`); no simula tiempos ni pérdidas. Respuesta de error para un paquete validado (ejemplo con el Controller detenido):

```json
{"packet_id": "pkt-002", "status": "failed", "trace": [], "error": {"code": "CONTROLLER_UNAVAILABLE", "message": "No fue posible conectar con el Controller.", "details": {}}}
```

| Estado | `error.code` | Cuándo | ¿Se registra? |
|---|---|---|---|
| 400 | `MALFORMED_JSON` / `INVALID_REQUEST` | Cuerpo ilegible o que no cumple el esquema (respuesta sin `packet_id`) | No |
| 404 | `NODE_NOT_FOUND` / `ROUTE_UNREACHABLE` | El Controller respondió ese 404 con un sobre válido | Sí, `failed` |
| 502 | `CONTROLLER_BAD_RESPONSE` | Respuesta del Controller no conforme a §4.3, o conexión cortada a mitad de respuesta | Sí, `failed` |
| 503 | `CONTROLLER_UNAVAILABLE` | Conexión rechazada o nombre no resoluble | Sí, `failed` |
| 504 | `CONTROLLER_TIMEOUT` | Se agotó el timeout de conexión o de lectura | Sí, `failed` |
| 500 | `LOG_PERSISTENCE_ERROR` | No se pudo guardar el resultado (éxito o fallo); prevalece sobre el error original | No consta |
| 500 | `INTERNAL_ERROR` | Error inesperado | No garantizado |

```json
{"packet_id": "pkt-004", "status": "failed", "trace": [], "error": {"code": "LOG_PERSISTENCE_ERROR", "message": "No fue posible guardar el resultado.", "details": {}}}
```

**Timeouts:** `HttpRouteClient` usa `CONTROLLER_CONNECT_TIMEOUT_SECONDS` (por defecto 1.0) y `CONTROLLER_READ_TIMEOUT_SECONDS` (por defecto 2.0), por ejemplo `httpx.Timeout(connect=1.0, read=2.0, write=2.0, pool=1.0)`. Son límites por fase, no una duración total garantizada.

### 4.3 Validación de la respuesta del Controller (`HttpRouteClient`)

Una respuesta 200 se acepta solo si:

1. El cuerpo es un objeto JSON con exactamente `source`, `destination`, `metric`, `path`, `total_cost`, `topology_version`.
2. `source`, `destination` y `metric` coinciden con la petición.
3. `path` es una lista no vacía de cadenas no vacías y sin repetidos, con `path[0] == src` y `path[-1] == dst`; si `src == dst`, `path == [src]` y `total_cost == "0"`.
4. `total_cost` es una cadena (no número ni booleano) y `shared.cost_format.is_canonical_cost(total_cost)` es verdadero (gramática, rango y ≤ 12 cifras significativas de `01` §5.3).
5. `topology_version` es un entero ≥ 1 (no booleano).

Un 404 con sobre `error` válido y `code` igual a `NODE_NOT_FOUND` o `ROUTE_UNREACHABLE` se propaga con el mismo estado, `code` y `message`; en `details`, el **valor** de `details.field` se reescribe al nombre de campo del paquete (`"src"` → `"source"`, `"dst"` → `"destination"`) y el resto se copia sin cambios. **Cualquier otra respuesta** (otro estado, sobre inválido, cuerpo no JSON o incumplimiento de 1–5) se convierte en 502 `CONTROLLER_BAD_RESPONSE`. El Router no verifica conectividad ni optimalidad: confía en el Controller (frontera de confianza intencional). Ejemplo: ante `{"source": "X", ...}` para una petición con `src=A`, el Router registra el fallo y responde:

```json
{"packet_id": "pkt-003", "status": "failed", "trace": [], "error": {"code": "CONTROLLER_BAD_RESPONSE", "message": "La respuesta del Controller no cumple el contrato.", "details": {}}}
```

### 4.4 Endpoints del Router en modo nodo *(C-32)*

Mismo `GET /health` de §4.1. Además:

**`GET /status`** → **200** `{"router_id": "A", "url": "http://127.0.0.1:8001", "mode": "node", "topology_version": 1, "synced_at": "2026-10-31T10:00:00.123Z", "sync_status": "ok", "sync_error": null}`. `sync_status` ∈ `pending` (aún sin tabla), `ok`, `error` (último intento fallido; `sync_error` = `{"code", "message"}`; se conserva la tabla anterior).

**`GET /forwarding-table?metric=delay`** → **200** la tabla local con la forma de §3.7 más `url` y `synced_at`. 400 `INVALID_REQUEST` (métrica ausente o inválida); 503 `FORWARDING_TABLE_UNAVAILABLE` si la instancia todavía no tiene tabla. No contacta al Controller.

**`POST /packets`** (ingreso): mismo cuerpo de §4.2; `source` debe ser el `router_id` de la instancia (si no, 400 `INVALID_REQUEST`, `details.fields = ["source"]`, solo con el sobre `{"error": …}` y sin registro; aclaración C-32.7). **`POST /forward`** (salto entre routers; `HopRequestSchema`, `extra="forbid"`): los campos del paquete más `topology_version` (entero ≥ 1) y `trace` (lista de `{"hop_index", "node", "router_url"}`, la traza hasta el router anterior).

Algoritmo de cada router: `02` §6.4. **200** (`NodeForwardingResponseSchema`), ejemplo A→D en F-20:

```json
{
  "packet_id": "pkt-001",
  "status": "forwarded",
  "route": {"source": "A", "destination": "D", "metric": "delay", "path": ["A", "B", "D"], "total_cost": "2", "topology_version": 1},
  "trace": [{"hop_index": 0, "node": "A", "router_url": "http://127.0.0.1:8001"},
            {"hop_index": 1, "node": "B", "router_url": "http://127.0.0.1:8002"},
            {"hop_index": 2, "node": "D", "router_url": "http://127.0.0.1:8004"}],
  "topology_version": 1,
  "forwarding_mode": "hop_by_hop"
}
```

`route.path` son los nodos de `trace`; `route.total_cost` es el de la fila del destino en la tabla del router de ingreso (`"0"` si origen = destino). En las respuestas intermedias de `POST /forward` es el costo desde el router que responde (aclaración C-32.8). Los errores de un paquete validado usan `PacketErrorSchema` (§4.2) con `details.at_router` = router donde se originó el error.

| Estado | `error.code` | Cuándo | ¿Se registra? |
|---|---|---|---|
| 400 | `MALFORMED_JSON` / `INVALID_REQUEST` | Cuerpo inválido o `source` ≠ `router_id` | No |
| 404 | `NODE_NOT_FOUND` / `ROUTE_UNREACHABLE` | Destino ausente o fila `unreachable` en la tabla del router | Sí, `failed` |
| 409 | `TOPOLOGY_CHANGED` | La versión del salto entrante difiere de la tabla vigente | Sí, `failed` |
| 502 | `NEXT_HOP_BAD_RESPONSE` / `CONTROLLER_BAD_RESPONSE` | Respuesta no conforme del siguiente router / del Controller | Sí, `failed` |
| 503 | `NEXT_HOP_UNAVAILABLE` / `CONTROLLER_UNAVAILABLE` / `FORWARDING_TABLE_UNAVAILABLE` | Conexión rechazada / Controller sin conexión / sin tabla todavía | Sí, `failed` |
| 504 | `NEXT_HOP_TIMEOUT` / `CONTROLLER_TIMEOUT` | Timeout de conexión o de lectura | Sí, `failed` |
| 508 | `FORWARDING_LOOP` / `HOP_LIMIT_EXCEEDED` | Nodo repetido en la traza / más saltos que nodos | Sí, `failed` |
| 500 | `LOG_PERSISTENCE_ERROR` / `INTERNAL_ERROR` | Como en §4.2 | Como en §4.2 |

Un error con sobre válido devuelto por el siguiente router y con un código de esta tabla se reproduce con el mismo estado, `code`, `message` y `details`; cualquier otra respuesta del siguiente router es 502 `NEXT_HOP_BAD_RESPONSE`. Una respuesta 200 del siguiente router se acepta solo si su `trace` empieza por la traza enviada, termina en `destination`, no repite nodos y `route.topology_version` es la versión enviada.

## 5. Matriz normalizada de errores

| Aplicación | HTTP | `error.code` | Cuándo | Acción de recuperación |
|---|---:|---|---|---|
| Ambas | 400 | `MALFORMED_JSON` | Cuerpo con sintaxis JSON inválida | Corregir el JSON |
| Ambas | 400 | `INVALID_REQUEST` | Parámetro o campo ausente, tipo erróneo, cadena vacía o `metric` no admitida | Corregir la solicitud |
| Controller (Router propaga) | 404 | `NODE_NOT_FOUND` | Nodo inexistente | Usar un ID válido |
| Controller | 404 | `LINK_NOT_FOUND` | No existe el enlace pedido | Elegir un enlace existente |
| Controller (Router propaga) | 404 | `ROUTE_UNREACHABLE` | Nodos existentes sin ruta utilizable | Restaurar enlaces o cambiar nodos |
| Controller | 500 | `NEGATIVE_CYCLE` | Ciclo negativo alcanzable: invariante de pesos no negativos violado | Revisar la carga de la topología |
| Router | 500 | `LOG_PERSISTENCE_ERROR` | Fallo al guardar en la bitácora | Revisar el sistema de archivos |
| Router | 502 | `CONTROLLER_BAD_RESPONSE` | Respuesta del Controller no conforme | Revisar el Controller |
| Router | 503 | `CONTROLLER_UNAVAILABLE` | Conexión rechazada | Iniciar el Controller |
| Router | 504 | `CONTROLLER_TIMEOUT` | Timeout de conexión o de lectura | Revisar carga, red o timeouts |
| Ambas | 404 | `UNKNOWN_ENDPOINT` | Ruta inexistente (fuera del contrato) | Usar un endpoint de §1 |
| Ambas | 405 | `METHOD_NOT_ALLOWED` | Método no admitido en una ruta existente | Usar el método de §1 |
| Ambas | 500 | `INTERNAL_ERROR` | Error inesperado | Consultar el registro del proceso |
| Router, modo nodo *(C-32)* | 409 | `TOPOLOGY_CHANGED` | La topología cambió durante el reenvío | Reenviar el paquete |
| Router, modo nodo *(C-32)* | 502 | `NEXT_HOP_BAD_RESPONSE` | Respuesta no conforme del siguiente router | Revisar esa instancia |
| Router, modo nodo *(C-32)* | 503 | `NEXT_HOP_UNAVAILABLE` | Siguiente router sin conexión | Iniciar esa instancia |
| Router, modo nodo *(C-32)* | 503 | `FORWARDING_TABLE_UNAVAILABLE` | La instancia aún no tiene tabla | Iniciar el Controller o esperar la sincronización |
| Router, modo nodo *(C-32)* | 504 | `NEXT_HOP_TIMEOUT` | El siguiente router no respondió a tiempo | Revisar carga o timeouts |
| Router, modo nodo *(C-32)* | 508 | `FORWARDING_LOOP` | Un nodo aparece dos veces en la traza | Revisar tablas y versión |
| Router, modo nodo *(C-32)* | 508 | `HOP_LIMIT_EXCEEDED` | La traza supera el número de nodos | Revisar tablas y versión |

## 6. Contrato de datos persistidos (bitácora del Router)

`JsonlForwardingLogDAO` anexa **una línea JSON por resultado** al archivo `FORWARDING_LOG_FILE`, con los campos de `ForwardingResult` (`packet_id`, `source`, `destination`, `metric`, `status`, `route`, `trace`, `topology_version`, `error`) más `recorded_at`, asignado por el DAO en UTC con el formato fijo `AAAA-MM-DDTHH:MM:SS.mmmZ` (milisegundos y sufijo `Z`). En los resultados `failed`, `route` y `topology_version` son `null`, `trace` es `[]` y `error` contiene `code`, `message` y `details`; así cada línea identifica qué se pidió aunque fallara. `ForwardingLogDAO.list_recent(limit)` relee estas líneas. Ejemplos de línea (valores ilustrativos):

```json
{"recorded_at": "2026-11-05T14:03:12.481Z", "packet_id": "pkt-001", "source": "A", "destination": "D", "metric": "delay", "status": "forwarded", "route": {"source": "A", "destination": "D", "metric": "delay", "path": ["A", "B", "D"], "total_cost": "2", "topology_version": 1}, "trace": [{"hop_index": 0, "node": "A"}, {"hop_index": 1, "node": "B"}, {"hop_index": 2, "node": "D"}], "topology_version": 1, "error": null}
```

```json
{"recorded_at": "2026-11-05T14:05:40.017Z", "packet_id": "pkt-002", "source": "A", "destination": "D", "metric": "delay", "status": "failed", "route": null, "trace": [], "topology_version": null, "error": {"code": "CONTROLLER_UNAVAILABLE", "message": "No fue posible conectar con el Controller.", "details": {}}}
```

La bitácora no contiene `payload` ni datos personales.

**Modo nodo (C-32).** Cada instancia escribe en **su** `data/routers/<router_id>/forwarding.jsonl` una línea por paquete que procesa, con los mismos campos más `router_id` y `role` (`ingress`, `transit` o `egress`) al final; en `trace` cada salto incluye `router_url`; en las líneas `failed`, `trace` es `[]` y `error.details` incluye `at_router` (aclaración C-32.7). Además, `JsonForwardingTableDAO` reemplaza de forma atómica `forwarding-table.json` (`{"router_id", "url", "topology_version", "synced_at", "tables": {"delay": [filas], "inverse_bandwidth": [...], "loss": [...]}}`) y anexa a `table-events.jsonl` una línea por cambio de versión: `{"recorded_at", "router_id", "previous_version", "topology_version", "changes": [{"metric", "destination", "before", "after"}]}`, donde `before`/`after` son `{"next_hop", "total_cost", "status"}` (`before` nulo en la primera sincronización).

## 7. Versiones y sincronización

- `POST /links/fail` y `/links/restore` son atómicos dentro del único proceso Controller; `topology_version` aumenta solo con un cambio efectivo.
- `GET /route` calcula sobre una instantánea de una sola versión y la informa en `topology_version`. Si un enlace cambia después, el Router registra la versión recibida; no hay garantía de actualidad instantánea ni consistencia entre varias instancias.
- Los errores de red nunca se convierten en 200: siempre producen un fallo controlado con `status: "failed"` y se intenta registrarlos en la bitácora; si ese registro falla, la respuesta es 500 `LOG_PERSISTENCE_ERROR` (§4.2).
- **Modo nodo (C-32):** la tabla de un router pertenece a una única `topology_version`. Antes de cada paquete y cada `TABLE_SYNC_INTERVAL_SECONDS` el router consulta `GET /topology/version` y solo pide `GET /forwarding-table` (tres métricas) si la versión cambió (NFR-12). Todos los saltos de un paquete usan la misma versión; si un router encuentra otra, responde 409 `TOPOLOGY_CHANGED`. No hay garantía de que todas las instancias cambien de versión en el mismo instante: la cota es 2 × `TABLE_SYNC_INTERVAL_SECONDS`, o el siguiente paquete.
