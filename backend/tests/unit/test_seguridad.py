import jwt
import pytest

from app.services.seguridad import (
    create_access_token,
    decode_access_token,
    hash_password,
    validar_longitud_minima,
    verify_password,
)


def test_hash_y_verify_password():
    hashed = hash_password("secreto-123")
    assert hashed != "secreto-123"
    assert verify_password(hashed, "secreto-123")
    assert not verify_password(hashed, "otra-cosa")


def test_longitud_minima():
    assert validar_longitud_minima("12345678")
    assert not validar_longitud_minima("1234567")


def test_jwt_roundtrip():
    token = create_access_token("contable1")
    payload = decode_access_token(token)
    assert payload["sub"] == "contable1"


def test_jwt_expirado_rechazado():
    token = create_access_token("contable1", expires_seconds=-10)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)
