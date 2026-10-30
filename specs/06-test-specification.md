# 06 — Especificación de pruebas funcionales, de arquitectura y no funcionales

| Campo | Valor |
|---|---|
| Versión | **1.0** (candidata a baseline `spec-1.0`) · 2026-10-29 |
| Estado | Pruebas **especificadas, no implementadas ni ejecutadas** (se ejecutan en la Sesión 2). Aprobación: ver `REVIEW-AND-BASELINE.md` |
| Mínimo exigido (PDF p. 5) | ≥ 8 pruebas automatizadas aprobadas, **incluidas TC-08 y TC-09**, más una revisión de código que verifique que los controladores MVC no contienen algoritmos de enrutamiento ni de reenvío |

## 1. Estrategia

| Nivel | Herramienta | Alcance |
|---|---|---|
| Unitario | pytest + dobles en `tests/` (`FakeTopologyDAO`, `FakeRouteClient`, `SpyRouteClient`, `FakeForwardingLogDAO`, `SpyCostPresenter`) | Servicios y motor sin HTTP ni disco |
| API | `fastapi.testclient.TestClient` sobre `create_controller_app(settings, dao=…)` y `create_router_app(settings, route_client=…, log_dao=…)` (puntos de inyección de `02` §7) | Contrato de `04` dentro de un proceso |
| Integración | Dos procesos Uvicorn reales + `httpx` | Comunicación Controller ↔ Router, fallos y recuperación |
| Arquitectura | Análisis AST + revisión manual (§6) | Reglas de `02` §1 y §8 |
| No funcional | Script de medición | NFR-10, NFR-11 |
| Oráculo | NetworkX (`bellman_ford_path_length`, `bellman_ford_predecessor_and_distance`) y referencia decimal de 100 cifras | Contraste independiente de costos y ciclos |

**Reglas comunes.** Cada caso se implementa como `tests/test_tcXX_*.py` con un fixture nuevo por prueba (copia temporal de `specs/fixtures/`); solo los pasos encadenados de un mismo caso comparten estado. Rutas, estados HTTP y `error.code` se comparan exactamente. `total_cost` debe cumplir siempre `is_canonical_cost`; para `delay` e `inverse_bandwidth` se compara como cadena exacta; para `loss` se acepta cualquier cadena canónica con error relativo ≤ 1 × 10⁻¹⁰ frente a una referencia de al menos 100 cifras (`01` §5.3), y la cadena de §3 es el redondeo correcto. Una prueba es **PASS** solo si se ejecutó y su salida quedó en `test-results.txt`; los fallos se registran tal cual, sin cambiar requisitos para que coincidan con código incorrecto (PDF p. 5). **Prioridad:** TC-01 a TC-09 primero; después el resto por riesgo (numéricos, errores, NFR).

## 2. Fixtures

Todos los archivos están en `specs/fixtures/` y cumplen `01` §4; son dirigidos salvo F-11. Los enlaces no indicados tienen `active=true`.

| Fixture | Contenido relevante | Usado en |
|---|---|---|
| F-01 | Base: A→B, B→D (`d=1, b=10, p=0.01`); A→C, C→D (`d=2, b=100, p=0.02`) | TC-01–TC-09, TC-10 (variantes inválidas), TC-12–TC-18, TC-39, demostración |
| F-02 | Dos rutas de 2 saltos con `d=2` por enlace; vía C mejor en `b` y `p` | TC-19 |
| F-03 | Vía B `1+1`; vía C `1+1.000000000001` | TC-20 |
| F-04 | A→D `d=2` frente a A→B→D `1+1` | TC-21 |
| F-05 / F-05b | Empate total entre A→B→D y A→C→D / entre A→B→E→D y A→B→F→D (orden JSON invertido a propósito) | TC-22, TC-26 |
| F-06 | A→B y B→A independientes | TC-25 |
| F-07 | Ciclo de costo cero A↔B con A→D `d=1` y B→D `d=1` | TC-21 |
| F-08 / F-08b | A→D `0.8` (o `0.800000000001`) frente a A→B `0.1` + B→D `0.7` | TC-27 |
| F-08c / F-08d | Casos del ejercicio *few-shot* P09: además A→C `0.4` + C→D `0.4` | TC-27 |
| F-09 | Un solo nodo A, sin enlaces | TC-28 |
| F-10 | A→B, D→E; C aislado | TC-29 |
| F-11 / F-12 | A–B, B–D no dirigido / mismos arcos dirigidos | TC-30 |
| F-13 | A→B con `p=1`, B→D, A→C, C→D | TC-36 |
| F-14a / F-14a-near / F-14b | Empates exactos en las tres métricas / variante con `p(A→D)=0.190000000000000000000000000001` / empate total de dos rutas | TC-37 |
| F-15 | A→B→D `0.5+1.5`, A→C→D `1+2`, A→D `3` | TC-23 |
| F-16 | A→D con `p=0.999999999999` | TC-38 |
| F-17 / F-17b | A→D con `p=0.25` / `p=0.250000000001` (frontera de la serie) | TC-39 |
| F-18 / F-18b | A→D con `p=1e-60` (escrito como literal decimal) / `p=0` | TC-38 |
| F-19 | Cadena de 100 nodos `N100`→…→`N001` (`d=1`) con cuerdas de dos saltos más caras (`d=3`): 197 arcos; la ruta óptima tiene 99 saltos | TC-15 (rendimiento; verificado con NetworkX, sin fila de oráculo) |

## 3. Oráculo de resultados esperados

Cada fila se recalculó con la verificación automática (`VALIDACION.md`) mediante enumeración exhaustiva de rutas simples y aritmética exacta. «Operaciones previas» se aplican en orden sobre el fixture recién cargado (versión inicial 1).

| Caso | TC | Fixture | Operaciones previas | Consulta | metric | Esperado | Versión |
|---|---|---|---|---|---|---|---|
| E-01 | TC-01 | F-01 | — | A→D | delay | 200 · ["A","B","D"] · "2" | 1 |
| E-02 | TC-02 | F-01 | — | A→D | inverse_bandwidth | 200 · ["A","C","D"] · "0.02" | 1 |
| E-03 | TC-02 | F-01 | — | A→D | loss | 200 · ["A","B","D"] · "0.020100671707" | 1 |
| E-04 | TC-03 | F-01 | fail B→D | A→D | delay | 200 · ["A","C","D"] · "4" | 2 |
| E-05 | TC-04 | F-01 | fail B→D; restore B→D | A→D | delay | 200 · ["A","B","D"] · "2" | 3 |
| E-06 | TC-17 | F-01 | fail B→D; fail C→D | A→D | delay | 404 · ROUTE_UNREACHABLE | 3 |
| E-07 | TC-17 | F-01 | fail B→D; fail C→D; restore C→D | A→D | delay | 200 · ["A","C","D"] · "4" | 4 |
| E-08 | TC-18 | F-01 | fail B→D; fail B→D | A→D | delay | 200 · ["A","C","D"] · "4" | 2 |
| E-09 | TC-19 | F-02 | — | A→D | delay | 200 · ["A","B","D"] · "4" | 1 |
| E-10 | TC-20 | F-03 | — | A→D | delay | 200 · ["A","B","D"] · "2" | 1 |
| E-11 | TC-21 | F-04 | — | A→D | delay | 200 · ["A","D"] · "2" | 1 |
| E-12 | TC-21 | F-07 | — | A→D | delay | 200 · ["A","D"] · "1" | 1 |
| E-13 | TC-22 | F-05 | — | A→D | delay | 200 · ["A","B","D"] · "4" | 1 |
| E-14 | TC-22 | F-05b | — | A→D | delay | 200 · ["A","B","E","D"] · "3" | 1 |
| E-15 | TC-23 | F-15 | — | A→D | delay | 200 · ["A","B","D"] · "2" | 1 |
| E-16 | TC-23 | F-15 | — | A→D | loss | 200 · ["A","D"] · "0" | 1 |
| E-17 | TC-25 | F-06 | fail A→B | A→B | delay | 404 · ROUTE_UNREACHABLE | 2 |
| E-18 | TC-25 | F-06 | fail A→B | B→A | delay | 200 · ["B","A"] · "1" | 2 |
| E-19 | TC-27 | F-08 | — | A→D | delay | 200 · ["A","D"] · "0.8" | 1 |
| E-20 | TC-27 | F-08b | — | A→D | delay | 200 · ["A","B","D"] · "0.8" | 1 |
| E-21 | TC-28 | F-09 | — | A→A | delay | 200 · ["A"] · "0" | 1 |
| E-22 | TC-28 | F-09 | — | A→B | delay | 404 · NODE_NOT_FOUND | 1 |
| E-23 | TC-29 | F-10 | — | A→C | delay | 404 · ROUTE_UNREACHABLE | 1 |
| E-24 | TC-29 | F-10 | — | A→E | delay | 404 · ROUTE_UNREACHABLE | 1 |
| E-25 | TC-29 | F-10 | — | C→C | delay | 200 · ["C"] · "0" | 1 |
| E-26 | TC-30 | F-11 | — | D→A | delay | 200 · ["D","B","A"] · "2" | 1 |
| E-27 | TC-30 | F-11 | fail A→B | D→A | delay | 404 · ROUTE_UNREACHABLE | 2 |
| E-28 | TC-30 | F-11 | fail A→B; fail B→A | A→D | delay | 404 · ROUTE_UNREACHABLE | 2 |
| E-29 | TC-30 | F-12 | — | D→A | delay | 404 · ROUTE_UNREACHABLE | 1 |
| E-30 | TC-36 | F-13 | — | A→D | delay | 200 · ["A","C","D"] · "4" | 1 |
| E-31 | TC-36 | F-13 | — | A→D | inverse_bandwidth | 200 · ["A","C","D"] · "0.2" | 1 |
| E-32 | TC-36 | F-13 | — | A→D | loss | 200 · ["A","C","D"] · "0" | 1 |
| E-33 | TC-36 | F-13 | restore A→B | A→D | delay | 200 · ["A","C","D"] · "4" | 1 |
| E-34 | TC-37 | F-14a | — | A→D | delay | 200 · ["A","D"] · "0.8" | 1 |
| E-35 | TC-37 | F-14a | — | A→D | inverse_bandwidth | 200 · ["A","D"] · "0.2" | 1 |
| E-36 | TC-37 | F-14a | — | A→D | loss | 200 · ["A","D"] · "0.210721031316" | 1 |
| E-37 | TC-37 | F-14a-near | — | A→D | loss | 200 · ["A","B","D"] · "0.210721031316" | 1 |
| E-38 | TC-37 | F-14a-near | — | A→D | delay | 200 · ["A","D"] · "0.8" | 1 |
| E-39 | TC-37 | F-14b | — | A→D | delay | 200 · ["A","B","D"] · "2" | 1 |
| E-40 | TC-37 | F-14b | — | A→D | inverse_bandwidth | 200 · ["A","B","D"] · "0.2" | 1 |
| E-41 | TC-37 | F-14b | — | A→D | loss | 200 · ["A","B","D"] · "0.210721031316" | 1 |
| E-42 | TC-38 | F-18 | — | A→D | loss | 200 · ["A","D"] · "1e-60" | 1 |
| E-43 | TC-38 | F-16 | — | A→D | loss | 200 · ["A","D"] · "27.6310211159" | 1 |
| E-44 | TC-38 | F-18b | — | A→D | loss | 200 · ["A","D"] · "0" | 1 |
| E-45 | TC-39 | F-17 | — | A→D | loss | 200 · ["A","D"] · "0.287682072452" | 1 |
| E-46 | TC-39 | F-17b | — | A→D | loss | 200 · ["A","D"] · "0.287682072453" | 1 |
| E-47 | TC-27 | F-08c | — | A→D | delay | 200 · ["A","D"] · "0.8" | 1 |
| E-48 | TC-27 | F-08d | — | A→D | delay | 200 · ["A","B","D"] · "0.8" | 1 |

