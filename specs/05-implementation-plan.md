# 05 — Plan de implementación: desglose, dependencias, propiedad y trazabilidad

| Campo | Valor |
|---|---|
| Versión | **1.0** (candidata a baseline `spec-1.0`) · 2026-10-29 |
| Estado de aprobación | Ver `REVIEW-AND-BASELINE.md`. Plan **sin código** (PDF p. 3); las duraciones son presupuestos, no mediciones. |
| Equipo | **Estudiante A — Mariana Arturo Pabón:** Controller · **Estudiante B — Laura Sofía Quintero Fernández:** Router |
| Calendario oficial | Sesión 1: 108 min (especificación) · Sesión 2: 108 min (implementación) · Defensa: 20 min por equipo |

## 1. Alcance y puertas de control

- **Puerta de la Sesión 1 (W-01):** las seis especificaciones, `prompts-session1.md` y la revisión cruzada están completas; ambas estudiantes confirman la versión 1.0 y se crea el tag Git `spec-1.0`. **No se escribe código antes de superar esta puerta.**
- **Mínimo obligatorio de la Sesión 2 (no reducible):** dos procesos con MVC, DAO e inyección de dependencias; carga JSON y NetworkX; Bellman-Ford con las tres métricas; fallo y restauración con versión; Router sin cálculo local; API completa de `04`; bitácora por DAO; errores controlados; **≥ 8 pruebas automatizadas aprobadas, incluidas TC-08 y TC-09**; revisión de código (`06` §6); `test-results.txt`, `demo-evidence/`, `prompts-session2.md`, README y commits individuales.
- **Pruebas complementarias (TC-10 a TC-39):** se ejecutan después de TC-01–TC-09 según el riesgo. Las que no se ejecuten se declaran **pendientes**; nunca se presentan como aprobadas. NFR-10 y NFR-11 solo se declaran cumplidos con mediciones reales.
- **Línea de corte (si el tiempo no alcanza):** primero se garantiza el mínimo obligatorio del PDF. Si en el punto G3 (min 55) el presentador de costos no está listo, `CostPresenter` usa provisionalmente `−Decimal.ln(S)` de 60 cifras en todos los casos de `loss`. Esa variante cumple la precisión salvo cuando `q = 1 − S` es menor que unos 10⁻⁵⁰ y `S` no es representable exactamente con 60 cifras (ningún fixture actual cae en ese caso: en F-18, `S = 1 − 10⁻⁶⁰` sí es representable); se documenta como **limitación conocida** en el README. No se recorta ningún FR ni se cambia el contrato.

## 2. Propiedad y colaboración (PDF p. 4)

| Estudiante A — Controller | Estudiante B — Router | Trabajo conjunto |
|---|---|---|
| `Topology`, `Link`, `LinkChangeResult`, `Route` (`shared/models.py`), `AppError` y errores del Controller (`InvalidRequestError`, `NodeNotFoundError`, `LinkNotFoundError`, `RouteUnreachableError`, `NegativeCycleError` en `shared/errors.py`), `TopologyDAO`, `JsonTopologyDAO`, `TopologyLoadError` | `Packet`, `ForwardingResult`, `TraceHop`, `ForwardingLogDAO`, `JsonlForwardingLogDAO`, errores del Router (`ControllerUnavailableError`, `ControllerTimeoutError`, `ControllerBadResponseError`, `LogPersistenceError`), `shared/error_contract.py`, `shared/cost_format.py` | Revisión cruzada de todo `shared/`, contrato `04`, control de cambios |
| `LinkCostPolicy`, `BellmanFordEngine`, `CostPresenter`, `RoutingService` | `RouteClient`, `HttpRouteClient`, `ForwardingService` | Integración entre procesos y pruebas cruzadas |
| `ControllerHTTP`, `controller/http_errors.py`, `create_controller_app` | `PacketHTTP`, `router/http_errors.py`, `create_router_app` | Revisión mutua del código: cada una explica ambos procesos en la defensa |
| Pruebas del Controller y con DAO falso (TC-01–TC-04, TC-08) | Pruebas del Router, resultados de reenvío y Controller caído (TC-05–TC-07, TC-09) | Evidencias, README y entrega |

**Reglas de colaboración:** una rama por estudiante (`feature/controller`, `feature/router`) y fusión en `main` tras revisión de la otra; commits individuales y descriptivos; ningún cambio a `shared/` o a `04` sin acuerdo de ambas y registro en `CHANGELOG-SPECS.md`. **Pruebas junto al código:** cada tarea de desarrollo incluye escribir las funciones de prueba de sus componentes, de modo que el bloque 5 se dedica a ejecutar, corregir y documentar.

