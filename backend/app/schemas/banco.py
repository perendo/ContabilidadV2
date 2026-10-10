from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MovimientoBancoIn(BaseModel):
    fecha_operacion: date
    fecha_valor: date
    concepto: str = Field(max_length=500)
    referencia: str | None = Field(default=None, max_length=100)
    referencia_2: str | None = Field(default=None, max_length=100)
    importe: Decimal = Field(decimal_places=2)
    saldo: Decimal = Field(decimal_places=2)
    divisa: str = Field(default="EUR", max_length=3)
    codigo_banco: str | None = Field(default=None, max_length=10)
    numero_documento: str | None = Field(default=None, max_length=50)
    info_adicional: str | None = Field(default=None, max_length=500)
    hash_unicidad: str = Field(max_length=64)
    origen_archivo: Literal["excel", "csv", "csb"]


class MovimientoBancoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ejercicio_id: int
    fecha_operacion: date
    fecha_valor: date
    concepto: str
    referencia: str | None
    referencia_2: str | None
    importe: Decimal
    saldo: Decimal
    divisa: str
    codigo_banco: str | None
    numero_documento: str | None
    info_adicional: str | None
    procesado: bool
    asiento_id: int | None
    regla_id: int | None
    hash_unicidad: str
    origen_archivo: str


class ReglaBancoIn(BaseModel):
    nombre: str = Field(max_length=100)
    patron_regex: str = Field(max_length=200)
    cuenta_debe: str = Field(max_length=10)
    cuenta_haber: str = Field(max_length=10)
    importe_fijo: Decimal | None = Field(default=None, decimal_places=2)
    porcentaje: Decimal | None = Field(default=None, decimal_places=2)
    prioridad: int = Field(default=0, ge=0)
    auto_asentar: bool = False
    activa: bool = True


class ReglaBancoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    nombre: str
    patron_regex: str
    cuenta_debe: str
    cuenta_haber: str
    importe_fijo: Decimal | None
    porcentaje: Decimal | None
    prioridad: int
    auto_asentar: bool
    activa: bool


class ImportRequest(BaseModel):
    ignorar_duplicados: bool = False


class ImportResponse(BaseModel):
    importados: int
    duplicados: int
    errores: list[str]
    formato_detectado: Literal["excel", "csv", "csb"]


class MatchItem(BaseModel):
    movimiento_id: int
    fecha_operacion: date
    fecha_valor: date
    concepto: str
    importe: Decimal
    saldo: Decimal
    cuenta_debe: str
    cuenta_haber: str
    importe_calculado: Decimal


class SimularResponse(BaseModel):
    matches: list[MatchItem]


class ProcesarResponse(BaseModel):
    creados: int
    pendientes: int
    fallidos: list[dict]
    log_id: int


class LogProcesamientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ejercicio_id: int
    usuario_id: int
    timestamp: datetime
    reglas_aplicadas_json: str
    creados: int
    pendientes: int
    fallidos_json: str