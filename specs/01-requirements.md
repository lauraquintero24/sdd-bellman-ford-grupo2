# 01 — Requisitos funcionales, no funcionales y criterios de aceptación

| Campo | Valor |
|---|---|
| Proyecto | Controller y Router SDN educativos con Bellman-Ford — Grupo 2 |
| Versión | **1.0** (candidata a baseline `spec-1.0`) · 2026-10-29 |
| Equipo | Mariana Arturo Pabón (Estudiante A — Controller) · Laura Sofía Quintero Fernández (Estudiante B — Router) |
| Estado de aprobación | Ver `REVIEW-AND-BASELINE.md` |
| Fuente normativa | PDF *SDD & Prompt Engineering — Group 2 Bellman-Ford*, pp. 1–7. Las decisiones propias del equipo se identifican como `DEC-xx` (§7). |

Este documento especifica **qué** hace el sistema. Los componentes y el diseño interno están en `02`, las interacciones en `03`, el contrato HTTP en `04`, el plan en `05` y las pruebas en `06`.

## 1. Alcance, límites y actores

El sistema está formado por **dos aplicaciones Python independientes** que se comunican por REST/HTTP con cuerpos JSON. Es una simulación educativa de estilo SDN, no una solución OpenFlow de producción.

| Aplicación | Responsabilidad | Prohibido |
|---|---|---|
| **Controller** (plano de control) | Cargar la topología JSON mediante `TopologyDAO`, representarla con NetworkX, calcular rutas de costo mínimo con Bellman-Ford, publicar la topología y aplicar fallos/restauraciones de enlaces. | Reenviar paquetes. |
| **Router** (plano de datos simulado) | Recibir paquetes lógicos, pedir **por HTTP** la ruta al Controller para cada paquete, simular el reenvío salto a salto por esa ruta y registrar el resultado mediante `ForwardingLogDAO`. | Calcular rutas, importar NetworkX o el motor del Controller, guardar rutas en caché. |

**Fuera de alcance:** reglas OpenFlow, paquetes reales, persistencia del estado de enlaces entre reinicios, autenticación, exposición a Internet y varias instancias del Controller.

**Actores:** *Cliente HTTP* (envía paquetes al Router), *Operador* (consulta topología y rutas; falla y restaura enlaces), *Router* (cliente HTTP del Controller) y *Equipo/profesor* (pruebas y evaluación).

**Convenciones:** identificadores de nodo y de paquete son cadenas no vacías, sin espacios en los extremos y sensibles a mayúsculas; métricas admitidas: `delay`, `inverse_bandwidth`, `loss`; JSON UTF-8 con nombres `snake_case`.

## 2. Requisitos funcionales (FR-01 a FR-10, obligatorios)

