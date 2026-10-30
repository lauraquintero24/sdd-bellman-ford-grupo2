# Grupo 2 — Controller y Router SDN con Bellman-Ford · Sesión 1: especificación y arquitectura

**Curso:** Informática para Telecomunicaciones · **Taller:** *SDD & Prompt Engineering — SDN Controller and Router Applications* (Grupo 2, Bellman-Ford)
**Equipo:** Mariana Arturo Pabón (Estudiante A — Controller) · Laura Sofía Quintero Fernández (Estudiante B — Router)
**Versión:** 1.0 (2026-10-29), candidata a baseline `spec-1.0`

Este paquete contiene los entregables de la **Sesión 1**: las seis especificaciones, el registro de prompts y la revisión cruzada para congelar la baseline. Conforme al PDF (pp. 3 y 7), **no contiene código**: `controller/`, `router/`, `shared/`, `tests/`, `test-results.txt`, `prompts-session2.md` y `demo-evidence/` son entregables de la Sesión 2. Las herramientas que verificaron la documentación (escritas con asistencia de IA) se entregan al equipo por separado; sus resultados están en `VALIDACION.md`.

## Estado

| Entregable de la Sesión 1 (PDF p. 4) | Archivo | Estado |
|---|---|---|
| Requisitos FR/NFR, casos de uso, restricciones, criterios de aceptación y dos NFR medibles | `specs/01-requirements.md` | Completo |
| Diagramas de componentes y de clases; MVC y DAO en ambas aplicaciones; inyección de dependencias | `specs/02-static-architecture.md` | Completo |
| Tres diagramas de secuencia (reenvío, fallo y restauración, Controller no disponible) | `specs/03-dynamic-architecture.md` | Completo |
| Contrato de API con ejemplos JSON, estados y errores | `specs/04-api-contract.md` | Completo |
| Desglose del trabajo, dependencias, propiedad y trazabilidad | `specs/05-implementation-plan.md` | Completo |
| ≥ 8 casos de prueba con resultados esperados, incluidos los de arquitectura | `specs/06-test-specification.md` (+ `specs/fixtures/`) | 37 casos especificados y 48 resultados esperados verificados; **no ejecutados** (Sesión 2) |
| Registro de prompts con técnicas, crítica y refinamientos | `prompts-session1.md` (+ `evidencias/prompts/`) | Completo; la crítica personal de cada estudiante va en su constancia de reconfirmación |
| Confirmación de ambas estudiantes y baseline congelada | `REVIEW-AND-BASELINE.md` | **Hecho:** versión 1.0 reconfirmada por ambas el 30/10/2026 y congelada en el commit `20c2289` (tag `spec-1.0`) | 

## Estructura

```text
README.md                    este archivo
REVIEW-AND-BASELINE.md       revisión cruzada, historial de aprobación y pasos de congelamiento
CHANGELOG-SPECS.md           cambios RC11 → 1.0 con motivo y artefactos afectados
VALIDACION.md                verificaciones ejecutadas, resultados y límites
SHA256SUMS                   inventario SHA-256 (formato de sha256sum -c)
prompts-session1.md          registro de prompts de la Sesión 1
specs/                       01–06 y fixtures/ (27 topologías JSON usadas por las pruebas)
diagrams/                    7 fuentes Mermaid (idénticas a las de 02 y 03) y sus SVG
evidencias/aprobaciones/     constancias RC11, firmas, plantilla y constancias de reconfirmación 1.0
evidencias/few_shot/         captura del ejercicio few-shot P09
evidencias/prompts/          transcripciones literales de los prompts largos
```

## Cómo comprobar el paquete

```bash
sha256sum -c SHA256SUMS                                                      # integridad de todos los archivos
for f in diagrams/*.mmd; do mmdc -i "$f" -o "${f%.mmd}.svg" -b white; done   # opcional: regenerar los SVG (Mermaid CLI)
```

## Acciones humanas pendientes

