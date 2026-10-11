"""Schemas de la Liquidación del Impuesto sobre Sociedades (spec 005)."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["AjusteIS", "LiquidacionISIn", "LiquidacionISOut"]


class AjusteIS(BaseModel):
    concepto: str = Field(min_length=1, max_length=200)
    sentido: Literal["aumento", "disminucion"]
    importe: Decimal = Field(gt=0)

    @field_validator("importe")
    @classmethod
    def _dos_decimales(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent < -2:
            raise ValueError("Importe con más de 2 decimales")
        return v


class LiquidacionISIn(BaseModel):
    resultado_contable: Decimal
    ajustes: list[AjusteIS] = Field(default_factory=list)
    tipo_gravamen: Decimal = Field(default=Decimal("25.00"), gt=0)
    retenciones_pagos_cuenta: Decimal = Field(default=Decimal("0"), ge=0)

    @field_validator("resultado_contable", "retenciones_pagos_cuenta")
    @classmethod
    def _dos_decimales(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent < -2:
            raise ValueError("Importe con más de 2 decimales")
        return v

    @field_validator("tipo_gravamen")
    @classmethod
    def _tipo_ok(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent < -2:
            raise ValueError("Tipo de gravamen con más de 2 decimales")
        return v

    @field_validator("retenciones_pagos_cuenta")
    @classmethod
    def _no_negativas(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Las retenciones no pueden ser negativas")
        return v


class LiquidacionISOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ejercicio_id: int
    resultado_contable: Decimal
    ajustes: list[AjusteIS] = []
    tipo_gravamen: Decimal
    retenciones_pagos_cuenta: Decimal
    base_imponible: Decimal | None = None
    cuota_integra: Decimal | None = None
    cuota_diferencial: Decimal | None = None
    estado: str
    asiento_id: int | None = None
    creado_por_usuario_id: int | None = None
    cerrado_por_usuario_id: int | None = None
    created_at: datetime | None = None
    cerrado_at: datetime | None = None