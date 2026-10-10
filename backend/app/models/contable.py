from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric
from sqlalchemy.schema import UniqueConstraint
from sqlmodel import Field, SQLModel

__all__ = [
    "Ejercicio",
    "Cuenta",
    "Asiento",
    "Apunte",
    "MovimientoBanco",
    "ReglaBanco",
    "LogProcesamientoBanco",
]


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

    # Trazabilidad conciliación bancaria (Spec 4)
    origen: str | None = Field(default=None, max_length=20)  # auto | manual | importado
    regla_id: int | None = Field(
        default=None,
        sa_column=Column(
            "regla_id", ForeignKey("regla_banco.id", ondelete="SET NULL"), nullable=True
        ),
    )


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


class MovimientoBanco(SQLModel, table=True):
    __tablename__ = "movimiento_banco"
    __table_args__ = (
        UniqueConstraint(
            "ejercicio_id", "hash_unicidad", name="uq_movimiento_banco_ejercicio_hash"
        ),
        Index("ix_movimiento_banco_ejercicio_procesado", "ejercicio_id", "procesado"),
        Index("ix_movimiento_banco_ejercicio_fecha_valor", "ejercicio_id", "fecha_valor"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ejercicio_id: int = Field(
        sa_column=Column(
            "ejercicio_id", ForeignKey("ejercicio.id", ondelete="CASCADE"), nullable=False
        )
    )
    fecha_operacion: date = Field(nullable=False)
    fecha_valor: date = Field(nullable=False)
    concepto: str = Field(nullable=False, max_length=500)
    referencia: str | None = Field(default=None, max_length=100)
    referencia_2: str | None = Field(default=None, max_length=100)
    importe: Decimal = Field(sa_column=Column(Numeric(19, 2), nullable=False))
    saldo: Decimal = Field(sa_column=Column(Numeric(19, 2), nullable=False))
    divisa: str = Field(default="EUR", max_length=3)
    codigo_banco: str | None = Field(default=None, max_length=10)
    numero_documento: str | None = Field(default=None, max_length=50)
    info_adicional: str | None = Field(default=None, max_length=500)
    procesado: bool = Field(default=False)
    asiento_id: int | None = Field(
        default=None,
        sa_column=Column("asiento_id", ForeignKey("asiento.id", ondelete="SET NULL"), nullable=True)
    )
    regla_id: int | None = Field(
        default=None,
        sa_column=Column(
            "regla_id", ForeignKey("regla_banco.id", ondelete="SET NULL"), nullable=True
        ),
    )
    hash_unicidad: str = Field(max_length=64)
    origen_archivo: str = Field(max_length=20)  # excel | csv | csb


class ReglaBanco(SQLModel, table=True):
    __tablename__ = "regla_banco"
    __table_args__ = (
        Index("ix_regla_banco_empresa_activa", "empresa_id", "activa"),
    )

    id: int | None = Field(default=None, primary_key=True)
    empresa_id: int = Field(
        sa_column=Column(
            "empresa_id", ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False
        )
    )
    nombre: str = Field(max_length=100)
    patron_regex: str = Field(max_length=200)
    cuenta_debe: str = Field(max_length=10)
    cuenta_haber: str = Field(max_length=10)
    importe_fijo: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(19, 2), nullable=True)
    )
    porcentaje: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(5, 2), nullable=True)
    )
    prioridad: int = Field(default=0)
    auto_asentar: bool = Field(default=False)
    activa: bool = Field(default=True)


class LogProcesamientoBanco(SQLModel, table=True):
    __tablename__ = "log_procesamiento_banco"
    __table_args__ = (
        Index("ix_log_procesamiento_ejercicio_fecha", "ejercicio_id", "timestamp"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ejercicio_id: int = Field(
        sa_column=Column(
            "ejercicio_id", ForeignKey("ejercicio.id", ondelete="CASCADE"), nullable=False
        )
    )
    usuario_id: int = Field(
        sa_column=Column(
            "usuario_id", ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False
        )
    )
    timestamp: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    reglas_aplicadas_json: str = Field()  # JSON array de IDs de reglas
    creados: int = Field(default=0)
    pendientes: int = Field(default=0)
    fallidos_json: str = Field()  # JSON array de objetos con error
