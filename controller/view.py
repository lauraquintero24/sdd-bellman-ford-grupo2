"""View del Controller: esquemas Pydantic de entrada y salida HTTP (02 §3.1, §4; 04 §3)."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, PlainSerializer


def _check_node_id(value: str) -> str:
    """IDs no vacíos y sin espacios en los extremos (04 §1)."""
    if value == "" or value != value.strip():
        raise ValueError("el identificador debe ser no vacío y sin espacios en los extremos")
    return value


def decimal_to_text(value: Decimal) -> str:
    """Cadena decimal exacta del valor leído (04 §3.2): notación fija si el exponente ajustado
    está entre −6 y 11; si no, científica con ``e`` minúscula y signo."""
    if -6 <= value.adjusted() <= 11:
        return format(value, "f")
    sign, digits, _ = value.as_tuple()
    text = "".join(map(str, digits))
    mantissa = text[0] + ("." + text[1:] if len(text) > 1 else "")
    exponent = value.adjusted()
    return f"{'-' if sign else ''}{mantissa}e{'+' if exponent >= 0 else '-'}{abs(exponent)}"


NodeId = Annotated[str, AfterValidator(_check_node_id)]
Metric = Literal["delay", "inverse_bandwidth", "loss"]
DecimalText = Annotated[Decimal, PlainSerializer(decimal_to_text, return_type=str)]


class LinkRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    source: NodeId
    target: NodeId


class LinkSchema(BaseModel):
    source: str
    target: str
    delay_ms: DecimalText
    bandwidth_mbps: DecimalText
    loss_probability: DecimalText
    active: bool


class TopologyResponseSchema(BaseModel):
    topology_version: int
    directed: bool
    nodes: list[str]
    links: list[LinkSchema]


class RouteResponseSchema(BaseModel):
    source: str
    destination: str
    metric: str
    path: list[str]
    total_cost: str
    topology_version: int


class LinkStatusSchema(BaseModel):
    source: str
    target: str
    active: bool
    changed: bool
    topology_version: int


class ControllerHealthSchema(BaseModel):
    status: str
    application: str


class ErrorBodySchema(BaseModel):
    code: str
    message: str
    details: dict
