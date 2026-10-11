"""Schemas de facturas, Libros Registro de IVA y Retenciones (spec 005)."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "LineaFacturaIVAIn",
    "FacturaIn",
    "LineaFacturaIVAOut",
    "FacturaOut",
    "FacturaResumen",
    "LibroIVARow",
    "TotalPorTipo",
    "LibroIVAResponse",
    "ResumenRetencionItem",
    "RetencionesResponse",
    "FacturasPaginado",
]


def _dos_decimales(v: Decimal) -> Decimal:
    if v.as_tuple().exponent < -2:
        raise ValueError("Importe con más de 2 decimales")
    return v


class LineaFacturaIVAIn(BaseModel):
    numero_linea: int = Field(ge=1)
    descripcion: str = Field(min_length=1, max_length=300)
    base_imponible: Decimal = Field(ge=0)
    tipo_iva: Decimal = Field(ge=0)
    cuota_iva: Decimal | None = Field(default=None, ge=0)
    tipo_re: Decimal | None = Field(default=None, ge=0)
    cuota_re: Decimal | None = Field(default=None, ge=0)
    operacion_exenta: bool = False
    base_retencion: Decimal | None = Field(default=None, ge=0)
    pct_retencion: Decimal | None = Field(default=None, ge=0, le=100)
    cuota_retencion: Decimal | None = Field(default=None, ge=0)

    @field_validator("base_imponible", "cuota_iva", "cuota_re", "base_retencion", "cuota_retencion")
    @classmethod
    def _decimales_ok(cls, v: Decimal | None) -> Decimal | None:
        if v is not None:
            return _dos_decimales(v)
        return v

    @field_validator("tipo_iva", "tipo_re", "pct_retencion")
    @classmethod
    def _porcentaje_ok(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v.as_tuple().exponent < -2:
            raise ValueError("Porcentaje con más de 2 decimales")
        return v


class FacturaIn(BaseModel):
    origen: Literal["venta", "compra"]
    numero: str = Field(min_length=1, max_length=50)
    fecha: date
    fecha_operacion: date | None = None
    tercero_cif: str = Field(min_length=9, max_length=9)
    tercero_razon_social: str = Field(min_length=1, max_length=200)
    solo_identificativo: bool = False
    tipo_retencion: Literal["111", "115"] | None = None
    notas: str | None = Field(default=None, max_length=1000)
    lineas: list[LineaFacturaIVAIn] = Field(min_length=1)


class LineaFacturaIVAOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_linea: int
    descripcion: str
    base_imponible: Decimal
    tipo_iva: Decimal
    cuota_iva: Decimal
    tipo_re: Decimal | None = None
    cuota_re: Decimal | None = None
    operacion_exenta: bool
    base_retencion: Decimal | None = None
    pct_retencion: Decimal | None = None
    cuota_retencion: Decimal | None = None


class FacturaOut(BaseModel):
    id: int
    ejercicio_id: int
    origen: str
    numero: str
    fecha: date
    fecha_operacion: date | None = None
    tercero_cif: str
    tercero_razon_social: str
    solo_identificativo: bool
    tipo_retencion: str | None = None
    estado: str
    notas: str | None = None
    asiento_id: int | None = None
    creado_por_usuario_id: int
    created_at: date | None = None
    lineas: list[LineaFacturaIVAOut] = []


class FacturaResumen(BaseModel):
    id: int
    origen: str
    numero: str
    fecha: date
    tercero_cif: str
    tercero_razon_social: str
    tipo_retencion: str | None = None
    estado: str
    asiento_id: int | None = None


class FacturasPaginado(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[FacturaResumen]


# ---------------------------------------------------------------------------
# Libro Registro de IVA (FR-009…011)
# ---------------------------------------------------------------------------


class LibroIVARow(BaseModel):
    fecha: date
    numero: str
    tercero_cif: str
    tercero_razon_social: str
    base_imponible: Decimal
    tipo_iva: Decimal
    cuota_iva: Decimal
    total: Decimal
    asiento_id: int | None = None


class TotalPorTipo(BaseModel):
    tipo_iva: Decimal
    base: Decimal
    cuota: Decimal


class LibroIVAResponse(BaseModel):
    origen: str
    desde: date
    hasta: date
    operaciones: list[LibroIVARow]
    totales_por_tipo: list[TotalPorTipo]
    total_base: Decimal
    total_cuota: Decimal


# ---------------------------------------------------------------------------
# Resumen de retenciones por perceptor (FR-016/017)
# ---------------------------------------------------------------------------


class ResumenRetencionItem(BaseModel):
    tercero_cif: str
    tercero_razon_social: str
    base_retencion: Decimal
    cuota_retencion: Decimal
    numero_facturas: int


class RetencionesResponse(BaseModel):
    tipo: str
    desde: date
    hasta: date
    por_perceptor: list[ResumenRetencionItem]
    total_base: Decimal
    total_retencion: Decimal