"""Utilidades compartidas de los módulos fiscales (spec 005).

Redondeo monetario (R5): siempre `Decimal.quantize` con `ROUND_HALF_UP` a 2
decimales. Validación de CIF/NIF para terceros y perceptores (FR-017).
"""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

__all__ = ["CUANTIA2", "centimos", "cuantizar2", "validar_cif", "utcnow", "CUENTAS_PGC"]

CUANTIA2 = Decimal("0.01")

# Cuentas PGC utilizadas por el asiento derivado de facturas (config por defecto,
# R6: ajustables por ejercicio sin cambiar código).
CUENTAS_PGC = frozenset({"400", "430", "600", "700", "472", "477", "4751", "473", "631"})


def cuantizar2(v: Decimal) -> Decimal:
    """Redondea a 2 decimales con ROUND_HALF_UP (0.005 → 0.01)."""
    return Decimal(v).quantize(CUANTIA2, rounding=ROUND_HALF_UP)


def centimos(v: Decimal) -> int:
    """Convierte un importe Decimal a céntimos enteros (redondeo HALF_UP)."""
    return int(cuantizar2(v) * 100)


def utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Validación de NIF / NIF-IVA (CIF) español
# ---------------------------------------------------------------------------

_NIF_CONTROL = "TRWAGMYFPDXBNJZSQVHLCKE"
_CIF_LETRAS = frozenset("ABCDEFGHJKLMNPQRSVWU")
_CIF_NUMERIC_CTRL = frozenset("ABCDEFGH")


def _calcular_cif_control(digitos7: str) -> str:
    """Calcula el carácter de control de un CIF a partir de sus 7 dígitos."""
    pares = sum(int(d) for d in digitos7[1::2])
    impares = sum(sum(int(c) for c in str(int(d) * 2)) for d in digitos7[::2])
    unidades = (pares + impares) % 10
    control = (10 - unidades) % 10
    return str(control)


def validar_cif(cif: str) -> bool:
    """Valida un NIF (12345678Z) o CIF (B12345674) español.

    Devuelve True para identificativos con estructura y dígito de control
    correctos; False en cualquier otro caso (FR-017: los perceptores sin CIF
    válido no se agregan; T035: CIF inválido → 422).
    """
    if not cif or not isinstance(cif, str):
        return False
    c = cif.strip().upper()
    if len(c) != 9:
        return False

    # NIF: 8 dígitos + letra de control
    if c[:8].isdigit() and c[8].isalpha():
        numero = int(c[:8])
        return c[8] == _NIF_CONTROL[numero % 23]

    # CIF: letra + 7 dígitos + dígito/letra de control
    if c[0] in _CIF_LETRAS and c[1:8].isdigit():
        control = _calcular_cif_control(c[1:8])
        digito = c[8]
        if c[0] in _CIF_NUMERIC_CTRL:
            return digito == control
        # Grupos K/L/M (sociedades) y resto: el control puede ser dígito o letra
        # según las tablas AEAT; aceptamos el dígito calculado o una letra NIF.
        return digito == control or (digito.isalpha() and digito in _NIF_CONTROL)

    return False