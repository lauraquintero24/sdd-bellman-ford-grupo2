# 02 — Arquitectura estática: componentes, clases, MVC, DAO e inyección de dependencias

| Campo | Valor |
|---|---|
| Versión | **1.0** (candidata a baseline `spec-1.0`) · 2026-10-29 |
| Estado de aprobación | Ver `REVIEW-AND-BASELINE.md` |
| Trazabilidad | FR-01–FR-10, NFR-01–NFR-11, DEC-01–DEC-09 (`01`) · secuencias en `03` · contrato en `04` |

## 1. Reglas arquitectónicas vinculantes

1. **Dos procesos independientes.** `controller` (plano de control) y `router` (plano de datos simulado) se ejecutan como procesos separados del sistema operativo, sin memoria, DAO ni archivos de estado compartidos. Solo se comunican por HTTP/JSON.
2. **Solo el Controller calcula rutas.** El Router no importa NetworkX ni código del Controller; obtiene cada ruta con `GET /route` (DEC-06).
3. **MVC en ambas aplicaciones** (PDF p. 2): **Model** = objetos de dominio (`Topology`, `Link`, `Route`, `Packet`, `ForwardingResult`); **View** = esquemas Pydantic de entrada y salida HTTP; **Controller MVC** = clases `*HTTP` con los handlers FastAPI, que solo validan, delegan en servicios y serializan. La lógica de negocio vive en **servicios de dominio**. Aquí «Controller» como aplicación no se confunde con el controlador HTTP de MVC.
4. **DAO en ambas aplicaciones:** `TopologyDAO` encapsula la obtención y el estado de la topología; `ForwardingLogDAO` encapsula el almacenamiento y la consulta de resultados de reenvío.
5. **Regla de diseño (PDF p. 2):** ni los controladores HTTP ni los servicios abren archivos ni conocen implementaciones concretas de DAO; los servicios dependen de **interfaces** (módulos `ports.py`) recibidas por **inyección de dependencias** en su constructor. Las implementaciones concretas solo se crean en la raíz de composición (`create_controller_app`, `create_router_app`).
6. **Semántica HTTP solo en los adaptadores.** Las excepciones de dominio llevan un código (`error.code`) pero no un estado HTTP; la correspondencia código → estado vive únicamente en `controller/http_errors.py` y `router/http_errors.py`.

## 2. Diagrama de componentes

```mermaid
flowchart LR
    CLI["Cliente HTTP / Operador"]
    subgraph CTRL["Proceso Controller · CONTROLLER_PORT, por defecto 8000"]
        direction TB
        C_COMP["create_controller_app<br/>raíz de composición DI"]
        C_HTTP["Controller MVC<br/>ControllerHTTP + http_errors"]
        C_VIEW["View<br/>esquemas Pydantic"]
        C_RS["Servicio de dominio<br/>RoutingService"]
        C_BF["Servicio de dominio<br/>BellmanFordEngine + LinkCostPolicy"]
        C_CP["Servicio de dominio<br/>CostPresenter"]
        C_MOD["Model<br/>Topology · Link · LinkChangeResult"]
        C_DAOI["«interfaz» TopologyDAO<br/>ports.py"]
        C_DAO["DAO concreto<br/>JsonTopologyDAO"]
    end
    subgraph RTR["Proceso Router · ROUTER_PORT, por defecto 8001"]
        direction TB
        R_COMP["create_router_app<br/>raíz de composición DI"]
        R_HTTP["Controller MVC<br/>PacketHTTP + http_errors"]
        R_VIEW["View<br/>esquemas Pydantic"]
        R_FS["Servicio de dominio<br/>ForwardingService"]
        R_MOD["Model<br/>Packet · ForwardingResult · TraceHop"]
        R_RCI["«interfaz» RouteClient<br/>ports.py"]
        R_HRC["Cliente HTTP<br/>HttpRouteClient"]
        R_DAOI["«interfaz» ForwardingLogDAO<br/>ports.py"]
        R_DAO["DAO concreto<br/>JsonlForwardingLogDAO"]
    end
    SH["shared/ · contratos puros<br/>Route · AppError y subclases · códigos · formato de costo"]
    subgraph PERS["Frontera de persistencia · sistema de archivos"]
        TF[("topology.json<br/>lectura única al arrancar")]
        LF[("forwarding.jsonl<br/>solo anexado")]
    end
    CLI -->|"GET /topology · GET /route · POST /links/fail · POST /links/restore · GET /health"| C_HTTP
    CLI -->|"POST /packets · GET /health"| R_HTTP
    C_HTTP --> C_VIEW
    C_HTTP --> C_RS
    C_RS --> C_DAOI
    C_RS --> C_BF
    C_RS --> C_CP
    C_RS --> C_MOD
    C_BF --> C_MOD
    C_DAO -. implementa .-> C_DAOI
    C_DAO --> TF
    C_COMP -. crea .-> C_DAO
    C_COMP -. inyecta .-> C_RS
    R_HTTP --> R_VIEW
    R_HTTP --> R_FS
    R_FS --> R_RCI
    R_FS --> R_DAOI
    R_FS --> R_MOD
    R_HRC -. implementa .-> R_RCI
    R_DAO -. implementa .-> R_DAOI
    R_DAO --> LF
    R_COMP -. crea .-> R_DAO
    R_COMP -. crea .-> R_HRC
    R_COMP -. inyecta .-> R_FS
    R_HRC ==>|"REST: GET /route · HTTP/JSON"| C_HTTP
    CTRL -. importa .-> SH
    RTR -. importa .-> SH
```

