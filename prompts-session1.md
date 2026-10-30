# Registro de prompts — Sesión 1 (especificación y arquitectura)

| Campo | Valor |
|---|---|
| Proyecto | Controller y Router SDN con Bellman-Ford — Grupo 2 |
| Versión | **1.0** · 2026-10-29 |
| Equipo | Mariana Arturo Pabón (A — Controller) · Laura Sofía Quintero Fernández (B — Router) |
| Exigencias del PDF | p. 4: usar y documentar *contextual framing*, *structured prompting*, *role prompting*, *few-shot examples* e *iterative refinement*; exigir IDs de requisito y criterios de aceptación verificables; pedir a la IA al menos tres ambigüedades y resolverlas con juicio propio. p. 5: por cada prompt, técnica, objetivo, texto, salida relevante, problema detectado, corrección y requisitos; las estudiantes verifican personalmente la salida de la IA. |

**Reglas de este registro.** Solo se registran interacciones que ocurrieron. Los textos largos se conservan literalmente en `evidencias/prompts/` (archivos `.txt` sin modificar); aquí se resume cada uno. Cuando el texto literal no se conservó, se indica expresamente.

**Autoría.** Este registro fue reorganizado con asistencia de IA (P10) a partir de los registros anteriores. Se marca **[Equipo]** lo que reproduce decisiones o textos de las estudiantes, y **[IA]** el análisis redactado por la IA (problemas, críticas y correcciones de §4 y §5), que ellas deben revisar. La crítica personal de cada estudiante y su justificación propia de las decisiones se recogen en su constancia de reconfirmación (`evidencias/aprobaciones/PLANTILLA-reconfirmacion-v1.0.md`, §3).

**Estado de la revisión humana a 29/10/2026 (fecha de este registro):** las salidas de IA incorporadas hasta RC11 (P01–P09) fueron revisadas por ambas estudiantes, que aprobaron esa versión ese mismo día (`REVIEW-AND-BASELINE.md` §2.1). Los cambios de la versión 1.0 (P10) se produjeron después de esa aprobación. La verificación matemática de los resultados esperados no depende de ninguna respuesta de IA (`VALIDACION.md`).

## 1. Cobertura de las exigencias del PDF

| Exigencia | Dónde se evidencia | Observación |
|---|---|---|
| *Contextual framing* | P01 (jerarquía de fuentes: PDF del Grupo 2 > plantillas > bibliografía; descripción del sistema) | También en P06–P08 y P10 |
| *Structured prompting* | P01 (etapas, entregables, formato) y P03 (hallazgos por archivo) | También en P06–P08 y P10 |
| *Role prompting* | P01 (cinco roles expertos) | También en P06–P08, P09 y P10 |
| *Few-shot examples* | P09 (dos ejemplos resueltos y un caso nuevo) | Captura de la respuesta en `evidencias/few_shot/` |
| *Iterative refinement* | P02 → decisión «usa la opcion a»; P09 versión 1 → versión 2; ciclo de revisiones P03–P08 y P10 | Cada iteración corrigió defectos concretos (§4) |
| IDs de requisito y criterios de aceptación verificables | P01, etapa 1: «Requisitos verificables y trazabilidad por identificadores» y «criterios de aceptación» | Resultado: FR/NFR con criterios y pruebas en `specs/01-requirements.md` |
| Al menos tres ambigüedades, resueltas con juicio propio | P01, etapa 1: «Detecta al menos tres ambigüedades relevantes del enunciado» | La IA propuso ocho; el equipo decidió DEC-01–DEC-09 en la versión aprobada el 29/10/2026 (§3) |
| ≥ 6 prompts sustanciales entre ambas sesiones | Seis con texto completo conservado: P01, P06, P07, P08, P09 y P10; P02 (una frase) y P03 (parcial) complementan; P04 y P05 **no se cuentan** (texto no conservado) | P06–P08 y P10 son del mismo tipo (auditoría y corrección); los prompts de generación de código y de pruebas corresponden a `prompts-session2.md` |

## 2. Resumen de los prompts