1. ~~Reconfirmación de la versión 1.0~~ — **hecha** el 30/10/2026 (`evidencias/aprobaciones/reconfirmacion-v1.0-Mariana.pdf` y `evidencias/aprobaciones/reconfirmacion-v1.0-Laura.pdf`; `REVIEW-AND-BASELINE.md` §2.4).
2. **Informar al docente** de que en una iteración temprana la IA produjo un borrador de código, que no se incluye ni se usará (`REVIEW-AND-BASELINE.md` §2.2).
3. ~~Congelar la baseline~~ — **hecho** el 30/10/2026: commit `20c2289`, tag `spec-1.0` (`REVIEW-AND-BASELINE.md` §3).
4. ~~Sesión 2~~ — **hecha** el 30/10/2026: implementación desde la baseline, `553 passed` en Windows 11 (incluidas TC-08 y TC-09), NFR-10 y NFR-11 medidos y evidencias en `demo-evidence/` (sección «Sesión 2» más abajo).

---

# Sesión 2 — Implementación, pruebas y evidencias

> Esta sección se añade a la de la Sesión 1 (que se conserva arriba sin cambios; su frase «no contiene código» describe el paquete de la Sesión 1). La implementación sigue la baseline congelada `spec-1.0`: `git diff --stat spec-1.0 HEAD -- specs diagrams prompts-session1.md` sale vacío.
> **Dónde se obtuvieron los resultados:** la suite de pruebas (`553 passed`) y la demostración de `demo-evidence/` se ejecutaron en **Windows 11 con Git Bash** el 30/10/2026, en el ordenador del equipo. Las mediciones de NFR-10 y NFR-11 (`demo-evidence/nfr10/`, `demo-evidence/nfr11/`) proceden de una **máquina Linux en la nube** (sesión de Claude Code en la web), donde también se ejecutó la suite (`552 passed, 1 skipped`).

## Instalación

Requisitos: Python ≥ 3.11 y Git. Dependencias con versiones exactas en `requirements.txt` (FastAPI 0.162.0, Uvicorn 0.54.0, Pydantic 2.14.2, NetworkX 3.6.1, httpx 0.28.1, pytest 9.2.0). El entorno virtual `.venv/` no se sube a Git.

Linux / macOS:

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
python -m pip install -r requirements.txt
```

Windows con Git Bash (equivalente; solo cambia la ruta del intérprete del entorno virtual):

```bash
python -m venv .venv
```

```bash
source .venv/Scripts/activate
```

```bash
python -m pip install -r requirements.txt
```

## Arranque de los dos procesos

Cada aplicación es un proceso independiente; se comunican solo por HTTP. Precedencia: opción CLI > variable de entorno > valor por defecto (`02` §7). Una topología inválida, un puerto fuera de 1–65535, un timeout ≤ 0 o un directorio de bitácora sin escritura impiden el arranque con un diagnóstico.

| Proceso | Opción CLI | Variable de entorno | Por defecto |
|---|---|---|---|
| Controller | `--host` | `CONTROLLER_HOST` | `127.0.0.1` |
| Controller | `--port` | `CONTROLLER_PORT` | `8000` |
| Controller | `--topology` | `TOPOLOGY_FILE` | `config/topology.json` (copia de F-01) |
| Router | `--host` | `ROUTER_HOST` | `127.0.0.1` |
| Router | `--port` | `ROUTER_PORT` | `8001` |
| Router | `--controller-url` | `CONTROLLER_URL` | `http://127.0.0.1:8000` |
| Router | `--log-file` | `FORWARDING_LOG_FILE` | `data/forwarding.jsonl` (se crea `data/`) |
| Router | `--connect-timeout` | `CONTROLLER_CONNECT_TIMEOUT_SECONDS` | `1.0` |
| Router | `--read-timeout` | `CONTROLLER_READ_TIMEOUT_SECONDS` | `2.0` |

En dos terminales (los mismos comandos sirven en Git Bash con el entorno activado):

```bash
python -m controller.main --port 8100 --topology specs/fixtures/F-01.json
```