| ID | Requisito (PDF p. 1) | Entradas → salidas | Condiciones de error | Criterio de aceptación verificable | Pruebas |
|---|---|---|---|---|---|
| FR-01 | Cargar una topología JSON mediante un DAO. | Archivo JSON (§4) → `Topology(version=1)` en memoria; expuesta por `GET /topology`. | JSON ilegible o que viola §4 → el proceso no arranca y emite un diagnóstico que nombra la regla violada. | `JsonTopologyDAO` carga F-01 y `GET /topology` devuelve 4 nodos, 4 enlaces y `topology_version=1`; cada archivo inválido de TC-10 impide el arranque. | TC-01, TC-10 |
| FR-02 | Admitir topologías válidas arbitrarias con NetworkX. | Cualquier topología conforme a §4 (≥1 nodo, dirigida o no dirigida, conexa o no, con ciclos) → `nx.DiGraph` o `nx.Graph`. | Topologías inválidas: ver FR-01. | Ningún nodo ni tamaño está codificado; se respeta la orientación de cada arco (dirigido) o la simetría (no dirigido); resultados correctos en F-06 y F-09 a F-12. | TC-25, TC-28, TC-29, TC-30 |
| FR-03 | Calcular caminos mínimos con Bellman-Ford. | `(topología, src, dst, metric)` → ruta simple de costo mínimo y su puntuación exacta (suma de costos, o producto de supervivencia en `loss`). | Sin camino → `ROUTE_UNREACHABLE`; ciclo negativo alcanzable (solo en grafo artificial de prueba) → `NEGATIVE_CYCLE`. | La ruta coincide con el óptimo exacto y con DEC-08 en todas las filas de `06` §3; para `delay` e `inverse_bandwidth` el costo coincide con `networkx.bellman_ford_path_length` (pesos `Fraction`); un ciclo negativo alcanzable se detecta y uno no alcanzable no. | TC-01, TC-11, TC-19–TC-23, TC-26, TC-27, TC-37 |
| FR-04 | Costos por retardo, ancho de banda inverso y probabilidad de pérdida. | Enlace `(d, b, p)` → costo `d`, `1/b` o `−ln(1−p)` según §5.1. | `d<0`, `b≤0`, `p∉[0,1]`, NaN o infinito → rechazo al cargar (FR-01); `p=1` → enlace inutilizable. | En F-01: `delay` → `[A,B,D]` `"2"`; `inverse_bandwidth` → `[A,C,D]` `"0.02"`; `loss` → `[A,B,D]` `"0.020100671707"`. Un enlace con `p=1` nunca forma parte de una ruta (F-13). `total_cost` cumple el formato y la precisión de §5.3. | TC-02, TC-10, TC-36, TC-37, TC-38, TC-39 |
| FR-05 | Exponer consultas de ruta mediante una API REST documentada. | `GET /route?src&dst&metric` → `source, destination, metric, path, total_cost, topology_version`. | 400 parámetro ausente o inválido; 404 `NODE_NOT_FOUND`; 404 `ROUTE_UNREACHABLE`. | Respuestas y errores conformes a `04` §3.3; `src=dst` → `path=[src]`, `total_cost="0"`. | TC-01, TC-12, TC-28 |
| FR-06 | Simular fallo y restauración de enlaces y actualizar las rutas siguientes. | `POST /links/fail` o `/links/restore` con `{source, target}` → `active, changed, topology_version`. | 400 cuerpo inválido; 404 `NODE_NOT_FOUND` o `LINK_NOT_FOUND`; repetición → 200 con `changed=false`. | Tras fallar B→D en F-01, la siguiente ruta `delay` A→D es `[A,C,D]` `"4"` con versión 2; tras restaurar vuelve a `[A,B,D]` `"2"` con versión 3; repetir no cambia la versión; un destino aislado da 404 `ROUTE_UNREACHABLE`. | TC-03, TC-04, TC-17, TC-18 |
| FR-07 | El Router solicita las rutas al Controller por HTTP. | Paquete válido → exactamente una petición `GET /route` por paquete. | Controller caído, lento o incoherente → 503, 504 o 502 (`04` §5). | `ForwardingService` depende de `RouteClient` (en producción `HttpRouteClient`); el código del Router no importa NetworkX ni el motor; la prueba de integración registra la petición HTTP real. | TC-05, TC-32, TC-34 |
| FR-08 | El Router simula el reenvío por la ruta elegida por el Controller. | `Route` válida → `ForwardingResult(status="forwarded", trace)`. | Ruta incoherente con la petición → 502 `CONTROLLER_BAD_RESPONSE`. | Para todo `i`: `trace[i].hop_index == i` y `trace[i].node == path[i]`; no se añaden, omiten ni reordenan nodos. | TC-06, TC-31 |
| FR-09 | Gestionar nodos inválidos, destinos inalcanzables y fallos de comunicación con el Controller. | Errores de entrada, de topología y de red. | 400/404/502/503/504 con cuerpo `error` (`04` §5); 500 si además falla la bitácora. | Cada caso devuelve el estado HTTP y el `error.code` de `04` §5; ambos procesos siguen respondiendo `GET /health` 200 después del error. | TC-07, TC-12, TC-31, TC-32 |
| FR-10 | Registrar los resultados del reenvío mediante un DAO. | `ForwardingResult` (incluye `packet_id`, `source`, `destination`, `metric`, `status`) → una línea JSONL mediante `ForwardingLogDAO.save` (`04` §6); recuperación con `list_recent`. | Fallo de escritura → 500 `LOG_PERSISTENCE_ERROR`; nunca 200. | Todo paquete que llega a `ForwardingService` (éxito o fallo) produce exactamente un `save`; el DAO se sustituye por un fake sin modificar el servicio. | TC-06, TC-09, TC-16, TC-33 |