Notas: la columna «Versión» es el estado interno del Controller; en las filas 404 se comprueba con `GET /topology`. En E-19 y E-47 una suma en `float` elegiría `[A,B,D]` (0.7999999999999999), de modo que ambas distinguen la aritmética exacta de `float`; en E-20 y E-48 `float` llegaría al mismo resultado por otra razón (un costo estrictamente menor). En E-17 el nodo B existe pero el único arco de A a B está inactivo; en E-28 el segundo fallo devuelve `changed=false` porque, en modo no dirigido, A–B y B–A son el mismo enlace; en E-33 restaurar un enlace ya activo devuelve `changed=false` y el enlace con `p=1` sigue excluido. La independencia del orden del JSON (TC-26) es una propiedad que debe demostrar la implementación; el oráculo, al enumerar todas las rutas, no depende del orden por construcción.

## 4. Casos oficiales TC-01 a TC-09 (formato de plantilla de plan de pruebas)

Los campos *Resultado real*, *Estado* y *Evidencia* se completan en la Sesión 2 con la ejecución real.

### TC-01 — Bellman-Ford devuelve la ruta de costo mínimo esperada

| Campo | Descripción |
|---|---|
| Requisitos | FR-01, FR-03, FR-05 |
| Tipo | API (`TestClient`) + oráculo NetworkX |
| Objetivo | Verificar la carga de la topología por DAO y que `GET /route` devuelve la ruta de costo mínimo. |
| Precondiciones | `create_controller_app` con `TOPOLOGY_FILE` = copia temporal de F-01. |
| Datos de entrada | `GET /topology`; `GET /route?src=A&dst=D&metric=delay`. |
| Pasos | 1. Pedir la topología. 2. Pedir la ruta. 3. Calcular `nx.bellman_ford_path_length(G, "A", "D", weight)` sobre F-01 con pesos `Fraction`. |
| Resultado esperado | 1: 200, 4 nodos, 4 enlaces activos, `topology_version=1`. 2: E-01 (`["A","B","D"]`, `"2"`, versión 1) con `source`, `destination` y `metric` iguales a la petición. 3: el costo del oráculo es 2. |
| Resultado real / Estado / Evidencia | Pendiente / No ejecutada / salida de pytest en `test-results.txt` |

### TC-02 — Se admiten las métricas de retardo, ancho de banda inverso y pérdida

| Campo | Descripción |
|---|---|
| Requisitos | FR-04 |
| Tipo | Unitario (`RoutingService` con `FakeTopologyDAO`) + API |
| Objetivo | Verificar los tres costos de `01` §5.1 y su presentación. |
| Precondiciones | F-01 cargado. |
| Datos de entrada | A→D con `metric` = `delay`, `inverse_bandwidth`, `loss`. |
| Pasos | Consultar las tres métricas; comparar `total_cost` de `loss` con `−2·ln(0.99)` calculado a 100 cifras. |
| Resultado esperado | E-01, E-02, E-03. `delay` y `loss` coinciden legítimamente en `["A","B","D"]`; no se exigen tres rutas distintas. Error relativo de `loss` ≤ 1 × 10⁻¹⁰. |
| Resultado real / Estado / Evidencia | Pendiente / No ejecutada / `test-results.txt` |

