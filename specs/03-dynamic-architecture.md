# 03 — Arquitectura dinámica: tres diagramas de secuencia

| Campo | Valor |
|---|---|
| Versión | **1.1** (borrador con C-32, aprobado por ambas el 31/10/2026; candidata a `spec-1.1`) · 2026-10-31 |
| Estado de aprobación | Ver `REVIEW-AND-BASELINE.md` |
| Reglas | Todo participante es una clase de `02` §3 (las interfaces `TopologyDAO` y `ForwardingLogDAO` se muestran por su tipo; en ejecución son `JsonTopologyDAO` y `JsonlForwardingLogDAO`). Toda petición HTTP coincide con `04`. Las flechas `-->>` son respuestas o propagación de excepciones, no llamadas nuevas. |

Datos comunes: fixture F-01 de `06` (grafo dirigido A→B, B→D con `delay_ms=1`; A→C, C→D con `delay_ms=2`), versión inicial 1, métrica `delay`.

## Secuencia 1 — Reenvío exitoso de un paquete

**Precondiciones:** ambos procesos activos; F-01 cargado por `JsonTopologyDAO`; bitácora escribible.
**Resultado:** el Router responde 200 `forwarded` con la traza `[A, B, D]`, idéntica a la ruta elegida por el Controller, después de registrar el resultado.

```mermaid
sequenceDiagram
    autonumber
    actor Cliente
    participant PA as PacketHTTP
    participant FS as ForwardingService
    participant RC as HttpRouteClient
    participant CA as ControllerHTTP
    participant RS as RoutingService
    participant TD as TopologyDAO
    participant BF as BellmanFordEngine
    participant CP as CostPresenter
    participant LD as ForwardingLogDAO
    Cliente->>PA: POST /packets {packet_id pkt-001, A→D, delay}
    Note over PA: PacketRequestSchema validado → Packet
    PA->>FS: forward(packet)
    FS->>RC: fetch_route(A, D, delay)
    RC->>CA: GET /route?src=A&dst=D&metric=delay
    CA->>RS: compute_route(A, D, delay)
    RS->>TD: get_topology()
    TD-->>RS: Topology (instantánea, version 1)
    RS->>BF: find_path(topology, A, D, delay)
    Note over BF: rondas Bellman-Ford exactas + desempate DEC-08
    BF-->>RS: ruta (A, B, D), score exacto 2
    RS->>CP: format_cost(2, delay)
    CP-->>RS: "2"
    RS-->>CA: Route [A, B, D], total_cost "2", version 1
    CA-->>RC: 200 RouteResponseSchema
    Note over RC: valida campos, extremos, ruta simple,<br/>formato de total_cost y versión
    RC-->>FS: Route
    Note over FS: trace = (0, A), (1, B), (2, D)
    FS->>LD: save(ForwardingResult forwarded)
    LD-->>FS: OK, línea JSONL anexada
    FS-->>PA: ForwardingResult
    PA-->>Cliente: 200 ForwardingResponseSchema
```

**Verificaciones:** el Router no ejecuta ningún algoritmo de rutas (TC-05); `trace[i].node == path[i]` (TC-06); `save` ocurre antes de la respuesta 200 (TC-06, TC-09); `RoutingService` pide una sola instantánea y llama una vez a `CostPresenter` (TC-08).

## Secuencia 2 — Fallo de enlace, nueva consulta y restauración

**Precondiciones:** F-01 recién cargado (versión 1); ruta inicial `[A, B, D]` con costo 2.
**Resultado:** tras fallar B→D, el siguiente paquete usa `[A, C, D]` con costo 4 (o, en una topología sin alternativa, recibe 404 `ROUTE_UNREACHABLE`); tras restaurar B→D vuelve a `[A, B, D]`. `topology_version` pasa de 1 a 2 y a 3.