## 3. Desglose del trabajo (WBS)

Minutos presupuestados por estudiante. Cada tarea se cierra solo con su entregable verificable. Los identificadores se mantienen desde versiones anteriores del plan para conservar la trazabilidad.

| ID | Responsable | Min | Ventana | Depende de | Entregable y criterio de terminado | Requisitos |
|---|---|---:|---|---|---|---|
| W-01 | A + B | — | Sesión 1 | — | Seis specs y prompts revisados; versión 1.0 confirmada por ambas; tag `spec-1.0` | NFR-08 |
| W-02A | A | 10 | 0–10 | W-01 | Entorno Python ≥ 3.11 con FastAPI, NetworkX, pytest; `shared/models.py` (`Route`), `AppError` y errores del Controller; `ControllerSettings` | NFR-05 |
| W-02B | B | 10 | 0–10 | W-01 | Entorno del Router; errores del Router en `shared/errors.py`, `shared/error_contract.py` y `shared/cost_format.py` (`is_canonical_cost`); `RouterSettings` | NFR-05 |
| W-03 | A | 23 | 10–33 | W-02A, W-02B | Modelos, `ports.TopologyDAO`, `JsonTopologyDAO` con validación de `01` §4 y lectura `Decimal`; `FakeTopologyDAO`; `RoutingService` con DI; prueba TC-08 escrita | FR-01, FR-02, FR-04, FR-06, NFR-01, NFR-02, NFR-07, NFR-09 |
| W-06 | B | 23 | 10–33 | W-02A, W-02B | Modelos, `ports.py`, `JsonlForwardingLogDAO`, fakes; `ForwardingService` con DI; prueba TC-09 escrita | FR-10, NFR-01, NFR-02, NFR-07, NFR-09, NFR-11 |
| W-04.1 | A | 14 | 33–47 | W-03 | Núcleo de relajación de `02` §6.2 con desempate y detección de ciclo negativo | FR-02, FR-03, NFR-03 |
| W-04.2 | A | 8 | 47–55 | W-04.1 | `LinkCostPolicy` exacta (tres métricas, `p=1` excluido), `CostPresenter` (`02` §6.3), cuya salida se comprueba con `is_canonical_cost` (entregada por B en G0) | FR-03, FR-04 |
| W-04A | A | 4 | 55–59 | W-04.2 | Comprobación rápida con E-01, E-19 y G1 de TC-11; pruebas TC-01 y TC-02 escritas | FR-03 |
| W-05 | A | 9 | 59–68 | W-04A | `ControllerHTTP`, View y `http_errors.py`: cinco endpoints conformes a `04` §3; pruebas TC-03 y TC-04 escritas | FR-01, FR-05, FR-06, FR-09, NFR-01, NFR-04, NFR-06 |
| W-07.1 | B | 14 | 33–47 | W-06 | `HttpRouteClient` con validación de `04` §4.3, errores 502/503/504 y `transport` inyectable | FR-07, FR-09, NFR-06 |
| W-07.2 | B | 13 | 47–60 | W-07.1 | `ForwardingService.forward` completo: traza, registro de éxito y fallo, `LogPersistenceError`; pruebas TC-05 y TC-06 escritas | FR-07, FR-08, FR-10, NFR-03 |
| W-08 | B | 8 | 60–68 | W-07.2 | `PacketHTTP`, View y `http_errors.py`: dos endpoints conformes a `04` §4; prueba TC-07 escrita | FR-08, FR-09, NFR-01, NFR-04, NFR-06 |
| W-11A | A | 15 | 68–83 | W-05, W-08 | Controller como proceso; fallo/restauración por HTTP con versión 1 → 2 → 3; arranque con puertos y topología no predeterminados (TC-14); capturas para `demo-evidence/` | FR-05, FR-06, NFR-05 |
| W-11B | B | 15 | 68–83 | W-05, W-08 | Router como proceso; reenvío por HTTP real; casos 404/503/504 observados; URL del Controller y bitácora configuradas (TC-14); capturas para `demo-evidence/` | FR-07, NFR-05 |
| W-09 | A | 10 | 83–93 | W-11A, W-11B | TC-01–TC-04, TC-08 y TC-12 ejecutadas y corregidas; resultados en `test-results.txt` | FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, NFR-09 |
| W-RA | A | 10 | 93–103 | W-09 | Reserva de contingencia; si sobra: parte AST de TC-13, TC-15 (NFR-10) y complementarias del Controller | NFR-10 |
| W-10 | B | 7 | 83–90 | W-11A, W-11B | TC-05–TC-07, TC-09 y TC-31 ejecutadas y corregidas | FR-07, FR-08, FR-09, FR-10, NFR-09 |
| W-13 | B (revisa A) | 3 | 90–93 | W-10 | `prompts-session2.md` con los prompts reales de la sesión | — |
| W-RB | B | 10 | 93–103 | W-13 | Reserva de contingencia; si sobra: TC-16 (NFR-11), TC-32, TC-33 y complementarias del Router | NFR-11 |
| W-12A | A | 5 | 103–108 | W-RA, W-13 | README (comandos y estado de requisitos), `test-results.txt` y revisión manual de código de TC-13 (`06` §6); borrador entregado a B en el minuto 105 | NFR-01, NFR-03, NFR-08 |
| W-12B | B | 5 | 103–108 | W-RA, W-RB | `demo-evidence/` y ZIP; empaqueta en el minuto 105 el borrador de W-12A (sincronización parcial que el grafo no modela) | — |