| ID | Fecha | Herramienta | Técnicas | Objetivo | Texto literal | Requisitos |
|---|---|---|---|---|---|---|
| P01 | Inicio del trabajo (sin fecha registrada) | Asistente conversacional (mismo hilo que P09, ChatGPT) | Rol, contexto, estructura | Analizar el PDF y redactar las seis especificaciones | `evidencias/prompts/P01-prompt-maestro-desarrollo-integral.txt` | FR-01–FR-10, NFR-01–NFR-11, DEC-01–DEC-08 |
| P02 | Iteración RC2 | Ídem | Refinamiento iterativo | Definir el desempate de rutas | Citado en §4 (una frase) | FR-03, FR-05, DEC-08 |
| P03 | Iteración RC3 | Ídem | Estructura, contexto, refinamiento | Corregir hallazgos de revisión del equipo | Parcial (petición final citada; tabla de hallazgos no conservada) | FR-08, FR-09, FR-10, NFR-06 |
| P04 | Iteración RC5 | Ídem | Rol, estructura, refinamiento | Corregir defectos algorítmicos y numéricos | **No conservado** | FR-03, FR-04, DEC-09 |
| P05 | Iteración RC6 | Ídem | Rol, estructura, refinamiento | Corregir dependencias y plan | **No conservado** | NFR-01, NFR-03, NFR-07, DEC-05 |
| P06 | 2026-10-28 | Ídem | Rol, contexto, estructura, refinamiento | Precisión de `loss`, fixtures completos, plan | `evidencias/prompts/P06-solicitud-correccion-rc7.txt` | FR-04, FR-05, DEC-09 |
| P07 | Iteración RC8 | Ídem | Rol, contexto, estructura, refinamiento | Contratos de clases y pruebas TC-09 | `evidencias/prompts/P07-solicitud-correccion-rc8.txt` | FR-10, NFR-07, NFR-09 |
| P08 | Iteración RC9 | Ídem | Rol, contexto, estructura, refinamiento | Simplificar la presentación numérica | `evidencias/prompts/P08-solicitud-correccion-rc9.txt` | FR-04, NFR-04, DEC-09 |
| P09 | Iteración RC10 | ChatGPT (captura) | **Few-shot**, rol, estructura, refinamiento | Verificar la política DEC-08/DEC-09 con ejemplos | `evidencias/prompts/P09-few-shot-bellman-ford.txt` | FR-03, FR-04, DEC-08, DEC-09 |
| P10 | 2026-10-29 | Claude (Anthropic) | Rol, contexto, estructura, refinamiento | Auditoría estricta y corrección integral → versión 1.0 | `evidencias/prompts/P10-prompt-auditoria-spdr-y-correccion.txt` | Todos (ver `CHANGELOG-SPECS.md`) |

## 3. Ambigüedades detectadas con la IA y resolución del equipo

En respuesta a P01, la IA señaló que el PDF no fija: (1) el formato JSON de la topología ni la direccionalidad, (2) el uso de enlaces con `p = 1` en otras métricas, (3) los códigos HTTP concretos, (4) la idempotencia de fallo y restauración, (5) qué DAO lleva cada aplicación, (6) la conducta del Router sin Controller, (7) cómo probar ciclos negativos con costos no negativos y (8) el desempate entre rutas de igual costo. La novena (comparación de decimales y del costo logarítmico) surgió en P04. Las nueve decisiones **DEC-01 a DEC-09** (`specs/01-requirements.md` §7) fueron aprobadas por ambas estudiantes en RC11. Evidencias de decisión del equipo frente a la propuesta de la IA:

- **[Equipo] DEC-08:** la IA propuso desempatar con las otras dos métricas (vector de cinco criterios, P02); tras una revisión externa que lo señalaba como riesgo, la estudiante eligió por escrito «usa la opcion a» («costo → saltos → ruta»).
- **[IA] DEC-03:** la versión aprobada en RC11 usaba 409 y 422; la auditoría P10 propuso alinearlos con el ejemplo oficial del PDF (400/404/503). Es una propuesta de la IA sujeta a la reconfirmación de ambas.

## 4. Registro detallado ([IA], salvo los textos citados de las estudiantes)

### P01 — Prompt maestro de desarrollo integral

- **Técnicas:** *role prompting* (ingeniero de software, ingeniero de telecomunicaciones, arquitecto MVC/DAO, especialista SDD y evaluador académico); *contextual framing* (jerarquía de fuentes, descripción de los dos procesos); *structured prompting* (etapas, entregables, criterios de calidad).
- **Objetivo:** analizar el PDF y producir las especificaciones de la Sesión 1 con IDs, criterios de aceptación y al menos tres ambigüedades.
- **Texto:** literal en `evidencias/prompts/P01-prompt-maestro-desarrollo-integral.txt`. Extracto de la etapa 1: «No generes código de implementación durante esta etapa. […] Detecta al menos tres ambigüedades relevantes del enunciado y propón cómo resolverlas justificadamente.»
- **Salida relevante:** primer borrador de los seis documentos, matriz de trazabilidad, plan de pruebas y ocho ambigüedades.
- **Problema detectado:** el prompt pedía desarrollar *todas* las etapas, incluido el código, lo que choca con la regla de la Sesión 1 (PDF pp. 3 y 7). Los registros RC2–RC3 del expediente mencionan un «código de referencia» surgido en esa conversación.
- **Corrección:** el trabajo se limitó a especificaciones; ningún código forma parte de la entrega ni se usó como evidencia, y la versión 1.0 elimina toda referencia a él. La implementación se hará en la Sesión 2 a partir de la baseline.
- **Requisitos:** FR-01–FR-10, NFR-01–NFR-11, DEC-01–DEC-08.

### P02 — Refinamiento del desempate

- **Técnica:** *iterative refinement* con elicitación de restricciones.
- **Texto literal:** «Establece más formas de desempate, por ej en distrajk era de acuerdo al orden alfabetico de los nodos, pero entonces establece todas las métricas o formas posibles de desempate para belman ford».
- **Salida:** vector lexicográfico de cinco criterios (métrica pedida, las otras dos métricas, saltos, ruta completa) y casos TC-19–TC-26.
- **Problema:** complejidad no exigida por el PDF; una revisión externa aportada por el equipo lo señaló como riesgo.
- **Corrección (decisión del equipo):** «usa la opcion a» → DEC-08 = costo de la métrica pedida, luego saltos, luego ruta completa; las otras métricas no desempatan (TC-19).
- **Requisitos:** FR-03, FR-05, DEC-08.

### P03 — Corrección dirigida por la revisión del equipo

- **Técnicas:** *structured prompting* (tabla de hallazgos por archivo elaborada por el equipo), *contextual framing*, *iterative refinement*.
- **Texto:** se conserva la petición final: «Entonces realiza todas esas correcciones y envíame nuevamente el zip de la sesión 1». La tabla de hallazgos no se conservó.
- **Salida / problema detectado por el equipo:** la IA había introducido una excepción `ForwardingRejected` y un atributo `error_code` inexistentes en el diseño, y rutas de módulos incoherentes.
- **Corrección:** `ForwardingResult` con `route`, `topology_version` y `error` opcionales; el servicio registra el fallo y relanza la misma `AppError` (`specs/02-static-architecture.md` §5, `specs/03-dynamic-architecture.md` S3).
- **Requisitos:** FR-08, FR-09, FR-10, NFR-06.

### P04 y P05 — Correcciones algorítmicas y de dependencias (texto literal no conservado)

- **Técnicas declaradas en el registro previo:** rol, contexto, estructura y refinamiento iterativo.
- **P04 — problema:** la regla de desempate de la iteración anterior comparaba igualdades en `float` (`dist[u] + w == dist[v]`), que fallan con `0.1 + 0.7`. **Corrección:** DEC-09, comparación exacta con `Fraction` (TC-27).
- **P05 — problema:** la IA había colocado importaciones de FastAPI en `shared/`, omitido el costo de ordenar arcos en la complejidad y asignado 0 minutos a la verificación del motor. **Corrección:** adaptadores HTTP por proceso (`specs/02-static-architecture.md` §8), cota de complejidad completa (§6.2) y tarea W-04A con 4 minutos.
- **Requisitos:** FR-03, FR-04, NFR-01, NFR-03, NFR-07, DEC-05, DEC-09.

### P06 — Corrección de la precisión de `loss` y de los fixtures (2026-10-28, fecha anotada en el registro RC11; no figura en la transcripción)

- **Técnicas:** *role prompting* (siete roles de revisión), *contextual framing* (PDF y evaluación previa), *structured prompting* (hallazgos numerados con criterios de cierre), *iterative refinement*. Tipo: revisión de arquitectura y especificación (P06–P08 incluyen puntuaciones de revisiones anteriores en su propio texto).
- **Objetivo:** corregir la viabilidad del plan, completar los fixtures de TC-23/TC-37 y la precisión de `loss`.
- **Texto:** `evidencias/prompts/P06-solicitud-correccion-rc7.txt`.
- **Salida relevante:** presentación de `loss` como cadena decimal con `q = 1 − S` exacto; fixtures F-14 y F-15 completos; nueva prueba TC-38.
- **Problema detectado:** con 50 cifras sobre `1 − S` ya redondeado, el costo de `p = 1e-60` se publicaba como `"0"`.
- **Corrección:** serie de 25 términos sobre `q` exacto (`specs/02-static-architecture.md` §6.3); E-42 lo comprueba.
- **Requisitos:** FR-04, FR-05, DEC-09.

### P07 — Contratos de clases y prueba TC-09

- **Técnicas:** rol, contexto, estructura, refinamiento iterativo.
- **Objetivo:** corregir hallazgos de contratos entre clases.
- **Texto:** `evidencias/prompts/P07-solicitud-correccion-rc8.txt`.
- **Salida relevante:** `Route` construido con argumentos nombrados; `RoutingService` como único invocador de `CostPresenter`.
- **Problema detectado:** TC-09 construía `Route` con argumentos posicionales y un costo numérico; la propiedad de `CostPresenter` era contradictoria entre el motor y el servicio.
- **Corrección:** firmas de `specs/02-static-architecture.md` §5; TC-08 verifica una sola llamada a `format_cost`.
- **Requisitos:** FR-10, NFR-07, NFR-09.

### P08 — Simplificación de la presentación numérica

- **Técnicas:** rol, contexto, estructura, refinamiento iterativo.
- **Objetivo:** reducir la complejidad del cálculo del costo sin perder la selección exacta.
- **Texto:** `evidencias/prompts/P08-solicitud-correccion-rc9.txt`.
- **Salida relevante:** presentación `Decimal` con objetivo de error relativo 10⁻¹⁰; `CostPresenter` añadido al diagrama de componentes; TC-39.
- **Problema detectado:** una presentación «certificada» por intervalos con límites artificiales (`PRESENTER_MAX_*`) producía errores 500 inventados, sin exigencia del PDF.
- **Corrección:** procedimiento acotado de `specs/02-static-architecture.md` §6.3.
- **Requisitos:** FR-04, NFR-04, DEC-09.

**[IA] Valoración de P06–P08:** estos prompts persiguen explícitamente una puntuación de revisión; su valor está en los defectos técnicos que hicieron aflorar, no en las autoevaluaciones de la IA, que no se usan como evidencia.

### P09 — Ejercicio *few-shot* de Bellman-Ford

- **Técnicas:** *few-shot* (dos ejemplos resueltos y un caso nuevo), *role prompting* («verificador de rutas Bellman-Ford»), *structured prompting* (salida solo JSON) e *iterative refinement* (versión 2).
- **Objetivo:** comprobar si la IA aplica DEC-08/DEC-09 a un caso de empate decimal que en `float` fallaría.
- **Texto y respuestas:** `evidencias/prompts/P09-few-shot-bellman-ford.txt`. La captura `evidencias/few_shot/P09-respuesta-chatgpt.png` muestra el final del prompt (Ejemplo 2) y la respuesta `{"path":["A","D"],"total_cost":"0.8"}` con la justificación «Las tres rutas cuestan exactamente 0.8 en aritmética decimal exacta, por lo que gana A→D al tener un solo salto…».
- **Verificación matemática:** correcto: `0.8 = 0.1 + 0.7 = 0.4 + 0.4` en aritmética exacta y gana `[A,D]` por un salto. La versión 2 (A→D = `0.800000000001`) tiene registrada la respuesta `{"path":["A","B","D"],"total_cost":"0.8"}`, matemáticamente correcta (dos rutas de 0.8 empatan y gana B por orden lexicográfico), pero **sin captura**: consta solo como texto anotado en RC10 y no se cuenta como evidencia independiente. Ambos casos se reproducen exactamente como E-47 y E-48 (fixtures F-08c y F-08d) de `specs/06-test-specification.md`, recalculados por la verificación automática (`VALIDACION.md`).
- **Problemas detectados:** la respuesta v1 es incompatible con una suma en `float` (que daría `0.1 + 0.7 = 0.7999999999999999` y elegiría `[A,B,D]`), pero la IA no muestra el cálculo; la v2 no discrimina, porque en `float` también se elige `[A,B,D]`; los ejemplos solo cubren `delay`; la respuesta de demostración anotada en RC10 tiene una redacción distinta de la captura.
- **Corrección:** la aceptación no depende de la IA: TC-27 exige comprobar `Fraction(Decimal("0.1")) + Fraction(Decimal("0.7")) == Fraction(4, 5)` y la ruta exacta; TC-37 y TC-38 cubren `inverse_bandwidth` y `loss`.
- **Requisitos:** FR-03, FR-04, DEC-08, DEC-09.

### P10 — Auditoría estricta y corrección integral (versión 1.0)

