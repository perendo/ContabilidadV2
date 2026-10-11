"""API de facturas, Libros Registro de IVA y Retenciones IRPF (spec 005, US1-US4)."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response
from sqlmodel import select

from app.api.deps import EjercicioDep, SessionDep, UsuarioDep
from app.api.errors import ApiError
from app.models import Factura, LineaFacturaIVA
from app.schemas.facturas import (
    FacturaIn,
    FacturaOut,
    FacturaResumen,
    FacturasPaginado,
    LibroIVAResponse,
    LineaFacturaIVAOut,
    RetencionesResponse,
)
from app.services import facturas as svc

router = APIRouter(prefix="/facturas", tags=["facturas"])

OrigenLibro = Annotated[Literal["repercutido", "soportado"], Query(description="Libro de IVA")]
TipoRetencion = Annotated[Literal["111", "115"], Query(description="Modelo de retenciones")]


def _to_out(factura: Factura, session: SessionDep) -> FacturaOut:
    lineas = session.exec(
        select(LineaFacturaIVA)
        .where(LineaFacturaIVA.factura_id == factura.id)
        .order_by(LineaFacturaIVA.numero_linea)
    ).all()
    return FacturaOut(
        id=factura.id,
        ejercicio_id=factura.ejercicio_id,
        origen=factura.origen,
        numero=factura.numero,
        fecha=factura.fecha,
        fecha_operacion=factura.fecha_operacion,
        tercero_cif=factura.tercero_cif,
        tercero_razon_social=factura.tercero_razon_social,
        solo_identificativo=factura.solo_identificativo,
        tipo_retencion=factura.tipo_retencion,
        estado=factura.estado,
        notas=factura.notas,
        asiento_id=factura.asiento_id,
        creado_por_usuario_id=factura.creado_por_usuario_id,
        created_at=factura.created_at.date() if factura.created_at else None,
        lineas=[LineaFacturaIVAOut.model_validate(ln) for ln in lineas],
    )


def _validar_rango(desde: date, hasta: date) -> None:
    if desde > hasta:
        raise ApiError(422, "desde no puede ser posterior a hasta")


@router.post("", response_model=FacturaOut, status_code=201)
def post_factura(
    payload: FacturaIn,
    session: SessionDep,
    usuario: UsuarioDep,
    ejercicio: EjercicioDep,
):
    factura = svc.crear_factura(session, ejercicio, payload, usuario.id)
    return _to_out(factura, session)


@router.get("/libros/iva", response_model=LibroIVAResponse)
def get_libro_iva(
    session: SessionDep,
    ejercicio: EjercicioDep,
    origen: OrigenLibro,
    desde: date,
    hasta: date,
):
    _validar_rango(desde, hasta)
    return svc.listar_libro_iva(session, ejercicio, origen, desde, hasta)


@router.get("/libros/iva/exportar")
def exportar_libro_iva(
    session: SessionDep,
    ejercicio: EjercicioDep,
    origen: OrigenLibro,
    desde: date,
    hasta: date,
):
    _validar_rango(desde, hasta)
    csv = svc.exportar_libro_iva(session, ejercicio, origen, desde, hasta)
    nombre = f"libro_iva_{origen}_{desde}_{hasta}.csv"
    return Response(
        content=csv.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre}"',
        },
    )


@router.get("/retenciones", response_model=RetencionesResponse)
def get_retenciones(
    session: SessionDep,
    ejercicio: EjercicioDep,
    tipo: TipoRetencion,
    desde: date,
    hasta: date,
):
    _validar_rango(desde, hasta)
    return svc.resumen_retenciones(session, ejercicio, tipo, desde, hasta)


@router.get("", response_model=FacturasPaginado)
def get_facturas(
    session: SessionDep,
    ejercicio: EjercicioDep,
    origen: Literal["venta", "compra"] | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    tercero_cif: str | None = Query(default=None, max_length=9),
    offset: int = 0,
    limit: int = Query(default=50, le=200),
):
    if desde and hasta and desde > hasta:
        raise ApiError(422, "desde no puede ser posterior a hasta")
    total, facturas = svc.listar_facturas(
        session, ejercicio, origen, desde, hasta, tercero_cif, offset, limit
    )
    return FacturasPaginado(
        total=total,
        offset=offset,
        limit=limit,
        items=[
            FacturaResumen(
                id=f.id,
                origen=f.origen,
                numero=f.numero,
                fecha=f.fecha,
                tercero_cif=f.tercero_cif,
                tercero_razon_social=f.tercero_razon_social,
                tipo_retencion=f.tipo_retencion,
                estado=f.estado,
                asiento_id=f.asiento_id,
            )
            for f in facturas
        ],
    )


@router.get("/{factura_id}", response_model=FacturaOut)
def get_factura(factura_id: int, session: SessionDep, ejercicio: EjercicioDep):
    factura = svc.obtener_factura(session, ejercicio, factura_id)
    return _to_out(factura, session)