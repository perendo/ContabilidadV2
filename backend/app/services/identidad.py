from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.api.errors import ApiError
from app.models import Ejercicio, Empresa, Usuario, empresa_usuario
from app.pgc import sembrar_pgc


def crear_empresa(session: Session, usuario: Usuario, payload) -> Empresa:
    if usuario.rol != "admin":
        raise ApiError(403, "Solo el rol admin puede crear empresas")
    empresa = Empresa(
        cif=payload.cif,
        razon_social=payload.razon_social,
        nombre_comercial=payload.nombre_comercial,
    )
    session.add(empresa)
    session.flush()
    session.execute(
        empresa_usuario.insert().values(
            usuario_id=usuario.id, empresa_id=empresa.id, rol_especifico="admin"
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ApiError(409, "CIF duplicado") from None
    session.refresh(empresa)
    return empresa


def crear_ejercicio(session: Session, empresa_id: int, payload) -> Ejercicio:
    ejercicio = Ejercicio(
        empresa_id=empresa_id,
        anio=payload.anio,
        fecha_inicio=payload.fecha_inicio,
        fecha_fin=payload.fecha_fin,
        estado="abierto",
    )
    session.add(ejercicio)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise ApiError(409, "El año ya existe en esta empresa") from None
    sembrar_pgc(session, ejercicio.id)
    session.commit()
    session.refresh(ejercicio)
    return ejercicio
