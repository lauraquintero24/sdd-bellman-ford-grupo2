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
| Corrección hecha | [IA] (1) `requirements.txt` con `networkx==3.6.1`. (2) Resuelto en S2-P03: la propietaria indicó el autor y el correo. (3) Se continuó con MODO A por indicación «continua»; después se cambió a MODO COMPLETO (S2-P04). (4) Resuelto al integrar W-02B en la misma rama (S2-P04) |
| Requisitos relacionados | NFR-05, NFR-08; W-02A |
| Verificación personal | Comprobé que la baseline no cambió: en Windows `sha256sum -c SHA256SUMS` dio TODO-OK y en GitHub `specs/` y `diagrams/` siguen con el commit «Congelar especificaciones spec-1.0» (tag `spec-1.0`, 20c2289). |

## S2-P02 — «continua»: generación del Controller (W-03 → W-05, W-RA)

| Campo | Contenido |
|---|---|
| Fecha | 2026-10-30 |
| Técnica | [IA] Continuación del prompt S2-P01 (mismas reglas R1–R10); tareas pequeñas y verificables con cierre por tarea; pruebas junto al código; oráculo independiente (NetworkX y referencia decimal de 120 cifras) |
| Objetivo | [IA] Implementar el Controller completo (DAO con reglas TOPO-*, motor Bellman-Ford exacto, presentador de costos, API de 04 §3) y su parte de TC-13 y TC-15 |
| Texto del prompt | «continua» (repetido al cierre de cada tarea W-xx) |
| Salida relevante | [IA] `controller/` completo; 48/48 filas del oráculo de 06 §3 por servicio y por HTTP; TC-08 aprobado con E/S bloqueada; NFR-10 medido (p95 F-01 2.414 ms, F-19 41.970 ms, máquina en la nube) |
| Problema detectado | [IA] (1) La primera versión de `test_tc08_routing_service_fake_dao.py` contenía una fixture de relleno sin uso. (2) TC-08, TC-01 (API) y TC-02 (API) se escribieron antes de que existieran el motor, el presentador y `controller/app.py`, y fallaron con `ModuleNotFoundError` hasta W-04.2 y W-05. (3) Una expectativa de `test_decimal_text_format` era incorrecta: esperaba `"1.23456789012e+11"` para `123456789012`, cuando 04 §3.2 manda notación fija para exponente 11. (4) La cadena «Comando» del informe de NFR-10 perdía las comillas del argumento `--machine` y no era reproducible |
| Corrección hecha | [IA] (1) Fixture eliminada. (2) Fallos registrados como tales en cada cierre; desaparecieron al implementar los módulos, sin desactivar pruebas. (3) Se corrigió la prueba, no el código, y se añadió el caso frontera `1e12` → `"1e+12"` (`tests/test_tc12_controller_api_contract.py`). (4) `shlex.join` en `scripts/measure_nfr10.py` y nueva medición; la primera medición se descartó |
| Requisitos relacionados | FR-01–FR-06, FR-09, NFR-01–NFR-07, NFR-09, NFR-10; TC-01–TC-04, TC-08, TC-10–TC-12, TC-15, TC-17–TC-30, TC-36–TC-39 |
| Verificación personal | Ejecuté en Windows 11 la suite completa (`553 passed`), que incluye TC-08 (`RoutingService` con DAO falso, sin HTTP) y TC-19–TC-23 (desempate DEC-08 de `_better()` en `controller/engine.py`). |

## S2-P03 — Aprobación y commits del carril A

| Campo | Contenido |
|---|---|
| Fecha | 2026-10-30 |
| Técnica | [Equipo] Instrucción operativa explícita con autoría y formato de salida verificable |
| Objetivo | [IA] Registrar con autoría individual el trabajo del Controller (commits individuales, PDF p. 7) |
| Texto del prompt | «Revisado y aprobado — Mariana Arturo Pabón / Haz ahora los commits de W-02A, W-03, W-04.1, W-04.2, W-04A, W-05 y la parte Controller de W-RA, uno por tarea, con --author="Mariana Arturo Pabón <marianaarturo@unicauca.edu.co>", y haz push a la rama claude/lucid-tesla-5aa8as. Al terminar, muéstrame `git log --oneline --format="%h %an — %s"` y confirma que el push se completó.» Después: «Reintenta el push: git push -u origin claude/lucid-tesla-5aa8as. Si funciona, muéstrame la salida y confirma que la rama existe en GitHub.» |
| Salida relevante | [IA] Siete commits (`3f2fc50` … `527d0d4`) con autora Mariana; rama publicada (`git ls-remote` → `527d0d4…`) |
| Problema detectado | [IA] (1) El primer push devolvió HTTP 403: la integración de GitHub no tenía acceso al repositorio. (2) `tests/test_tc11_negative_cycle.py` pertenecía a dos tareas: W-04.1 y el subcaso API de W-05 |
| Corrección hecha | [IA] (1) Las estudiantes corrigieron el acceso y el push se repitió con éxito. (2) En el commit de W-04.1 se incluyó el archivo sin el subcaso API, que entró en el commit de W-05; cada commit deja el árbol coherente |
| Requisitos relacionados | PDF p. 7 (commits individuales); 05 §2 y §8 |
| Verificación personal | Comprobé con `git log` que los commits de W-02A a W-RA tienen mi autoría y revisé cada tarea antes de aprobarla en el chat. |