**Lectura del diagrama.** Las flechas continuas son dependencias de llamada; las punteadas, implementación, creación o importación. Solo los DAO concretos cruzan la **frontera de persistencia**: `JsonTopologyDAO` lee `topology.json` una vez al arrancar y conserva el estado mutable en memoria; `JsonlForwardingLogDAO` anexa una línea por resultado y las relee para consultas. `shared/` es un paquete instalable (o copiado de forma idéntica) en ambos procesos que solo contiene contratos de datos, excepciones y funciones puras, sin FastAPI, Pydantic, NetworkX, httpx ni estado.

## 3. Diagrama de clases

El modelo se presenta en tres vistas que muestran la **propiedad** de cada clase (PDF p. 4): Controller (Estudiante A), Router (Estudiante B) y contratos compartidos. `«interface»` marca los puertos inyectables. `Route` (módulo `shared/models.py`) se detalla en la vista Controller porque su propietaria es la Estudiante A; en la vista Router aparece como referencia `«shared»`. Las clases `«module»` representan módulos con funciones (adaptadores de errores), no clases instanciables. Los constructores usan la notación UML (nombre de la clase), que en Python corresponde a `__init__`; los parámetros con `= None` son opcionales. Los atributos privados que corresponden a dependencias (`dao`, `engine`, `presenter`, `client`, `log_dao`) se reciben por inyección; `policy`, `state` y `lock` son internos.

### 3.1 Vista Controller (propietaria: Estudiante A)

```mermaid
classDiagram
    direction TB
    class Link {
        +str source
        +str target
        +Decimal delay_ms
        +Decimal bandwidth_mbps
        +Decimal loss_probability
        +bool active
        +is_usable() bool
    }
    class Topology {
        +bool directed
        +int version
        +tuple~str~ nodes
        +tuple~Link~ links
        +has_node(node_id: str) bool
        +find_link(source: str, target: str) Link
    }
    class LinkChangeResult {
        +str source
        +str target
        +bool active
        +bool changed
        +int topology_version
    }
    class TopologyDAO {
        <<interface>>
        +get_topology() Topology
        +set_link_status(source: str, target: str, active: bool) LinkChangeResult
    }
    class JsonTopologyDAO {
        -Path path
        -Topology state
        -Lock lock
        +JsonTopologyDAO(path: Path)
        +get_topology() Topology
        +set_link_status(source: str, target: str, active: bool) LinkChangeResult
    }
    class TopologyLoadError {
        <<exception>>
        +str rule
        +str detail
    }
    class LinkCostPolicy {
        +weight(link: Link, metric: str) Fraction
    }
    class RouteLabel {
        +Fraction score
        +int hops
        +tuple~str~ path
    }
    class PathScore {
        +tuple~str~ path
        +Fraction score
    }
    class BellmanFordEngine {
        -LinkCostPolicy policy
        +BellmanFordEngine()
        +find_path(topology: Topology, src: str, dst: str, metric: str) PathScore
        +run_bellman_ford_on_weighted_graph(graph: nx.Graph, src: str, mode: str) dict~str, RouteLabel~
    }
    class CostPresenter {
        +format_cost(score: Fraction, metric: str) str
    }
    class RoutingService {
        -TopologyDAO dao
        -BellmanFordEngine engine
        -CostPresenter presenter
        +RoutingService(dao: TopologyDAO, engine: BellmanFordEngine, presenter: CostPresenter)
        +read_topology() Topology
        +compute_route(src: str, dst: str, metric: str) Route
        +set_link_status(source: str, target: str, active: bool) LinkChangeResult
    }
    class ControllerHTTP {
        <<Controller MVC>>
        -RoutingService service
        +ControllerHTTP(service: RoutingService)
        +get_topology() TopologyResponseSchema
        +get_route(src: str, dst: str, metric: str) RouteResponseSchema
        +fail_link(LinkRequestSchema) LinkStatusSchema
        +restore_link(LinkRequestSchema) LinkStatusSchema
        +health() ControllerHealthSchema
    }
    class TopologyResponseSchema {
        <<View>>
        +int topology_version
        +bool directed
        +list~str~ nodes
        +list~LinkSchema~ links
    }
    class LinkSchema {
        <<View>>
        +str source
        +str target
        +Decimal delay_ms
        +Decimal bandwidth_mbps
        +Decimal loss_probability
        +bool active
    }
    class RouteResponseSchema {
        <<View>>
        +str source
        +str destination
        +str metric
        +list~str~ path
        +str total_cost
        +int topology_version
    }
    class LinkRequestSchema {
        <<View>>
        +str source
        +str target
    }
    class LinkStatusSchema {
        <<View>>
        +str source
        +str target
        +bool active
        +bool changed
        +int topology_version
    }
    class ControllerHealthSchema {
        <<View>>
        +str status
        +str application
    }
    class ControllerSettings {
        +str host
        +int port
        +Path topology_file
    }
    class ErrorBodySchema {
        <<View>>
        +str code
        +str message
        +dict details
    }
    class ControllerHttpErrors {
        <<module http_errors.py>>
        +install_error_handlers(app: FastAPI) None
    }
    class ControllerComposition {
        <<composition root>>
        +create_controller_app(settings: ControllerSettings, dao: TopologyDAO = None) FastAPI
    }
    class Route {
        <<shared, dataclass inmutable>>
        +str source
        +str destination
        +str metric
        +tuple~str~ path
        +str total_cost
        +int topology_version
    }
    Topology "1" *-- "0..*" Link : contiene
    TopologyDAO <|.. JsonTopologyDAO
    JsonTopologyDAO "1" o-- "1" Topology : estado vigente
    JsonTopologyDAO ..> LinkChangeResult : devuelve
    JsonTopologyDAO ..> TopologyLoadError : lanza al cargar
    RoutingService "1" --> "1" TopologyDAO : inyectada
    RoutingService "1" --> "1" BellmanFordEngine : inyectado
    RoutingService "1" --> "1" CostPresenter : inyectado
    RoutingService ..> Route : crea
    BellmanFordEngine "1" *-- "1" LinkCostPolicy
    BellmanFordEngine ..> RouteLabel : usa
    BellmanFordEngine ..> PathScore : devuelve
    BellmanFordEngine ..> Topology : lee
    ControllerHTTP "1" --> "1" RoutingService : invoca
    ControllerHTTP ..> TopologyResponseSchema
    ControllerHTTP ..> RouteResponseSchema
    ControllerHTTP ..> LinkRequestSchema
    ControllerHTTP ..> LinkStatusSchema
    ControllerHTTP ..> ControllerHealthSchema
    TopologyResponseSchema "1" *-- "0..*" LinkSchema
    ControllerComposition ..> ControllerSettings : lee
    ControllerComposition ..> JsonTopologyDAO : crea si no se inyecta dao
    ControllerComposition ..> RoutingService : crea e inyecta
    ControllerComposition ..> ControllerHTTP : registra
    ControllerComposition ..> ControllerHttpErrors : instala
    ControllerHttpErrors ..> ErrorBodySchema : serializa errores
```

