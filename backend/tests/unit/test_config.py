import os
import pytest
from pydantic import ValidationError
from app.config import Settings


def test_settings_sin_jwt_secret_lanza_validation_error(monkeypatch):
    """(a) Settings() sin APP_JWT_SECRET lanza ValidationError."""
    monkeypatch.delenv("APP_JWT_SECRET", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_settings_produccion_secreto_debil_lanza_error(monkeypatch):
    """(b) En environment='production' y secreto débil (<32 chars o 'change-me') lanza ValidationError/ValueError."""
    monkeypatch.setenv("APP_ENVIRONMENT", "production")

    # Caso corto (< 32 caracteres)
    monkeypatch.setenv("APP_JWT_SECRET", "clave-muy-corta")
    with pytest.raises(ValidationError):
        Settings()

    # Caso con 'change-me'
    monkeypatch.setenv("APP_JWT_SECRET", "esta-clave-tiene-mas-de-32-chars-pero-change-me")
    with pytest.raises(ValidationError):
        Settings()


def test_settings_produccion_secreto_valido(monkeypatch):
    """En producción con secreto seguro (>= 32 chars y sin change-me) carga correctamente."""
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    monkeypatch.setenv("APP_JWT_SECRET", "super-secret-key-that-is-at-least-32-characters-long")
    s = Settings()
    assert s.jwt_secret == "super-secret-key-that-is-at-least-32-characters-long"
    assert s.environment == "production"
    assert s.jwt_expires_seconds <= 3600