## S2-P04 — MODO COMPLETO: generación del Router (W-02B → W-08)

| Campo | Contenido |
|---|---|
| Fecha | 2026-10-30 |
| Técnica | [Equipo] Cambio de modo con restricciones (mismas reglas, propietaria del carril, commit y push por tarea, sin merge ni tags) |
| Objetivo | [IA] Implementar el Router y la parte B de `shared/` en la misma rama, con autoría de Laura |
| Texto del prompt | «Cambia a MODO COMPLETO: estamos usando un solo ordenador y una sola rama, así que continúa en claude/lucid-tesla-5aa8as con el resto del plan. 1. MODO B: W-02B, W-06, W-07.1, W-07.2 y W-08 con las mismas reglas (R1–R10 y la adaptación web). Propietaria: Laura Sofia Quintero Fernandez <laurasquintero@unicauca.edu.co>. 2. Después, FASE 3 y FASE FINAL. Como el Controller y el Router quedan en esta misma rama, la condición del MODO INTEGRACION («ambas partes en la misma rama») se cumple sin necesidad de merge. 3. Commits: al cerrar cada tarea, muestra el resumen y espera la frase «Revisado y aprobado — <nombre>» de la propietaria (Router → Laura; integración y documentación → repartidas según 05 §2). Tras cada commit, haz push inmediato a la rama para no perder trabajo. 4. No hagas push a main, ni merge, ni tags.» Después: «continua» al cierre de cada tarea |
| Salida relevante | [IA] `shared/error_contract.py`, `shared/cost_format.py`, `router/` completo; TC-09 aprobado con E/S bloqueada; G0 completa (la prueba de TC-39 con `is_canonical_cost`, que fallaba desde W-04.2, pasó) |
| Problema detectado | [IA] (1) En `tests/test_tc31_route_response_validation.py`, `kwargs.pop` modificaba el diccionario compartido de casos parametrizados. (2) Los imports de los dobles del Router quedaron a mitad de `tests/fakes.py`. (3) TC-06 (API) falló con `ModuleNotFoundError` hasta W-08. (4) El subcaso de TC-33 con permisos de archivo no puede ejecutarse como administrador |
| Corrección hecha | [IA] (1) Se sustituyó por `kwargs.get` sin mutación. (2) Imports movidos al principio del archivo. (3) Fallo registrado; pasó al crear `router/app.py`. (4) La prueba comprueba si los permisos aplican y, si no, se declara NO EJECUTADA (06 TC-33 lo prevé); registrado en `test-results.txt` y en el README |
| Requisitos relacionados | FR-07–FR-10, NFR-04–NFR-07, NFR-09, NFR-11; TC-05–TC-07, TC-09, TC-14, TC-16, TC-31–TC-33 |
| Verificación personal | Ejecuté en Windows 11 la suite completa (`553 passed`), incluidas TC-09 y TC-32, y comprobé en la demostración que el Router responde 503 con el Controller detenido y 504 con un Controller que no responde (`router/client.py`: `ConnectError` → 503, `TimeoutException` → 504, respuesta no conforme → 502). |

## S2-P05 — Revisión de arquitectura (parte automática de TC-13)

| Campo | Contenido |
|---|---|
| Fecha | 2026-10-30 |
| Técnica | [IA] Verificación automática por AST de reglas declarativas (tabla de importaciones prohibidas de 02 §8) + lista de revisión manual para las estudiantes |
| Objetivo | [IA] Demostrar que los handlers no contienen algoritmos, que el Router no calcula rutas y que la DI es verificable (NFR-01–NFR-03) |
| Texto del prompt | Parte de S2-P01 (FASE 3, punto 4: «una prueba AST que verifique las reglas de importación de 02 §8 y que ningún http.py contiene bucles de relajación ni de reenvío») |
| Salida relevante | [IA] `tests/test_tc13_architecture_ast.py`: 28 pruebas aprobadas sobre `controller/`, `router/` y `shared/`; lista manual de 06 §6 en `test-results.txt` sin marcar |
| Problema detectado | [IA] `controller/http_errors.py` y `router/http_errors.py` importan `starlette.exceptions` para capturar los 404/405 de enrutamiento; 02 §8 permite «FastAPI» en los adaptadores y prohíbe Starlette solo en `shared/` |
| Corrección hecha | [IA] Se admite Starlette en los adaptadores HTTP como base de FastAPI (declarado en el código de la prueba y en esta entrada); sigue prohibido en `shared/`, modelos, puertos y servicios |
| Requisitos relacionados | NFR-01, NFR-02, NFR-03, NFR-08; TC-13 |
| Verificación personal | Repetí a mano la revisión de TC-13 con `grep`: la única coincidencia en los `http.py` es la línea 52 de `controller/http.py`, que solo convierte cada enlace en `LinkSchema` para la respuesta de `GET /topology` (serialización, no algoritmo); `router/` no importa NetworkX, `engine` ni `controller`; los constructores de `RoutingService` y `ForwardingService` reciben sus dependencias. |

## S2-P06 — Integración, demostración y mediciones (FASE 3)

| Campo | Contenido |
|---|---|
| Fecha | 2026-10-30 |
| Técnica | [IA] Guion reproducible que captura cada comando con su salida literal; mediciones con datos crudos y entorno |
| Objetivo | [IA] Evidencia de la demostración obligatoria (PDF p. 5) con dos procesos reales; NFR-11 con procesos reales; `test-results.txt` |
| Texto del prompt | «continua» (tras el cierre de W-08), bajo S2-P01 (FASE 3) y S2-P04 |
| Salida relevante | [IA] `scripts/demo.sh`, `demo-evidence/` (pasos 00, a, b, c, c2, d, e, f y registros de los procesos); `scripts/measure_nfr11.py` y `demo-evidence/nfr11/` (PASS); `test-results.txt` (552 aprobadas, 1 subcaso no ejecutado); TC-34 con dos directorios |
| Problema detectado | [IA] (1) La primera versión del guion fallaba también C→D dentro del paso b, de modo que la secuencia de versiones no era 1 → 2 → 3 como en W-11A y 03 S2. (2) Los comandos guardados usaban los atajos `http` y `packet` sin explicarlos. (3) TC-34 solo estaba cubierta parcialmente (TC-07 y AST), sin los «dos directorios» de 06 |
| Corrección hecha | [IA] (1) El destino inalcanzable pasó a un paso propio (c2) después de la restauración; se borró la primera evidencia y se repitió la demostración. (2) Cada archivo de evidencia incluye la definición de los atajos y las URL. (3) Nueva prueba `tests/test_tc34_process_independence.py` |
| Requisitos relacionados | FR-06, FR-07, FR-09, FR-10, NFR-05, NFR-06, NFR-10, NFR-11; TC-05, TC-07, TC-14–TC-16, TC-34 |
| Verificación personal | Ejecuté `bash scripts/demo.sh` en Windows 11 (Git Bash) y comprobé: ruta A→B→D; con B→D fallado, A→C→D (versión 2); tras restaurar, A→B→D (versión 3); destino inalcanzable 404; Controller detenido 503 y Controller sin respuesta 504; la bitácora tiene 7 líneas. |

## S2-P07 — Corrección del fallo observado en Windows 11 (503 esperado, 504 recibido)

| Campo | Contenido |
|---|---|
| Fecha | 2026-10-30 |
| Técnica | [Equipo] Informe de defecto con evidencia real (resultado literal de pytest y medición del tiempo de rechazo), hipótesis de causa, tareas numeradas con propietaria y restricciones explícitas (no cambiar el valor por defecto ni la especificación) |
| Objetivo | [IA] Que TC-07 y TC-34 sean válidas en Windows sin alterar el contrato, y documentar la limitación con datos medidos |
| Texto del prompt | Literal en el anexo S2-P07, al final de este registro |
| Salida relevante | [IA] `--connect-timeout 3` (con comentario y el dato de 2.03 s) en `test_tc07_unreachable_controller_down_and_timeout` y `test_tc34_two_separate_directories`; README (demo en Windows y limitación n.º 10); apartado «Ejecución en Windows 11 (30/10/2026)» en `test-results.txt`; suite en Linux tras la corrección: 552 passed, 1 skipped |
| Problema detectado | [IA] (1) El README debía decir que la demo arranca el Router con `--connect-timeout 3` en Windows, pero `scripts/demo.sh` no lo hacía: el paso d habría mostrado 504 en Windows. (2) La corrección no puede verificarse en la máquina en la nube, donde la conexión rechazada falla al instante. (3) Con la configuración por defecto, en Windows un Controller detenido sigue produciendo 504 y no el 503 de `04` §5 |
| Corrección hecha | [IA] (1) `scripts/demo.sh` usa 3 s en Git Bash (MINGW/MSYS/Cygwin) y 1.0 en Linux, configurable con `CONNECT_TIMEOUT_DEMO`; se propuso como commit separado, pendiente de aprobación. (2) `test-results.txt` queda «pendiente de re-ejecución en Windows tras la corrección». (3) Documentado como limitación; un cambio del valor por defecto requeriría un cambio de especificación aprobado por ambas |
| Requisitos relacionados | FR-07, FR-09, NFR-05, NFR-06; TC-07, TC-34; `02` §7, `04` §5 |
| Verificación personal | Detecté en mi PC que TC-07 y TC-34 fallaban (504 en vez de 503). Medí que una conexión rechazada a 127.0.0.1 tarda 2,03 s en Windows, más que el timeout de 1 s. Tras la corrección, `pytest` dio `553 passed` y la demo devolvió 503. |

## S2-P08 — HttpRouteClient sin cliente abierto permanente; regresión de latencia y variante A′

| Campo | Contenido |
|---|---|
| Fecha | 2026-10-30 |
| Técnica | [Equipo] Petición de cambio con restricciones (mismas firmas, excepciones y mapeo 503/504/502; transport inyectable), verificación pedida con una métrica (TC-15) y cambio de especificación opcional condicionado a la aprobación de ambas |
| Objetivo | [IA] Que `HttpRouteClient` no mantenga un `httpx.Client` abierto durante la vida del proceso, sin regresiones; decidir con datos sobre C-32 |
| Texto del prompt | Literal en el anexo S2-P08 (dos mensajes) |
| Salida relevante | [IA] `router/client.py` crea un `httpx.Client` por llamada dentro de `with`, con el contexto SSL creado una vez en `__init__` (`verify=self._ssl_context`). Suite: 552 passed, 1 skipped (2026-10-30T17:56:42Z). TC-15/NFR-10 tras el cambio A: p95 F-01 = 3,031 ms y F-19 = 56,256 ms (umbral 300 ms). Medición informativa de `POST /packets` (F-01, procesos reales): 8,554 ms antes; 81,746 ms con A; 8,440 ms con A′ en una copia y 9,324 ms con A′ en el repositorio. Cambio B no aplicado por decisión del equipo |
| Problema detectado | [IA] (1) TC-15 mide `GET /route` del Controller, que no usa `HttpRouteClient`: por construcción no podía detectar el efecto del cambio. (2) La medición del Router mostró una regresión de unas 10 veces en el p95 con la variante A: cada `httpx.Client()` recargaba los certificados raíz (≈ 51 ms por cliente, frente a 0,85 ms con un contexto SSL reutilizado). (3) La propuesta C-32 omitía `04` §4.2, que también fija el valor por defecto 1.0 y el ejemplo `httpx.Timeout(connect=1.0, …)`, y la prueba `test_tc14_router_settings.py::test_defaults` |
| Corrección hecha | [IA] (1) Se añadió una medición informativa de `POST /packets` antes y después. (2) Variante A′ propuesta, medida en una copia y aplicada tras la aprobación de Laura, con un comentario en el código que da el motivo y las cifras. (3) Señalado al equipo; C-32 no se escribió y `specs/` no se modificó (decisión del equipo; la limitación 10 del README se mantiene) |
| Requisitos relacionados | FR-07, FR-09, NFR-06, NFR-10; TC-15, TC-32; `02` §5, §7; `04` §4.2 |
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

### Anexo S2-P07 — texto literal

````text
Contexto: proyecto de la Sesión 2 ya fusionado en main (baseline spec-1.0 intacta). Reglas: no modificar specs/, diagrams/, prompts-session1.md ni evidencias/; no inventar resultados; un commit por cambio con la autoría indicada, solo tras «Revisado y aprobado — <nombre>»; push inmediato a la rama de la sesión; nada en main.