### TC-03 — Los enlaces fallados se excluyen de las rutas siguientes

| Campo | Descripción |
|---|---|
| Requisitos | FR-06 |
| Tipo | API del Controller |
| Objetivo | Verificar que un enlace fallado no se usa. |
| Precondiciones | F-01 recién cargado (versión 1). |
| Datos de entrada | `POST /links/fail {"source":"B","target":"D"}`; `GET /route?src=A&dst=D&metric=delay`. |
| Pasos | 1. Fallar B→D. 2. Consultar la ruta. |
| Resultado esperado | 1: 200 `{"active": false, "changed": true, "topology_version": 2}`. 2: E-04 (`["A","C","D"]`, `"4"`, versión 2); la ruta no contiene el arco B→D. |
| Resultado real / Estado / Evidencia | Pendiente / No ejecutada / `test-results.txt` |

### TC-04 — Restaurar un enlace actualiza las rutas siguientes

| Campo | Descripción |
|---|---|
| Requisitos | FR-06 |
| Tipo | API del Controller (continúa el estado de TC-03 dentro de la misma prueba) |
| Objetivo | Verificar la restauración, el versionado y la idempotencia. |
| Precondiciones | Pasos de TC-03 ejecutados en la misma prueba (versión 2). |
| Datos de entrada | `POST /links/restore {"source":"B","target":"D"}` dos veces; `GET /route?src=A&dst=D&metric=delay`. |
| Pasos | 1. Restaurar. 2. Consultar. 3. Restaurar de nuevo. |
| Resultado esperado | 1: 200 `changed=true`, versión 3. 2: E-05 (`["A","B","D"]`, `"2"`, versión 3). 3: 200 `changed=false`, versión 3. |
| Resultado real / Estado / Evidencia | Pendiente / No ejecutada / `test-results.txt` |

### TC-05 — El Router obtiene la ruta por HTTP en lugar de calcularla

| Campo | Descripción |
|---|---|
| Requisitos | FR-07 |
| Tipo | Unitario con espía + inspección AST + integración |
| Objetivo | Demostrar que el Router usa la ruta del Controller y no tiene capacidad de cálculo. |
| Precondiciones | `ForwardingService(client=SpyRouteClient, log_dao=FakeForwardingLogDAO)`; para la parte de integración, ambos procesos con F-01. |
| Datos de entrada | Espía que devuelve `Route(path=("A","C","D"), total_cost="4", …)` para `A→D delay` (una ruta que no es la óptima de F-01). |
| Pasos | 1. `forward(Packet(packet_id="pkt-1", source="A", destination="D", payload="", metric="delay"))`. 2. AST de `router/`. 3. Con procesos reales, enviar un paquete y revisar el registro de accesos del Controller. |
| Resultado esperado | 1: `fetch_route` se llama exactamente una vez con `("A","D","delay")` y la traza es `A, C, D` (la del espía, sin recalcular). 2: ningún módulo de `router/` importa `networkx` ni `controller`. 3: exactamente un `GET /route?src=A&dst=D&metric=delay` por paquete. |
| Resultado real / Estado / Evidencia | Pendiente / No ejecutada / `test-results.txt` y registro de accesos en `demo-evidence/` |

### TC-06 — La traza de reenvío informa un resultado válido

| Campo | Descripción |
|---|---|
| Requisitos | FR-08, FR-10 |
| Tipo | API del Router (`TestClient`) con `FakeRouteClient` y bitácora JSONL temporal |
| Objetivo | Verificar la traza, la respuesta y el registro de un reenvío exitoso. |
| Precondiciones | `create_router_app(settings, route_client=FakeRouteClient(ruta de E-01), log_dao=JsonlForwardingLogDAO(tmp/forwarding.jsonl))`; bitácora temporal vacía. |
| Datos de entrada | `POST /packets {"packet_id":"pkt-001","source":"A","destination":"D","metric":"delay"}`. |
| Pasos | 1. Enviar el paquete. 2. Leer la bitácora con `log_dao.list_recent(10)` y directamente del archivo. |
| Resultado esperado | 1: 200 con `status="forwarded"`, `route` igual a la del fake, `trace=[{0,A},{1,B},{2,D}]`, `topology_version=1`. 2: exactamente una línea JSONL válida según `04` §6 con `packet_id="pkt-001"`, `source="A"`, `destination="D"`, `metric="delay"` y `status="forwarded"`; `list_recent` devuelve ese mismo resultado. |
| Resultado real / Estado / Evidencia | Pendiente / No ejecutada / `test-results.txt` |

### TC-07 — La caída del Controller y el destino inalcanzable se gestionan limpiamente

