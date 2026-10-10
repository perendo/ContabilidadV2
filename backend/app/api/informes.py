from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.api.deps import EjercicioDep, EmpresaDep, SessionDep
from app.models import Empresa as EmpresaModel
from app.schemas.informes import BalanceOut, MayorCuentaOut, MayorGlobalOut
from app.services.informes import balance, exportar_csv, exportar_pdf, mayor_cuenta, mayor_cuentas

informes_router = APIRouter(prefix="/informes", tags=["informes"])

FormatoQuery = Annotated[Literal["csv", "pdf"], Query(description="Formato de salida")]


def _validar_rango(desde: date | None, hasta: date | None) -> None:
    if desde and hasta and desde > hasta:
        raise HTTPException(status_code=422, detail="desde no puede ser posterior a hasta")


@informes_router.get("/mayor", response_model=MayorCuentaOut)
def get_mayor_cuenta(
    session: SessionDep,
    ejercicio: EjercicioDep,
    empresa: EmpresaDep,
    cuenta: Annotated[str, Query(description="Código exacto de la cuenta")],
    desde: Annotated[date | None, Query(description="Inicio del rango")] = None,
    hasta: Annotated[date | None, Query(description="Fin del rango")] = None,
):
    _validar_rango(desde, hasta)

    data = mayor_cuenta(session, ejercicio, cuenta, desde, hasta)
    if not data:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return MayorCuentaOut(**data)


@informes_router.get("/mayor/cuentas", response_model=MayorGlobalOut)
def get_mayor_cuentas(
    session: SessionDep,
    ejercicio: EjercicioDep,
    empresa: EmpresaDep,
    desde: date | None = None,
    hasta: date | None = None,
):
    _validar_rango(desde, hasta)

    data = mayor_cuentas(session, ejercicio, desde, hasta)
    return MayorGlobalOut(**data)


@informes_router.get("/balance", response_model=BalanceOut)
def get_balance(
    session: SessionDep,
    ejercicio: EjercicioDep,
    empresa: EmpresaDep,
    desde: date | None = None,
    hasta: date | None = None,
):
    _validar_rango(desde, hasta)

    data = balance(session, ejercicio, desde, hasta)
    return BalanceOut(**data)


@informes_router.get("/mayor/export")
def export_mayor(
    session: SessionDep,
    ejercicio: EjercicioDep,
    empresa: EmpresaDep,
    formato: FormatoQuery,
    cuenta: Annotated[str, Query(description="Código de la cuenta")],
    desde: date | None = None,
    hasta: date | None = None,
):
    _validar_rango(desde, hasta)
    if formato not in ("csv", "pdf"):
        raise HTTPException(status_code=422, detail="formato debe ser csv o pdf")

    empresa_obj = session.get(EmpresaModel, empresa)
    if not empresa_obj:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    data = mayor_cuenta(session, ejercicio, cuenta, desde, hasta)
    if not data:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    filename = f"mayor_{cuenta}"
    if desde:
        filename += f"_{desde.isoformat()}"
    if hasta:
        filename += f"-{hasta.isoformat()}"
    filename += f".{formato}"

    if formato == "csv":
        content = exportar_csv(
            session, ejercicio, empresa_obj.razon_social, empresa_obj.cif, "mayor",
            cuenta=cuenta, desde=desde, hasta=hasta,
        )
        media_type = "text/csv; charset=utf-8"
    else:
        content = exportar_pdf(
            session, ejercicio, empresa_obj.razon_social, empresa_obj.cif, "mayor", cuenta=cuenta,
            desde=desde, hasta=hasta,
        )
        media_type = "application/pdf"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@informes_router.get("/balance/export")
def export_balance(
    session: SessionDep,
    ejercicio: EjercicioDep,
    empresa: EmpresaDep,
    formato: FormatoQuery,
    desde: date | None = None,
    hasta: date | None = None,
):
    _validar_rango(desde, hasta)
    if formato not in ("csv", "pdf"):
        raise HTTPException(status_code=422, detail="formato debe ser csv o pdf")

    empresa_obj = session.get(EmpresaModel, empresa)
    if not empresa_obj:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    filename = "balance"
    if desde:
        filename += f"_{desde.isoformat()}"
    if hasta:
        filename += f"-{hasta.isoformat()}"
    filename += f".{formato}"

    if formato == "csv":
        content = exportar_csv(
            session, ejercicio, empresa_obj.razon_social, empresa_obj.cif, "balance",
            desde=desde, hasta=hasta,
        )
        media_type = "text/csv; charset=utf-8"
    else:
        content = exportar_pdf(
            session, ejercicio, empresa_obj.razon_social, empresa_obj.cif, "balance",
            desde=desde, hasta=hasta,
        )
        media_type = "application/pdf"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )