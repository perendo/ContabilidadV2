from functools import lru_cache
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", str(_BACKEND_DIR / ".env"), str(_ROOT_DIR / ".env")),
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
    )

    database_url: str = "sqlite:///./contabilidadv2.db"
    jwt_secret: str  # Obligatorio, sin valor por defecto
    jwt_algorithm: str = "HS256"
    jwt_expires_seconds: int = 3600  # Máximo 1 hora
    environment: str = "development"
    rate_limit_login: str = "5/minute"
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        if self.environment == "production":
            if not self.jwt_secret or len(self.jwt_secret) < 32:
                raise ValueError("APP_JWT_SECRET debe tener al menos 32 caracteres en producción")
            if "change-me" in self.jwt_secret.lower():
                raise ValueError("APP_JWT_SECRET no puede contener 'change-me' en producción")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