```bash
python -m router.main --port 8101 --controller-url http://127.0.0.1:8100 --log-file data/forwarding.jsonl
```

Ejemplos de uso:

```bash
curl -s "http://127.0.0.1:8100/route?src=A&dst=D&metric=delay"
```

```bash
curl -s -X POST http://127.0.0.1:8100/links/fail -H 'Content-Type: application/json' -d '{"source": "B", "target": "D"}'
```

```bash
curl -s -X POST http://127.0.0.1:8101/packets -H 'Content-Type: application/json' -d '{"packet_id": "pkt-001", "source": "A", "destination": "D", "metric": "delay"}'
```

Si en Windows hay un proxy configurado en el sistema, añadir `--noproxy '*'` a `curl`. La documentación OpenAPI está en `/docs` de cada proceso; si difiere, prevalece `specs/04-api-contract.md`.

## Pruebas, demostración y mediciones

```bash
python -m pytest -v -rA 2>&1 | tee test-results.txt
```

```bash
bash scripts/demo.sh "descripción de la máquina"
```

```bash
python scripts/measure_nfr10.py --machine "descripción de la máquina"
```

```bash
python scripts/measure_nfr11.py --machine "descripción de la máquina"
```

- `scripts/demo.sh` arranca Controller (8100) y Router (8101) y guarda en `demo-evidence/` un archivo por paso con fecha, comando y salida literal: paquete con ruta y traza (a), fallo de un enlace de la ruta (b), restauración con versión 1 → 2 → 3 (c), destino inalcanzable (c2), Controller detenido → 503 y Controller que no responde → 504 (d), bitácora JSONL (e) y registro de accesos del Controller (f). Detecta `.venv/Scripts/python.exe` (Windows) o `.venv/bin/python` (Linux); los puertos se cambian con `CONTROLLER_PORT_DEMO`, `ROUTER_PORT_DEMO`, `ROUTER2_PORT_DEMO` y `SILENT_PORT_DEMO`. **En Windows (Git Bash) la demo arranca el Router con `--connect-timeout 3`** (en Linux, con el valor por defecto 1.0; se cambia con `CONNECT_TIMEOUT_DEMO`), para que el paso d muestre 503 con el Controller detenido: ver la limitación 10. **Solo se ha ejecutado en Linux;** debe ensayarse en el ordenador de la defensa.
- Si en Windows se arranca el Router a mano para la demostración, usar también `--connect-timeout 3`:

```bash
python -m router.main --port 8101 --controller-url http://127.0.0.1:8100 --log-file data/forwarding.jsonl --connect-timeout 3
```
- La prueba con DAO falso exigida en la demostración es `python -m pytest -v tests/test_tc08_routing_service_fake_dao.py tests/test_tc09_forwarding_service_fake_dao.py`.

## Estructura y correspondencia MVC/DAO

```text
controller/   main.py · settings.py · app.py (composición DI) · http.py (Controller MVC) · http_errors.py
              view.py (View) · models.py (Model) · ports.py (TopologyDAO) · service.py (RoutingService)
              engine.py (BellmanFordEngine, LinkCostPolicy) · presenter.py (CostPresenter) · dao.py (JsonTopologyDAO)
router/       main.py · settings.py · app.py (composición DI) · http.py (Controller MVC) · http_errors.py
              view.py (View) · models.py (Model) · ports.py (RouteClient, ForwardingLogDAO) · service.py (ForwardingService)
              client.py (HttpRouteClient) · dao.py (JsonlForwardingLogDAO)
shared/       models.py (Route) · errors.py (AppError y subclases) · error_contract.py · cost_format.py (is_canonical_cost)
config/       topology.json (copia de F-01, valor por defecto de TOPOLOGY_FILE)
tests/        test_tcXX_*.py (una o más por caso de 06), fakes.py (dobles), oracle.py (48 filas de 06 §3), conftest.py
scripts/      demo.sh · measure_nfr10.py · measure_nfr11.py
demo-evidence/  salidas literales de la demostración y mediciones (nfr10/, nfr11/)
test-results.txt  salida de pytest, tabla TC → estado y revisión manual (por firmar)
prompts-session2.md  registro de prompts de la Sesión 2
```