```mermaid
sequenceDiagram
    autonumber
    actor Operador
    actor Cliente
    participant PA as PacketHTTP
    participant FS as ForwardingService
    participant RC as HttpRouteClient
    participant CA as ControllerHTTP
    participant RS as RoutingService
    participant TD as TopologyDAO
    participant BF as BellmanFordEngine
    participant CP as CostPresenter
    participant LD as ForwardingLogDAO
    Operador->>CA: POST /links/fail {source B, target D}
    CA->>RS: set_link_status(B, D, false)
    RS->>TD: set_link_status(B, D, false)
    Note over TD: active pasa a false, version 1 → 2
    TD-->>RS: LinkChangeResult changed true, version 2
    RS-->>CA: LinkChangeResult
    CA-->>Operador: 200 {active false, changed true, topology_version 2}
    Cliente->>PA: POST /packets {pkt-002, A→D, delay}
    PA->>FS: forward(packet)
    FS->>RC: fetch_route(A, D, delay)
    RC->>CA: GET /route?src=A&dst=D&metric=delay
    CA->>RS: compute_route(A, D, delay)
    RS->>TD: get_topology()
    TD-->>RS: Topology version 2 (B→D inactivo)
    RS->>BF: find_path(topology, A, D, delay)
    alt F-01: existe la ruta alternativa A→C→D
        BF-->>RS: ruta (A, C, D), score 4
        RS->>CP: format_cost(4, delay)
        CP-->>RS: "4"
        RS-->>CA: Route [A, C, D], version 2
        CA-->>RC: 200 RouteResponseSchema
        RC-->>FS: Route
        FS->>LD: save(ForwardingResult forwarded)
        LD-->>FS: OK
        FS-->>PA: ForwardingResult
        PA-->>Cliente: 200 forwarded, trace [A, C, D]
    else si no quedara ruta utilizable (p. ej. C→D también inactivo: TC-17)
        BF-->>RS: RouteUnreachableError
        RS-->>CA: RouteUnreachableError
        CA-->>RC: 404 ROUTE_UNREACHABLE
        RC-->>FS: RouteUnreachableError
        FS->>LD: save(ForwardingResult failed)
        LD-->>FS: OK
        FS-->>PA: RouteUnreachableError
        PA-->>Cliente: 404 ROUTE_UNREACHABLE, status failed, trace []
    end
    Operador->>CA: POST /links/restore {source B, target D}
    CA->>RS: set_link_status(B, D, true)
    RS->>TD: set_link_status(B, D, true)
    TD-->>RS: LinkChangeResult changed true, version 3
    RS-->>CA: LinkChangeResult
    CA-->>Operador: 200 {active true, changed true, topology_version 3}
    Cliente->>PA: POST /packets {pkt-003, A→D, delay}
    PA->>FS: forward(packet)
    FS->>RC: fetch_route(A, D, delay)
    RC->>CA: GET /route?src=A&dst=D&metric=delay
    CA->>RS: compute_route(A, D, delay)
    RS->>TD: get_topology()
    TD-->>RS: Topology version 3
    RS->>BF: find_path(topology, A, D, delay)
    BF-->>RS: ruta (A, B, D), score 2
    RS->>CP: format_cost(2, delay)
    CP-->>RS: "2"
    RS-->>CA: Route [A, B, D], version 3
    CA-->>RC: 200 RouteResponseSchema
    RC-->>FS: Route
    FS->>LD: save(ForwardingResult forwarded)
    LD-->>FS: OK
    FS-->>PA: ForwardingResult
    PA-->>Cliente: 200 forwarded, trace [A, B, D]
```

**Reglas:** en modo dirigido, fallar B→D no afecta a D→B. El Router no recuerda rutas: cada paquete genera una consulta nueva y observa el estado vigente (DEC-06). Repetir el fallo o la restauración devuelve 200 con `changed=false` sin cambiar la versión (DEC-04). Un enlace con `p=1` sigue excluido aunque se restaure (DEC-02). Pruebas: TC-03, TC-04, TC-17, TC-18.

## Secuencia 3 — Controller no disponible, lento o incoherente

**Precondiciones:** Router activo; Controller detenido, lento o con respuesta no conforme; timeouts `CONTROLLER_CONNECT_TIMEOUT_SECONDS` y `CONTROLLER_READ_TIMEOUT_SECONDS` configurados (`02` §7).
**Resultado:** el Router responde un error estable y documentado (503, 504 o 502; 500 si además falla la bitácora), registra el resultado `failed` y sigue vivo.

```mermaid
sequenceDiagram
    autonumber
    actor Cliente
    participant PA as PacketHTTP
    participant FS as ForwardingService
    participant RC as HttpRouteClient
    participant CA as ControllerHTTP
    participant LD as ForwardingLogDAO
    Cliente->>PA: POST /packets (paquete válido)
    PA->>FS: forward(packet)
    FS->>RC: fetch_route(src, dst, metric)
    alt Controller detenido: conexión rechazada
        RC-xCA: GET /route (la conexión no se establece)
        Note over RC: ConnectError → ControllerUnavailableError (503)
    else Controller lento o bloqueado: timeout de conexión o de lectura
        RC->>CA: GET /route
        Note over RC,CA: en un timeout de conexión la petición no llega a CA
        Note over RC: sin respuesta dentro del plazo → ControllerTimeoutError (504)
    else respuesta no conforme
        RC->>CA: GET /route
        CA-->>RC: JSON inválido, ruta incoherente o estado HTTP no previsto
        Note over CA: p. ej. un 500 del Controller (INTERNAL_ERROR, NEGATIVE_CYCLE),<br/>otra versión u otro proceso en CONTROLLER_URL (TC-31, TC-32)
        Note over RC: ControllerBadResponseError (502)
    end
    RC-->>FS: AppError normalizado
    FS->>LD: save(ForwardingResult failed, trace vacía, error)
    alt el registro se guarda
        LD-->>FS: OK
        FS-->>PA: relanza el mismo AppError
        PA-->>Cliente: 503, 504 o 502 {packet_id, status failed, trace [], error}
    else la bitácora falla
        LD-->>FS: LogPersistenceError
        FS-->>PA: LogPersistenceError
        PA-->>Cliente: 500 LOG_PERSISTENCE_ERROR (nunca 200)
    end
    Cliente->>PA: GET /health
    PA-->>Cliente: 200 {status ok, application router}
```

