from fastapi import APIRouter
from sqlmodel import select
from app.api.deps import EmpresaDep, SessionDep, UsuarioDep
from app.api.errors import ApiError
from app.models import Ejercicio, Empresa, empresa_usuario
from app.schemas.identidad import EjercicioIn, EjercicioOut, EmpresaIn, EmpresaOut
from app.services import identidad as svc

router = APIRouter(prefix="/api/v1", tags=["identidad"])


@router.get("/empresas", response_model=list[EmpresaOut])
def listar_empresas(usuario: UsuarioDep, session: SessionDep) -> list[EmpresaOut]:
    vinculos = session.execute(
        select(empresa_usuario.c.empresa_id).where(empresa_usuario.c.usuario_id == usuario.id)
    ).all()
    ids = {row._mapping["empresa_id"] for row in vinculos}
    empresas = session.exec(
        select(Empresa).where(Empresa.id.in_(list(ids)), Empresa.activa.is_(True))
    ).all()
    return [EmpresaOut.model_validate(e) for e in empresas]


@router.post("/empresas", response_model=EmpresaOut, status_code=201)
def crear_empresa(payload: EmpresaIn, usuario: UsuarioDep, session: SessionDep) -> EmpresaOut:
    empresa = svc.crear_empresa(session, usuario, payload)
    return EmpresaOut.model_validate(empresa)


@router.get("/ejercicios", response_model=list[EjercicioOut])
def listar_ejercicios(session: SessionDep, empresa_id: EmpresaDep) -> list[EjercicioOut]:
    ejercicios = session.exec(select(Ejercicio).where(Ejercicio.empresa_id == empresa_id)).all()
    return [EjercicioOut.model_validate(e) for e in ejercicios]


@router.post("/ejercicios", response_model=EjercicioOut, status_code=201)
def crear_ejercicio(
    payload: EjercicioIn, session: SessionDep, empresa_id: EmpresaDep, usuario: UsuarioDep
) -> EjercicioOut:
    if usuario.rol != "admin":
        raise ApiError(403, "Solo el rol admin puede crear ejercicios")
    ejercicio = svc.crear_ejercicio(session, empresa_id, payload)
    return EjercicioOut.model_validate(ejercicio)
