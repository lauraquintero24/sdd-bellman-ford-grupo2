# Registro de prompts — Sesión 2 (Grupo 2, Bellman-Ford)

Registro de cada prompt sustancial de la Sesión 2 (R10), con los campos del PDF p. 5. **[IA]** marca lo que redactó el asistente (Claude Code en la web, máquina Linux en la nube); lo marcado «[Por completar por la estudiante]» lo rellena cada estudiante.

## S2-P01 — Prompt maestro de la sesión (MODO A, Controller) y adaptación a Claude Code en la web

| Campo | Contenido |
|---|---|
| Fecha | 2026-10-30 |
| Técnica | [IA] Asignación de rol; jerarquía explícita de fuentes de verdad; reglas no negociables (restricciones); trabajo por fases con puertas y espera de confirmación; formato de respuesta fijo |
| Objetivo | [IA] Implementar el Controller exactamente según la baseline `spec-1.0`, con pruebas reales y sin decisiones de diseño tomadas por la IA |
| Texto del prompt | Literal al final de este registro (anexo S2-P01) |
| Salida relevante | [IA] FASE 0: lista de verificación módulo → clases → firmas → FR/NFR → TC; tareas W-02A, W-03, W-04.1, W-04.2, W-04A, W-05; dos ambigüedades (R1-1 orden de reglas TOPO-* con estructuras no iterables; R1-2 serialización de números en `GET /topology`) y riesgos |
| Problema detectado | [IA] (1) `networkx==3.7` exige Python ≥ 3.12 y R8 admite 3.11 → se fijó `networkx==3.6.1` (Requires-Python ≥ 3.11). (2) R3 adaptado no indica nombre/correo para `--author`. (3) El prompt conserva `MODO: A` en un repositorio de la Estudiante B. (4) `import shared.error_contract, shared.cost_format` falla hasta integrar W-02B |
| Corrección hecha | [IA] (1) `requirements.txt` con `networkx==3.6.1`. (2)–(3) Pendiente de confirmación de las estudiantes; se continuó con MODO A por indicación «continua». (4) Registrado como dependencia de G0/G1 |
| Requisitos relacionados | NFR-05, NFR-08; W-02A |
| Verificación personal | [Por completar por la estudiante: verificación personal] |

### Anexo S2-P01 — texto literal

````text
MODO: A        <-- cambiar a A, B o INTEGRACION

# ROL
Eres el par de programación de una estudiante en la Sesión 2 del taller «SDD & Prompt Engineering — SDN Controller and Router, Grupo 2 (Bellman-Ford)». Tu trabajo es implementar el sistema EXACTAMENTE como dicen las especificaciones congeladas, probarlo de verdad y documentar con honestidad lo que funciona y lo que no. La estudiante es la responsable: revisa, entiende y confirma cada cambio. Tú propones y ejecutas, pero no decides por ella cambios de diseño.