**Modelo de fallos:** `HttpRouteClient` convierte cada fallo de red (todo `httpx.TransportError`, incluida una conexión cortada a mitad de respuesta, que se trata como respuesta no conforme) en una subclase de `AppError`; `ForwardingService.forward` guarda un `ForwardingResult` con `packet_id`, `source`, `destination`, `metric`, `status="failed"`, `trace=()`, `route=None`, `topology_version=None` y `error`, y relanza **la misma** excepción; `router/http_errors.py` la traduce a `PacketErrorSchema` con el estado HTTP que su tabla asigna al `error.code` (las excepciones no llevan estado HTTP). El Router no reintenta, no usa caché y no calcula rutas (DEC-06). `GET /health` informa la vida del proceso, no la del Controller. Las respuestas no exponen la excepción original ni la dirección del Controller. Pruebas: TC-07, TC-31, TC-32, TC-33.

## Secuencia 4 — Reenvío salto a salto entre instancias Router (modo nodo, C-32)

**Precondiciones:** Controller con F-20 (o F-01) y cuatro instancias Router (A–D) en modo nodo, con sus tablas sincronizadas en la versión 1; métrica `delay`.
**Resultado:** cada salto es un `POST /forward` real a la URL del siguiente router según **su propia** tabla; la traza `A, B, D` coincide con `GET /route?src=A&dst=D&metric=delay`; cada router registra el paquete en su bitácora. Diagrama fuente: `diagrams/03-4-secuencia-salto-a-salto.mmd`.

```mermaid
sequenceDiagram
    autonumber
    actor Cliente
    participant NA as Router A (NodeHTTP + NodeForwardingService)
    participant NB as Router B (NodeHTTP + NodeForwardingService)
    participant ND as Router D (NodeHTTP + NodeForwardingService)
    participant CA as ControllerHTTP
    Cliente->>NA: POST /packets {pkt-1, A→D, delay}
    NA->>CA: GET /topology/version
    CA-->>NA: 200 {topology_version 1}
    Note over NA: versión igual a la tabla local → sin pedir tabla<br/>fila D: next_hop B · trace = (0, A)
    NA->>NB: POST /forward {pkt-1, trace [(0,A)], topology_version 1}
    NB->>CA: GET /topology/version
    CA-->>NB: 200 {topology_version 1}
    Note over NB: fila D: next_hop D · trace = (0,A), (1,B)
    NB->>ND: POST /forward {pkt-1, trace [(0,A),(1,B)], topology_version 1}
    ND->>CA: GET /topology/version
    CA-->>ND: 200 {topology_version 1}
    Note over ND: destino alcanzado · trace = (0,A), (1,B), (2,D)<br/>registra rol egress
    ND-->>NB: 200 forwarded, trace A, B, D
    Note over NB: valida prefijo, destino y versión · registra rol transit
    NB-->>NA: 200 forwarded, trace A, B, D
    Note over NA: valida y registra rol ingress
    NA-->>Cliente: 200 forwarded, route.path [A, B, D], trace con router_url
```

**Reglas:** cada router comprueba la versión con el Controller antes de decidir y solo pide su tabla si cambió (DEC-10, NFR-12); una versión distinta entre saltos produce 409 `TOPOLOGY_CHANGED`; un nodo repetido, 508 `FORWARDING_LOOP`; más saltos que nodos, 508 `HOP_LIMIT_EXCEEDED`; un siguiente router caído o lento, 503 `NEXT_HOP_UNAVAILABLE` o 504 `NEXT_HOP_TIMEOUT`, que se propagan hasta el origen con `status: "failed"` y registro `failed` en cada router que procesó el paquete. Pruebas: TC-46, TC-47.

## Secuencia 5 — Actualización de las tablas tras un fallo de enlace (modo nodo, C-32)

**Precondiciones:** F-20 recién cargado (versión 1); tablas sincronizadas. **Resultado:** tras fallar B–D, todas las instancias publican su tabla de la versión 2 en ≤ 2 × `TABLE_SYNC_INTERVAL_SECONDS` (o antes, al procesar un paquete), con los valores de `06` §3.1; al restaurar, la versión 3 recupera las filas originales. Diagrama fuente: `diagrams/03-5-secuencia-actualizacion-tablas.mmd`.

