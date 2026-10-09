"""Tests de regresión de seguridad para Spec 2 (Hardening).
Verifica que las vulnerabilidades detectadas en la auditoría quedan resueltas.
"""
from datetime import date
from decimal import Decimal
from sqlmodel import Session
from app.models import Asiento, Apunte, Empresa
from app.services.seguridad import create_access_token


def test_asentar_asiento_sin_apuntes_retorna_422(contexto, client, session: Session):
    """(CONT-01) Verifica que un asiento sin apuntes es rechazado por partida doble."""
    ctx = contexto()
    asiento = Asiento(
        ejercicio_id=ctx["ejercicio"].id,
        numero=None,
        fecha=date(2026, 5, 10),
        concepto="Asiento vacío fraudulento",
        estado="borrador",
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


def test_empresa_inactiva_retorna_403(contexto, client, session: Session):
    """(SEC-03) Un usuario vinculado no puede operar en una empresa desactivada."""
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
    """(SEC-04) Solo el administrador puede abrir nuevos ejercicios fiscales."""
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
    """(PERF-01) El endpoint paginado devuelve el total y respeta limit."""
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
