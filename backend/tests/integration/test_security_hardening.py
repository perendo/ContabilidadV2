"""Tests de regresión de seguridad para Spec 2 (Hardening).
Verifica que todas las vulnerabilidades detectadas quedan blindadas.
"""
from datetime import date
from decimal import Decimal
import pytest
from sqlmodel import Session, select
from app.models import Asiento, Apunte, Empresa
from app.services.seguridad import create_access_token


def test_asentar_asiento_sin_apuntes_retorna_422(contexto, client, session: Session):
    """(T008 / CONT-01) Verifica que un asiento sin apuntes es rechazado por partida doble."""
    ctx = contexto()
    asiento = Asiento(
        ejercicio_id=ctx["ejercicio"].id,
        numero=None,
        fecha=date(2026, 5, 10),
        concepto="Asiento vacío fraudulento",
        estado="borrador",
        creado_por_usuario_id=ctx["usuario"].id,
    )
    session.add(asiento)
    session.commit()
    session.refresh(asiento)

    headers = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }
    resp = client.post(f"/api/v1/asientos/{asiento.id}/asentar", headers=headers)
    assert resp.status_code == 422
    assert "al menos 2" in resp.json()["detail"].lower()


def test_trazabilidad_asiento_creacion_y_asentado(contexto, client, session: Session):
    """(T009 / LEGAL-01) Verifica que se persisten creado_por_id, asentado_por_id y version."""
    ctx = contexto()
    c1 = ctx["cuentas"]["banco"]
    c2 = ctx["cuentas"]["proveedor"]

    headers = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }

    # 1. Crear borrador
    payload = {
        "fecha": "2026-05-10",
        "concepto": "Factura recibida",
        "apuntes": [
            {"cuenta_id": c1.id, "debe": "100.00", "haber": "0.00"},
            {"cuenta_id": c2.id, "debe": "0.00", "haber": "100.00"},
        ],
    }
    r_borrador = client.post("/api/v1/asientos", headers=headers, json=payload)
    assert r_borrador.status_code == 201
    asiento_id = r_borrador.json()["id"]

    asiento_db = session.get(Asiento, asiento_id)
    assert asiento_db.creado_por_usuario_id == ctx["usuario"].id
    assert asiento_db.created_at is not None
    assert asiento_db.asentado_por_usuario_id is None
    assert asiento_db.asentado_at is None
    assert asiento_db.version == 1

    # 2. Asentar
    r_asentar = client.post(f"/api/v1/asientos/{asiento_id}/asentar", headers=headers)
    assert r_asentar.status_code == 200

    session.refresh(asiento_db)
    assert asiento_db.estado == "asentado"
    assert asiento_db.asentado_por_usuario_id == ctx["usuario"].id
    assert asiento_db.asentado_at is not None
    assert asiento_db.version >= 2


def test_empresa_inactiva_retorna_403(contexto, client, session: Session):
    """(T017 / SEC-03) Un usuario vinculado no puede operar en una empresa desactivada."""
    ctx = contexto()
    empresa = session.get(Empresa, ctx["empresa"].id)
    empresa.activa = False
    session.add(empresa)
    session.commit()

    headers = {**ctx["headers"], "X-Empresa-Id": str(empresa.id)}
    resp = client.get("/api/v1/ejercicios", headers=headers)
    assert resp.status_code == 403
    assert "inactiva" in resp.json()["detail"].lower()


def test_usuario_contable_no_puede_crear_ejercicio_403(contexto, client, make_usuario):
    """(T018 / SEC-04) Solo el administrador puede abrir nuevos ejercicios fiscales."""
    ctx = contexto()
    contable = make_usuario("contable_user", rol="contable")
    token = create_access_token(contable.username)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Empresa-Id": str(ctx["empresa"].id),
    }

    payload = {
        "anio": 2028,
        "fecha_inicio": "2028-01-01",
        "fecha_fin": "2028-12-31",
    }
    resp = client.post("/api/v1/ejercicios", headers=headers, json=payload)
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"].lower()


def test_paginacion_utiliza_count_y_limita_items(contexto, client):
    """(T021 / PERF-01) El endpoint paginado devuelve el total y respeta limit."""
    ctx = contexto()
    headers = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }
    resp = client.get("/api/v1/asientos?offset=0&limit=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert len(data["items"]) <= 5


def test_mutacion_con_cookie_sin_cabecera_csrf_rechazada(contexto, client):
    """(T025 / SEC-02) Mutación usando solo cookie sin cabecera CSRF debe ser rechazada con 403."""
    ctx = contexto()
    token = create_access_token(ctx["usuario"].username)
    client.cookies.set("access_token", token)

    # Intento de mutación SIN cabecera X-Requested-With ni Bearer
    resp = client.post(
        "/api/v1/cuentas",
        headers={"X-Ejercicio-Id": str(ctx["ejercicio"].id), "X-Empresa-Id": str(ctx["empresa"].id)},
        json={"codigo": "572009", "nombre": "Banco Sec", "nivel": 4},
    )
    assert resp.status_code == 403
    assert "csrf" in resp.json()["detail"].lower()

    # Intento de mutación CON cabecera X-Requested-With: XMLHttpRequest
    resp_ok = client.post(
        "/api/v1/cuentas",
        headers={
            "X-Ejercicio-Id": str(ctx["ejercicio"].id),
            "X-Empresa-Id": str(ctx["empresa"].id),
            "X-Requested-With": "XMLHttpRequest",
        },
        json={"codigo": "572009", "nombre": "Banco Sec", "nivel": 4},
    )
    assert resp_ok.status_code == 201


def test_health_no_expone_detalles_internos(client):
    """(T026 / SEC-06) El endpoint /health devuelve solo {'status': 'ok'}."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "ok"}
    assert "db" not in body
    assert "busy_timeout" not in body
    assert "foreign_keys" not in body
    assert "migrations" not in body
