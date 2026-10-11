"""Servicio de la Liquidación del Impuesto sobre Sociedades (spec 005, US5).

El cálculo (base imponible, cuota íntegra, cuota diferencial) vive SOLO aquí
(FR-024). En estado `borrador` los importes se recalculan al consultar; al
`cerrar` se congelan y la liquidación es inmutable (FR-020/021).
"""

import json
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.errors import ApiError
from app.models import Ejercicio, LiquidacionImpuestoSociedades
from app.schemas.impuesto_sociedades import AjusteIS, LiquidacionISIn
from app.services.fiscales_util import cuantizar2, utcnow

_CIEN = Decimal("100")

__all__ = [
    "calcular_liquidacion",
    "crear_liquidacion",
    "actualizar_liquidacion",
    "obtener_liquidacion",
    "cerrar_liquidacion",
    "ajustes_de",
    "datos_visibles",
]


def ajustes_de(liquidacion: LiquidacionImpuestoSociedades) -> list[AjusteIS]:
    if not liquidacion.ajustes_json:
        return []
    return [AjusteIS(**a) for a in json.loads(liquidacion.ajustes_json)]


def calcular_liquidacion(
    liquidacion: LiquidacionImpuestoSociedades,
) -> tuple[Decimal, Decimal, Decimal]:
    """Base imponible, cuota íntegra y cuota diferencial (FR-024/025)."""
    ajustes = ajustes_de(liquidacion)
    aumentos = sum(a.importe for a in ajustes if a.sentido == "aumento")
    disminuciones = sum(a.importe for a in ajustes if a.sentido == "disminucion")
    base = cuantizar2(liquidacion.resultado_contable + aumentos - disminuciones)
    cuota = cuantizar2(base * liquidacion.tipo_gravamen / _CIEN)
    diferencial = cuantizar2(cuota - liquidacion.retenciones_pagos_cuenta)
    return base, cuota, diferencial


def datos_visibles(liquidacion: LiquidacionImpuestoSociedades) -> tuple[Decimal, Decimal, Decimal]:
    if liquidacion.estado == "cerrada":
        return (
            liquidacion.base_imponible or Decimal("0"),
            liquidacion.cuota_integra or Decimal("0"),
            liquidacion.cuota_diferencial or Decimal("0"),
        )
    return calcular_liquidacion(liquidacion)


def crear_liquidacion(
    session: Session, ejercicio_id: int, payload: LiquidacionISIn, usuario_id: int
) -> LiquidacionImpuestoSociedades:
    ejercicio = session.get(Ejercicio, ejercicio_id)
    if ejercicio is None:
        raise ApiError(400, "Ejercicio de contexto no encontrado")
    if ejercicio.estado != "abierto":
        raise ApiError(409, "El ejercicio está cerrado")
    existente = session.exec(
        select(LiquidacionImpuestoSociedades).where(
            LiquidacionImpuestoSociedades.ejercicio_id == ejercicio_id
        )
    ).first()
    if existente is not None:
        raise ApiError(409, "El ejercicio ya tiene liquidación del Impuesto sobre Sociedades")

    resultado = cuantizar2(payload.resultado_contable)
    liquidacion = LiquidacionImpuestoSociedades(
        ejercicio_id=ejercicio_id,
        resultado_contable=resultado,
        ajustes_json=json.dumps(
            [a.model_dump(mode="json") for a in payload.ajustes], ensure_ascii=False
        ),
        tipo_gravamen=payload.tipo_gravamen,
        retenciones_pagos_cuenta=cuantizar2(payload.retenciones_pagos_cuenta),
        base_imponible=None,
        cuota_integra=None,
        cuota_diferencial=None,
        estado="borrador",
        creado_por_usuario_id=usuario_id,
    )
    base, cuota, diferencial = calcular_liquidacion(liquidacion)
    # Guardados como pre-cálculo; en borrador se recalculan al consultar.
    liquidacion.base_imponible = base
    liquidacion.cuota_integra = cuota
    liquidacion.cuota_diferencial = diferencial
    session.add(liquidacion)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ApiError(409, "El ejercicio ya tiene liquidación") from None
    session.refresh(liquidacion)
    return liquidacion


def actualizar_liquidacion(
    session: Session,
    ejercicio_id: int,
    payload: LiquidacionISIn,
) -> LiquidacionImpuestoSociedades:
    """Actualiza la liquidación solo si está en `borrador` (FR/SC-007).

    Si `estado="cerrada"` → 409 (inmutable). Mismo body que POST; recalcula los
    importes y los deja como pre-cálculo mientras siga en borrador.
    """
    liquidacion = obtener_liquidacion(session, ejercicio_id)
    if liquidacion.estado != "borrador":
        raise ApiError(409, "La liquidación está cerrada y es inmutable")

    liquidacion.resultado_contable = cuantizar2(payload.resultado_contable)
    liquidacion.ajustes_json = json.dumps(
        [a.model_dump(mode="json") for a in payload.ajustes], ensure_ascii=False
    )
    liquidacion.tipo_gravamen = payload.tipo_gravamen
    liquidacion.retenciones_pagos_cuenta = cuantizar2(payload.retenciones_pagos_cuenta)
    base, cuota, diferencial = calcular_liquidacion(liquidacion)
    liquidacion.base_imponible = base
    liquidacion.cuota_integra = cuota
    liquidacion.cuota_diferencial = diferencial
    session.add(liquidacion)
    session.commit()
    session.refresh(liquidacion)
    return liquidacion


def obtener_liquidacion(
    session: Session, ejercicio_id: int
) -> LiquidacionImpuestoSociedades:
    liquidacion = session.exec(
        select(LiquidacionImpuestoSociedades).where(
            LiquidacionImpuestoSociedades.ejercicio_id == ejercicio_id
        )
    ).first()
    if liquidacion is None:
        raise ApiError(404, "No existe liquidación del IS para el ejercicio")
    return liquidacion


def cerrar_liquidacion(
    session: Session, liquidacion: LiquidacionImpuestoSociedades, usuario_id: int
) -> LiquidacionImpuestoSociedades:
    if liquidacion.estado != "borrador":
        raise ApiError(409, "La liquidación ya está cerrada")
    base, cuota, diferencial = calcular_liquidacion(liquidacion)
    liquidacion.base_imponible = base
    liquidacion.cuota_integra = cuota
    liquidacion.cuota_diferencial = diferencial
    liquidacion.estado = "cerrada"
    liquidacion.cerrado_por_usuario_id = usuario_id
    liquidacion.cerrado_at = utcnow()
    session.add(liquidacion)
    session.commit()
    session.refresh(liquidacion)
    return liquidacion