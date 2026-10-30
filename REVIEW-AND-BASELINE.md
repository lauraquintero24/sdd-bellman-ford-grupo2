# Revisión cruzada y baseline de especificaciones (actividad 6 de la Sesión 1)

| Campo | Valor |
|---|---|
| Versión candidata | **1.0** — 2026-10-29 — seis especificaciones, `specs/fixtures/`, `diagrams/` y `prompts-session1.md` (SHA-256 en `SHA256SUMS`) |
| Baseline objetivo | Tag Git `spec-1.0` |
| Estado | **CONGELADA (spec-1.0)** — reconfirmada por ambas estudiantes el 30/10/2026 (`evidencias/aprobaciones/reconfirmacion-v1.0-Mariana.pdf`, `evidencias/aprobaciones/reconfirmacion-v1.0-Laura.pdf`). Commit y tag Git `spec-1.0`: pendientes (§3, paso 5). Este es el único documento donde cambia el estado. |

## 1. Revisión cruzada (PDF p. 4: diagramas, requisitos, API y pruebas concuerdan)

La columna «Resultado automático» resume la verificación ejecutada el 29/10/2026 con herramientas escritas con asistencia de IA (salida completa en `VALIDACION.md`). Las herramientas no forman parte de esta entrega, para que el paquete de la Sesión 1 no contenga código; el equipo las recibe aparte. La revisión y las correcciones de la versión 1.0 fueron hechas con asistencia de IA (registro P10 de `prompts-session1.md`); por eso las dos últimas columnas, que solo completan las estudiantes, son imprescindibles.

| Verificación | Método | Resultado automático | Estudiante A | Estudiante B |
|---|---|---|---|---|
| Cada FR/NFR tiene criterio verificable, prueba, tarea y componente; cada prueba traza a un requisito | Comparación `01` ↔ `05` §6 ↔ `06` en ambos sentidos | OK: 21 requisitos, 37 pruebas activas, 0 huérfanos | Confirmado (30/10/2026) | Confirmado (30/10/2026) |
| Los participantes y los métodos de las secuencias existen en el diagrama de clases | `03` ↔ `02` §3 | OK | Confirmado en su constancia, §2 (30/10/2026) | Confirmado en su constancia, §2 (30/10/2026) |
| Las peticiones de las secuencias existen en el contrato | `03` ↔ `04` | OK | Confirmado (30/10/2026) | Confirmado (30/10/2026) |
| Estado HTTP y `error.code` coherentes en todos los documentos | Matriz `04` §5 ↔ `01`–`06` | OK | Confirmado (30/10/2026) | Confirmado (30/10/2026) |
| Los 48 resultados esperados de las pruebas son correctos | Enumeración exhaustiva de rutas simples, redondeo exacto y referencia de 120 cifras; NetworkX para `delay` e `inverse_bandwidth` | OK | Confirmado (30/10/2026) | Confirmado (30/10/2026) |
| El ejemplo de `04` §2 es el fixture F-01 y todos los fixtures son topologías válidas | `01` §4 | OK: 27 fixtures | Confirmado (30/10/2026) | Confirmado (30/10/2026) |
| El plan es acíclico y cada carril suma 108 min con 10 min de reserva | `05` §3–§4 | OK | Confirmado (30/10/2026) | Confirmado (30/10/2026) |
| Los diagramas se renderizan desde las fuentes vigentes | Mermaid CLI 11.16.0 → `diagrams/*.svg` | OK: 7 SVG | Confirmado (30/10/2026) | Confirmado (30/10/2026) |
| Legibilidad de los diagramas y adecuación a la intención del equipo | Revisión visual humana | No automatizable | Confirmado (30/10/2026) | Confirmado (30/10/2026) |

## 2. Historial de aprobación

### 2.1 Versión RC11 — aprobada por ambas estudiantes

| Campo | Estudiante A — Controller | Estudiante B — Router |
|---|---|---|
| Nombre | Mariana Arturo Pabón | Laura Sofía Quintero Fernández |
| Constancia | `evidencias/aprobaciones/conformidad-Mariana.pdf` | `evidencias/aprobaciones/conformidad-Laura.pdf` |
| Firma (imagen aportada por separado) | `evidencias/aprobaciones/firma-Mariana.jpeg` | `evidencias/aprobaciones/firma-Laura.jpeg` |
| Fecha y versión | 29/10/2026 · RC11 | 29/10/2026 · RC11 |
| Alcance declarado | Seis especificaciones, arquitectura, contratos REST/JSON, DEC-01–DEC-09, diagramas, plan, casos de prueba y documentación de Prompt Engineering | Ídem |
| Observación literal | «No se identificaron observaciones adicionales, se realizaron pruebas en la revisión.» | «No se identificaron observaciones adicionales.» |
| Decisión literal | «Apruebo la versión identificada anteriormente.» | «Apruebo la versión identificada anteriormente.» |

Los archivos se conservan byte a byte: sus SHA-256 coinciden con los del inventario del expediente RC11 recibido, lo que puede comprobarse con ese ZIP original; las firmas solo se renombraron sin espacios. La autenticidad de las firmas no se verificó criptográficamente. Hechos observables que el docente puede pedir aclarar: ambos PDF tienen en sus metadatos el autor «Mariana Arturo» y fueron creados con 72 segundos de diferencia (15:26:40 y 15:27:52 del 29/10/2026); las imágenes de firma no están incrustadas en los PDF. Por eso la plantilla de reconfirmación exige que **cada estudiante cree su propio archivo**. El plan RC11 contenía además una revisión operativa fechada el 29/10/2026 por ambas, con el texto «Se comprobo los resultados», «ninguno identificado» como bloqueos y «Código de sesión 2 desarrollado previamente: NO».

