# Constancia de reconfirmación — especificaciones versión 1.0 (plantilla sin completar)

> Cada estudiante completa **su propia** copia (en Word, PDF o Markdown) y la guarda en `evidencias/aprobaciones/` como `reconfirmacion-v1.0-Mariana.pdf` o `reconfirmacion-v1.0-Laura.pdf` (`REVIEW-AND-BASELINE.md` §3). Nadie más puede completarla en su nombre: el archivo debe crearlo la propia estudiante (los metadatos del PDF mostrarán su autoría). Si alguna observación exige un cambio, se registra en `CHANGELOG-SPECS.md` y se repite la revisión.

| Campo | Valor |
|---|---|
| Proyecto | SDN Controller y Router — Bellman-Ford, Grupo 2 |
| Estudiante | |
| Responsabilidad | Controller (A) / Router (B) |
| Versión revisada | 1.0 (SHA-256 de `specs/` y `prompts-session1.md` según `SHA256SUMS`) |
| Fecha de revisión | |

## 1. Revisión de los cambios respecto de RC11 (`CHANGELOG-SPECS.md`)

| Cambio | Lo revisé | ¿Lo acepto? (sí / no, con motivo) |
|---|---|---|
| C-01 Códigos HTTP 400/404 (DEC-03) | | |
| C-02 Propagación de errores en el Router | | |
| C-03 Formato canónico de `total_cost` | | |
| C-04 y C-05 Diagramas de componentes y de clases | | |
| C-06 y C-07 Módulos y configuración | | |
| C-08 Secuencia 3 | | |
| C-09 Diseño del motor movido a `02` §6 | | |
| C-10 y C-11 Bitácora JSONL y validación de topología | | |
| C-12 Pruebas y fixtures | | |
| C-13 Plan de implementación | | |
| C-14 a C-16 Limpieza, registro de prompts y paquete | | |
| C-17 a C-19 Puertos, puntos de inyección y errores sin estado HTTP | | |
| C-20 y C-21 `ForwardingResult`, bitácora y precisión de `total_cost` | | |
| C-22 NFR-10 (F-19) y NFR-11 (concurrencia) | | |
| C-23 y C-24 Reglas `TOPO-*`, fixtures P09, plan con reservas y congelamiento | | |
| C-25 Herramientas fuera de la entrega; `SHA256SUMS`; `VALIDACION.md` | | |
| C-26 Redondeo exacto de `total_cost` | | |
| C-27 Ciclos en ambos modos; errores de red 502/504; 404/405 de rutas inexistentes | | |
| C-28 `GET /topology` con cadenas decimales; ID con espacios → 400; `details.field` | | |
| C-29 NFR-10 sobre F-19 (100 nodos) y ajustes del plan | | |
| C-30 Diagramas, esquemas renombrados, secuencias y registro de prompts | | |
| C-31 Ajustes de la cuarta auditoría (atributo `weight`, importaciones, validación en el Model, errores del Router, plan) | | |

## 2. Confirmación de consistencia (PDF p. 4)

| Afirmación | Confirmo |
|---|---|
| Los diagramas, los requisitos, el contrato de API y los casos de prueba concuerdan | |
| Revisé el registro de prompts y verifiqué personalmente las salidas de la IA que usamos | |
| Revisé `VALIDACION.md` (o ejecuté las herramientas de verificación entregadas aparte) y entiendo qué se verificó y qué no | |
| No he escrito ni incorporado al repositorio código de las aplicaciones antes de congelar esta versión (el borrador de la IA citado en P01 no se usa) | |

## 3. Crítica personal de una salida de IA (obligatoria, con mis palabras)

&nbsp;

## 4. Justificación propia de al menos tres decisiones (con mis palabras; debe incluir DEC-03, que cambió en la versión 1.0)

| Decisión | Por qué la acepto o la cambiaría |
|---|---|
| DEC-03 (códigos HTTP) | |
| DEC-0_ | |
| DEC-0_ | |

## 5. Mi contribución en la Sesión 1 (actividades del PDF p. 3 en las que trabajé y partes que redacté o revisé)

&nbsp;

## 6. Observaciones

&nbsp;

## 7. Decisión

☐ Apruebo la versión 1.0 como baseline `spec-1.0`.  ☐ No la apruebo por las observaciones anteriores.

Nombre y firma: ______________________________