## 3. Requisitos no funcionales (NFR-01 a NFR-09 oficiales; NFR-10 y NFR-11 del equipo)

| ID | Restricción | Criterio verificable | Método de verificación | Pruebas |
|---|---|---|---|---|
| NFR-01 | Ambas aplicaciones implementan MVC con responsabilidades documentadas. | Cada aplicación tiene Model, View, Controller HTTP y servicios en módulos separados según `02` §4. | Revisión de código y análisis AST de importaciones. | TC-13 |
| NFR-02 | Carga, consulta y persistencia mediante DAO; sin acceso directo a almacenamiento en servicios. | Los servicios dependen de `TopologyDAO` / `ForwardingLogDAO` (interfaces); ningún servicio ni handler abre archivos ni instancia DAO concretos. | AST: sin `open()` ni E/S de `pathlib` en `http.py`, `service.py`, `engine.py`, `presenter.py`; DAO concretos solo en `app.py`. | TC-08, TC-09, TC-13 |
| NFR-03 | Bellman-Ford y el reenvío quedan fuera de los handlers HTTP. | Bellman-Ford solo en `controller/engine.py`; reenvío solo en `router/service.py`. | AST y revisión manual obligatoria de handlers (PDF p. 5). | TC-13 |
| NFR-04 | Las interfaces HTTP/JSON cumplen el contrato aprobado. | Toda respuesta nominal y de error coincide con `04`. | `TestClient` y llamadas HTTP reales entre procesos. | TC-12, TC-31 |
| NFR-05 | Puertos y ubicación del archivo de topología configurables. | Puertos, archivo de topología, URL del Controller, archivo de bitácora y timeouts se cambian por variables de entorno o CLI sin editar código (`02` §7). | Arranque de ambos procesos con valores no predeterminados. | TC-14 |
| NFR-06 | Los fallos esperados producen errores controlados y documentados; las aplicaciones siguen vivas. | Fallo esperado → 4xx/5xx con cuerpo `error`, sin traza interna; `GET /health` sigue respondiendo 200. | Pruebas de fallo seguidas de `GET /health`. | TC-07, TC-12, TC-31, TC-32, TC-33 |
| NFR-07 | Implementación orientada a objetos, modular y con dependencias testeables. | Los servicios se instancian con dobles de prueba, sin servidor ni disco. | Instanciación directa en pruebas unitarias. | TC-08, TC-09 |
| NFR-08 | Los requisitos se trazan a tareas, componentes y pruebas automatizadas. | La matriz de `05` §6 no tiene requisitos huérfanos ni pruebas sin requisito. | Verificación automática de la documentación (resultados en `VALIDACION.md`) y revisión del equipo. | Auditoría documental, TC-13 |
| NFR-09 | Las dependencias DAO se reemplazan por mocks/fakes en las pruebas. | `FakeTopologyDAO` y `FakeForwardingLogDAO` se inyectan sin cambiar los servicios. | Pruebas unitarias sin HTTP ni disco. | TC-08, TC-09 |
| NFR-10 *(equipo)* | Latencia local de `GET /route`. | Por loopback, 10 peticiones de calentamiento y 100 peticiones secuenciales exitosas para cada fixture: F-01 (A→D, 4 nodos) y F-19 (N100→N001, cadena de 100 nodos y 197 arcos cuya ruta óptima tiene 99 saltos, lo que obliga al núcleo síncrono a 99 rondas: su peor caso); **p95 ≤ 300 ms** en ambos, con p95 = 95.º valor de las 100 latencias ordenadas. | Script de medición con reloj monotónico del cliente; se guardan las latencias, SO, CPU, RAM, versiones de Python/FastAPI/NetworkX y puertos. | TC-15 |
| NFR-11 *(equipo)* | Integridad de la bitácora con peticiones concurrentes. | Con bitácora temporal vacía, 100 paquetes válidos con `packet_id` distintos enviados por **4 clientes concurrentes** (25 cada uno) producen **exactamente 100 líneas JSONL parseables, sin líneas mezcladas, con 100 IDs distintos**; un fallo de escritura produce 500 y nunca 200. | Prueba con hilos cliente y archivo temporal; DAO fake que falla. | TC-16, TC-33 |

**Alcance de NFR-10 y NFR-11:** son compromisos medibles propuestos por el equipo (PDF p. 2) y se miden en la Sesión 2 con procesos reales. El umbral de 300 ms mantiene la consulta en el rango de respuesta interactiva y deja un margen de más de 6 veces respecto del timeout de lectura del Router (2 s); F-19 lo hace exigente, porque cada una de sus 99 rondas extiende y compara rutas de hasta 100 nodos con aritmética exacta, de modo que una implementación ineficiente (copias profundas, comparaciones con `float`, sin salida temprana) puede incumplirlo. NFR-10 no es una prueba de escalabilidad general. NFR-11 verifica la exclusión mutua del DAO (`lock`), pero no garantiza `fsync` ni recuperación ante cortes de energía.

## 4. Contrato semántico de la topología (DEC-01, DEC-02)

1. **Estructura.** Objeto JSON con exactamente las claves `directed` (booleano), `nodes` (lista no vacía de IDs únicos) y `links` (lista). Cada enlace tiene exactamente `source`, `target`, `delay_ms`, `bandwidth_mbps`, `loss_probability` y `active` (booleano). Las claves desconocidas se rechazan.
2. **Grafo simple.** `source` y `target` existen y son distintos (sin lazos); no hay enlaces paralelos: en modo dirigido, un único enlace por par ordenado; en modo no dirigido, un único enlace por par no ordenado.
3. **Dominios numéricos.** `delay_ms` finito ≥ 0; `bandwidth_mbps` finito > 0; `loss_probability` finito en [0, 1]. Deben ser números JSON (no cadenas ni booleanos), con como máximo 64 cifras significativas y exponente decimal ajustado en [−1000, 1000]. NaN e infinito se rechazan.
4. **Lectura exacta (DEC-09).** Cada literal numérico se convierte a `Decimal` directamente desde su texto, sin pasar por `float`.
5. **Orientación (DEC-01).** `directed=true` (modo de los fixtures y de la demostración): A→B y B→A son enlaces independientes; fallar uno no afecta al otro. `directed=false`: cada enlace es bidireccional, con un único estado y los mismos atributos en ambos sentidos.
6. **Enlaces inutilizables (DEC-02).** Un enlace con `active=false` o con `loss_probability=1` no se usa en ninguna métrica; el segundo caso persiste aunque se restaure (`active=true`).
7. **Versión y estado.** El archivo no contiene versión: `topology_version` empieza en 1 y aumenta en 1 solo cuando cambia efectivamente el estado `active` de un enlace. El estado vive en la memoria del Controller; el archivo fuente nunca se modifica y un reinicio vuelve a su contenido.