```mermaid
sequenceDiagram
    autonumber
    actor Operador
    participant CA as ControllerHTTP
    participant RS as RoutingService
    participant BF as BellmanFordEngine
    participant NA as Router A (sincronización periódica)
    participant TD as JsonForwardingTableDAO (A)
    Operador->>CA: POST /links/fail {source B, target D}
    CA->>RS: set_link_status(B, D, false)
    RS-->>CA: LinkChangeResult changed true, version 2
    CA-->>Operador: 200 {active false, changed true, topology_version 2}
    loop cada TABLE_SYNC_INTERVAL_SECONDS
        NA->>CA: GET /topology/version
        CA-->>NA: 200 {topology_version 2}
    end
    Note over NA: 2 ≠ 1 (versión guardada) → pedir las tres tablas
    NA->>CA: GET /forwarding-table?router_id=A&metric=delay
    CA->>RS: compute_forwarding_table(A, delay)
    RS->>BF: find_all_paths(topology v2, A, delay)
    BF-->>RS: mejores rutas desde A (un único núcleo)
    RS-->>CA: ForwardingTable v2: D → next_hop C, "4"
    CA-->>NA: 200 tabla delay v2
    Note over NA: ídem inverse_bandwidth y loss
    NA->>TD: save(NodeTables v2)
    TD-->>NA: forwarding-table.json reemplazado · línea en table-events.jsonl
    Note over NA: GET /forwarding-table (y /ui) muestran la tabla v2,<br/>con la versión sin cambios no se vuelve a pedir ninguna tabla (NFR-12)
```

**Reglas:** el Controller no conoce a los routers para sincronizar: cada router pregunta la versión (DEC-10). Un destino que queda sin camino aparece con `status: "unreachable"` y sin siguiente salto. Si el Controller no responde, el router conserva la última tabla, informa `sync_status: "error"` en `GET /status` y, al recibir un paquete, responde 503/504/502 (DEC-06). Pruebas: TC-44, TC-45.

## Matriz de consistencia secuencia → métodos → endpoints → pruebas

| Secuencia | Métodos (declarados en `02` §3) | Endpoints (`04`) | Requisitos | Pruebas |
|---|---|---|---|---|
| S1 | `PacketHTTP.post_packet`, `ForwardingService.forward`, `HttpRouteClient.fetch_route`, `ControllerHTTP.get_route`, `RoutingService.compute_route`, `TopologyDAO.get_topology`, `BellmanFordEngine.find_path`, `CostPresenter.format_cost`, `ForwardingLogDAO.save` | `POST /packets`, `GET /route` | FR-01, FR-03, FR-05, FR-07, FR-08, FR-10 | TC-01, TC-05, TC-06, TC-08, TC-09 |
| S2 | `ControllerHTTP.fail_link`, `ControllerHTTP.restore_link`, `RoutingService.set_link_status`, `TopologyDAO.set_link_status` y los métodos de S1 | `POST /links/fail`, `POST /links/restore`, `GET /route`, `POST /packets` | FR-06, FR-07, FR-09 | TC-03, TC-04, TC-17, TC-18 |
| S3 | `PacketHTTP.post_packet`, `PacketHTTP.health`, `ForwardingService.forward`, `HttpRouteClient.fetch_route`, `ForwardingLogDAO.save` | `POST /packets`, `GET /route`, `GET /health` | FR-07, FR-09, FR-10, NFR-06 | TC-07, TC-31, TC-32, TC-33 |
| S4 *(C-32)* | `NodeHTTP.post_packet`, `NodeHTTP.forward`, `NodeForwardingService.handle`, `NodeForwardingService.sync_if_changed`, `TableClient.fetch_topology_version`, `NextHopClient.forward`, `ForwardingLogDAO.save` | `POST /packets`, `POST /forward`, `GET /topology/version` | FR-07, FR-11, FR-13 | TC-46, TC-47 |
| S5 *(C-32)* | `ControllerHTTP.fail_link`, `RoutingService.set_link_status`, `NodeForwardingService.sync_if_changed`, `TableClient.fetch_forwarding_table`, `RoutingService.compute_forwarding_table`, `BellmanFordEngine.find_all_paths`, `ForwardingTableDAO.save` | `POST /links/fail`, `POST /links/restore`, `GET /topology/version`, `GET /forwarding-table` | FR-06, FR-12, NFR-12 | TC-44, TC-45 |

**Concurrencia:** `get_topology()` devuelve una instantánea inmutable; el DAO protege su estado y su versión con un candado de proceso, de modo que una consulta nunca mezcla dos versiones. No se garantiza consistencia entre varias instancias del Controller (fuera de alcance).