| Capa | Controller | Router |
|---|---|---|
| Model | `Topology`, `Link`, `LinkChangeResult`; `Route` (shared) | `Packet`, `ForwardingResult`, `TraceHop`; `Route` |
| View | esquemas Pydantic de `controller/view.py` | esquemas Pydantic de `router/view.py` |
| Controller MVC | `ControllerHTTP` + `http_errors.py` | `PacketHTTP` + `http_errors.py` |
| Servicio | `RoutingService`, `BellmanFordEngine`, `CostPresenter` | `ForwardingService` |
| Puerto / DAO | `TopologyDAO` → `JsonTopologyDAO` | `ForwardingLogDAO` → `JsonlForwardingLogDAO`; `RouteClient` → `HttpRouteClient` |
| Composición (DI) | `create_controller_app(settings, dao=None)` | `create_router_app(settings, route_client=None, log_dao=None)` |

## Estado de los requisitos

Evidencia en `test-results.txt` (Windows 11: 553 aprobadas, 0 fallidas; nube: 552 aprobadas y 1 subcaso omitido por permisos) y en `demo-evidence/`.

| Requisito | Estado | Evidencia |
|---|---|---|
| FR-01 Carga JSON por DAO | Cumplido | TC-01, TC-10 |
| FR-02 Topologías arbitrarias con NetworkX | Cumplido | TC-25, TC-28, TC-29, TC-30 |
| FR-03 Bellman-Ford | Cumplido | TC-01, TC-11, TC-19–TC-23, TC-26, TC-27, TC-37; oráculo 48/48 |
| FR-04 Tres métricas | Cumplido | TC-02, TC-10, TC-36–TC-39 |
| FR-05 API REST de rutas | Cumplido | TC-01, TC-12, TC-28 |
| FR-06 Fallo y restauración | Cumplido | TC-03, TC-04, TC-17, TC-18; `demo-evidence/b-…`, `c-…` |
| FR-07 Router pide rutas por HTTP | Cumplido | TC-05, TC-32, TC-34; `demo-evidence/f-registro-accesos-controller.txt` |
| FR-08 Reenvío salto a salto | Cumplido | TC-06, TC-31 |
| FR-09 Errores controlados | Cumplido | TC-07, TC-12, TC-31, TC-32; `demo-evidence/c2-…`, `d-…` |
| FR-10 Bitácora por DAO | Cumplido | TC-06, TC-09, TC-16, TC-33 (todos los subcasos en Windows 11) |
| NFR-01 MVC | Cumplido | AST de TC-13 aprobado; revisión manual de 06 §6 firmada por ambas (30/10/2026) |
| NFR-02 DAO, sin E/S en servicios | Cumplido | TC-08, TC-09, AST de TC-13 |
| NFR-03 Algoritmos fuera de los handlers | Cumplido | AST de TC-13 aprobado (sin bucles de algoritmo en `http.py`); revisión manual firmada por ambas |
| NFR-04 Contrato HTTP/JSON | Cumplido | TC-12, TC-31, TC-32 |
| NFR-05 Configuración | Cumplido | TC-14 (ambos procesos en puertos no predeterminados) |
| NFR-06 Errores documentados, procesos vivos | Cumplido | TC-07, TC-12, TC-31, TC-32, TC-33 |
| NFR-07 OO y dependencias testeables | Cumplido | TC-08, TC-09 |
| NFR-08 Trazabilidad | Cumplido | Matriz verificada en la Sesión 1 (`VALIDACION.md`); tabla TC → estado en `test-results.txt`; TC-13 manual firmada |
| NFR-09 DAO sustituibles por fakes | Cumplido | TC-08, TC-09 |
| NFR-10 p95 de `GET /route` ≤ 300 ms | Cumplido (máquina en la nube) | TC-15; `demo-evidence/nfr10/`: p95 F-01 = 2.414 ms, F-19 = 41.970 ms; repetir en el ordenador de la defensa |
| NFR-11 Bitácora concurrente | Cumplido (máquina en la nube) | TC-16; `demo-evidence/nfr11/`: 4 × 25, 100 líneas, 100 IDs; fallo de escritura → 500 en TC-33 |

