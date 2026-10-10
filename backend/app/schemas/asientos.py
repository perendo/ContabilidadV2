from datetime import date, datetime
from decimal import Decimal
from typing import TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class Paginado[T](BaseModel):
    total: int
    offset: int
    limit: int
    items: list[T]


class ApunteIn(BaseModel):
    cuenta_id: int = Field(gt=0)
    debe: Decimal = Field(default=Decimal("0"), ge=0)
    haber: Decimal = Field(default=Decimal("0"), ge=0)

    @field_validator("debe", "haber")
    @classmethod
    def _dos_decimales(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent < -2:
            raise ValueError("Importes con más de 2 decimales")
        return v


class AsientoRequest(BaseModel):
    fecha: date
    concepto: str = Field(min_length=1, max_length=300)
    apuntes: list[ApunteIn] = Field(min_length=2)

    @field_validator("apuntes")
    @classmethod
    def _una_cara_por_linea(cls, apuntes: list[ApunteIn]) -> list[ApunteIn]:
        for ap in apuntes:
            if (ap.debe > 0) == (ap.haber > 0):
                raise ValueError(
                    "Cada línea exige exactamente un importe (debe o haber) mayor que cero"
                )
        return apuntes


class ApunteOut(BaseModel):
    cuenta_id: int
    cuenta_codigo: str
    debe: Decimal
    haber: Decimal


class AsientoOut(BaseModel):
    id: int
    ejercicio_id: int
    numero: int | None
    fecha: date
    concepto: str
    estado: str
    apuntes: list[ApunteOut]
    creado_por_usuario_id: int | None = None
    asentado_por_usuario_id: int | None = None
    created_at: datetime | None = None
    asentado_at: datetime | None = None
    version: int | None = None
    origen: str | None = None  # auto | manual | importado
    regla_id: int | None = None


class AsientoResumen(BaseModel):
    id: int
    ejercicio_id: int
    numero: int | None
    fecha: date
    concepto: str
    estado: str
    total_debe: Decimal
    total_haber: Decimal
    delta: Decimal | None = None
