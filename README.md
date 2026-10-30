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
| Confirmación de ambas estudiantes y baseline congelada | `REVIEW-AND-BASELINE.md` | **Hecho:** versión 1.0 reconfirmada por ambas el 30/10/2026; falta el commit y tag `spec-1.0` |

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
3. **Congelar la baseline** con un commit propio y el tag `spec-1.0` (`REVIEW-AND-BASELINE.md` §3).
4. **Sesión 2:** implementar desde la baseline, ejecutar al menos ocho pruebas aprobadas (incluidas TC-08 y TC-09), medir NFR-10 y NFR-11 y registrar evidencias reales.