**Códigos de regla.** `TopologyLoadError.rule` toma uno de estos valores, para que cada rechazo sea comprobable (TC-10). Las reglas se evalúan en el orden de la tabla y se informa la **primera** violada (por ejemplo, un número escrito como cadena es `TOPO-TYPE` aunque además estuviera fuera de rango). Un objeto JSON con claves duplicadas se rechaza como `TOPO-JSON`.

| `rule` | Violación |
|---|---|
| `TOPO-JSON` | El archivo no es JSON válido o contiene `NaN`/`Infinity` |
| `TOPO-KEYS` | Faltan claves o hay claves desconocidas (topología o enlace) |
| `TOPO-NODES` | `nodes` vacío, o algún ID vacío o con espacios en los extremos |
| `TOPO-DUP-NODE` | ID de nodo repetido |
| `TOPO-ENDPOINT` | `source` o `target` no existe |
| `TOPO-SELF-LOOP` | `source` igual a `target` |
| `TOPO-PARALLEL` | Enlace paralelo según el modo |
| `TOPO-TYPE` | Tipo incorrecto en cualquier campo: `directed` o `active` no booleanos, `nodes` o `links` no listas, ID de nodo, `source` o `target` no textuales, valor numérico escrito como cadena o booleano |
| `TOPO-RANGE` | `delay_ms < 0`, `bandwidth_mbps ≤ 0` o `loss_probability` fuera de [0, 1] |
| `TOPO-DOMAIN` | Más de 64 cifras significativas o exponente fuera de [−1000, 1000] |

## 5. Costos, selección de rutas y semántica numérica

### 5.1 Costos de enlace (PDF p. 1)

| `metric` | Costo aditivo del enlace | Dominio utilizable |
|---|---|---|
| `delay` | `d = delay_ms` | `d ≥ 0` |
| `inverse_bandwidth` | `1 / bandwidth_mbps` | `b > 0` |
| `loss` | `−ln(1 − loss_probability)` | `0 ≤ p < 1` |

El costo de una ruta es la suma de los costos de sus enlaces. **Limitaciones declaradas:** minimizar Σ 1/b es una heurística y no equivale a maximizar el ancho de banda de cuello de botella; minimizar Σ −ln(1−p) equivale a maximizar la probabilidad de entrega Π(1−p) **solo** si las pérdidas por enlace son independientes; el Controller ejecuta Bellman-Ford de forma centralizada, lo que no equivale a un protocolo distribuido de vector de distancias (Kurose y Ross, cap. 5).

### 5.2 Selección y desempate (DEC-08)

Para la métrica solicitada se elige la ruta que minimiza, en este orden: **(1)** el costo exacto de esa métrica; **(2)** el número de saltos `H = len(path) − 1`; **(3)** la secuencia completa de IDs `tuple(path)` en orden lexicográfico (comparación de cadenas Python por punto de código Unicode, sensible a mayúsculas). Las otras dos métricas **nunca** desempatan. La ruta elegida es siempre simple y no depende del orden de `nodes` ni de `links` en el JSON.

### 5.3 Semántica numérica (DEC-09)

