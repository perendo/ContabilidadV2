from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import func
from sqlmodel import select

from app.api.deps import EjercicioDep, SessionDep
from app.api.errors import ApiError
from app.models import Apunte, Asiento
from app.schemas.asientos import (
    ApunteOut,
    AsientoOut,
    AsientoRequest,
    AsientoResumen,
    Paginado,
)
from app.services import asientos as svc

router = APIRouter(prefix="/asientos", tags=["asientos"])


def _asiento_del_ejercicio(session: SessionDep, asiento_id: int, ejercicio_id: int) -> Asiento:
    asiento = session.get(Asiento, asiento_id)
    if asiento is None or asiento.ejercicio_id != ejercicio_id:
        raise ApiError(404, "Asiento no encontrado")
    return asiento


def _to_out(asiento: Asiento, session: SessionDep) -> AsientoOut:
    apuntes = svc.obtener_apuntes(session, asiento.id)
    return AsientoOut(
        id=asiento.id,
        ejercicio_id=asiento.ejercicio_id,
        numero=asiento.numero,
        fecha=asiento.fecha,
        concepto=asiento.concepto,
        estado=asiento.estado,
        apuntes=[ApunteOut(**a) for a in apuntes],
    )


def _totales(session: SessionDep, asiento_id: int) -> tuple:
    debe, haber = session.exec(
        select(func.sum(Apunte.debe), func.sum(Apunte.haber)).where(Apunte.asiento_id == asiento_id)
    ).one()
    return debe or 0, haber or 0


def _resumen(asiento: Asiento, session: SessionDep) -> AsientoResumen:
    debe, haber = _totales(session, asiento.id)
    return AsientoResumen(
        id=asiento.id,
        ejercicio_id=asiento.ejercicio_id,
        numero=asiento.numero,
        fecha=asiento.fecha,
        concepto=asiento.concepto,
        estado=asiento.estado,
        total_debe=debe,
        total_haber=haber,
        delta=(debe - haber) if asiento.estado == "borrador" else None,
    )


@router.post("", response_model=AsientoOut, status_code=201)
def crear_borrador(
    payload: AsientoRequest, session: SessionDep, ejercicio: EjercicioDep
) -> AsientoOut:
    asiento = svc.guardar_borrador(
        session,
        ejercicio,
        payload.fecha,
        payload.concepto,
        [a.model_dump() for a in payload.apuntes],
    )
    return _to_out(asiento, session)


@router.put("/{asiento_id}", response_model=AsientoOut)
def editar_borrador(
    asiento_id: int, payload: AsientoRequest, session: SessionDep, ejercicio: EjercicioDep
) -> AsientoOut:
    asiento = _asiento_del_ejercicio(session, asiento_id, ejercicio)
    asiento = svc.editar_borrador(
        session,
        asiento,
        payload.fecha,
        payload.concepto,
        [a.model_dump() for a in payload.apuntes],
    )
    return _to_out(asiento, session)


@router.post("/{asiento_id}/asentar", response_model=AsientoOut)
def asentar(asiento_id: int, session: SessionDep, ejercicio: EjercicioDep) -> AsientoOut:
    asiento = _asiento_del_ejercicio(session, asiento_id, ejercicio)
    asiento = svc.asentar(session, asiento)
    return _to_out(asiento, session)


@router.get("", response_model=Paginado[AsientoResumen])
def diario(
    session: SessionDep,
    ejercicio: EjercicioDep,
    since: date | None = None,
    until: date | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> Paginado[AsientoResumen]:
    query = select(Asiento).where(Asiento.ejercicio_id == ejercicio, Asiento.estado == "asentado")
    if since is not None:
        query = query.where(Asiento.fecha >= since)
    if until is not None:
        query = query.where(Asiento.fecha <= until)
    total = len(session.exec(query).all())
    asientos = session.exec(query.order_by(Asiento.numero).offset(offset).limit(limit)).all()
    return Paginado(
        total=total,
        offset=offset,
        limit=limit,
        items=[_resumen(a, session) for a in asientos],
    )


@router.get("/borradores", response_model=Paginado[AsientoResumen])
def borradores(
    session: SessionDep,
    ejercicio: EjercicioDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> Paginado[AsientoResumen]:
    query = select(Asiento).where(Asiento.ejercicio_id == ejercicio, Asiento.estado == "borrador")
    total = len(session.exec(query).all())
    asientos = session.exec(query.order_by(Asiento.fecha.desc()).offset(offset).limit(limit)).all()
    return Paginado(
        total=total,
        offset=offset,
        limit=limit,
        items=[_resumen(a, session) for a in asientos],
    )


@router.get("/{asiento_id}", response_model=AsientoOut)
def detalle(asiento_id: int, session: SessionDep, ejercicio: EjercicioDep) -> AsientoOut:
    asiento = _asiento_del_ejercicio(session, asiento_id, ejercicio)
    return _to_out(asiento, session)