Problema real observado en Windows 11 (Python 3.14, Git Bash), al ejecutar python -m pytest -q: «2 failed, 551 passed». Fallan test_tc07_unreachable_controller_down_and_timeout y test_tc34_two_separate_directories: esperan 503 CONTROLLER_UNAVAILABLE con el Controller detenido y reciben 504. Causa probable: en Windows, una conexión rechazada a 127.0.0.1 tarda unos 2 s en fallar, y el connect timeout por defecto es 1.0 s (02 §7), así que httpx lanza ConnectTimeout.

Haz:
1. En esas dos pruebas, arranca el Router con --connect-timeout 3, con un comentario que cite esta causa. No cambies el valor por defecto ni la especificación. (Propietaria: Laura Sofia Quintero Fernandez <laurasquintero@unicauca.edu.co>.)
2. En la sección «Sesión 2» del README: en Windows, la demo arranca el Router con --connect-timeout 3; añade la limitación conocida con su explicación. (Propietaria: Mariana Arturo Pabón <marianaarturo@unicauca.edu.co>.)
3. En test-results.txt añade un apartado «Ejecución en Windows 11 (30/10/2026)» con el resultado real que os doy literalmente: «2 failed, 551 passed, 1 warning in 22.42s», los nombres de las dos pruebas y la causa. No borres nada. Deja indicado «pendiente de re-ejecución en Windows tras la corrección». (Propietaria: Mariana.)
4. Añade un registro S2-P07 en prompts-session2.md con este prompt.
5. Regenera SHA256SUMS (autoría de Laura), ejecuta la suite, crea la PR y muéstrame el resultado. Dato medido en el Windows del equipo: socket.connect a 127.0.0.1:9 (puerto cerrado) → «ConnectionRefusedError 2.03 s». Cítalo en el comentario de las pruebas, en el README y en test-results.txt.
````

### Anexo S2-P08 — texto literal

Mensaje 1:

````text
Contexto: proyecto Sesión 2 en main; baseline spec-1.0. Reglas: no inventar resultados; un commit por cambio, con autoría Laura Sofia Quintero Fernandez <laurasquintero@unicauca.edu.co> (propietaria del Router, 05 §2), solo tras «Revisado y aprobado — <nombre>»; push inmediato a la rama de la sesión; nada en main.

Cambio A (sin cambio de especificación): en router/client.py, HttpRouteClient no debe mantener un httpx.Client abierto durante toda la vida del proceso. Crea el cliente dentro de fetch_route con «with httpx.Client(base_url=…, timeout=…, transport=self._transport) as http:», conserva el transport inyectable y las mismas firmas, excepciones y mapeo 503/504/502. Ejecuta toda la suite y TC-15 (NFR-10) y muéstrame que p95 sigue ≤ 300 ms.

[OPCIONAL: incluir solo si ambas aprobáis cambiar la especificación]
Cambio B (cambio de especificación, control de cambios de REVIEW-AND-BASELINE.md §4): propone la entrada C-32 en CHANGELOG-SPECS.md: «Valor por defecto de CONTROLLER_CONNECT_TIMEOUT_SECONDS: 1.0 → 3.0 s. Motivo: en Windows 11 una conexión rechazada a 127.0.0.1 tarda 2,03 s (medido por el equipo) y con 1.0 s FR-09 devuelve 504 en vez de 503». Artefactos afectados: 02 §7 (tabla), router/settings.py y README (limitación 10). NO modifiques specs/ hasta que ambas escriban «Apruebo C-32 — <nombre>». Después: actualiza 02 §7, el código y el README, quita el --connect-timeout 3 de las pruebas y de demo.sh (ya no hace falta), ejecuta la suite y deja indicado que hay que crear el tag spec-1.1.

Al final regenera SHA256SUMS (autoría de Laura) y crea la PR.
````

Mensaje 2:

````text
Revisado y aprobado — Laura Sofia Quintero Fernandez
Aplica la variante A′ (contexto SSL creado una vez en __init__ y verify=self._ssl_context). No aplicamos el cambio B: no escribas C-32 ni toques specs/; la limitación 10 del README se mantiene.
Añade en router/client.py un comentario breve con el motivo (evitar recargar certificados en cada llamada; p95 de POST /packets medido: 8,554 → 81,746 ms con A y 8,440 ms con A′).
Añade el registro S2-P08 en prompts-session2.md con este prompt y el anterior, la regresión detectada y su corrección, con «Verificación personal» vacía para que la complete yo.
Ejecuta la suite completa, haz los commits (autoría de Laura), regenera SHA256SUMS el último, haz push y crea la PR.
````
