"""Contratos compartidos de la Estudiante B: errores del Router y error_contract (02 §3.3; 04 §5)."""

import pytest

from shared import error_contract as ec
from shared.errors import (
    AppError,
    ControllerBadResponseError,
    ControllerTimeoutError,
    ControllerUnavailableError,
    ForwardingLoopError,
    ForwardingTableUnavailableError,
    HopLimitExceededError,
    InvalidRequestError,
    LinkNotFoundError,
    LogPersistenceError,
    NegativeCycleError,
    NextHopBadResponseError,
    NextHopTimeoutError,
    NextHopUnavailableError,
    NodeNotFoundError,
    RouteUnreachableError,
    TopologyChangedError,
)


@pytest.mark.parametrize(
    "cls, code",
    [
        (LogPersistenceError, ec.LOG_PERSISTENCE_ERROR),
        (ControllerBadResponseError, ec.CONTROLLER_BAD_RESPONSE),
        (ControllerUnavailableError, ec.CONTROLLER_UNAVAILABLE),
        (ControllerTimeoutError, ec.CONTROLLER_TIMEOUT),
    ],
)
def test_router_error_codes(cls, code):
    err = cls("m")
    assert isinstance(err, AppError) and err.code == code
    assert err.to_dict() == {"code": code, "message": "m", "details": {}}


def test_every_app_error_code_is_in_the_contract():
    classes = [InvalidRequestError, NodeNotFoundError, LinkNotFoundError, RouteUnreachableError, NegativeCycleError,
               LogPersistenceError, ControllerBadResponseError, ControllerUnavailableError, ControllerTimeoutError,
               ForwardingTableUnavailableError, TopologyChangedError, NextHopBadResponseError, NextHopUnavailableError,
               NextHopTimeoutError, ForwardingLoopError, HopLimitExceededError]
    assert {c.code for c in classes} <= ec.ERROR_CODES
    assert len(ec.ERROR_CODES) == 20  # matriz de 04 §5: 13 de 1.0 + 7 del modo nodo (C-32)


def test_contract_constants():
    assert ec.ROUTE_FIELDS == ("source", "destination", "metric", "path", "total_cost", "topology_version")
    assert ec.PROPAGATED_CONTROLLER_CODES == {"NODE_NOT_FOUND", "ROUTE_UNREACHABLE"}
    assert ec.DETAILS_FIELD_RENAMES == {"src": "source", "dst": "destination"}
    assert ec.LOG_RECORD_FIELDS[0] == "recorded_at" and len(ec.LOG_RECORD_FIELDS) == 10