### 3.2 Vista Router (propietaria: Estudiante B)

```mermaid
classDiagram
    direction LR
    class Packet {
        +str packet_id
        +str source
        +str destination
        +str payload
        +str metric
    }
    class TraceHop {
        +int hop_index
        +str node
    }
    class ForwardingResult {
        +str packet_id
        +str source
        +str destination
        +str metric
        +str status
        +tuple~TraceHop~ trace
        +Optional~Route~ route
        +Optional~int~ topology_version
        +Optional~dict~ error
    }
    class RouteClient {
        <<interface>>
        +fetch_route(src: str, dst: str, metric: str) Route
    }
    class HttpRouteClient {
        -str base_url
        -float connect_timeout_s
        -float read_timeout_s
        -httpx.Client http
        +HttpRouteClient(base_url: str, connect_timeout_s: float, read_timeout_s: float, transport: httpx.BaseTransport = None)
        +fetch_route(src: str, dst: str, metric: str) Route
    }
    class ForwardingLogDAO {
        <<interface>>
        +save(result: ForwardingResult) None
        +list_recent(limit: int) list~ForwardingResult~
    }
    class JsonlForwardingLogDAO {
        -Path path
        -Lock lock
        +JsonlForwardingLogDAO(path: Path)
        +save(result: ForwardingResult) None
        +list_recent(limit: int) list~ForwardingResult~
    }
    class ForwardingService {
        -RouteClient client
        -ForwardingLogDAO log_dao
        +ForwardingService(client: RouteClient, log_dao: ForwardingLogDAO)
        +forward(packet: Packet) ForwardingResult
    }
    class PacketHTTP {
        <<Controller MVC>>
        -ForwardingService service
        +PacketHTTP(service: ForwardingService)
        +post_packet(PacketRequestSchema) ForwardingResponseSchema
        +health() RouterHealthSchema
    }
    class PacketRequestSchema {
        <<View>>
        +str packet_id
        +str source
        +str destination
        +str payload = ""
        +str metric
    }
    class ForwardingResponseSchema {
        <<View>>
        +str packet_id
        +str status
        +RouteSchema route
        +list~TraceHopSchema~ trace
        +int topology_version
    }
    class RouteSchema {
        <<View>>
        +str source
        +str destination
        +str metric
        +list~str~ path
        +str total_cost
        +int topology_version
    }
    class TraceHopSchema {
        <<View>>
        +int hop_index
        +str node
    }
    class RouterHealthSchema {
        <<View>>
        +str status
        +str application
    }
    class RouterSettings {
        +str host
        +int port
        +str controller_url
        +float connect_timeout_s
        +float read_timeout_s
        +Path log_file
    }
    class PacketErrorSchema {
        <<View>>
        +str packet_id
        +str status
        +list~TraceHopSchema~ trace
        +ErrorBodySchema error
    }
    class ErrorBodySchema {
        <<View>>
        +str code
        +str message
        +dict details
    }
    class RouterHttpErrors {
        <<module http_errors.py>>
        +install_error_handlers(app: FastAPI) None
    }
    class RouterComposition {
        <<composition root>>
        +create_router_app(settings: RouterSettings, route_client: RouteClient = None, log_dao: ForwardingLogDAO = None) FastAPI
    }
    class Route {
        <<shared>>
    }
    RouteClient <|.. HttpRouteClient
    ForwardingLogDAO <|.. JsonlForwardingLogDAO
    ForwardingService "1" --> "1" RouteClient : inyectada
    ForwardingService "1" --> "1" ForwardingLogDAO : inyectada
    ForwardingService ..> Packet : recibe
    ForwardingService ..> ForwardingResult : crea
    ForwardingResult "1" *-- "0..*" TraceHop : traza
    ForwardingResult "1" --> "0..1" Route : ruta usada
    HttpRouteClient ..> Route : valida y crea
    PacketHTTP "1" --> "1" ForwardingService : invoca
    PacketHTTP ..> PacketRequestSchema
    PacketHTTP ..> ForwardingResponseSchema
    PacketHTTP ..> RouterHealthSchema
    ForwardingResponseSchema "1" *-- "1" RouteSchema
    ForwardingResponseSchema "1" *-- "1..*" TraceHopSchema
    RouterComposition ..> RouterSettings : lee
    RouterComposition ..> HttpRouteClient : crea si no se inyecta route_client
    RouterComposition ..> JsonlForwardingLogDAO : crea si no se inyecta log_dao
    RouterComposition ..> ForwardingService : crea e inyecta
    RouterComposition ..> PacketHTTP : registra
    RouterComposition ..> RouterHttpErrors : instala
    RouterHttpErrors ..> PacketErrorSchema : errores de paquetes validados
    RouterHttpErrors ..> ErrorBodySchema : errores de entrada
    PacketErrorSchema "1" *-- "1" ErrorBodySchema
```

