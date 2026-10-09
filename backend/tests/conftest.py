import os
import tempfile
from datetime import date

import pytest

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["APP_DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"
os.environ["APP_JWT_SECRET"] = "test-secret-key-32-chars-long-for-testing-only-12345"
os.environ["APP_ENVIRONMENT"] = "development"

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.db import engine, get_session
from app.main import app
from app.models import Ejercicio, Empresa, Usuario, empresa_usuario
from app.services.seguridad import create_access_token, hash_password

get_settings.cache_clear()

_alembic_cfg = Config("alembic.ini")
command.upgrade(_alembic_cfg, "head")


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def session():
    with next(get_session()) as s:
        yield s


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as conn:
        for table in (
            "apunte",
            "asiento",
            "cuenta",
            "ejercicio",
            "empresausuario",
            "empresa",
            "usuario",
        ):
            conn.execute(text(f"DELETE FROM {table}"))


def auth_headers(usuario: Usuario) -> dict[str, str]:
    token = create_access_token(usuario.username)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_usuario(session):
    def _make(username="contable1", rol="contable", activo=True) -> Usuario:
        usuario = Usuario(
            username=username,
            email=f"{username}@example.es",
            hashed_password=hash_password("secreto-123"),
            rol=rol,
            activo=activo,
        )
        session.add(usuario)
        session.commit()
        session.refresh(usuario)
        return usuario

    return _make


@pytest.fixture()
def make_empresa(session):
    def _make(creador: Usuario, cif="B12345678", razon_social="Acme SL", nombre="Acme") -> Empresa:
        empresa = Empresa(cif=cif, razon_social=razon_social, nombre_comercial=nombre)
        session.add(empresa)
        session.flush()
        session.execute(
            empresa_usuario.insert().values(
                usuario_id=creador.id, empresa_id=empresa.id, rol_especifico="admin"
            )
        )
        session.commit()
        session.refresh(empresa)
        return empresa

    return _make


@pytest.fixture()
def make_ejercicio(session):
    def _make(empresa_id: int, anio=2026, estado="abierto") -> Ejercicio:
        ejercicio = Ejercicio(
            empresa_id=empresa_id,
            anio=anio,
            fecha_inicio=date(anio, 1, 1),
            fecha_fin=date(anio, 12, 31),
            estado=estado,
        )
        session.add(ejercicio)
        session.commit()
        session.refresh(ejercicio)
        return ejercicio

    return _make


@pytest.fixture()
def make_cuenta(session):
    def _make(ejercicio_id: int, codigo="57200001", nombre="Bancos c/c", nivel=4):
        from app.models import Cuenta

        cuenta = Cuenta(ejercicio_id=ejercicio_id, codigo=codigo, nombre=nombre, nivel=nivel)
        session.add(cuenta)
        session.commit()
        session.refresh(cuenta)
        return cuenta

    return _make


@pytest.fixture()
def contexto(session, make_usuario, make_empresa, make_ejercicio, make_cuenta):
    """Empresa + ejercicio abierto + cuentas de ejemplo para endpoints de negocio."""

    def _build(username="contable1", cif="B12345678"):
        usuario = make_usuario(username)
        empresa = make_empresa(usuario, cif=cif)
        ejercicio = make_ejercicio(empresa.id)
        c_in = make_cuenta(ejercicio.id, "57200001", "Bancos c/c", 4)
        c_out = make_cuenta(ejercicio.id, "41000000", "Proveedores", 4)
        c_caja = make_cuenta(ejercicio.id, "57000000", "Caja", 4)
        return {
            "usuario": usuario,
            "headers": auth_headers(usuario),
            "empresa": empresa,
            "ejercicio": ejercicio,
            "cuentas": {"banco": c_in, "proveedor": c_out, "caja": c_caja},
        }

    return _build
