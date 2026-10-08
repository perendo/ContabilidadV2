from pydantic import BaseModel, Field, field_validator


class CuentaIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=10)
    nombre: str = Field(min_length=1, max_length=200)
    nivel: int = Field(ge=1, le=5)

    @field_validator("codigo")
    @classmethod
    def _codigo_digitos(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("El código de cuenta solo admite dígitos")
        return v


class CuentaOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    ejercicio_id: int
    codigo: str
    nombre: str
    nivel: int
