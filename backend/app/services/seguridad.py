from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import get_settings

_ph = PasswordHasher()
MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except (VerifyMismatchError, TypeError, ValueError):
        return False


def validar_longitud_minima(password: str) -> bool:
    return len(password) >= MIN_PASSWORD_LENGTH


def create_access_token(username: str, expires_seconds: int | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expiry = expires_seconds or settings.jwt_expires_seconds
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(seconds=expiry),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
