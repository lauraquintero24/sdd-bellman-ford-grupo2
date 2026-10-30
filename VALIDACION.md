# Validación de la versión 1.0 — Sesión 1

Comprobaciones **realmente ejecutadas** el 2026-10-30 (última ejecución, tras incorporar las constancias de reconfirmación) sobre este paquete con herramientas escritas con asistencia de IA (`verify_specs.py`, `check_package.py`, `generate_sha256sums.py`). Las herramientas **no forman parte de la entrega** para que el paquete de la Sesión 1 no contenga código; se entregan al equipo por separado. Demuestran coherencia documental, corrección matemática de los resultados esperados e integridad del paquete; **no** demuestran el funcionamiento del software de la Sesión 2, que aún no existe.

## 1. Resumen

| Comprobación | Entorno | Resultado | Qué demuestra | Qué no demuestra |
|---|---|---|---|---|
| `verify_specs.py` | Python 3.13.18 + NetworkX 3.7 | PASA (código 0) | Trazabilidad 01 ↔ 05 ↔ 06, plan, JSON y fixtures, 48 resultados esperados (enumeración exhaustiva, redondeo exacto, referencia de 120 cifras, NetworkX), formato canónico, errores HTTP, diagramas ↔ clases ↔ API | Que el código futuro cumpla |
| `verify_specs.py` | Python 3.11.18 sin NetworkX | PASA (código 0) | Funciona con la versión mínima exigida y sin dependencias | — |
| Pruebas de mutación del verificador | 7 errores introducidos a propósito en copias temporales | 7/7 detectados | Que el verificador no es vacuo | — |
| `check_package.py` | Python 3.13.18 | PASA (código 0) | Paquete sin código, `SHA256SUMS` completo y correcto, evidencias RC11 intactas, SVG coherentes con sus fuentes, referencias de archivos | Autenticidad de las firmas |
| `sha256sum -c SHA256SUMS` | GNU coreutils | PASA (código 0) | Integridad de cada archivo | — |
| Renderizado de `diagrams/*.mmd` | Mermaid CLI 11.16.0 (biblioteca mermaid 11.16.1) | 7 SVG generados sin errores | Sintaxis Mermaid válida y renderizable | Legibilidad juzgada por humanos |
| `markdownlint` (reglas por defecto salvo longitud de línea, HTML en línea y estilo de tablas) | markdownlint-cli | PASA (código 0) | Markdown bien formado | Calidad del contenido |

## 2. Salida de `verify_specs.py` (Python 3.13.18)

```text
OK   Markdown: 6 specs, bloques cerrados, tablas con columnas consistentes, sin residuos de historial
OK   Trazabilidad: 21 requisitos, 9 DEC, 37 TC activas + 2 retiradas; 01 = 05 = 06 en ambos sentidos
OK   Plan: 21 tareas W, grafo acíclico, dos carriles de 108 min con ventanas encadenadas
OK   JSON: 16 bloques válidos; 27 fixtures conformes a 01 §4; ejemplo de 04 §2 = F-01
OK   Oráculo: 48 resultados esperados de 06 §3 recalculados por enumeración exhaustiva y referencia de 120 cifras; costos de delay/inverse_bandwidth confirmados con NetworkX
OK   F-19: ruta óptima N100→N001 de 99 saltos y costo 99 (NetworkX)
OK   Formato canónico: gramática de 01 §5.3 comprobada con 17 casos y en 3 ejemplos JSON de las specs
OK   Contraste aleatorio (semilla 20261029): 3656 consultas, costo de la enumeración = NetworkX
OK   TC-11: G1 (ciclo negativo alcanzable), G2 (no alcanzable) y G3 (producto > 1) confirmados; G1/G2 también con NetworkX
OK   DEC-09: 0.1 + 0.7 = 0.8 en aritmética exacta y distinto en float
OK   Errores: 13 códigos en 04 §5; 46 referencias estado+código coherentes en las seis specs
OK   Mermaid: 7 diagramas = archivos de diagrams/; 52 clases; 29 llamadas de secuencia con método declarado

RESULTADO: todas las comprobaciones documentales y matemáticas pasan.
AVISO: no se ejecuta software de la Sesión 2; los TC siguen 'especificados, no ejecutados'.
```

## 3. Pruebas de mutación

| Error introducido | Resultado | Primer mensaje del verificador |
|---|---|---|
| versión esperada errónea en E-04 | detectado | `FAIL E-04: versión 3 != 2` |
| costo de loss truncado en E-03 | detectado | `FAIL E-03: '0.0201006717' no es el redondeo correcto de 0.020100671707002882367` |
| TC eliminada de la matriz de 05 | detectado | `FAIL Trazabilidad FR-06: 01=['TC-03', 'TC-04', 'TC-17', 'TC-18'] 05=['TC-03', 'TC-04', 'TC-17']` |
| código 409 para ROUTE_UNREACHABLE en 01 | detectado | `FAIL 01: 409 ROUTE_UNREACHABLE contradice 04 §5 (404)` |
| método inexistente en una secuencia | detectado | `FAIL secuencia: HttpRouteClient.fetch_routes no declarado` |
| duración de tarea que rompe los 108 min | detectado | `FAIL 05: ventana de W-07.2 (47–60) no encadena con 47 o no mide 12` |
| ruta esperada no óptima en E-09 | detectado | `FAIL E-09: ruta esperada ["A","C","D"] != óptima ['A', 'B', 'D']` |

## 4. Salida de `check_package.py`

```text
OK   18 archivos obligatorios presentes
OK   5 evidencias originales con SHA-256 idéntico al inventario RC11
OK   66 archivos inventariados en SHA256SUMS con SHA-256 correcto; ningún archivo de código
OK   7 SVG válidos que contienen los identificadores de su fuente .mmd
OK   134 referencias a archivos del paquete en los Markdown, todas existentes

RESULTADO: paquete íntegro. AVISO: no autentica firmas ni ejecuta software de la Sesión 2.
```

## 5. Pendiente o no verificable a 30/10/2026

| Elemento | Estado | Responsable |
|---|---|---|
| Reconfirmación de la versión 1.0 | Hecha el 30/10/2026: dos constancias en `evidencias/aprobaciones/` (contenido no verificable por estas herramientas; firmas con nombre escrito, sin firma manuscrita ni criptográfica) | Ambas estudiantes (`REVIEW-AND-BASELINE.md` §2.4) |
| Commit y tag Git `spec-1.0` | Hecho el 30/10/2026: commit `20c2289`, tag `spec-1.0` |
| Ejecución de TC-01 a TC-39 | No ejecutadas: no existe código (Sesión 2) | Equipo, Sesión 2 |
| Mediciones de NFR-10 (p95 ≤ 300 ms) y NFR-11 (100 líneas concurrentes) | No medidas | Equipo, Sesión 2 |
| Factibilidad real del cronograma de 108 min | No medida (presupuesto) | Equipo, Sesión 2 |
| Autenticidad de las firmas de RC11 y de la versión 1.0 | No verificable criptográficamente | — |
| Revisión visual humana de los diagramas | Declarada confirmada por ambas el 30/10/2026 (`REVIEW-AND-BASELINE.md` §1); no verificable por herramientas | Ambas estudiantes |
