# Control de cambios de la implementación

Cambios de código y pruebas que **no** modifican las especificaciones (`specs/`, `diagrams/`) ni el contrato de `04`. Los cambios de especificación se registran en `CHANGELOG-SPECS.md`.

| Fecha | Cambio | Artefactos | Estado |
|---|---|---|---|
| 2026-11-01 | Robustez Windows del DAO del Router: reintento acotado ante PermissionError; pruebas de carrera tras fallo/restauración de enlace. Pendiente de verificación en Windows 11. | `router/dao.py`; `tests/test_tc40_tc45_tc46_five_processes.py`; `tests/test_tc45_race_after_link_change.py` | Linux: 683 passed, 1 skipped. Windows 11: no ejecutado |
