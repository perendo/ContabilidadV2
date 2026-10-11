"""Schemas de Presentación AEAT (vista + fichero de posiciones fijas, spec 005)."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

__all__ = [
    "CasillaPresentacion",
    "BloqueDescarga",
    "PresentacionVista",
    "FicheroOut",
]


class CasillaPresentacion(BaseModel):
    casilla: int
    label: str
    importe: Decimal


class BloqueDescarga(BaseModel):
    habilitado: bool
    motivo: str | None = None


class PresentacionVista(BaseModel):
    modelo: str
    periodo: str
    cerrada: bool
    resumen: dict[str, Any]
    casillas: list[CasillaPresentacion]
    bloque_descarga: BloqueDescarga


class FicheroOut(BaseModel):
    modelo: str
    periodo: str
    ruta: str
    hash_sha256: str
    generado_por_usuario_id: int
    generado_at: datetime