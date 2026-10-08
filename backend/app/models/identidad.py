from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlmodel import Field, SQLModel, Table

__all__ = ["Usuario", "Empresa", "empresa_usuario"]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(nullable=False, max_length=50, unique=True)
    email: str = Field(nullable=False, unique=True)
    hashed_password: str = Field(nullable=False)
    rol: str = Field(default="contable", max_length=20)
    activo: bool = Field(default=True)


class Empresa(SQLModel, table=True):
    __tablename__ = "empresa"

    id: int | None = Field(default=None, primary_key=True)
    cif: str = Field(nullable=False, max_length=9, unique=True)
    razon_social: str = Field(nullable=False, max_length=120)
    nombre_comercial: str | None = Field(default=None, max_length=120)
    activa: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime()))


empresa_usuario = Table(
    "empresausuario",
    SQLModel.metadata,
    Column("usuario_id", Integer, ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True),
    Column("empresa_id", Integer, ForeignKey("empresa.id", ondelete="CASCADE"), primary_key=True),
    Column("rol_especifico", String(20), nullable=True),
)