| Campo | Descripción |
|---|---|
| Requisitos | FR-09, NFR-06 |
| Tipo | Integración (dos procesos) |
| Objetivo | Verificar respuestas de error estables, registro `failed` y continuidad del Router. |
| Precondiciones | Controller con F-01 y Router con bitácora temporal; timeout de lectura reducido a 0.5 s para el caso c. |
| Datos de entrada | Paquetes A→D con `metric=delay`. |
| Pasos | a. Fallar B→D y C→D; enviar un paquete. b. Detener el Controller; enviar un paquete. c. Apuntar el Router a un servidor de prueba que acepta la conexión y no responde; enviar un paquete. d. `GET /health` del Router tras cada paso. |
| Resultado esperado | a: 404 `ROUTE_UNREACHABLE` (E-06). b: 503 `CONTROLLER_UNAVAILABLE`. c: 504 `CONTROLLER_TIMEOUT`. En a–c: `status="failed"`, `trace=[]`, una línea `failed` por paquete. d: 200 siempre. |
| Resultado real / Estado / Evidencia | Pendiente / No ejecutada / `test-results.txt` y capturas en `demo-evidence/` |

### TC-08 — `RoutingService` funciona con un `TopologyDAO` falso y sin servidor HTTP

| Campo | Descripción |
|---|---|
| Requisitos | NFR-02, NFR-07, NFR-09 |
| Tipo | Unitario de arquitectura (obligatorio) |
| Objetivo | Demostrar el aislamiento por inyección de dependencias en el Controller. |
| Precondiciones | Sin servidores; `open()` y `socket.socket` sustituidos por funciones que fallan si se invocan. |
| Datos de entrada | Copia en memoria de F-01. |
| Pasos | Ver el bloque siguiente. |
| Resultado esperado | `first.path == ("A","B","D")`, `first.total_cost == "2"`, `first.topology_version == 1`; `second.path == ("A","C","D")`, `second.total_cost == "4"`, `second.topology_version == 2`; `fake_dao.get_topology` llamado 2 veces y `set_link_status` 1 vez; variante con `SpyCostPresenter`: `format_cost` llamado una vez por consulta con `(Fraction(2), "delay")` y `(Fraction(4), "delay")`; ninguna E/S de archivo ni de red. |
| Resultado real / Estado / Evidencia | Pendiente / No ejecutada / `test-results.txt` |

```text
fake_dao  = FakeTopologyDAO(topology=fixture_F01)        # definido solo en tests/
engine    = BellmanFordEngine()
presenter = CostPresenter()
service   = RoutingService(dao=fake_dao, engine=engine, presenter=presenter)
first  = service.compute_route(src="A", dst="D", metric="delay")
service.set_link_status(source="B", target="D", active=False)
second = service.compute_route(src="A", dst="D", metric="delay")
```

### TC-09 — `ForwardingService` usa su DAO de bitácora y se prueba de forma independiente

| Campo | Descripción |
|---|---|
| Requisitos | FR-10, NFR-02, NFR-07, NFR-09 |
| Tipo | Unitario de arquitectura (obligatorio) |
| Objetivo | Demostrar el aislamiento del Router respecto de la red y del sistema de archivos. |
| Precondiciones | Sin servidores ni disco. |
| Datos de entrada | `Route(source="A", destination="D", metric="delay", path=("A","B","D"), total_cost="2", topology_version=1)`; `Packet(packet_id="pkt-1", source="A", destination="D", payload="", metric="delay")`. |
| Pasos | 1. `ForwardingService(client=FakeRouteClient(route), log_dao=FakeForwardingLogDAO())`; `forward(packet)`. 2. Cliente falso que lanza `ControllerUnavailableError`; `forward` de `pkt-2`. 3. DAO falso cuyo `save` lanza `OSError`; `forward` de `pkt-3`. |
| Resultado esperado | 1: resultado `forwarded`, traza A, B, D, `route` sin modificar, un `save` con ese resultado. 2: se relanza `ControllerUnavailableError` y se guarda un segundo resultado `failed` con `source`, `destination` y `metric` del paquete, `trace=()`, `route=None`, `error.code="CONTROLLER_UNAVAILABLE"`. 3: el servicio envuelve el `OSError` y lanza `LogPersistenceError`; no se devuelve resultado exitoso. Cero llamadas HTTP. |
| Resultado real / Estado / Evidencia | Pendiente / No ejecutada / `test-results.txt` |

## 5. Casos complementarios TC-10 a TC-39

