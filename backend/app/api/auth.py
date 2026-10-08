from fastapi import APIRouter, Response
from sqlmodel import select

from app.api.deps import SessionDep, UsuarioDep
from app.api.errors import ApiError
from app.config import get_settings
from app.models import Empresa, Usuario, empresa_usuario
from app.schemas.identidad import (
    LoginRequest,
    LoginResponse,
    PerfilOut,
    UsuarioOut,
)
from app.services.seguridad import (
    create_access_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, session: SessionDep) -> LoginResponse:
    usuario = session.exec(select(Usuario).where(Usuario.username == payload.username)).first()
    if usuario is None or not verify_password(usuario.hashed_password, payload.password):
        raise ApiError(401, "Credenciales inválidas")
    if not usuario.activo:
        raise ApiError(401, "Usuario inactivo")

    token = create_access_token(usuario.username)
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=_settings.jwt_expires_seconds,
        httponly=True,
        samesite="lax",
    )
    return LoginResponse(
        access_token=token,
        expires_in=_settings.jwt_expires_seconds,
        usuario=UsuarioOut(
            id=usuario.id,
            username=usuario.username,
            email=usuario.email,
            rol=usuario.rol,
            activo=usuario.activo,
        ),
    )


@router.get("/me", response_model=PerfilOut)
def me(usuario: UsuarioDep, session: SessionDep) -> PerfilOut:
    vinculos = session.execute(
        select(empresa_usuario.c.empresa_id).where(empresa_usuario.c.usuario_id == usuario.id)
    ).all()
    ids_vinculados = {row._mapping["empresa_id"] for row in vinculos}
    empresas = session.exec(select(Empresa).where(Empresa.id.in_(list(ids_vinculados)))).all()
    return PerfilOut(
        id=usuario.id,
        username=usuario.username,
        email=usuario.email,
        rol=usuario.rol,
        activo=usuario.activo,
        empresas=[e.id for e in empresas if e.activa],
    )


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie("access_token")
