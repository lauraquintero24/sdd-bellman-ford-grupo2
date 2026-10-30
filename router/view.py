"""View del Router: esquemas Pydantic de entrada y salida HTTP (02 §3.2, §4; 04 §4)."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict


def _check_id(value: str) -> str:
    """Identificadores no vacíos y sin espacios en los extremos (04 §1)."""
    if value == "" or value != value.strip():
        raise ValueError("el identificador debe ser no vacío y sin espacios en los extremos")
    return value


Identifier = Annotated[str, AfterValidator(_check_id)]
Metric = Literal["delay", "inverse_bandwidth", "loss"]


class PacketRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    packet_id: Identifier
    source: Identifier
    destination: Identifier
    payload: str = ""
    metric: Metric


class RouteSchema(BaseModel):
    source: str
    destination: str
    metric: str
    path: list[str]
    total_cost: str
    topology_version: int


class TraceHopSchema(BaseModel):
    hop_index: int
    node: str


class ForwardingResponseSchema(BaseModel):
    packet_id: str
    status: str
    route: RouteSchema
    trace: list[TraceHopSchema]
    topology_version: int


class RouterHealthSchema(BaseModel):
    status: str
    application: str


class ErrorBodySchema(BaseModel):
    code: str
    message: str
    details: dict


class PacketErrorSchema(BaseModel):
    packet_id: str
    status: str
    trace: list[TraceHopSchema]
    error: ErrorBodySchema