| ID | Nombre | Requisitos | Entrada / fixture | Procedimiento | Resultado esperado |
|---|---|---|---|---|---|
| TC-10 | Validación de la topología al arrancar | FR-01, FR-04 | Variantes inválidas de F-01, una por regla de `01` §4: JSON ilegible y `NaN` (`TOPO-JSON`); clave desconocida (`TOPO-KEYS`); `nodes` vacío (`TOPO-NODES`); ID repetido (`TOPO-DUP-NODE`); extremo inexistente (`TOPO-ENDPOINT`); lazo A→A (`TOPO-SELF-LOOP`); enlace paralelo dirigido y no dirigido (`TOPO-PARALLEL`); número como cadena (`TOPO-TYPE`); `delay_ms=-1`, `bandwidth_mbps=0`, `loss_probability` 1.5 y −0.1 (`TOPO-RANGE`); 65 cifras significativas y exponente 1001 (`TOPO-DOMAIN`) | Construir `JsonTopologyDAO` y arrancar el proceso con cada archivo | Cada caso lanza `TopologyLoadError` con el `rule` indicado y el proceso no abre el puerto; F-13 (con `p=1`) sí carga; ningún valor pasa por `float` (espía de `parse_float`) |
| TC-11 | Ciclo negativo alcanzable y no alcanzable | FR-03 | Grafos artificiales `nx.DiGraph` con el peso `Fraction` en el atributo `weight`, origen A. Modo aditivo: G1: A→B 1, B→C −3, C→A 1, C→D 1; G2: A→D 1, X→Y −2, Y→X 1. Modo producto: G3 con factores A→B 2, B→A 1, A→D 1/2. Subcaso API: `create_controller_app(settings, dao=FakeTopologyDAO(t))`, con `t` = `Topology` dirigida, nodos A, B, C, D y los arcos de G1 como `delay_ms` (`bandwidth_mbps=10`, `loss_probability=0`, `active=true`); es posible porque el Model no valida (`02` §4) | `run_bellman_ford_on_weighted_graph(G, "A", "additive")`; cruce con `nx.bellman_ford_predecessor_and_distance`; espía que confirma que `find_path` usa el mismo núcleo; `GET /route?src=A&dst=D&metric=delay` en el subcaso API | G1 → `NegativeCycleError`; G2 → sin error y etiqueta de D = `(1, 1, ("A","D"))`; G3 (modo `product`) → `NegativeCycleError`; subcaso API → 500 `NEGATIVE_CYCLE` y `/health` 200 |
| TC-12 | Contrato API del Controller | FR-05, FR-09, NFR-04, NFR-06 | F-01; peticiones de §5.1 | `TestClient`; validar cada cuerpo contra `04` | Estados y `error.code` exactos de §5.1; sin trazas; `/health` 200 al final |
| TC-13 | Revisión de arquitectura y trazabilidad | NFR-01, NFR-02, NFR-03, NFR-08 | Código de la Sesión 2 | Script AST con las reglas de `02` §8 (incluidas importaciones dentro de funciones) + lista de revisión manual §6 + verificación de la matriz `05` §6 | Cero violaciones; los handlers solo delegan; ningún requisito ni prueba huérfanos |
| TC-14 | Configuración por entorno y CLI | NFR-05 | Puertos 18000/18001, `TOPOLOGY_FILE` y `FORWARDING_LOG_FILE` temporales, `CONTROLLER_URL` acorde; repetir con opciones CLI; puerto 70000 | Arrancar ambos procesos | `/health` 200 en los puertos alternativos; un paquete `forwarded` registrado en el archivo temporal; puerto inválido → el proceso no arranca |
| TC-15 | Latencia p95 de `GET /route` | NFR-10 | F-01 (A→D) y F-19 (N100→N001, ruta esperada de 99 saltos y costo `"99"`) por loopback | Por fixture, con el Controller arrancado con ese `TOPOLOGY_FILE`: 10 peticiones de calentamiento + 100 secuenciales `delay`, medidas con `time.perf_counter_ns` | PASS si las 200 respuestas son 200 y p95 ≤ 300 ms en cada fixture; se guardan las latencias y el entorno; sin esos datos el resultado es NO VERIFICADO |
| TC-16 | Bitácora con peticiones concurrentes | FR-10, NFR-11 | Bitácora temporal vacía; `pkt-000` a `pkt-099`; `create_router_app(settings, route_client=FakeRouteClient(ruta de E-01))` para aislar la bitácora | 4 hilos cliente envían 25 `POST /packets` cada uno, simultáneamente | 100 respuestas 200; exactamente 100 líneas JSONL parseables y conformes a `04` §6, ninguna mezclada; 100 `packet_id` distintos; `list_recent(100)` devuelve los 100 |
| TC-17 | Destino inalcanzable y recuperación | FR-06 | F-01 | Fallar B→D y C→D; consultar; restaurar C→D; consultar | E-06 y E-07 |
| TC-18 | Idempotencia y errores de enlace | FR-06 | F-01 | Fallar B→D dos veces; restaurar B→D dos veces; fallar D→B; fallar A→X | E-08; `changed` true/false según corresponda; versiones 2, 2, 3, 3; D→B → 404 `LINK_NOT_FOUND`; A→X → 404 `NODE_NOT_FOUND`; los errores no cambian la versión |
| TC-19 | Las otras métricas no desempatan | FR-03 | F-02 | Consultar `delay` | E-09 |
| TC-20 | Casi empate no es empate | FR-03 | F-03 | Consultar `delay` | E-10, sin tolerancias |
| TC-21 | Menos saltos y ciclo de costo cero | FR-03 | F-04, F-07 | Consultar `delay` | E-11, E-12; el ciclo A↔B de costo 0 no aparece en la ruta |
| TC-22 | Desempate lexicográfico por ruta completa | FR-03 | F-05, F-05b | Consultar `delay` | E-13, E-14 |
| TC-23 | El costo prevalece sobre los saltos | FR-03 | F-15 | Consultar `delay` y `loss` | E-15, E-16 |
| TC-24 | *Retirado en 1.0: duplicaba TC-02 y TC-37* | — | — | — | — |
| TC-25 | Orientación de los enlaces dirigidos | FR-02 | F-06 | Fallar A→B; consultar A→B y B→A | E-17, E-18 |
| TC-26 | Independencia del orden del JSON | FR-03 | F-05 (4 enlaces) y F-05b (5 enlaces) | Consultar con las 24 y 120 permutaciones de `links`, cada una con `nodes` en orden original e inverso | En todas: el resultado de E-13 y E-14, respectivamente |
| TC-27 | Empate decimal exacto 0.1 + 0.7 = 0.8 | FR-03 | F-08, F-08b, F-08c, F-08d (los dos últimos reproducen P09) | Cargar con el parser `Decimal`; consultar `delay` | E-19, E-20, E-47, E-48; `Fraction(Decimal("0.1")) + Fraction(Decimal("0.7")) == Fraction(4, 5)` |
| TC-28 | Grafo de un nodo | FR-02, FR-05 | F-09 | Consultar A→A y A→B | E-21, E-22 |
| TC-29 | Componentes desconectadas y nodo aislado | FR-02 | F-10 | `RoutingService(dao=FakeTopologyDAO(F-10), engine=BellmanFordEngine(), presenter=CostPresenter())` y `GET /route` | E-23, E-24, E-25 (excepción `RouteUnreachableError` en el servicio) |
| TC-30 | Modo no dirigido frente a dirigido | FR-02 | F-11, F-12 | Consultar; fallar A→B y luego B→A en F-11 | E-26 a E-29; en F-11 el segundo fallo da `changed=false` |
| TC-31 | Validación de entrada y de respuestas en el Router | FR-08, FR-09, NFR-04, NFR-06 | `create_router_app(settings, route_client=HttpRouteClient(…, transport=httpx.MockTransport(…)), log_dao=FakeForwardingLogDAO())`: cuerpo ilegible; campo adicional; sin `metric`; `metric` inválida; respuestas del Controller sin JSON, `path` vacío, `["X","D"]`, `["A","B","A","D"]`, `total_cost` como número `2`, `"NaN"`, `"-0"`, `"-1"`, `""`, `"2.0"`, `"1e-07"`, `true`, `topology_version` 0 o `true`, `metric` distinta; 404 `NODE_NOT_FOUND` con `details.field="src"` | `TestClient` del Router, un defecto por caso | Entrada inválida → 400 sin registro; respuesta no conforme → 502 `CONTROLLER_BAD_RESPONSE`, registro `failed`, `trace=[]`; el 404 se propaga con `details.field="source"`; nunca `forwarded`; `/health` 200 |
| TC-32 | Normalización de errores de red | FR-07, FR-09, NFR-06 | `HttpRouteClient(…, transport=httpx.MockTransport(…))` que produce `ConnectError`, `ConnectTimeout`, `ReadTimeout`, `WriteTimeout`, `PoolTimeout`, `ReadError`, `RemoteProtocolError`, HTTP 500, HTTP 400, HTTP 200 válido | `fetch_route` y `POST /packets`; inspeccionar los timeouts configurados | 503; 504 para los cuatro timeouts; 502 para `ReadError`, `RemoteProtocolError`, HTTP 500 y HTTP 400; `Route` válida para el 200; en todos los fallos, un registro `failed`; los timeouts de conexión y lectura son los configurados |
| TC-33 | Fallo de la bitácora | FR-10, NFR-06, NFR-11 | `create_router_app(settings, route_client=…, log_dao=FakeForwardingLogDAO que lanza OSError en save)`; además JSONL real al que se retira el permiso de escritura **después** del arranque (ejecutando las pruebas sin privilegios de administrador; si no es posible, el subcaso se marca como no ejecutado) | Paquete con ruta válida y paquete con Controller caído | Ambos → 500 `LOG_PERSISTENCE_ERROR` (el servicio envuelve el `OSError`; nunca 200 ni 503); diagnóstico en el registro del proceso; `/health` 200 |
| TC-34 | Independencia de procesos | FR-07 | Dos directorios o entornos, cada uno con su aplicación y `shared/` | Arrancar ambos; detener el Controller; consultar `/health` del Router; revisar importaciones | Comunicación solo por HTTP; el Router sigue vivo; ningún archivo de estado común |
| TC-35 | *Retirado en 1.0: duplicaba TC-15* | — | — | — | — |
| TC-36 | Enlace con `p = 1` inutilizable | FR-04 | F-13 | Consultar las tres métricas; restaurar A→B y consultar | E-30 a E-33; nunca se evalúa `ln(0)` |
| TC-37 | Empates exactos en las tres métricas | FR-03, FR-04 | F-14a, F-14a-near, F-14b | Consultar las métricas indicadas | E-34 a E-41; las rutas se comparan exactamente y no dependen de `total_cost` |
| TC-38 | Presentación de `loss` en extremos | FR-04 | F-18, F-16, F-18b | Consultar `loss` | E-42, E-43, E-44; error relativo ≤ 1 × 10⁻¹⁰ frente a la referencia de 100 cifras; `"1e-60"` nunca se publica como `"0"` |
| TC-39 | Separación entre selección y presentación | FR-04 | F-17, F-17b, F-01 | Frontera `q = 1/4`: F-17 ejecuta la rama de la serie y F-17b la de `Decimal.ln()` (comprobado con cobertura de ramas); cada resultado se contrasta con su propia referencia, no entre sí; `RoutingService` con `SpyCostPresenter` que devuelve `"999"`; `is_canonical_cost` sobre las salidas del presentador real | E-45, E-46; con el espía, la ruta no cambia y `format_cost` se llama una vez con el `score` exacto del motor; toda salida real cumple `is_canonical_cost`; el motor no usa `float` (AST) |

