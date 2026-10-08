from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    database_url: str = "sqlite:///./contabilidadv2.db"
    jwt_secret: str = "dev-only-secret-0123456789abcdef-change-me"  # noqa: S105
    jwt_algorithm: str = "HS256"
    jwt_expires_seconds: int = 43200
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