## Limitaciones conocidas

1. **Mediciones en la nube.** NFR-10 y NFR-11 se midieron en la máquina Linux en la nube; no se han repetido en Windows (`scripts/measure_nfr10.py` y `scripts/measure_nfr11.py` admiten `--machine` y `--out`). La demostración y la suite completa sí se ejecutaron en Windows 11.
2. **TC-33, subcaso con permisos:** «JSONL real sin permiso de escritura» quedó omitido en la nube porque esa máquina ejecuta como administrador; en Windows 11 se ejecutó y pasó (`553 passed`).
3. **Revisión manual de código (TC-13, 06 §6):** completada y firmada por ambas estudiantes el 30/10/2026 (`test-results.txt`).
4. **Interpretaciones sin cambio de especificación:** (a) orden de las reglas TOPO-* con estructuras no iterables: cada regla examina solo los valores de su tipo; una raíz o un enlace que no son objetos son `TOPO-TYPE`; un `source` no textual ausente de `nodes` es `TOPO-ENDPOINT` (lectura literal de `01` §4); (b) los números de `GET /topology` se serializan con un formateador propio de `04` §3.2 (`"1.0"`, `"1e-60"`, `"1.5e+13"`); (c) un costo negativo (solo posible con un grafo artificial sin ciclo) produce 500 `INTERNAL_ERROR`; (d) `CONTROLLER_URL` debe empezar por `http://` o `https://`; (e) los timeouts de escritura y de pool de httpx valen, respectivamente, el de lectura y el de conexión (ejemplo de `04` §4.2).
5. **NetworkX 3.6.1** en lugar de 3.7, porque 3.7 exige Python ≥ 3.12 y la especificación admite 3.11.
6. **Aviso de Starlette:** el `TestClient` de FastAPI emite `StarletteDeprecationWarning` («Using `httpx` with `starlette.testclient` is deprecated»); no afecta a los resultados.
7. **Alcance de NFR-11:** la exclusión mutua es un candado del proceso Router; no hay `fsync` ni protección si varios procesos escriben el mismo archivo.
8. **Estado en memoria:** fallos y restauraciones se pierden al reiniciar el Controller (`01` §4.7). El Router confía en la optimalidad de la ruta del Controller (`04` §4.3).
9. No se aplicó la línea de corte de `05` §1: `CostPresenter` implementa el procedimiento completo de `02` §6.3.
10. **Controller detenido en Windows con el connect timeout por defecto: 504 en lugar de 503.** En Windows una conexión rechazada a 127.0.0.1 no falla al instante: el equipo midió `socket.connect` a 127.0.0.1:9 (puerto cerrado) → «ConnectionRefusedError 2.03 s». Con `CONTROLLER_CONNECT_TIMEOUT_SECONDS` = 1.0 (valor por defecto de `02` §7) httpx agota antes el plazo de conexión y lanza `ConnectTimeout`, que `04` §5 traduce a 504 `CONTROLLER_TIMEOUT`, en lugar de `ConnectError` → 503 `CONTROLLER_UNAVAILABLE`. Por eso, en Windows, TC-07 y TC-34 fallaban (`2 failed, 551 passed`, ver `test-results.txt`). Corrección sin cambiar el valor por defecto ni la especificación: esas dos pruebas y la demo en Git Bash arrancan el Router con `--connect-timeout 3`. En Linux la conexión rechazada falla al instante y el comportamiento no cambia. Con la configuración por defecto, en Windows un Controller detenido se sigue viendo como 504; cambiar el valor por defecto exigiría un cambio de especificación aprobado por ambas (`CHANGELOG-SPECS.md`).
