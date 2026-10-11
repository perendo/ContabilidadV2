"""Tests del cimiento fiscal (T013): migración, unicidad y helpers compartidos."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import Factura, LineaFacturaIVA
from app.services.fiscales_util import cuantizar2, validar_cif


def test_migracion_aplica_tablas_fiscales(session):
    """La migración crea las 4 tablas fiscales en la BD temporal (T009)."""
    filas = session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    ).scalars().all()
    for tabla in (
        "factura",
        "linea_factura_iva",
        "liquidacion_impuesto_sociedades",
        "fichero_presentacion",
    ):
        assert tabla in filas


def test_unicidad_cif_numero_ejercicio_integrityerror(contexto, session):
    """La BD (backstop FR-006) rechaza duplicado CIF+numero+ejercicio."""
    ctx = contexto()

    def insertar(numero: str, anio_base=2026):
        factura = Factura(
            ejercicio_id=ctx["ejercicio"].id,
            origen="venta",
            numero=numero,
            fecha=date(anio_base, 3, 1),
            tercero_cif="B12345674",
            tercero_razon_social="Cliente SL",
            estado="registrada",
            creado_por_usuario_id=ctx["usuario"].id,
        )
        session.add(factura)
        session.flush()
        return factura

    f1 = insertar("FV-001")
    session.add(
        LineaFacturaIVA(
            factura_id=f1.id,
            numero_linea=1,
            descripcion="Servicio",
            base_imponible=Decimal("1000.00"),
            tipo_iva=Decimal("21.00"),
            cuota_iva=Decimal("210.00"),
        )
    )
    with pytest.raises(IntegrityError):
        insertar("FV-001")
    session.rollback()


def test_mismo_numero_distinto_ejercicio_valido(contexto, session, make_ejercicio):
    """El mismo número en otro ejercicio no está duplicado (Edge Case)."""
    ctx = contexto()
    otro = make_ejercicio(ctx["empresa"].id, anio=2027, estado="abierto")

    def insertar(ejercicio_id: int):
        session.add(
            Factura(
                ejercicio_id=ejercicio_id,
                origen="venta",
                numero="FV-001",
                fecha=date(2026, 3, 1) if ejercicio_id == ctx["ejercicio"].id else date(2027, 3, 1),
                tercero_cif="B12345674",
                tercero_razon_social="Cliente SL",
                estado="registrada",
                creado_por_usuario_id=ctx["usuario"].id,
            )
        )
        session.flush()

    insertar(ctx["ejercicio"].id)
    insertar(otro.id)  # no debe elevar IntegrityError
    session.rollback()


def test_cuantizar2_half_up():
    """Redondeo monetario R5: HALF_UP a 2 decimales."""
    assert cuantizar2(Decimal("0.005")) == Decimal("0.01")
    assert cuantizar2(Decimal("2.345")) == Decimal("2.35")
    assert cuantizar2(Decimal("1.004")) == Decimal("1.00")
    assert cuantizar2(Decimal("-0.005")) == Decimal("-0.01")


def test_validar_cif_casos_limite():
    """validar_cif acepta NIF/CIF correctos y rechaza los demás (FR-017)."""
    assert validar_cif("B12345674") is True
    assert validar_cif("12345678Z") is True
    assert validar_cif("12345678z") is True  # normaliza a mayúsculas
    assert validar_cif("B12345678") is False  # dígito de control incorrecto
    assert validar_cif("12345678") is False
    assert validar_cif("B1234567") is False
    assert validar_cif("ZZZZZZZZZ") is False
    assert validar_cif("") is False
    assert validar_cif(None) is False  # type: ignore[arg-type]