- **Técnicas:** *role prompting* («comité de evaluación académica»), *structured prompting* (cinco fases y reglas), *contextual framing* (PDF, plantillas y expediente RC11), *iterative refinement* (RC11 → 1.0 con segunda auditoría).
- **Texto:** literal en `evidencias/prompts/P10-prompt-auditoria-spdr-y-correccion.txt`.
- **Salida relevante:** versión 1.0 de las seis especificaciones, fixtures en JSON, verificador automático, diagramas renderizados y este registro reorganizado.
- **Problemas detectados:** códigos 409/422 distintos del ejemplo oficial; secuencia 3 que dibujaba como entregada una petición rechazada; falta de frontera de persistencia; formato de `total_cost` contradictorio; referencias al «código de referencia» en las especificaciones; pruebas duplicadas (TC-24, TC-35); registro de prompts sin los campos exigidos.
- **Iteración interna:** tras la primera corrección, dos auditorías sucesivas hechas por revisores de IA independientes (sin acceso al razonamiento previo) señalaron defectos adicionales —falta de puntos de inyección para pruebas, interfaces mezcladas con implementaciones, discrepancia entre la precisión exigida y las pruebas, código del verificador demasiado parecido a la implementación, errores en este registro sobre P09— que se corrigieron (cambios C-17 a C-30); también señalaron que la autoría de este registro debía distinguirse (marcas [IA]/[Equipo]) y que los verificadores en Python no debían formar parte de la entrega de la Sesión 1.
- **Corrección:** ver `CHANGELOG-SPECS.md` (motivo y artefactos afectados de cada cambio).
- **Verificación humana:** se documenta fuera de este registro, en las constancias de reconfirmación de cada estudiante (`REVIEW-AND-BASELINE.md` §3).
- **Requisitos:** todos.

## 5. [IA] Errores de la IA detectados y su corrección (insumo para la defensa)

| # | Sugerencia incorrecta de la IA | Por qué era incorrecta | Corrección adoptada | Detectado por |
|---|---|---|---|---|
| 1 | Desempatar con igualdad de `float` | `0.1 + 0.7 ≠ 0.8` en binario: elegiría una ruta de dos saltos | Comparación exacta `Fraction` (DEC-09, TC-27) | Revisión SPDR externa aportada por el equipo en P04 (autor de la revisión no registrado) |
| 2 | Vector de desempate con las otras dos métricas | Complejidad no exigida y difícil de verificar | DEC-08 simplificada (TC-19) | Equipo, tras revisión externa (P02) |
| 3 | `ForwardingRejected` y `error_code` | Clases inexistentes en el diseño | `AppError` relanzada; `ForwardingResult.error` | Equipo (P03) |
| 4 | FastAPI importado en `shared/` | Rompe la independencia de los procesos y la pureza del núcleo | Adaptadores HTTP por proceso (`02` §8, TC-13) | Revisión SPDR externa aportada por el equipo en P05 (autor no registrado) |
| 5 | Logaritmo con 50 cifras sobre `1 − S` redondeado | Cancelación: `p = 1e-60` se publicaba como `"0"` | Serie con `q` exacto (`02` §6.3, TC-38) | Revisión SPDR externa citada en el texto de P06 (hallazgo RC6-04) |
| 6 | Límites `PRESENTER_MAX_*` con error 500 | Errores artificiales no exigidos | Eliminados; procedimiento acotado | Revisión SPDR externa citada en el texto de P08 |
| 7 | Petición a un Controller caído dibujada como entregada | Semántica errónea del diagrama de secuencia | Mensaje perdido `-x` en S3 | Auditoría de la IA en P10 |

## 6. Prompts preparados para la Sesión 2 (no ejecutados)

Se registrarán en `prompts-session2.md` solo si se usan, con su salida real.

- **PS2-01 (*structured prompting*, generación de código):** «Con la baseline `spec-1.0`, implementa solo las clases del Controller declaradas en `specs/02-static-architecture.md` §3.1 con sus firmas exactas, FastAPI y DAO inyectable; prohíbe acceso a archivos o NetworkX en los handlers. Incluye pruebas para TC-01, TC-02 y TC-08. Si una firma es ambigua, señala la discrepancia en lugar de cambiar el diseño.»
- **PS2-02 (*iterative refinement*, pruebas):** «Revisa `ForwardingService` y sus pruebas contra TC-05, TC-06, TC-07 y TC-09 de `specs/06-test-specification.md`; usa `FakeRouteClient` y `FakeForwardingLogDAO`; informa qué pruebas pasaron y cuáles fallaron con la salida real de pytest, sin inventarla.»