### 2.2 Código generado por la IA durante la especificación

Los registros del expediente (RC3, véase `CHANGELOG-SPECS.md`, y P01 de `prompts-session1.md`) mencionan un «código de referencia» producido en la conversación con la IA en una iteración temprana, lo que contradice la regla del PDF de no generar código de implementación en la Sesión 1 (pp. 3 y 7). Ese código no se incluye en este paquete ni se usará; la implementación partirá de la baseline en la Sesión 2. **Acción humana:** el equipo debe informarlo al docente.

### 2.3 Proceso y cronología conocidos

| Etapa | Fecha | Herramienta de IA | Fuente |
|---|---|---|---|
| RC1–RC10: redacción e iteraciones de las especificaciones | Sin fecha registrada hasta RC7 (P06: 28/10/2026) | ChatGPT (según el registro de P09) | `CHANGELOG-SPECS.md`, `prompts-session1.md` |
| RC11: consolidación y aprobación de ambas estudiantes | 29/10/2026 | ChatGPT | Constancias de §2.1 |
| Versión 1.0: auditoría y correcciones C-01 a C-31 | 29–30/10/2026 | Claude (P10) | `CHANGELOG-SPECS.md` |

El trabajo se extendió más allá de los 108 minutos de la sesión presencial. El expediente no registra qué actividades de la Sesión 1 (PDF p. 3) hizo cada estudiante; cada una lo declara en su constancia de reconfirmación (§5 de la plantilla), porque la rúbrica reparte los puntos «sujeto a contribución verificada».

### 2.4 Versión 1.0 — reconfirmada

La versión 1.0 introduce los cambios C-01 a C-31 de `CHANGELOG-SPECS.md`; los marcados «Sí» en su última columna modifican comportamiento especificado (códigos HTTP, formato y precisión de `total_cost`, contratos de datos y de errores, validación, NFR-10/NFR-11, puntos de inyección, nombres de esquemas). Todos fueron propuestos con asistencia de IA. Por eso la aprobación de RC11 no se trasladó automáticamente a la versión 1.0 y se pidió una reconfirmación independiente.

**Reconfirmación.** El 30/10/2026, Mariana Arturo Pabón (Estudiante A, Controller) y Laura Sofía Quintero Fernández (Estudiante B, Router) revisaron por separado los cambios C-01 a C-31 y aprobaron la versión 1.0 como baseline `spec-1.0`. Cada una entregó su propia constancia, con su nombre escrito como firma: `evidencias/aprobaciones/reconfirmacion-v1.0-Mariana.pdf` y `evidencias/aprobaciones/reconfirmacion-v1.0-Laura.pdf`. Ambas constancias incluyen la crítica personal de una salida de IA, la justificación propia de al menos tres decisiones (entre ellas DEC-03) y la contribución de cada una en la Sesión 1; ambas marcan «Sí» en los cambios de §1 y en las cuatro afirmaciones de §2 de la plantilla, sin observaciones.

**Hechos observables que el docente puede pedir aclarar.** Ambos PDF se generaron con Word a partir de la misma plantilla (versión definitiva exportada a las 06:02:36 la de Mariana y a las 05:58:26 la de Laura, el 30/10/2026; sustituye a una primera versión que conservaba textos de propuesta de la plantilla), y en sus metadatos el autor figura como «Pendiente de completar por la estudiante». Las firmas son el nombre escrito; no hay firma manuscrita ni criptográfica.

**Estado del procedimiento de §3:** pasos 1–4 completados el 30/10/2026; queda el paso 5 (commit y tag `spec-1.0` en el repositorio del equipo).

## 3. Procedimiento único de congelamiento (acción humana)

1. Cada estudiante lee `CHANGELOG-SPECS.md` y las secciones afectadas, revisa `VALIDACION.md` (o ejecuta las herramientas de verificación entregadas aparte) y revisa visualmente `diagrams/*.svg`.
2. Cada una completa y firma su propia copia de `evidencias/aprobaciones/PLANTILLA-reconfirmacion-v1.0.md` (en Word, PDF o Markdown), incluida su crítica personal y la justificación propia de al menos tres decisiones, y la guarda en `evidencias/aprobaciones/` como `reconfirmacion-v1.0-Mariana.pdf` o `reconfirmacion-v1.0-Laura.pdf`. La constancia se refiere a los SHA-256 de `specs/` y `prompts-session1.md` que figuran en `SHA256SUMS`; esos archivos no se tocan durante el congelamiento.
3. Si ambas aprueban: completar las columnas A y B de §1 y cambiar el campo «Estado» de este documento a **CONGELADA (spec-1.0)**.
4. Regenerar el inventario desde la raíz del paquete: `find . -type f ! -name SHA256SUMS ! -path './.git/*' | sort | xargs sha256sum > SHA256SUMS` (o el generador de las herramientas entregadas aparte) y comprobarlo con `sha256sum -c SHA256SUMS`.
5. `git add -A` → `git commit -m "Congelar especificaciones spec-1.0"` → `git tag spec-1.0`, y anotar aquí el SHA real que devuelva Git (en un commit posterior, sin reescribir el tag).
6. Si alguna no aprueba: registrar sus observaciones como cambio nuevo en `CHANGELOG-SPECS.md`, corregir y repetir desde el paso 1.

## 4. Cambios posteriores al congelamiento

Cualquier cambio de diseño posterior se registra en `CHANGELOG-SPECS.md` con motivo, artefactos afectados y aprobación de ambas antes de modificar el código (PDF p. 4). La implementación de la Sesión 2 sigue la baseline congelada; si el código no la cumple, se corrige el código o se registra el fallo, nunca se ajusta el requisito para que coincida con un código incorrecto (PDF p. 5).
