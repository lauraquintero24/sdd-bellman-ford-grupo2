# 04 — Contrato REST/HTTP + JSON

| Campo | Valor |
|---|---|
| Versión | **1.0** (candidata a baseline `spec-1.0`) · 2026-10-29 |
| Estado de aprobación | Ver `REVIEW-AND-BASELINE.md` |
| Bases por defecto | Controller `http://127.0.0.1:8000` · Router `http://127.0.0.1:8001` (configurables, `02` §7) |

## 1. Convenciones

- Cuerpos `application/json` en UTF-8; nombres `snake_case`; sin `NaN` ni `Infinity`. Los identificadores (`src`, `dst`, `source`, `target`, `destination`, `packet_id`) son cadenas no vacías y sin espacios en los extremos (un ID con espacios en los extremos es entrada inválida: 400 `INVALID_REQUEST`, antes de buscarlo en la topología); `metric` es obligatoria y vale `delay`, `inverse_bandwidth` o `loss`. No existen opciones de desempate en la petición: DEC-08 se aplica siempre. Los cuerpos de petición no admiten campos adicionales (`extra="forbid"`: 400 `INVALID_REQUEST`); los parámetros de consulta desconocidos se ignoran.
- **Errores:** sobre normalizado `{"error": {"code": "...", "message": "...", "details": {...}}}`. `code` y la estructura son estables; `message` es informativo y puede variar. Ninguna respuesta incluye trazas Python, rutas de archivo ni direcciones internas. El Router añade `packet_id`, `status: "failed"` y `trace: []` cuando el paquete ya fue validado.
- **Códigos HTTP (DEC-03, conforme al ejemplo del PDF p. 4):** 400 para toda entrada inválida; 404 para nodo, enlace o camino ausente, distinguidos por `error.code`; 502/503/504 para fallos del Controller vistos por el Router; 500 para fallos internos, de la bitácora o del invariante `NEGATIVE_CYCLE`. Fuera del contrato, una ruta o un método inexistentes reciben 404 `UNKNOWN_ENDPOINT` o 405 `METHOD_NOT_ALLOWED` con el mismo sobre `error`. No se usa ningún otro código de error.
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

## 6. Contrato de datos persistidos (bitácora del Router)

`JsonlForwardingLogDAO` anexa **una línea JSON por resultado** al archivo `FORWARDING_LOG_FILE`, con los campos de `ForwardingResult` (`packet_id`, `source`, `destination`, `metric`, `status`, `route`, `trace`, `topology_version`, `error`) más `recorded_at`, asignado por el DAO en UTC con el formato fijo `AAAA-MM-DDTHH:MM:SS.mmmZ` (milisegundos y sufijo `Z`). En los resultados `failed`, `route` y `topology_version` son `null`, `trace` es `[]` y `error` contiene `code`, `message` y `details`; así cada línea identifica qué se pidió aunque fallara. `ForwardingLogDAO.list_recent(limit)` relee estas líneas. Ejemplos de línea (valores ilustrativos):

```json
{"recorded_at": "2026-11-05T14:03:12.481Z", "packet_id": "pkt-001", "source": "A", "destination": "D", "metric": "delay", "status": "forwarded", "route": {"source": "A", "destination": "D", "metric": "delay", "path": ["A", "B", "D"], "total_cost": "2", "topology_version": 1}, "trace": [{"hop_index": 0, "node": "A"}, {"hop_index": 1, "node": "B"}, {"hop_index": 2, "node": "D"}], "topology_version": 1, "error": null}
```

```json
{"recorded_at": "2026-11-05T14:05:40.017Z", "packet_id": "pkt-002", "source": "A", "destination": "D", "metric": "delay", "status": "failed", "route": null, "trace": [], "topology_version": null, "error": {"code": "CONTROLLER_UNAVAILABLE", "message": "No fue posible conectar con el Controller.", "details": {}}}
```

La bitácora no contiene `payload` ni datos personales.

## 7. Versiones y sincronización

- `POST /links/fail` y `/links/restore` son atómicos dentro del único proceso Controller; `topology_version` aumenta solo con un cambio efectivo.
- `GET /route` calcula sobre una instantánea de una sola versión y la informa en `topology_version`. Si un enlace cambia después, el Router registra la versión recibida; no hay garantía de actualidad instantánea ni consistencia entre varias instancias.
- Los errores de red nunca se convierten en 200: siempre producen un fallo controlado con `status: "failed"` y se intenta registrarlos en la bitácora; si ese registro falla, la respuesta es 500 `LOG_PERSISTENCE_ERROR` (§4.2).