1. **Selección exacta.** Los valores `Decimal` se convierten a `Fraction`. `delay` e `inverse_bandwidth` se comparan como sumas racionales exactas. `loss` se compara mediante el producto racional exacto de supervivencia `S(P) = Π(1 − p)`: mayor `S` equivale a menor `Σ −ln(1−p)` porque `−ln` es estrictamente decreciente en (0, 1]. No se usan `float`, tolerancias, `math.isclose` ni `math.fsum` para elegir rutas.
2. **Ejemplo obligatorio (F-08).** A→D con `delay_ms=0.8` frente a A→B `0.1` + B→D `0.7`. En `float`, `0.1 + 0.7 = 0.7999999999999999` y se elegiría por error la ruta de dos saltos. En aritmética exacta `1/10 + 7/10 = 4/5`: hay empate y gana `[A,D]` por tener un salto.
3. **Presentación.** `total_cost` es una **cadena** decimal no negativa que solo informa; nunca se usa para comparar rutas. **Precisión:** para `delay` e `inverse_bandwidth` es el valor racional exacto redondeado (`ROUND_HALF_EVEN`) a 12 cifras significativas, por lo que las pruebas lo comparan como cadena exacta; para `loss` es una aproximación de `−ln(S)` con **error relativo ≤ 1 × 10⁻¹⁰** frente a una referencia de al menos 100 cifras (procedimiento en `02` §6.3), por lo que las pruebas aceptan cualquier cadena canónica dentro de esa tolerancia (el valor de referencia de `06` §3 es el redondeo correcto). `"0"` se usa solo si el costo es matemáticamente cero; un costo positivo nunca se publica como `"0"`.
4. **Formato canónico.** Con `r` = valor redondeado a como máximo 12 cifras significativas: si 10⁻⁶ ≤ r < 10¹², notación fija sin ceros finales ni punto final (`"2"`, `"20"`, `"0.02"`, `"0.000001"`, `"27.6310211159"`); en otro caso, notación científica con mantisa normalizada sin ceros finales, `e` minúscula, signo obligatorio y exponente sin ceros a la izquierda (`"1e-7"`, `"1e-60"`, `"1.5e+13"`). Gramática: `^(0|[1-9][0-9]*(\.[0-9]*[1-9])?|0\.[0-9]*[1-9]|[1-9](\.[0-9]*[1-9])?e[+-][1-9][0-9]*)$`, más las condiciones de rango anteriores y ≤ 12 cifras significativas. La comprobación es la función pura `is_canonical_cost` de `shared/cost_format.py`, usada por el Router (`04` §4.3) y por las pruebas.

### 5.4 Ciclos negativos (DEC-07)

Las tres métricas solo producen costos ≥ 0 (factores de supervivencia en (0, 1]), por lo que una topología válida no puede contener ciclos negativos. Aun así, el motor implementa la pasada de detección de Bellman-Ford en su núcleo común de relajación, **en ambos modos**: en el aditivo, una mejora estricta de la suma; en el de producto (`loss`), una mejora estricta del producto, que solo es posible con factores > 1 (`p < 0`). La prueba TC-11 le inyecta directamente grafos artificiales: uno con un ciclo negativo alcanzable (debe lanzar `NegativeCycleError`), otro con un ciclo negativo no alcanzable desde el origen (no debe lanzarlo) y uno con un ciclo de ganancia en modo producto (debe lanzarlo). Los valores negativos en archivos de topología siguen rechazándose (`TOPO-RANGE`).

## 6. Escenarios operativos y de error

| Escenario | Precondición / entrada | Resultado obligatorio |
|---|---|---|
| Consulta exitosa | `src` y `dst` existen y hay camino utilizable | 200 con `path`, `metric`, `total_cost`, `topology_version` |
| Mismo origen y destino | ID existente con `src = dst` | 200, `path=[src]`, `total_cost="0"` |
| Nodo inexistente | `src` o `dst` no está en la topología | 404 `NODE_NOT_FOUND` (se valida `src` antes que `dst`) |
| Sin camino | Ambos nodos existen pero no hay ruta utilizable | 404 `ROUTE_UNREACHABLE` |
| Entrada inválida | Parámetro o campo ausente, tipo erróneo, cadena vacía o `metric` no admitida | 400 `INVALID_REQUEST` |
| JSON ilegible | Cuerpo con sintaxis JSON inválida | 400 `MALFORMED_JSON` |
| Enlace inexistente | Fallo/restauración de un par sin enlace | 404 `LINK_NOT_FOUND` (404 `NODE_NOT_FOUND` si un extremo no existe) |
| Fallo o restauración repetidos | El enlace ya está en el estado pedido | 200 con `changed=false`; la versión no cambia |
| Controller rechaza la conexión | Proceso detenido o puerto cerrado | Router 503 `CONTROLLER_UNAVAILABLE`; registro `failed` |
| Controller no responde a tiempo | Se excede el timeout de conexión o de lectura | Router 504 `CONTROLLER_TIMEOUT`; registro `failed` |
| Respuesta incoherente del Controller | JSON inválido, campos o ruta incoherentes, estado no previsto | Router 502 `CONTROLLER_BAD_RESPONSE`; registro `failed` |
| Fallo de la bitácora | `ForwardingLogDAO.save` falla | Router 500 `LOG_PERSISTENCE_ERROR`; nunca 200 |
| Ciclo negativo (invariante violado) | Grafo con pesos negativos inyectado por la prueba en el motor o mediante un DAO falso; imposible con una topología validada | `NegativeCycleError`; por HTTP, 500 `NEGATIVE_CYCLE`; ninguna ruta |
| Topología inválida al arrancar | Viola §4 | El proceso no arranca; diagnóstico con la regla violada |

