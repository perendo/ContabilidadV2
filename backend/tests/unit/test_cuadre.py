from decimal import Decimal

import pytest

from app.services.asientos import calcular_delta, validar_lineas

CUENTA_A = 1
CUENTA_B = 2


def test_delta_cero_conjunto_cuadrado():
    apuntes = [
        {"cuenta_id": CUENTA_A, "debe": Decimal("1000.00"), "haber": Decimal("0")},
        {"cuenta_id": CUENTA_B, "debe": Decimal("600.00"), "haber": Decimal("0")},
        {"cuenta_id": CUENTA_A, "debe": Decimal("0"), "haber": Decimal("1600.00")},
    ]
    assert calcular_delta(apuntes) == Decimal("0")


def test_delta_descuadre_por_conjunto():
    apuntes = [
        {"cuenta_id": CUENTA_A, "debe": Decimal("1000.00"), "haber": Decimal("0")},
        {"cuenta_id": CUENTA_B, "debe": Decimal("0"), "haber": Decimal("900.00")},
    ]
    assert calcular_delta(apuntes) == Decimal("100.00")


def test_delta_por_conjunto_no_por_pares():
    # 3 a debe / 2 a haber: cuadra como conjunto aunque no exista par a par
    apuntes = [
        {"cuenta_id": CUENTA_A, "debe": Decimal("300.00"), "haber": Decimal("0")},
        {"cuenta_id": CUENTA_B, "debe": Decimal("400.00"), "haber": Decimal("0")},
        {"cuenta_id": CUENTA_A, "debe": Decimal("300.00"), "haber": Decimal("0")},
        {"cuenta_id": CUENTA_B, "debe": Decimal("0"), "haber": Decimal("1000.00")},
    ]
    assert calcular_delta(apuntes) == Decimal("0")


def test_linea_mixta_rechazada():
    with pytest.raises(ValueError):
        validar_lineas([{"cuenta_id": CUENTA_A, "debe": Decimal("100"), "haber": Decimal("50")}])


def test_linea_en_ceros_rechazada():
    with pytest.raises(ValueError):
        validar_lineas([{"cuenta_id": CUENTA_A, "debe": Decimal("0"), "haber": Decimal("0")}])


def test_minimo_dos_apuntes():
    with pytest.raises(ValueError):
        validar_lineas([{"cuenta_id": CUENTA_A, "debe": Decimal("100"), "haber": Decimal("0")}])


def test_importes_dos_decimales():
    with pytest.raises(ValueError):
        validar_lineas(
            [
                {"cuenta_id": CUENTA_A, "debe": Decimal("100.001"), "haber": Decimal("0")},
                {"cuenta_id": CUENTA_B, "debe": Decimal("0"), "haber": Decimal("100.001")},
            ]
        )


def test_lineas_validas_dos_n():
    apuntes = [
        {"cuenta_id": CUENTA_A, "debe": Decimal("100.50"), "haber": Decimal("0")},
        {"cuenta_id": CUENTA_B, "debe": Decimal("0"), "haber": Decimal("100.50")},
    ]
    assert validar_lineas(apuntes) == Decimal("0")
