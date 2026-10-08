from fastapi import APIRouter, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.api.deps import EjercicioDep, SessionDep
from app.api.errors import ApiError
from app.models import Cuenta, Ejercicio
from app.schemas.asientos import Paginado
from app.schemas.cuentas import CuentaIn, CuentaOut

router = APIRouter(prefix="/cuentas", tags=["cuentas"])


@router.get("", response_model=Paginado[CuentaOut])
def listar_cuentas(
    session: SessionDep,
    ejercicio: EjercicioDep,
    query: str | None = None,
    nivel: int | None = Query(default=None, ge=1, le=5),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> Paginado[CuentaOut]:
    filtro = select(Cuenta).where(Cuenta.ejercicio_id == ejercicio)
    if query:
        like = f"%{query}%"
        filtro = filtro.where(Cuenta.codigo.like(like) | Cuenta.nombre.like(like))
    if nivel is not None:
        filtro = filtro.where(Cuenta.nivel == nivel)
    total = len(session.exec(filtro).all())
    cuentas = session.exec(filtro.order_by(Cuenta.codigo).offset(offset).limit(limit)).all()
    return Paginado(
        total=total,
        offset=offset,
        limit=limit,
        items=[CuentaOut.model_validate(c) for c in cuentas],
    )


@router.post("", response_model=CuentaOut, status_code=201)
def crear_cuenta(session: SessionDep, ejercicio: EjercicioDep, payload: CuentaIn) -> CuentaOut:
    ej = session.get(Ejercicio, ejercicio)
    if ej is None or ej.estado != "abierto":
        raise ApiError(409, "El ejercicio está cerrado")
    cuenta = Cuenta(
        ejercicio_id=ejercicio,
        codigo=payload.codigo,
        nombre=payload.nombre,
        nivel=payload.nivel,
    )
    session.add(cuenta)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ApiError(409, "Código de cuenta duplicado en el ejercicio") from None
    session.refresh(cuenta)
    return CuentaOut.model_validate(cuenta)
