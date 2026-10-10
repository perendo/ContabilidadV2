from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CuentaRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nombre: str
    nivel: int


class MovimientoMayor(BaseModel):
    fecha: date
    numero: int
    asiento_id: int
    concepto: str
    debe: Decimal = Field(decimal_places=2)
    haber: Decimal = Field(decimal_places=2)
    saldo: Decimal = Field(decimal_places=2)


class FilaBalance(BaseModel):
    codigo: str
    nombre: str
    nivel: int
    suma_debe: Decimal = Field(decimal_places=2)
    suma_haber: Decimal = Field(decimal_places=2)
    saldo_deudor: Decimal = Field(decimal_places=2)
    saldo_acreedor: Decimal = Field(decimal_places=2)


class FilaMayorCuenta(BaseModel):
    codigo: str
    nombre: str
    nivel: int
    suma_debe: Decimal = Field(decimal_places=2)
    suma_haber: Decimal = Field(decimal_places=2)
    saldo: Decimal = Field(decimal_places=2)
    saldo_tipo: Literal["deudor", "acreedor", "cero"]


class MayorCuentaOut(BaseModel):
    cuenta: CuentaRef
    desde: date | None
    hasta: date | None
    saldo_inicial: Decimal = Field(decimal_places=2)
    movimientos: list[MovimientoMayor]
    total_debe: Decimal = Field(decimal_places=2)
    total_haber: Decimal = Field(decimal_places=2)
    saldo_final: Decimal = Field(decimal_places=2)


class MayorGlobalOut(BaseModel):
    ejercicio_id: int
    desde: date | None
    hasta: date | None
    cuentas: list[FilaMayorCuenta]


class BalanceOut(BaseModel):
    ejercicio_id: int
    desde: date | None
    hasta: date | None
    filas: list[FilaBalance]
    total_debe: Decimal = Field(decimal_places=2)
    total_haber: Decimal = Field(decimal_places=2)
    total_saldo_deudor: Decimal = Field(decimal_places=2)
    total_saldo_acreedor: Decimal = Field(decimal_places=2)
    cuadra: bool