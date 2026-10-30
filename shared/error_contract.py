"""Constantes del contrato de errores y de los nombres de campos JSON (02 §3.3; 04 §1, §4.3, §5, §6).

Solo biblioteca estándar (02 §8).
"""

# error.code (04 §5)
MALFORMED_JSON = "MALFORMED_JSON"
INVALID_REQUEST = "INVALID_REQUEST"
NODE_NOT_FOUND = "NODE_NOT_FOUND"
LINK_NOT_FOUND = "LINK_NOT_FOUND"
ROUTE_UNREACHABLE = "ROUTE_UNREACHABLE"
NEGATIVE_CYCLE = "NEGATIVE_CYCLE"
LOG_PERSISTENCE_ERROR = "LOG_PERSISTENCE_ERROR"
CONTROLLER_BAD_RESPONSE = "CONTROLLER_BAD_RESPONSE"
CONTROLLER_UNAVAILABLE = "CONTROLLER_UNAVAILABLE"
CONTROLLER_TIMEOUT = "CONTROLLER_TIMEOUT"
UNKNOWN_ENDPOINT = "UNKNOWN_ENDPOINT"
METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
INTERNAL_ERROR = "INTERNAL_ERROR"

ERROR_CODES = frozenset({
    MALFORMED_JSON, INVALID_REQUEST, NODE_NOT_FOUND, LINK_NOT_FOUND, ROUTE_UNREACHABLE, NEGATIVE_CYCLE,
    LOG_PERSISTENCE_ERROR, CONTROLLER_BAD_RESPONSE, CONTROLLER_UNAVAILABLE, CONTROLLER_TIMEOUT,
    UNKNOWN_ENDPOINT, METHOD_NOT_ALLOWED, INTERNAL_ERROR,
})

# Sobre de error (04 §1)
ERROR_KEY = "error"
ERROR_FIELDS = ("code", "message", "details")

# Respuesta de GET /route (04 §3.3, §4.3)
ROUTE_FIELDS = ("source", "destination", "metric", "path", "total_cost", "topology_version")
METRICS = ("delay", "inverse_bandwidth", "loss")

# 404 del Controller que el Router propaga, y renombrado de details.field (04 §4.3)
PROPAGATED_CONTROLLER_CODES = frozenset({NODE_NOT_FOUND, ROUTE_UNREACHABLE})
DETAILS_FIELD_RENAMES = {"src": "source", "dst": "destination"}

# Estados de un ForwardingResult y campos de la línea JSONL (04 §6)
STATUS_FORWARDED = "forwarded"
STATUS_FAILED = "failed"
LOG_RECORD_FIELDS = (
    "recorded_at", "packet_id", "source", "destination", "metric", "status",
    "route", "trace", "topology_version", "error",
)