### 3.3 Vista de excepciones compartidas (`shared/errors.py`)

`Route` (`shared/models.py`) se detalla en §3.1. Esta vista muestra la jerarquía de excepciones de `shared/errors.py`.

```mermaid
classDiagram
    direction TB
    class AppError {
        <<exception>>
        +str code
        +str message
        +dict details
        +to_dict() dict
    }
    class InvalidRequestError {
        +code = "INVALID_REQUEST"
    }
    class NodeNotFoundError {
        +code = "NODE_NOT_FOUND"
    }
    class LinkNotFoundError {
        +code = "LINK_NOT_FOUND"
    }
    class RouteUnreachableError {
        +code = "ROUTE_UNREACHABLE"
    }
    class NegativeCycleError {
        +code = "NEGATIVE_CYCLE"
    }
    class LogPersistenceError {
        +code = "LOG_PERSISTENCE_ERROR"
    }
    class ControllerBadResponseError {
        +code = "CONTROLLER_BAD_RESPONSE"
    }
    class ControllerUnavailableError {
        +code = "CONTROLLER_UNAVAILABLE"
    }
    class ControllerTimeoutError {
        +code = "CONTROLLER_TIMEOUT"
    }
    AppError <|-- InvalidRequestError
    AppError <|-- NodeNotFoundError
    AppError <|-- LinkNotFoundError
    AppError <|-- RouteUnreachableError
    AppError <|-- NegativeCycleError
    AppError <|-- LogPersistenceError
    AppError <|-- ControllerBadResponseError
    AppError <|-- ControllerUnavailableError
    AppError <|-- ControllerTimeoutError
```

Además de estas clases, `shared/` contiene `error_contract.py` (constantes de `error.code` y nombres de campos JSON) y `cost_format.py` (función pura `is_canonical_cost(text: str) -> bool` que implementa la gramática de `01` §5.3). `MALFORMED_JSON` e `INTERNAL_ERROR` no son subclases de `AppError`: los generan los adaptadores HTTP (§9). `TopologyLoadError` pertenece al Controller y nunca se traduce a HTTP: aborta el arranque.

## 4. Correspondencia MVC/DAO y responsabilidades

| Capa | Controller (Estudiante A) | Router (Estudiante B) | Responsabilidad | Puede depender de |
|---|---|---|---|---|
| Model | `Topology`, `Link`, `LinkChangeResult` (`controller/models.py`); `Route` (`shared/models.py`) | `Packet`, `ForwardingResult`, `TraceHop` (`router/models.py`); `Route` | Objetos de dominio inmutables, sin E/S y **sin validación** (la validación de topologías la hace solo `JsonTopologyDAO`; así una prueba puede construir un `Topology` con pesos negativos, TC-11) | Biblioteca estándar |
| View | `TopologyResponseSchema`, `LinkSchema`, `RouteResponseSchema`, `LinkRequestSchema`, `LinkStatusSchema`, `ControllerHealthSchema`, `ErrorBodySchema` (`controller/view.py`) | `PacketRequestSchema`, `ForwardingResponseSchema`, `RouteSchema`, `TraceHopSchema`, `RouterHealthSchema`, `ErrorBodySchema`, `PacketErrorSchema` (`router/view.py`) | Esquemas Pydantic de entrada y salida HTTP (`extra="forbid"` en las entradas) | Pydantic, Model |
| Controller MVC | `ControllerHTTP` (`controller/http.py`) + `controller/http_errors.py` | `PacketHTTP` (`router/http.py`) + `router/http_errors.py` | Validar con View, invocar el servicio, serializar; traducir excepciones a HTTP | Servicio, View, FastAPI |
| Servicio de dominio | `RoutingService` (`service.py`), `BellmanFordEngine`, `LinkCostPolicy`, `RouteLabel`, `PathScore` (`engine.py`), `CostPresenter` (`presenter.py`) | `ForwardingService` (`service.py`) | Reglas de negocio: elegir rutas; construir trazas y registrar resultados | `ports.py`, Model, `shared`; NetworkX solo en `engine.py` |
| Puertos (interfaces) | `TopologyDAO` (`controller/ports.py`) | `RouteClient`, `ForwardingLogDAO` (`router/ports.py`) | Contratos abstractos que usan los servicios | Model, `shared` |
| DAO concreto | `JsonTopologyDAO`, `TopologyLoadError` (`controller/dao.py`) | `JsonlForwardingLogDAO` (`router/dao.py`) | Leer, validar y mantener la topología; anexar y releer resultados | `ports.py`, sistema de archivos |
| Cliente de comunicación | — | `HttpRouteClient` (`router/client.py`) | Obtener y validar la ruta por HTTP; normalizar errores de red | `ports.py`, httpx, `shared` |
| Composición | `create_controller_app` (`controller/app.py`) | `create_router_app` (`router/app.py`) | Leer configuración, crear implementaciones e inyectarlas | Todo su propio proceso y `shared` |