**Dependencias:** el grafo de tareas es acíclico (comprobado por la verificación automática; ver `VALIDACION.md`). Los dos carriles se sincronizan en G0 (cada una necesita la parte de `shared/` que escribe la otra: W-03 y W-06 dependen de W-02A y W-02B), en la integración (W-11A/W-11B) y en el cierre; entre esos puntos cada estudiante trabaja contra los fakes y el contrato `04`, sin bloquear a la otra.

## 4. Cronograma de la Sesión 2 y ruta crítica

| Bloque oficial (PDF p. 4) | Min | Carril A — Controller | Carril B — Router | Punto de control al cierre del bloque |
|---|---:|---|---|---|
| 1. Revisar specs y preparar entorno | 10 | W-02A | W-02B | G0 (min 10): `shared/` completo (A + B), importable en ambos entornos; configuración leída |
| 2. Modelos y patrones | 23 | W-03 | W-06 | G1 (min 33): fakes instanciables; TC-08 y TC-09 escritas |
| 3. Desarrollar ambas aplicaciones | 35 | W-04.1 (14) → W-04.2 (8) → W-04A (4) → W-05 (9) | W-07.1 (14) → W-07.2 (13) → W-08 (8) | G2 (min 47): motor devuelve E-01; cliente valida un `Route` falso · G3 (min 55): tres métricas y presentador · G4 (min 68): cinco endpoints del Controller y dos del Router |
| 4. Integrar | 15 | W-11A | W-11B | G5 (min 83): paquete reenviado por HTTP real; fallo y restauración observados |
| 5. Probar y verificar | 20 | W-09 (10) → W-RA (10) | W-10 (7) → W-13 (3) → W-RB (10) | G6 (min 93): ≥ 8 PASS reales, incluidas TC-08 y TC-09, o incumplimiento registrado |
| 6. Entregar | 5 | W-12A | W-12B | G7 (min 108): repositorio, evidencias y ZIP |

**Ruta crítica (CPM sobre presupuestos):** carril A = 10 + 23 + 14 + 8 + 4 + 9 + 15 + 10 + 10 + 5 = **108 min**; carril B = 10 + 23 + 14 + 13 + 8 + 15 + 7 + 3 + 10 + 5 = **108 min**. Las tareas productivas de cada carril forman una cadena crítica de 98 min; las reservas W-RA y W-RB (10 min cada una) son la **holgura explícita** del plan y absorben retrasos de cualquier tarea anterior sin mover la entrega. Sin ensayo cronometrado, la factibilidad sigue siendo un **riesgo abierto** (R-01, R-06), no un hecho verificado.

**Si una puerta falla:** se registra el bloqueo con la hora real, se consume la reserva, se aplica la línea de corte de §1 si procede e, informado el docente, se documenta lo pendiente. No se elimina ningún requisito ni se marca como cumplido lo que no se demostró.

## 5. Riesgos y contingencias