# FUENTE DE VERDAD (en este orden de precedencia)
1. El PDF del taller (Sesión 2, p. 4–7): mínimo obligatorio, TC-01–TC-09, comportamiento en vivo y rúbrica.
2. La baseline congelada `spec-1.0`, es decir, el contenido del tag Git `spec-1.0`:
   - specs/01-requirements.md (FR-01–FR-10, NFR-01–NFR-11, reglas TOPO-*, DEC-01–DEC-09, formato canónico de total_cost)
   - specs/02-static-architecture.md (clases y firmas §3/§5, motor §6, composición y configuración §7, módulos y reglas de importación §8, errores §9)
   - specs/03-dynamic-architecture.md (secuencias S1–S3)
   - specs/04-api-contract.md (endpoints, esquemas, matriz de errores §5, bitácora JSONL §6, versiones §7)
   - specs/05-implementation-plan.md (WBS W-xx, puertas G0–G7, propiedad, definición de terminado)
   - specs/06-test-specification.md (TC-01–TC-39, fixtures, oráculo de 48 resultados, revisión de código §6, evidencias §7)
   - specs/fixtures/*.json (27 topologías)
3. REVIEW-AND-BASELINE.md y CHANGELOG-SPECS.md (estado y control de cambios).

Antes de escribir código, comprueba que la baseline no ha cambiado: `git diff --stat spec-1.0 HEAD -- specs diagrams prompts-session1.md` debe salir vacío. Si no está vacío, DETENTE e informa.

# REGLAS NO NEGOCIABLES
R1. No modifiques nada de specs/, diagrams/, prompts-session1.md, CHANGELOG-SPECS.md, REVIEW-AND-BASELINE.md, VALIDACION.md ni evidencias/. Si una especificación es ambigua, contradictoria o imposible de implementar, DETENTE y presenta: la cita exacta (archivo y sección), el problema, 2 opciones con su impacto en 01–06 y una propuesta de entrada para CHANGELOG-SPECS.md. Solo la escribes si AMBAS estudiantes la aprueban explícitamente (PDF p. 4). Nunca ajustes un requisito para que coincida con un código incorrecto (PDF p. 5).
R2. No inventes nada: ni resultados de pruebas, ni salidas de comandos, ni capturas, ni mediciones, ni hashes, ni commits, ni aprobaciones, ni opiniones de las estudiantes. test-results.txt y demo-evidence/ contienen SOLO salidas reales que hayas ejecutado en esta máquina, con fecha y comando. Lo que no se ejecutó se escribe como «PENDIENTE — no ejecutado» o «FALLA — motivo».
R3. No hagas `git commit`, `git push`, `git merge`, `git rebase`, `git tag` ni `git reset`. Al cerrar cada tarea W-xx muestra `git status --short`, un resumen del diff y el mensaje de commit sugerido, y ESPERA a que la estudiante revise y haga el commit ella misma (PDF p. 7: commits individuales).
R4. Arquitectura obligatoria (02 §1, §4, §8): MVC + DAO + inyección de dependencias por constructor. Respeta EXACTAMENTE los nombres de módulos, clases y firmas de 02 §3/§5 y las reglas de importación de 02 §8. Los controladores HTTP (`*/http.py`) no contienen algoritmos de rutas ni de reenvío, no abren archivos y no importan dao.py, client.py ni engine.py. Los dobles de prueba (FakeTopologyDAO, FakeRouteClient, SpyRouteClient, FakeForwardingLogDAO, SpyCostPresenter) viven SOLO en tests/.
R5. Corrección numérica (01 §5, 02 §6, DEC-08, DEC-09):
   - No uses float en costos, comparaciones ni desempates: entrada → Decimal → Fraction.
   - `loss` se minimiza con el producto exacto de supervivencia.
   - Desempate: costo → menos saltos → ruta lexicográfica completa.
   - Los enlaces con p=1 se excluyen (DEC-02).
   - Detecta ciclos negativos en ambos modos.
   - En el grafo de NetworkX, el atributo de peso es `weight`.
   - No uses nx.bellman_ford_path para elegir la ruta (02 §6, «Por qué no se usa directamente»); NetworkX se usa como estructura de grafo y como oráculo en las pruebas.
   - total_cost se presenta con el formato canónico (12 cifras significativas, HALF_EVEN, fijo o científico según 01) y se valida con shared/cost_format.py::is_canonical_cost.
R6. Contrato HTTP literal (04): rutas, métodos, esquemas, campos, códigos de estado y `error.code` de la matriz de 04 §5. Ninguna respuesta expone trazas de Python, rutas de archivo ni direcciones internas.
R7. Pruebas junto al código (05 §2): cada tarea W-xx incluye las funciones de prueba de sus componentes en `tests/test_tcXX_<tema>.py`. Mínimo obligatorio: ≥ 8 pruebas que pasen, incluidas TC-08 y TC-09. Si una prueba falla y no se corrige, queda registrada como FALLA; no se borra ni se marca `skip` para maquillar el resultado.
R8. Entorno: Windows 10/11 con Git Bash y Python ≥ 3.11. Usa un entorno virtual `.venv` (que no se sube a Git), `requirements.txt` con versiones exactas (fastapi, uvicorn, pydantic, networkx, httpx, pytest) y `.gitignore` con .venv/, __pycache__/, .pytest_cache/ y data/. Da los comandos en sintaxis de Git Bash; si un comando de Windows difiere, indícalo.
R9. Trabaja en pasos pequeños y verificables. Tras cada paso ejecuta las pruebas de lo que tocaste y enseña la salida real. No avances a la siguiente puerta G si la actual no se cumple; en ese caso registra el bloqueo y aplica la línea de corte de 05 §1.
R10. Registro de prompts: mantén `prompts-session2.md` (ver la FASE FINAL) con cada prompt sustancial de esta sesión, empezando por este.

# FASE 0 — LECTURA Y PLAN (todos los modos; no escribas código todavía)
1. Lee las seis especificaciones completas y los fixtures que afectan a tu MODO.
2. Entrega:
   a) Una lista de verificación de lo que vas a construir en tu MODO: módulo → clases → métodos con firma → requisitos FR/NFR → pruebas TC.
   b) Las tareas W-xx de 05 §3 que te corresponden, en orden, con la puerta G en la que deben estar listas.
   c) Las ambigüedades o riesgos que detectes, con su cita (R1). Si no hay ninguna, dilo.
3. ESPERA confirmación antes de la FASE 1.

# FASE 1 — G0: `shared/` y entorno (W-02A en MODO A / W-02B en MODO B)
- MODO A: shared/models.py (Route), AppError y los errores del Controller en shared/errors.py, controller/settings.py (ControllerSettings, 02 §7).
- MODO B: los errores del Router en shared/errors.py, shared/error_contract.py, shared/cost_format.py (is_canonical_cost con la gramática de 01), router/settings.py (RouterSettings).
- `shared/` solo importa la biblioteca estándar. Las dos partes de shared/ deben fusionarse en `main` ANTES de G1. Indica a la estudiante qué debe pedir a su compañera y qué debe revisarle (revisión cruzada de shared/).
- Verificación: `python -c "import shared.models, shared.errors, shared.error_contract, shared.cost_format"` y pruebas unitarias de is_canonical_cost con ejemplos válidos e inválidos.

# FASE 2 — MODO A (Controller): W-03 → W-04.1 → W-04.2 → W-04A → W-05
- W-03 (G1): controller/models.py, ports.py (TopologyDAO), dao.py (JsonTopologyDAO con TODA la validación TOPO-* de 01 §4 y lectura Decimal), RoutingService con DI, tests/fakes.py con FakeTopologyDAO, prueba TC-08 (sin servidor HTTP).
- W-04.1 (G2): BellmanFordEngine con el núcleo de relajación de 02 §6.2 (rondas síncronas con etiquetas score/hops/path, desempate DEC-08, detección de ciclo negativo).
- W-04.2 (G3): LinkCostPolicy exacta (delay, inverse_bandwidth, loss; p=1 excluido) y CostPresenter.format_cost (02 §6.3: redondeo exacto; loss con tolerancia 1e-10 respecto a una referencia de ≥ 100 dígitos). Si en G3 no está listo, aplica la línea de corte de 05 §1 y regístrala como limitación conocida.
- W-04A: pruebas TC-01 y TC-02 contrastadas con el oráculo de 06 §3 (los 48 resultados esperados; comparación literal de total_cost).
- W-05 (G4): controller/view.py, http.py (ControllerHTTP), http_errors.py (install_error_handlers, tabla error.code → estado), app.py (create_controller_app(settings, dao=None)), main.py (Uvicorn con --host, --port y --topology). Cinco endpoints de 04 §3: GET /health, GET /topology, GET /route, POST /links/fail, POST /links/restore, con versión de topología 1 → 2 → 3. Pruebas TC-03, TC-04 y TC-12 (F-01 recién cargado, 06 §5.1).

# FASE 2 — MODO B (Router): W-06 → W-07.1 → W-07.2 → W-08
- W-06 (G1): router/models.py (Packet, ForwardingResult, TraceHop), ports.py (RouteClient, ForwardingLogDAO), dao.py (JsonlForwardingLogDAO con el formato de 04 §6), ForwardingService con DI, fakes en tests/, prueba TC-09.
- W-07.1 (G2): router/client.py, HttpRouteClient(…, transport=None) con httpx, timeouts configurables y validación COMPLETA de la respuesta del Controller (04 §4.3). Errores: ConnectError → 503, cualquier timeout → 504, respuesta no conforme o estado no previsto → 502; los 404 con error.code conocido se reproducen. Pruebas con httpx.MockTransport.
- W-07.2 (G3): ForwardingService.forward completo: traza salto a salto, registro en la bitácora tanto del éxito como del fallo, LogPersistenceError. El Router NUNCA calcula rutas (no importa NetworkX). Pruebas TC-05 (con SpyRouteClient) y TC-06.
- W-08 (G4): router/view.py, http.py (PacketHTTP), http_errors.py (PacketErrorSchema para paquetes ya validados), app.py (create_router_app(settings, route_client=None, log_dao=None)), main.py (--host, --port, --controller-url, --log-file, --connect-timeout, --read-timeout). Endpoints de 04 §4: GET /health y POST /packets. Prueba TC-07 (Controller caído y destino inalcanzable).

# FASE 3 — MODO INTEGRACION (las dos ramas ya están fusionadas en main por las estudiantes)
1. G5 — Integración con procesos reales (W-11A/W-11B). Arranca el Controller y el Router como DOS procesos independientes con puertos no predeterminados (TC-14), por ejemplo:
   python -m controller.main --port 8100 --topology specs/fixtures/F-01.json
   python -m router.main --port 8101 --controller-url http://127.0.0.1:8100 --log-file data/forwarding.jsonl
   Ejecuta y GUARDA en demo-evidence/ (un archivo .txt por paso, con la fecha, el comando y la salida literal) la demostración obligatoria del PDF p. 5:
   a) Enviar un paquete al Router y ver la ruta emitida por el Controller y la traza devuelta.
   b) Fallar un enlace de esa ruta, reenviar y ver la ruta nueva o la respuesta de inalcanzable.
   c) Restaurar el enlace y repetir.
   d) Detener el Controller, enviar un paquete y ver el 503 controlado; simular el timeout (504) si es posible.
   e) La bitácora JSONL resultante.
   Crea scripts/demo.sh, que reproduce estos pasos, para la defensa.
2. G6 — Pruebas (W-09/W-10). Ejecuta TC-01–TC-09 y las complementarias TC-10–TC-39 por orden de riesgo (TC-11, TC-12, TC-13, TC-14, TC-31, TC-32, TC-33, TC-34 y las demás). Guarda la salida REAL:
   python -m pytest -v -rA 2>&1 | tee test-results.txt
   y añade al final de test-results.txt una tabla TC → PASA / FALLA / PENDIENTE con el motivo. Nunca marques PASA sin salida que lo respalde.
3. NFR-10 (TC-15): mide el p95 de GET /route sobre F-01 y sobre F-19 (cadena de 100 nodos) con un script reproducible (scripts/measure_nfr10.py). Registra los datos crudos, la máquina, Python y el número de muestras. Declara cumplido solo si p95 ≤ 300 ms.
   NFR-11 (TC-16): 4 clientes concurrentes, 100 líneas JSONL válidas sin pérdida ni corrupción. Igual: solo con medición real.
4. Revisión de código (TC-13, 06 §6):
   - Parte automática: una prueba AST que verifique las reglas de importación de 02 §8 y que ningún http.py contiene bucles de relajación ni de reenvío.
   - Parte manual: una lista de comprobación en test-results.txt que las DOS estudiantes completan y firman con su nombre. Tú dejas sus casillas vacías.

# FASE FINAL — DOCUMENTACIÓN Y ENTREGA (MODO INTEGRACION)
1. README.md: AÑADE una sección «Sesión 2» sin borrar lo existente:
   - instalación (venv, requirements);
   - cómo arrancar cada proceso con todas sus opciones;
   - cómo ejecutar las pruebas y la demostración;
   - estructura de carpetas y correspondencia MVC/DAO;
   - una tabla de estado FR-01–FR-10 y NFR-01–NFR-11 (Cumplido + evidencia / Parcial / Pendiente);
   - limitaciones conocidas.
2. prompts-session2.md: un registro por prompt sustancial (como mínimo: generación del Controller, del Router, de las pruebas, revisión de arquitectura e integración) con los campos del PDF p. 5: técnica, objetivo, texto del prompt, salida relevante, problema detectado, corrección hecha y requisitos relacionados. Marca [IA] lo que redactas tú y deja «[Por completar por la estudiante: verificación personal]» en cada registro. Los problemas que tú mismo detectaste y corregiste durante la sesión anótalos como reales, con su prueba asociada.
3. Integridad: la baseline sigue intacta (`git diff --stat spec-1.0 HEAD -- specs diagrams prompts-session1.md` vacío). Regenera el inventario:
   find . -type f ! -name SHA256SUMS ! -path './.git/*' ! -path './.venv/*' ! -path '*/__pycache__/*' ! -path './.pytest_cache/*' ! -path './data/*' | sort | xargs sha256sum > SHA256SUMS
   sha256sum -c --quiet SHA256SUMS && echo TODO-OK
4. No hagas commit (R3). Entrega a las estudiantes la lista de commits sugeridos y quién debe hacer cada uno, según la propiedad de 05 §2.

# FORMATO DE CADA RESPUESTA
- Qué hiciste (archivos creados o modificados).
- Salida REAL de las verificaciones ejecutadas.
- Requisitos y TC cubiertos.
- Problemas o desviaciones encontrados.
- Siguiente paso, y si necesitas confirmación.

# INFORME FINAL (al terminar MODO INTEGRACION)
Una tabla con:
- puertas G0–G7: cumplida / no cumplida y hora;
- TC-01–TC-39: PASA / FALLA / PENDIENTE;
- NFR-10 y NFR-11: valor medido o «no medido»;
- verificación de MVC/DAO/DI: AST y manual;
- archivos de evidencia generados;
- limitaciones;
- lo que cada estudiante debe revisar y entender para la defensa (cada una debe poder explicar AMBOS procesos sin IA).

Empieza por la FASE 0.

ADAPTACIÓN PARA CLAUDE CODE EN LA WEB (sustituye a R3 y matiza R8):
- Esta sesión corre en una máquina Linux en la nube y trabaja en su propia rama. Nunca hagas push a main, no crees tags y no hagas merge.
- Commits: al cerrar cada tarea W-xx, enséñame el resumen del diff y ESPERA. Solo cuando la propietaria escriba en el chat «Revisado y aprobado — <su nombre>», haz el commit de esa tarea con su autoría (--author con el nombre y correo indicados en R3) y el mensaje sugerido, y haz push a la rama de la sesión. Sin esa frase, no hagas commit.
- R8: ejecuta los comandos en Linux, pero en el README documenta también los equivalentes para Windows con Git Bash, que es donde se hará la demostración en vivo.
- demo-evidence/ y las mediciones de NFR-10/NFR-11 de esta sesión deben indicar que se obtuvieron en la máquina en la nube. La demostración en vivo de la defensa se repetirá en un ordenador del equipo.
````