### 5.1 Detalle de TC-12 (F-01 recién cargado)

| Petición | Estado | `error.code` / cuerpo |
|---|---:|---|
| `GET /route?src=A&dst=D` (sin `metric`) | 400 | `INVALID_REQUEST` |
| `GET /route?src=A&dst=D&metric=foo` | 400 | `INVALID_REQUEST` |
| `GET /route?src=&dst=D&metric=delay` | 400 | `INVALID_REQUEST` |
| `GET /route?src=X&dst=D&metric=delay` | 404 | `NODE_NOT_FOUND`, `details.field="src"` |
| `GET /route?src=X&dst=Y&metric=delay` | 404 | `NODE_NOT_FOUND`, `details.field="src"` (se valida `src` primero) |
| `GET /route?src=A&dst=Y&metric=delay` | 404 | `NODE_NOT_FOUND`, `details.field="dst"` |
| `GET /route?src=A&dst=A&metric=loss` | 200 | `path=["A"]`, `total_cost="0"` |
| `GET /route?src=%20A&dst=D&metric=delay` (espacio inicial) | 400 | `INVALID_REQUEST` |
| `GET /rutas` | 404 | `UNKNOWN_ENDPOINT` |
| `DELETE /topology` | 405 | `METHOD_NOT_ALLOWED` |
| `POST /links/fail` con cuerpo `{"source": "B",` | 400 | `MALFORMED_JSON` |
| `POST /links/fail` con `{"source": "B"}` | 400 | `INVALID_REQUEST` |
| `POST /links/fail` con `{"source": "B", "target": "D", "x": 1}` | 400 | `INVALID_REQUEST` |
| `POST /links/fail` con `{"source": "X", "target": "D"}` | 404 | `NODE_NOT_FOUND` |
| `POST /links/fail` con `{"source": "D", "target": "A"}` | 404 | `LINK_NOT_FOUND` |
| `GET /health` | 200 | `{"status": "ok", "application": "controller"}` |

