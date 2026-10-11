"""API de Presentación AEAT (spec 005, US-PRES): vista en pantalla + fichero."""

from fastapi import APIRouter, Response

from app.api.deps import EjercicioDep, EmpresaDep, SessionDep, UsuarioDep
from app.models import Ejercicio, Empresa
from app.schemas.presentaciones import PresentacionVista
from app.services import presentaciones as svc

presentaciones_router = APIRouter(prefix="/presentaciones", tags=["presentaciones"])


@presentaciones_router.get("/{modelo}", response_model=PresentacionVista)
def get_vista(
    modelo: str,
    periodo: str,
    session: SessionDep,
    ejercicio: EjercicioDep,
):
    ejercicio_obj = session.get(Ejercicio, ejercicio)
    return svc.vista(session, ejercicio_obj, modelo, periodo)


@presentaciones_router.get("/{modelo}/fichero")
def get_fichero(
    modelo: str,
    periodo: str,
    session: SessionDep,
    ejercicio: EjercicioDep,
    empresa: EmpresaDep,
    usuario: UsuarioDep,
):
    ejercicio_obj = session.get(Ejercicio, ejercicio)
    empresa_obj = session.get(Empresa, empresa)
    contenido, _fichero = svc.generar_fichero(
        session, ejercicio_obj, empresa_obj, usuario, modelo, periodo
    )
    return Response(
        content=contenido,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{modelo}_{periodo}.txt"',
        },
    )