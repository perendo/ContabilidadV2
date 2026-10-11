"""Modelos de los módulos fiscales (spec 005): facturas con IVA/retenciones,
liquidación del Impuesto sobre Sociedades y trazabilidad de ficheros AEAT.

Enums persistidos como `String` (patrón del proyecto); importes siempre
`Decimal` sobre `Numeric(19,2)` (FR-022).
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric
from sqlalchemy.schema import UniqueConstraint
from sqlmodel import Field, SQLModel

__all__ = [
    "OrigenFactura",
    "TipoRetencion",
    "EstadoFactura",
    "EstadoLiquidacionIS",
    "Factura",
    "LineaFacturaIVA",
    "LiquidacionImpuestoSociedades",
    "FicheroPresentacion",
]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class OrigenFactura(StrEnum):
    venta = "venta"
    compra = "compra"


class TipoRetencion(StrEnum):
    modelo_111 = "111"
    modelo_115 = "115"


class EstadoFactura(StrEnum):
    registrada = "registrada"
    anulada = "anulada"


class EstadoLiquidacionIS(StrEnum):
    borrador = "borrador"
    cerrada = "cerrada"


class Factura(SQLModel, table=True):
    __tablename__ = "factura"
    __table_args__ = (
        UniqueConstraint(
            "ejercicio_id", "tercero_cif", "numero", name="uq_factura_ejercicio_cif_numero"
        ),
        Index("ix_factura_ejercicio_fecha", "ejercicio_id", "fecha"),
        Index("ix_factura_ejercicio_origen", "ejercicio_id", "origen"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ejercicio_id: int = Field(
        sa_column=Column(
            "ejercicio_id", ForeignKey("ejercicio.id", ondelete="RESTRICT"), nullable=False
        )
    )
    origen: str = Field(nullable=False, max_length=10)
    numero: str = Field(nullable=False, max_length=50)
    fecha: date = Field(nullable=False)
    fecha_operacion: date | None = Field(default=None)
    tercero_cif: str = Field(nullable=False, max_length=9)
    tercero_razon_social: str = Field(nullable=False, max_length=200)
    solo_identificativo: bool = Field(default=False)
    tipo_retencion: str | None = Field(default=None, max_length=3)
    estado: str = Field(default=EstadoFactura.registrada.value, max_length=20)
    notas: str | None = Field(default=None, max_length=1000)
    asiento_id: int | None = Field(
        default=None,
        sa_column=Column(
            "asiento_id", ForeignKey("asiento.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    creado_por_usuario_id: int = Field(
        sa_column=Column(
            "creado_por_usuario_id", ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False
        )
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class LineaFacturaIVA(SQLModel, table=True):
    __tablename__ = "linea_factura_iva"
    __table_args__ = (Index("ix_linea_factura_factura", "factura_id"),)

    id: int | None = Field(default=None, primary_key=True)
    factura_id: int = Field(
        sa_column=Column(
            "factura_id", ForeignKey("factura.id", ondelete="CASCADE"), nullable=False
        )
    )
    numero_linea: int = Field(nullable=False)
    descripcion: str = Field(nullable=False, max_length=300)
    base_imponible: Decimal = Field(sa_column=Column(Numeric(19, 2), nullable=False))
    tipo_iva: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    cuota_iva: Decimal = Field(sa_column=Column(Numeric(19, 2), nullable=False))
    tipo_re: Decimal | None = Field(default=None, sa_column=Column(Numeric(5, 2), nullable=True))
    cuota_re: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(19, 2), nullable=True)
    )
    operacion_exenta: bool = Field(default=False)
    base_retencion: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(19, 2), nullable=True)
    )
    pct_retencion: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(5, 2), nullable=True)
    )
    cuota_retencion: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(19, 2), nullable=True)
    )


class LiquidacionImpuestoSociedades(SQLModel, table=True):
    __tablename__ = "liquidacion_impuesto_sociedades"
    __table_args__ = (UniqueConstraint("ejercicio_id", name="uq_lis_ejercicio"),)

    id: int | None = Field(default=None, primary_key=True)
    ejercicio_id: int = Field(
        sa_column=Column(
            "ejercicio_id", ForeignKey("ejercicio.id", ondelete="RESTRICT"), nullable=False
        )
    )
    resultado_contable: Decimal = Field(sa_column=Column(Numeric(19, 2), nullable=False))
    ajustes_json: str = Field(nullable=False, max_length=12000)
    tipo_gravamen: Decimal = Field(default=Decimal("25.00"), sa_column=Column(Numeric(5, 2)))
    retenciones_pagos_cuenta: Decimal = Field(
        default=Decimal("0"), sa_column=Column(Numeric(19, 2), nullable=False)
    )
    base_imponible: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(19, 2), nullable=True)
    )
    cuota_integra: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(19, 2), nullable=True)
    )
    cuota_diferencial: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(19, 2), nullable=True)
    )
    estado: str = Field(default=EstadoLiquidacionIS.borrador.value, max_length=20)
    asiento_id: int | None = Field(
        default=None,
        sa_column=Column(
            "asiento_id", ForeignKey("asiento.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    creado_por_usuario_id: int = Field(
        sa_column=Column(
            "creado_por_usuario_id", ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False
        )
    )
    cerrado_por_usuario_id: int | None = Field(
        default=None,
        sa_column=Column(
            "cerrado_por_usuario_id", ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    cerrado_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


class FicheroPresentacion(SQLModel, table=True):
    __tablename__ = "fichero_presentacion"
    __table_args__ = (
        UniqueConstraint(
            "ejercicio_id", "modelo", "periodo", name="uq_fichero_ejercicio_modelo_periodo"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    ejercicio_id: int = Field(
        sa_column=Column(
            "ejercicio_id", ForeignKey("ejercicio.id", ondelete="RESTRICT"), nullable=False
        )
    )
    modelo: str = Field(nullable=False, max_length=3)
    periodo: str = Field(nullable=False, max_length=8)
    ruta: str = Field(nullable=False, max_length=255)
    hash_sha256: str = Field(nullable=False, max_length=64)
    generado_por_usuario_id: int = Field(
        sa_column=Column(
            "generado_por_usuario_id",
            ForeignKey("usuario.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    generado_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )