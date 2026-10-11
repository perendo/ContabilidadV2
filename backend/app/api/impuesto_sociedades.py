"""API de la Liquidación del Impuesto sobre Sociedades (spec 005, US5)."""

from fastapi import APIRouter

from app.api.deps import EjercicioDep, SessionDep, UsuarioDep
from app.schemas.impuesto_sociedades import LiquidacionISIn, LiquidacionISOut
from app.services.impuesto_sociedades import (
    actualizar_liquidacion,
    ajustes_de,
    cerrar_liquidacion,
    crear_liquidacion,
    datos_visibles,
    obtener_liquidacion,
)

is_router = APIRouter(prefix="/is", tags=["is"])


def _to_out(liquidacion) -> LiquidacionISOut:
    base, cuota, diferencial = datos_visibles(liquidacion)
    return LiquidacionISOut(
        id=liquidacion.id,
        ejercicio_id=liquidacion.ejercicio_id,
        resultado_contable=liquidacion.resultado_contable,
        ajustes=ajustes_de(liquidacion),
        tipo_gravamen=liquidacion.tipo_gravamen,
        retenciones_pagos_cuenta=liquidacion.retenciones_pagos_cuenta,
        base_imponible=base,
        cuota_integra=cuota,
        cuota_diferencial=diferencial,
        estado=liquidacion.estado,
        asiento_id=liquidacion.asiento_id,
        creado_por_usuario_id=liquidacion.creado_por_usuario_id,
        cerrado_por_usuario_id=liquidacion.cerrado_por_usuario_id,
        created_at=liquidacion.created_at,
        cerrado_at=liquidacion.cerrado_at,
    )


@is_router.get("", response_model=LiquidacionISOut)
def get_liquidacion(session: SessionDep, ejercicio: EjercicioDep):
    return _to_out(obtener_liquidacion(session, ejercicio))


@is_router.post("", response_model=LiquidacionISOut, status_code=201)
def post_liquidacion(
    payload: LiquidacionISIn,
    session: SessionDep,
    usuario: UsuarioDep,
    ejercicio: EjercicioDep,
):
    liquidacion = crear_liquidacion(session, ejercicio, payload, usuario.id)
    return _to_out(liquidacion)


@is_router.put("", response_model=LiquidacionISOut)
def put_liquidacion(
    payload: LiquidacionISIn,
    session: SessionDep,
    ejercicio: EjercicioDep,
):
    liquidacion = actualizar_liquidacion(session, ejercicio, payload)
    return _to_out(liquidacion)


@is_router.post("/cerrar", response_model=LiquidacionISOut)
def cerrar(session: SessionDep, usuario: UsuarioDep, ejercicio: EjercicioDep):
    liquidacion = obtener_liquidacion(session, ejercicio)
    return _to_out(cerrar_liquidacion(session, liquidacion, usuario.id))