**Orden de validación:** formato y esquema (400) → existencia de nodos, primero `src` y luego `dst` (404) → conectividad (404) → cálculo. **Registro en bitácora:** las solicitudes rechazadas por la capa View antes de llegar a `ForwardingService` no se registran; todo resultado producido dentro del servicio, de éxito o de fallo, sí, salvo que falle la propia bitácora.

## 7. Ambigüedades del enunciado y decisiones del equipo

Las ambigüedades se identificaron con apoyo de IA (registro P01 de `prompts-session1.md`); las decisiones corresponden al equipo. El origen y el estado de aprobación de cada decisión, incluida la revisión de DEC-03 en la versión 1.0 (cambio C-01, propuesto con asistencia de IA), constan en `CHANGELOG-SPECS.md` y `REVIEW-AND-BASELINE.md`. No son instrucciones literales del docente.

| ID | Ambigüedad del PDF | Decisión | Justificación |
|---|---|---|---|
| DEC-01 | No fija formato JSON, direccionalidad ni enlaces paralelos. | Formato de §4; grafo simple; modo dirigido en fixtures y demostración, modo no dirigido también admitido; estado en memoria. | FR-02 exige topologías arbitrarias; el modo dirigido permite modelar enlaces asimétricos. |
| DEC-02 | No dice si un enlace con `p=1` puede usarse con otras métricas. | Inutilizable para todas las métricas. | Una ruta con `p=1` nunca entrega el paquete, aunque minimice el retardo. |
| DEC-03 | Los códigos HTTP se dan solo como ejemplo («400 invalid input, 404 node/path absent, 503 controller unavailable»). | 400 para toda entrada inválida (`MALFORMED_JSON`, `INVALID_REQUEST`); 404 para nodo, enlace o camino ausente, distinguidos por `error.code`; Router: 503 sin conexión, 504 timeout, 502 respuesta no conforme, 500 fallo de bitácora; 500 `NEGATIVE_CYCLE` si se violara el invariante de pesos no negativos. | Sigue literalmente el ejemplo oficial y distingue la ausencia de camino de la entrada de nodo inválida mediante `error.code`, como pide el PDF p. 4; 504 y 502 refinan el «controller unavailable» según la semántica estándar de una pasarela. |
| DEC-04 | No dice si fallar o restaurar dos veces es un error. | Operaciones idempotentes: 200 con `changed=false` y sin aumento de versión. | Reintentos seguros del operador; versión ligada a cambios reales. |
| DEC-05 | Exige DAO en ambas aplicaciones pero solo nombra dos persistencias. | `TopologyDAO` en el Controller y `ForwardingLogDAO` en el Router; el cliente HTTP del Router es otra interfaz (`RouteClient`), no un DAO. | Separa el acceso a datos de la comunicación entre procesos. |
| DEC-06 | No precisa el comportamiento del Router si el Controller falla. | Sin caché ni cálculo local: 503/504/502, traza vacía y registro `failed`. | Preserva la separación SDN entre control y reenvío. |
| DEC-07 | Exige detectar ciclos negativos, pero las métricas no producen pesos negativos. | Detección en el núcleo del motor, probada con un grafo artificial inyectado (§5.4). | Cumple FR-03 sin relajar la validación de topologías. |
| DEC-08 | No define el desempate entre rutas de igual costo. | Costo de la métrica pedida → menos saltos → ruta lexicográfica completa (§5.2). | Resultado determinista e independiente del orden de iteración de NetworkX. |
| DEC-09 | Los decimales JSON y el costo logarítmico de `loss` requieren una comparación consistente. | Comparación exacta con `Fraction` y producto de supervivencia; `total_cost` es una cadena canónica solo de presentación (§5.3). | Evita errores de `float` (F-08) y costos positivos diminutos publicados como cero (F-18). |

## 8. Casos de uso

| ID | Actor | Precondición | Flujo principal | Flujos alternativos | Postcondición | FR |
|---|---|---|---|---|---|---|
| UC-01 Consultar ruta | Operador o Router | Controller activo con topología válida | 1. Envía `GET /route`. 2. `RoutingService` obtiene una instantánea vía `TopologyDAO`. 3. El motor elige la ruta (DEC-08). 4. Se devuelve la ruta con costo y versión. | Parámetro inválido → 400; nodo ausente → 404 `NODE_NOT_FOUND`; sin camino → 404 `ROUTE_UNREACHABLE`. | Sin cambios de estado. | FR-02, FR-03, FR-04, FR-05, FR-09 |
| UC-02 Reenviar paquete | Cliente HTTP | Router activo | 1. Envía `POST /packets`. 2. `ForwardingService` pide la ruta por HTTP. 3. Construye la traza. 4. Registra el resultado. 5. Responde 200 `forwarded`. | Error del Controller → 404/502/503/504 y registro `failed`; fallo de bitácora → 500. | Una línea nueva en la bitácora (salvo fallo de la propia bitácora). | FR-07, FR-08, FR-09, FR-10 |
| UC-03 Fallar o restaurar enlace | Operador | Controller activo | 1. Envía `POST /links/fail` o `/links/restore`. 2. El DAO cambia `active` y aumenta la versión si hubo cambio. 3. Responde el nuevo estado. | Repetición → 200 `changed=false`; enlace o nodo ausente → 404. | Las consultas siguientes usan el nuevo estado. | FR-06 |
| UC-04 Consultar topología | Operador | Controller activo | `GET /topology` devuelve nodos, enlaces con su estado y versión. | — | Sin cambios. | FR-01, FR-05 |
| UC-05 Verificar arquitectura | Equipo | Código de la Sesión 2 | Las pruebas inyectan fakes de ambos DAO y de `RouteClient`, sin servidores ni disco. | — | Evidencia de aislamiento (TC-08, TC-09). | FR-10, NFR-02, NFR-09 |

## 9. Restricciones, supuestos y referencias

- **Tecnología de la Sesión 2:** Python ≥ 3.11, FastAPI, Uvicorn, NetworkX, httpx y pytest; dos procesos del sistema operativo con puertos configurables. En la Sesión 1 no se genera código de implementación (PDF p. 3 y p. 7).
- **Supuestos:** pérdidas independientes entre enlaces; una sola instancia del Controller; API de laboratorio sin autenticación, escucha por defecto en `127.0.0.1` y no debe exponerse a Internet.
- **Referencias:** PDF del taller Grupo 2 (pp. 1–7); J. F. Kurose y K. W. Ross, *Computer Networking: A Top-Down Approach*, 7.ª ed., 2017, cap. 5 (algoritmos de enrutamiento de costo mínimo; control centralizado frente a distribuido); diapositivas *Chapter 5 — Network Layer: Control Plane*, pp. 4–6; Google, *Gemini for Google Workspace: Prompting Guide 101*, 2024, pp. 2–3 (técnicas de prompting).