**`CostPresenter` y `Route.total_cost`.** `Route` no es un objeto interno del motor sino el contrato de datos que viaja al Router, y el contrato define `total_cost` como cadena canónica (`01` §5.3). Por eso `RoutingService` invoca `CostPresenter` antes de crear `Route`; la selección nunca usa ese campo, porque el motor trabaja solo con `PathScore`. Los `Settings` de cada proceso viven en `settings.py` (§8).

## 5. Contratos de métodos públicos

| Operación | Firma y comportamiento | Prohibido |
|---|---|---|
| `TopologyDAO.get_topology()` | `() -> Topology`: instantánea inmutable y consistente con su `version`. | Que un servicio lea el archivo JSON. |
| `TopologyDAO.set_link_status(source, target, active)` | `-> LinkChangeResult`; cambio atómico bajo `lock`; `version += 1` solo si `active` cambia; `NodeNotFoundError` si un extremo no existe; `LinkNotFoundError` si no hay enlace; en modo no dirigido `(A,B)` y `(B,A)` designan el mismo enlace. | Que un handler edite el estado. |
| `RoutingService.read_topology()` | `-> Topology` vía DAO (usado por `GET /topology`). | Acceso directo a archivos. |
| `RoutingService.compute_route(src, dst, metric)` | `-> Route`; valida `metric` (`InvalidRequestError`); pide **una** instantánea al DAO y comprueba en ella `src` y después `dst` (`NodeNotFoundError`); llama a `engine.find_path`; después llama **una vez** a `presenter.format_cost(score, metric)`; construye `Route(source=…, destination=…, metric=…, path=…, total_cost=…, topology_version=snapshot.version)` con argumentos nombrados. | Algoritmo en HTTP o DAO. |
| `RoutingService.set_link_status(source, target, active)` | `-> LinkChangeResult`; delega en el DAO. | Decidir rutas. |
| `BellmanFordEngine.find_path(topology, src, dst, metric)` | `-> PathScore(path, score)`: ruta simple y puntuación exacta (suma para `delay`/`inverse_bandwidth`, producto de supervivencia para `loss`); lanza `RouteUnreachableError` o `NegativeCycleError`; **no conoce** a `CostPresenter` ni produce JSON. Salvo el caso trivial `src == dst` (que devuelve `[src]` sin invocar el núcleo), siempre llama a `run_bellman_ford_on_weighted_graph`. | Ejecutarse en el Router. |
| `BellmanFordEngine.run_bellman_ford_on_weighted_graph(graph, src, mode)` | `mode ∈ {"additive", "product"}` → `dict[str, RouteLabel]`; núcleo común de relajación, desempate y detección de ciclo negativo en ambos modos (§6.2); `graph` es un `nx.Graph` o un `nx.DiGraph` (subclase de `nx.Graph`) con el peso de cada arco en el atributo `weight` (`Fraction`; en modo `product`, el factor `1 − p`). | Una rama de algoritmo exclusiva para pruebas. |
| `LinkCostPolicy.weight(link, metric)` | `-> Fraction`: `d`, `1/b` o factor `1 − p` (equivalente multiplicativo de `−ln(1−p)`). | Redondear antes de seleccionar. |
| `CostPresenter.format_cost(score, metric)` | `-> str` que cumple `is_canonical_cost` y la precisión de `01` §5.3 (§6.3). | Influir en la selección. |
| `HttpRouteClient.fetch_route(src, dst, metric)` | `-> Route`; un `GET /route` con timeouts de conexión y lectura; valida la respuesta (`04` §4.3) usando `shared.cost_format.is_canonical_cost`; convierte **todo** `httpx.TransportError` y toda respuesta no conforme en una de las excepciones de §9. El parámetro opcional `transport` permite inyectar `httpx.MockTransport` en pruebas. | Recalcular costos u optimalidad. |
| `ForwardingService.forward(packet)` | `-> ForwardingResult`; llama una vez a `client.fetch_route`; construye `trace` igual a `path`; llama una vez a `log_dao.save(result)` antes de devolver. Ante **cualquier** excepción del cliente guarda un resultado `failed` (con `error.code` de la excepción, o `INTERNAL_ERROR` si no es `AppError`) y relanza la misma excepción. Si `save` lanza cualquier excepción, la envuelve en `LogPersistenceError` (defensa adicional al contrato del DAO). | Acceder a archivos o calcular rutas. |
| `ForwardingLogDAO.save(result)` | `-> None` solo si la línea quedó escrita; los errores de E/S se convierten en `LogPersistenceError`. | Escribir desde un handler. |
| `ForwardingLogDAO.list_recent(limit)` | `-> list[ForwardingResult]`: los `limit` últimos resultados en orden de escritura (recuperación exigida por el PDF p. 2; usado por TC-06 y TC-16). | Exponerlo por HTTP (no hay endpoint). |
| `ControllerHTTP.*`, `PacketHTTP.*` | Reciben esquemas ya validados, invocan un método del servicio y devuelven esquemas de respuesta. | Leer archivos o ejecutar algoritmos. |