| Riesgo | Prob. | Impacto | Responsable | Señal temprana | Mitigación (sin eliminar obligaciones) |
|---|---|---|---|---|---|
| R-01 El motor exacto (W-04.1 + W-04.2 + W-04A, 26 min) se retrasa | Alta | Alto | A | G2 sin E-01 al minuto 47 | Pseudocódigo y fixtures ya especificados; priorizar ruta correcta antes que presentación (línea de corte de §1); B continúa con fakes; reserva W-RA |
| R-02 Respuestas HTTP difieren del contrato | Media | Alto | A + B | 502 en la primera integración | Esquemas copiados de `04`; `is_canonical_cost` compartida; revisión cruzada de DTO |
| R-03 `shared/` no disponible o con dependencias de framework | Media | Medio | A + B | `ModuleNotFoundError` al arrancar por separado | Instalar `shared/` en ambos entornos en W-02; regla AST de `02` §8 |
| R-04 Desempate o ciclo negativo mal implementados | Media | Alto | A | Falla E-19 o G1 de TC-11 | Núcleo único para producción y prueba; fixtures con resultado exacto |
| R-05 La bitácora falla, pierde o mezcla resultados | Media | Medio | B | TC-09, TC-16 o TC-33 fallan | `lock` en el DAO; DAO falso que lanza `OSError`; nunca responder 200 sin registro |
| R-06 Las pruebas y evidencias exceden el bloque 5 | Alta | Alto | A + B | Menos de 8 PASS al minuto 93 | Pruebas escritas durante el desarrollo; reservas W-RA/W-RB; ejecutar primero TC-08 y TC-09; declarar pendientes |

## 6. Matriz de trazabilidad requisito → decisión → componente → método → API → secuencia → tarea → prueba

| Requisito | DEC | Componentes | Métodos | Endpoint | Secuencia | Tareas | Pruebas |
|---|---|---|---|---|---|---|---|
| FR-01 | DEC-01, DEC-09 | `JsonTopologyDAO`, `ControllerHTTP` | `get_topology`, `read_topology` | `GET /topology` | S1 | W-03, W-05, W-09 | TC-01, TC-10 |
| FR-02 | DEC-01 | `Topology`, `BellmanFordEngine` | `find_path` | `GET /route` | S1 | W-03, W-04.1 | TC-25, TC-28, TC-29, TC-30 |
| FR-03 | DEC-07, DEC-08, DEC-09 | `BellmanFordEngine`, `RouteLabel` | `find_path`, `run_bellman_ford_on_weighted_graph` | `GET /route` (TC-11: núcleo y subcaso API) | S1 | W-04.1, W-04.2, W-04A | TC-01, TC-11, TC-19, TC-20, TC-21, TC-22, TC-23, TC-26, TC-27, TC-37 |
| FR-04 | DEC-02, DEC-09 | `LinkCostPolicy`, `CostPresenter` | `weight`, `format_cost` | `GET /route` | S1 | W-03, W-04.2 | TC-02, TC-10, TC-36, TC-37, TC-38, TC-39 |
| FR-05 | DEC-03, DEC-08 | `ControllerHTTP`, `RouteResponseSchema` | `get_route`, `compute_route` | `GET /route` | S1 | W-05, W-11A | TC-01, TC-12, TC-28 |
| FR-06 | DEC-01, DEC-04 | `RoutingService`, `TopologyDAO` | `set_link_status` | `POST /links/fail`, `POST /links/restore` | S2 | W-03, W-05, W-11A | TC-03, TC-04, TC-17, TC-18 |
| FR-07 | DEC-05, DEC-06 | `HttpRouteClient`, `ForwardingService` | `fetch_route` | `GET /route` (desde el Router) | S1, S2, S3 | W-07.1, W-07.2, W-11B | TC-05, TC-32, TC-34 |
| FR-08 | DEC-06 | `ForwardingService`, `PacketHTTP` | `forward`, `post_packet` | `POST /packets` | S1, S2 | W-07.2, W-08 | TC-06, TC-31 |
| FR-09 | DEC-03, DEC-06 | `AppError`, `http_errors`, `HttpRouteClient` | `install_error_handlers`, `fetch_route` | Todos | S2, S3 | W-05, W-07.1, W-08 | TC-07, TC-12, TC-31, TC-32 |
| FR-10 | DEC-05 | `ForwardingLogDAO`, `JsonlForwardingLogDAO` | `save` | `POST /packets` | S1, S2, S3 | W-06, W-07.2 | TC-06, TC-09, TC-16, TC-33 |
| NFR-01 | DEC-05 | `ControllerHTTP`, `PacketHTTP`, View, Model | — | Ambas API | S1, S2, S3 | W-03, W-05, W-06, W-08 | TC-13 |
| NFR-02 | DEC-05 | `TopologyDAO`, `ForwardingLogDAO` | `get_topology`, `save` | — | S1, S2, S3 | W-03, W-06 | TC-08, TC-09, TC-13 |
| NFR-03 | DEC-06 | `BellmanFordEngine`, `ForwardingService` | `find_path`, `forward` | — | S1 | W-04.1, W-07.2 | TC-13 |
| NFR-04 | DEC-03 | View, `http_errors` | `install_error_handlers` | Todos | S1, S2, S3 | W-05, W-08 | TC-12, TC-31 |
| NFR-05 | — | `ControllerSettings`, `RouterSettings` | `create_controller_app`, `create_router_app` | — | — | W-02A, W-02B | TC-14 |
| NFR-06 | DEC-03, DEC-06 | `AppError`, `HttpRouteClient`, `ForwardingService` | `fetch_route`, `forward` | Errores 4xx/5xx | S3 | W-05, W-07.1, W-08 | TC-07, TC-12, TC-31, TC-32, TC-33 |
| NFR-07 | DEC-05 | Servicios e interfaces | Constructores con DI | — | — | W-03, W-06 | TC-08, TC-09 |
| NFR-08 | — | Esta matriz, `tests/` | — | — | — | W-01, W-12A | TC-13 y auditoría documental |
| NFR-09 | DEC-05 | Interfaces DAO y fakes | — | — | — | W-03, W-06, W-09, W-10 | TC-08, TC-09 |
| NFR-10 | DEC-09 | `ControllerHTTP`, `RoutingService` | `get_route` | `GET /route` | S1 | W-RA | TC-15 |
| NFR-11 | DEC-05 | `JsonlForwardingLogDAO` | `save` | `POST /packets` | S1, S3 | W-06, W-RB | TC-16, TC-33 |

