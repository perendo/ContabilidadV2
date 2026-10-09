from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric
from sqlalchemy.schema import UniqueConstraint
from sqlmodel import Field, SQLModel

__all__ = ["Ejercicio", "Cuenta", "Asiento", "Apunte"]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Ejercicio(SQLModel, table=True):
    __tablename__ = "ejercicio"
    __table_args__ = (UniqueConstraint("empresa_id", "anio", name="uq_ejercicio_empresa_anio"),)

    id: int | None = Field(default=None, primary_key=True)
    empresa_id: int = Field(
        sa_column=Column(
            "empresa_id", ForeignKey("empresa.id", ondelete="RESTRICT"), nullable=False
        )
    )
    anio: int = Field(nullable=False)
    fecha_inicio: date = Field(nullable=False)
    fecha_fin: date = Field(nullable=False)
    estado: str = Field(default="abierto", max_length=20)


class Cuenta(SQLModel, table=True):
    __tablename__ = "cuenta"
    __table_args__ = (
        UniqueConstraint("ejercicio_id", "codigo", name="uq_cuenta_ejercicio_codigo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ejercicio_id: int = Field(
        sa_column=Column(
            "ejercicio_id", ForeignKey("ejercicio.id", ondelete="CASCADE"), nullable=False
        )
    )
    codigo: str = Field(nullable=False, max_length=10)
    nombre: str = Field(nullable=False, max_length=200)
    nivel: int = Field(nullable=False)


class Asiento(SQLModel, table=True):
    __tablename__ = "asiento"
    __table_args__ = (
        UniqueConstraint("ejercicio_id", "numero", name="uq_asiento_ejercicio_numero"),
        Index("ix_asiento_ejercicio_estado_fecha", "ejercicio_id", "estado", "fecha"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ejercicio_id: int = Field(
        sa_column=Column(
            "ejercicio_id", ForeignKey("ejercicio.id", ondelete="RESTRICT"), nullable=False
        )
    )
    numero: int | None = Field(default=None)
    fecha: date = Field(nullable=False)
    concepto: str = Field(nullable=False, max_length=300)
    estado: str = Field(default="borrador", max_length=20)

    # Trazabilidad legal y control de concurrencia (Spec 2 - LEGAL-01 / CONC-01)
    creado_por_usuario_id: int = Field(
        sa_column=Column(
            "creado_por_usuario_id", ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False
        )
    )
    asentado_por_usuario_id: int | None = Field(
        default=None,
        sa_column=Column(
            "asentado_por_usuario_id", ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=True
        ),
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    asentado_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    version: int = Field(default=1, nullable=False)


class Apunte(SQLModel, table=True):
    __tablename__ = "apunte"

    id: int | None = Field(default=None, primary_key=True)
    asiento_id: int = Field(
        sa_column=Column("asiento_id", ForeignKey("asiento.id", ondelete="CASCADE"), nullable=False)
    )
    cuenta_id: int = Field(
        sa_column=Column("cuenta_id", ForeignKey("cuenta.id", ondelete="RESTRICT"), nullable=False)
    )
    debe: Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(19, 2), nullable=False))
    haber: Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(19, 2), nullable=False))