## 6. Diseño interno del motor de rutas y del presentador de costos

### 6.1 Construcción del grafo

`find_path` toma la instantánea `Topology`, descarta enlaces con `active=false` o `loss_probability=1` y crea un `nx.DiGraph` (dirigido) o `nx.Graph` (no dirigido, cuyos enlaces se recorren en ambos sentidos). Cada arco guarda su peso exacto en el atributo de arista **`weight`** (`graph[u][v]["weight"]`, de tipo `Fraction`), calculado por `LinkCostPolicy`: `d` o `1/b` en modo `additive`; `1 − p` en modo `product` (métrica `loss`). Si `src == dst`, devuelve directamente `PathScore((src,), 0)` en modo aditivo o `PathScore((src,), 1)` en modo producto, sin invocar el núcleo (la ruta vacía es óptima con pesos no negativos).

**Por qué no se usa directamente `nx.bellman_ford_path`:** devuelve una de las rutas de igual costo según el orden de iteración (no garantiza DEC-08) y no admite el modo producto exacto de `loss`. NetworkX se usa para representar el grafo y, en las pruebas, como oráculo independiente: `bellman_ford_path_length` para el costo de `delay` e `inverse_bandwidth`, y `bellman_ford_predecessor_and_distance` (que lanza `NetworkXUnbounded` solo si el ciclo negativo es alcanzable desde el origen) para TC-11.

### 6.2 Núcleo de relajación (especificación, no código)

```text
run_bellman_ford_on_weighted_graph(graph, src, mode):
    label[src] = RouteLabel(score = 0 si mode=="additive" si no 1, hops = 0, path = (src,))
    los demás nodos: sin etiqueta (inalcanzables)
    repetir |V| − 1 rondas síncronas:
        nuevo = copia(label)                      # solo se extienden etiquetas de la ronda anterior
        para cada arco u→v con label[u] definida (en cualquier orden):
            cand = extender(label[u], v, peso(u, v))   # suma o producto; hops + 1; path + (v,)
            si v sin etiqueta en nuevo o mejor(cand, nuevo[v]): nuevo[v] = cand
        si nuevo == label: salir                   # sin cambios
        label = nuevo
    para cada arco u→v con label[u] definida:          # pasada de detección, ambos modos
        si mejora_primaria(extender(label[u], v, peso(u, v)).score, label[v].score):
            lanzar NegativeCycleError
    devolver label

mejor(a, b) := clave(a) < clave(b), con clave = (score, hops, path) en modo additive
                                     y (−score, hops, path) en modo product
mejora_primaria(x, y) := x < y en modo additive;  x > y en modo product
```

- **Corrección.** Tras la ronda `k`, cada etiqueta es la mejor caminata de como máximo `k` arcos según `(costo, saltos, ruta)`: el orden se conserva al extender (se suma el mismo peso, o se multiplica por el mismo factor positivo, y se añade el mismo nodo final). Con pesos ≥ 0, o factores en (0, 1], todo ciclo empeora el costo o, si es neutro, aumenta los saltos; por tanto la óptima es una ruta simple de como máximo `|V| − 1` arcos, y las rondas terminan con la solución de DEC-08.
- **Ciclos negativos.** En la pasada final `label[v]` siempre está definida cuando lo está `label[u]`: todo nodo alcanzable tiene una ruta simple de como máximo `|V| − 1` arcos y queda etiquetado en las rondas (o antes, si se alcanza un punto fijo). La pasada compara **solo** la magnitud primaria y detecta un ciclo de mejora alcanzable desde `src`: en modo aditivo, de suma negativa; en modo producto, de producto > 1 (solo posible con factores > 1, es decir, `p < 0`, que la validación de topologías rechaza). Un ciclo en otra componente no se detecta porque sus nodos nunca reciben etiqueta.
- **Terminación y complejidad.** Como máximo `|V| − 1` rondas y una pasada de detección; los ciclos de costo cero no causan bucles. Por ronda se hacen `|E|` extensiones (cada una crea y compara rutas de longitud ≤ `|V|`: `O(|E|·|V|)`) más la copia y la comparación de las etiquetas (`O(|V|²)`); en total `O(|V|²·(|V| + |E|))` operaciones elementales. Como cada ronda solo lee etiquetas de la anterior y el orden `(costo, saltos, ruta)` es total, el resultado no depende del orden en que se recorran los arcos, por lo que no hace falta ordenarlos. Memoria `O(|V|² + |E|)`. Son cotas de operaciones abstractas: el costo de la aritmética `Fraction` crece con el tamaño de numeradores y denominadores.

### 6.3 Procedimiento de `CostPresenter.format_cost`

1. Contexto `decimal.localcontext()` con `prec = 60` y `rounding = ROUND_HALF_EVEN`; nunca se usa `float`.
2. `delay`, `inverse_bandwidth` (redondeo **exacto** del racional, sin división decimal intermedia): si `score = 0` → `"0"`; si no, se halla el exponente decimal `e` con `10^e ≤ score < 10^(e+1)` comparando `Fraction`, se calcula `m = round(score / 10^(e−11))` (la función `round` de Python redondea un `Fraction` de forma exacta y *half-even*) y el valor es `m · 10^(e−11)`; si `m = 10^12`, se reescribe como `10^(e+1)`.
3. `loss`: `S = score`; si `S = 1` → `"0"`. Con `q = 1 − S` exacto: si `0 < q ≤ 1/4`, costo = `Σ_{j=1..25} q^j / j` (sin formar `1 − Decimal(S)` redondeado, lo que evita la cancelación con `p = 1e-60`; el error relativo de truncamiento es ≤ `q^25 / (26(1 − q))` ≤ 4.6 × 10⁻¹⁷); si `q > 1/4`, costo = `−(Decimal(S.numerator) / Decimal(S.denominator)).ln()`.
4. Para `loss`, redondear el valor calculado a 12 cifras significativas (`ROUND_HALF_EVEN`). En todos los casos, escribir en el formato canónico de `01` §5.3: el resultado debe cumplir `is_canonical_cost` y, para `loss`, un error relativo ≤ 1 × 10⁻¹⁰ frente a una referencia de al menos 100 cifras (TC-38, TC-39).

## 7. Composición, inyección de dependencias y configuración (NFR-05, NFR-07)

`create_controller_app(settings, dao=None)` usa el `dao` recibido o, si no se pasa, crea `JsonTopologyDAO(settings.topology_file)`; crea `BellmanFordEngine()`, `CostPresenter()` y `RoutingService(dao=…, engine=…, presenter=…)`; registra `ControllerHTTP` y los manejadores de `controller/http_errors.py`. `create_router_app(settings, route_client=None, log_dao=None)` usa los dobles recibidos o crea `HttpRouteClient(…)` y `JsonlForwardingLogDAO(settings.log_file)`; crea `ForwardingService(client=…, log_dao=…)` y registra `PacketHTTP` y `router/http_errors.py`. Los parámetros opcionales son el **punto de inyección de las pruebas de API** (TC-06, TC-11, TC-16, TC-31, TC-32, TC-33); los constructores de los servicios, en cambio, no tienen valores por defecto: omitir una dependencia es un error. Los dobles (`FakeTopologyDAO`, `FakeRouteClient`, `SpyRouteClient`, `FakeForwardingLogDAO`, `SpyCostPresenter`) viven solo en `tests/`.

| Proceso | Variable de entorno | Opción CLI | Valor por defecto |
|---|---|---|---|
| Controller | `CONTROLLER_HOST` | `--host` | `127.0.0.1` |
| Controller | `CONTROLLER_PORT` | `--port` | `8000` |
| Controller | `TOPOLOGY_FILE` | `--topology` | `config/topology.json` |
| Router | `ROUTER_HOST` | `--host` | `127.0.0.1` |
| Router | `ROUTER_PORT` | `--port` | `8001` |
| Router | `CONTROLLER_URL` | `--controller-url` | `http://127.0.0.1:8000` |
| Router | `FORWARDING_LOG_FILE` | `--log-file` | `data/forwarding.jsonl` |
| Router | `CONTROLLER_CONNECT_TIMEOUT_SECONDS` | `--connect-timeout` | `1.0` |
| Router | `CONTROLLER_READ_TIMEOUT_SECONDS` | `--read-timeout` | `2.0` |

Precedencia: opción CLI > variable de entorno > valor por defecto. Impiden el arranque con un diagnóstico claro: un puerto fuera de 1–65535, un timeout ≤ 0, un `TOPOLOGY_FILE` inexistente o inválido, y un `FORWARDING_LOG_FILE` cuyo directorio no admite escritura. El archivo de bitácora se crea si no existe; el directorio por defecto `data/` se crea al arrancar, mientras que el directorio de una ruta indicada explícitamente debe existir.

## 8. Módulos y reglas de importación (para la Sesión 2)

```text
controller/
  main.py         # punto de entrada: carga la configuración y arranca Uvicorn
  settings.py     # ControllerSettings (entorno y CLI, §7)
  app.py          # raíz de composición: create_controller_app(settings, dao=None)
  http.py         # Controller MVC: ControllerHTTP
  http_errors.py  # adaptador de errores FastAPI y tabla error.code -> estado HTTP
  view.py         # View: esquemas Pydantic del Controller
  models.py       # Model: Topology, Link, LinkChangeResult
  ports.py        # interfaz TopologyDAO
  service.py      # RoutingService
  engine.py       # BellmanFordEngine, LinkCostPolicy, RouteLabel, PathScore
  presenter.py    # CostPresenter
  dao.py          # JsonTopologyDAO, TopologyLoadError
router/
  main.py, settings.py (RouterSettings), app.py, http.py (PacketHTTP), http_errors.py, view.py,
  models.py (Packet, ForwardingResult, TraceHop), ports.py (RouteClient, ForwardingLogDAO),
  service.py (ForwardingService), client.py (HttpRouteClient), dao.py (JsonlForwardingLogDAO)
shared/
  models.py (Route), errors.py (AppError y subclases), error_contract.py (constantes),
  cost_format.py (is_canonical_cost)
config/topology.json   tests/   (se crean en la Sesión 2)
```