| Decisión | Tareas | Pruebas que la verifican |
|---|---|---|
| DEC-01 Formato y orientación | W-03, W-04.1 | TC-10, TC-25, TC-30 |
| DEC-02 `p = 1` inutilizable | W-03, W-04.2 | TC-36 |
| DEC-03 Códigos HTTP | W-05, W-07.1, W-08 | TC-12, TC-31, TC-32 |
| DEC-04 Idempotencia | W-03, W-05 | TC-18 |
| DEC-05 DAO por aplicación | W-03, W-06 | TC-08, TC-09, TC-13 |
| DEC-06 Sin caché ni cálculo en el Router | W-07.1, W-07.2 | TC-05, TC-07 |
| DEC-07 Ciclos negativos | W-04.1 | TC-11 |
| DEC-08 Desempate | W-04.1, W-04A | TC-19–TC-23, TC-26 |
| DEC-09 Aritmética exacta y presentación | W-03, W-04.2 | TC-27, TC-37, TC-38, TC-39 |

## 7. Definición de terminado (por tarea y por requisito)

| Criterio | Evidencia |
|---|---|
| El componente existe con la firma de `02` §5 y respeta las reglas de importación de `02` §8 | Revisión de código + TC-13 |
| Sus funciones de prueba se escribieron en la misma tarea | Archivo `tests/test_tcXX_*.py` en el commit de la tarea |
| Las pruebas asociadas en §6 se ejecutaron y su resultado real quedó en `test-results.txt` | Salida de pytest |
| Entradas, salidas y errores coinciden con `04` | TC-12, TC-31 |
| Se integró con el otro proceso por HTTP real | Registro en `demo-evidence/` |
| La otra estudiante revisó el código | Nota en `test-results.txt` |
| Se demostró en vivo (defensa) | Evaluación del docente |

## 8. Control de cambios, Git y entrega

1. **Congelamiento:** se sigue el procedimiento único de `REVIEW-AND-BASELINE.md` §3 (reconfirmación de ambas, regeneración de `SHA256SUMS`, `git add -A`, commit y tag `spec-1.0`). Se anota el SHA que devuelva Git; nunca se inventa.
2. **Cambios posteriores (PDF p. 4):** todo cambio de diseño se registra en `CHANGELOG-SPECS.md` con motivo, artefactos afectados y aprobación de ambas antes de modificar código.
3. **Sesión 2:** commits individuales en las ramas de §2; `prompts-session2.md` antes de W-12; pruebas, evidencias y limitaciones documentadas sin maquillar.
4. **Defensa:** demostración en vivo (paquete, fallo y restauración, caída del Controller, TC-08/TC-09) y explicación de ambos procesos por cada estudiante.