## 6. Revisión de código obligatoria (PDF p. 5; parte manual de TC-13)

| Verificación | Cómo |
|---|---|
| `ControllerHTTP` y `PacketHTTP` no contienen Bellman-Ford, construcción de grafos, relajaciones ni construcción de trazas | Lectura de cada handler: solo validan, llaman a un método del servicio y serializan |
| Servicios y handlers no abren archivos ni instancian DAO concretos | Búsqueda de `open(`, `Path.read_text`, `Path.write_text`, `JsonTopologyDAO(`, `JsonlForwardingLogDAO(` fuera de `dao.py` y `app.py` |
| El Router no calcula rutas | Ausencia de `networkx`, `engine` y `controller` en `router/` |
| Inyección verificable | Los constructores de `RoutingService` y `ForwardingService` reciben todas sus dependencias como parámetros obligatorios |

Ambas estudiantes revisan el código de la otra y firman el resultado en `test-results.txt`.

## 7. Evidencias exigidas en la Sesión 2

- `test-results.txt`: salida completa de `pytest -v` (fecha, versiones de Python y bibliotecas, PASS/FAIL por caso) y resultado de la revisión de código.
- `demo-evidence/`: capturas o vídeo de los comportamientos obligatorios del PDF p. 5: ambos procesos en puertos configurables; paquete con ruta y traza; fallo de un enlace de la ruta y nueva respuesta; restauración y nueva consulta; una prueba con DAO falso (TC-08 o TC-09).
- Mediciones crudas de TC-15 y TC-16.

## 8. Estado al cierre de la Sesión 1

TC-01 a TC-39 (excepto TC-24 y TC-35, retiradas) están **especificadas, no implementadas y no ejecutadas**. Ningún resultado de este documento es una observación de software en ejecución. Los resultados esperados de §3 sí están verificados matemáticamente (ver `VALIDACION.md`).