| Módulo | Puede importar | No puede importar | Verificación |
|---|---|---|---|
| `shared/*` | Biblioteca estándar | FastAPI, Starlette, Pydantic, NetworkX, httpx, `controller`, `router` | TC-13 |
| `controller/models.py`, `ports.py`, `service.py`, `engine.py`, `presenter.py` | `shared`, `models`, `ports`; `service.py` además `engine.py` y `presenter.py` (tipos de sus dependencias inyectadas); NetworkX solo en `engine.py` | FastAPI, Pydantic, `router`, `controller/dao.py`, `open()` | TC-08, TC-13 |
| `router/models.py`, `ports.py`, `service.py` | `shared`, `models`, `ports` | FastAPI, NetworkX, httpx, `controller`, `router/dao.py`, `router/client.py`, `open()` | TC-09, TC-13 |
| `controller/http.py`, `router/http.py`, `*/http_errors.py`, `*/view.py` | FastAPI, Pydantic, servicio propio, `models`, `shared` | `dao.py`, `client.py`, `engine.py`, `open()` | TC-13 |
| `controller/dao.py`, `router/dao.py`, `router/client.py` | Biblioteca estándar, `shared`, `models`, `ports`; httpx solo en `client.py` | Código del otro proceso | TC-13, TC-34 |
| `controller/app.py`, `router/app.py` | Todo su propio proceso y `shared` | Código del otro proceso | TC-34 |

## 9. Errores por componente y adaptadores HTTP

| Componente | Lanza | Traducción en `http_errors.py` (`04` §5) |
|---|---|---|
| Capa View (FastAPI `RequestValidationError`) | Error de sintaxis JSON / de esquema o campo no permitido | 400 `MALFORMED_JSON` / 400 `INVALID_REQUEST` |
| `RoutingService` | `InvalidRequestError`, `NodeNotFoundError` | 400 / 404 |
| `JsonTopologyDAO` | `NodeNotFoundError`, `LinkNotFoundError`; `TopologyLoadError` al arrancar | 404 / 404; sin HTTP (aborta el arranque) |
| `BellmanFordEngine` | `RouteUnreachableError`; `NegativeCycleError` (invariante violado: imposible con una topología validada) | 404; 500 `NEGATIVE_CYCLE` |
| `HttpRouteClient` | `ControllerUnavailableError` (`httpx.ConnectError`: conexión rechazada o DNS), `ControllerTimeoutError` (`ConnectTimeout`, `ReadTimeout`, `WriteTimeout`, `PoolTimeout`), `ControllerBadResponseError` (cualquier otro `httpx.TransportError`, p. ej. conexión cortada a mitad de respuesta, y toda respuesta no conforme o con estado no previsto); reproduce `NodeNotFoundError` / `RouteUnreachableError` si el Controller respondió 404 con ese `error.code` | 503 / 504 / 502; 404 |
| `ForwardingService`, `JsonlForwardingLogDAO` | `LogPersistenceError` | 500 |
| FastAPI (ruta o método inexistente) | — | 404 `UNKNOWN_ENDPOINT` / 405 `METHOD_NOT_ALLOWED`, con el mismo sobre `error` |
| Cualquier otra excepción | — | 500 `INTERNAL_ERROR`, sin traza en la respuesta |

Cada `http_errors.py` contiene la tabla `error.code → estado HTTP` de su proceso y registra sus manejadores con `install_error_handlers(app)` desde la raíz de composición. Para los errores de un paquete ya validado, `PacketHTTP` adjunta el `packet_id` a la excepción y `router/http_errors.py` construye `PacketErrorSchema` (`packet_id`, `status: "failed"`, `trace: []`, `error`); para los errores de entrada construye solo el sobre `{"error": ErrorBodySchema}`. Ninguna respuesta expone trazas Python, rutas de archivo ni direcciones internas.

## 10. Correspondencia con las secuencias de `03`

| Secuencia | Métodos utilizados (todos declarados en §3) |
|---|---|
| S1 — reenvío exitoso | `PacketHTTP.post_packet`, `ForwardingService.forward`, `HttpRouteClient.fetch_route`, `ControllerHTTP.get_route`, `RoutingService.compute_route`, `TopologyDAO.get_topology`, `BellmanFordEngine.find_path`, `CostPresenter.format_cost`, `ForwardingLogDAO.save` |
| S2 — fallo, nueva ruta y restauración | `ControllerHTTP.fail_link`, `ControllerHTTP.restore_link`, `RoutingService.set_link_status`, `TopologyDAO.set_link_status` y el flujo de S1 |
| S3 — Controller no disponible | `PacketHTTP.post_packet`, `ForwardingService.forward`, `HttpRouteClient.fetch_route`, `ForwardingLogDAO.save`, `PacketHTTP.health` |

## 11. Fuentes

PDF del taller Grupo 2, pp. 1–4; Kurose y Ross (2017), cap. 5; diapositivas *Network Layer: Control Plane*, pp. 4–6 (separación entre reenvío y enrutamiento; control lógicamente centralizado). La solución es una aproximación educativa: el Controller responde rutas bajo demanda y no instala tablas en dispositivos.
