from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.seguridad import MIN_PASSWORD_LENGTH, validar_longitud_minima


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str

    @field_validator("password")
    @classmethod
    def _password_minima(cls, v: str) -> str:
        if not validar_longitud_minima(v):
            raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres")
        return v


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    rol: str
    activo: bool


class PerfilOut(UsuarioOut):
    empresas: list[int]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
    usuario: UsuarioOut


class EmpresaIn(BaseModel):
    cif: str = Field(min_length=9, max_length=9)
    razon_social: str = Field(min_length=1, max_length=120)
    nombre_comercial: str | None = Field(default=None, max_length=120)

    @field_validator("cif")
    @classmethod
    def _cif_formato(cls, v: str) -> str:
        if not v.isalnum() or not v.isupper():
            raise ValueError("CIF inválido: 9 caracteres alfanuméricos en mayúsculas")
        return v


class EmpresaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cif: str
    razon_social: str
    nombre_comercial: str | None
    activa: bool
    created_at: datetime


class EjercicioIn(BaseModel):
    anio: int = Field(ge=2000, le=2100)
    fecha_inicio: date
    fecha_fin: date

    @field_validator("fecha_fin")
    @classmethod
    def _orden_fechas(cls, v: date, info) -> date:
        inicio = info.data.get("fecha_inicio")
        if inicio and v <= inicio:
            raise ValueError("fecha_fin debe ser posterior a fecha_inicio")
        return v


class EjercicioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    anio: int
    fecha_inicio: date
    fecha_fin: date
    estado: str
