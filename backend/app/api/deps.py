from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.api.errors import ApiError
from app.db import get_session
from app.models import Ejercicio, Empresa, Usuario, empresa_usuario
from app.services.seguridad import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[Session, Depends(get_session)],
    access_token: Annotated[str | None, Cookie()] = None,
) -> Usuario:
    token = credentials.credentials if credentials else access_token
    if token is None:
        raise ApiError(401, "No autenticado")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise ApiError(401, "Token inválido o expirado") from None
    username = payload.get("sub")
    usuario = session.exec(select(Usuario).where(Usuario.username == username)).first()
    if usuario is None or not usuario.activo:
        raise ApiError(401, "No autenticado")
    return usuario


def get_empresa_context(
    usuario: Annotated[Usuario, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    x_empresa_id: Annotated[str | None, Header(alias="X-Empresa-Id")] = None,
) -> int:
    if x_empresa_id is None or not x_empresa_id.strip():
        raise ApiError(400, "Cabecera X-Empresa-Id requerida")
    if not x_empresa_id.isdigit():
        raise ApiError(400, "Cabecera X-Empresa-Id inválida")
    empresa_id = int(x_empresa_id)
    empresa = session.get(Empresa, empresa_id)
    if empresa is None or not empresa.activa:
        raise ApiError(403, "Sin acceso a la empresa o empresa inactiva")
    vinculo = session.exec(
        select(empresa_usuario).where(
            empresa_usuario.c.usuario_id == usuario.id,
            empresa_usuario.c.empresa_id == empresa_id,
        )
    ).first()
    if vinculo is None:
        raise ApiError(403, "Sin acceso a la empresa")
    return empresa_id


def get_ejercicio_context(
    empresa_id: Annotated[int, Depends(get_empresa_context)],
    session: Annotated[Session, Depends(get_session)],
    x_ejercicio_id: Annotated[str | None, Header(alias="X-Ejercicio-Id")] = None,
) -> int:
    if x_ejercicio_id is None or not x_ejercicio_id.strip():
        raise ApiError(400, "Cabecera X-Ejercicio-Id requerida")
    if not x_ejercicio_id.isdigit():
        raise ApiError(400, "Cabecera X-Ejercicio-Id inválida")
    ejercicio_id = int(x_ejercicio_id)
    ejercicio = session.get(Ejercicio, ejercicio_id)
    if ejercicio is None or ejercicio.empresa_id != empresa_id:
        raise ApiError(403, "Sin acceso al ejercicio")
    return ejercicio_id


SessionDep = Annotated[Session, Depends(get_session)]
UsuarioDep = Annotated[Usuario, Depends(get_current_user)]
EmpresaDep = Annotated[int, Depends(get_empresa_context)]
EjercicioDep = Annotated[int, Depends(get_ejercicio_context)]
