import json
import re
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlmodel import select

from app.api.deps import EjercicioDep, EmpresaDep, SessionDep, UsuarioDep
from app.models.contable import (
    LogProcesamientoBanco,
    MovimientoBanco,
    ReglaBanco,
)
from app.schemas.banco import (
    ImportResponse,
    LogProcesamientoOut,
    MovimientoBancoOut,
    ProcesarResponse,
    ReglaBancoIn,
    ReglaBancoOut,
)
from app.services import asientos as svc_asientos
from app.services.banco import (
    convertir_signo_banco_a_contable,
    importar_extractos,
    validar_cuentas_regla,
)

banco_router = APIRouter(prefix="/banco", tags=["banco"])


def _regla_matches(regla: ReglaBanco, mov: MovimientoBanco) -> bool:
    if re.search(regla.patron_regex, mov.concepto, re.IGNORECASE):
        return True
    return bool(mov.referencia and re.search(regla.patron_regex, mov.referencia, re.IGNORECASE))


def _calcular_importe(regla: ReglaBanco, mov: MovimientoBanco) -> Decimal:
    if regla.importe_fijo is not None:
        return regla.importe_fijo
    if regla.porcentaje is not None:
        return mov.importe * (regla.porcentaje / Decimal("100"))
    return abs(mov.importe)


@banco_router.post("/importar", response_model=ImportResponse)
async def importar_extracto(
    session: SessionDep,
    ejercicio: EjercicioDep,
    empresa: EmpresaDep,
    usuario: UsuarioDep,
    file: Annotated[UploadFile, File()],
    ignorar_duplicados: Annotated[bool, Form()] = False,
):
    """Importa extracto bancario (Excel Santander, CSV, CSB)."""
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (mÃ¡x 10MB)")

    file_bytes = await file.read()
    filename = file.filename or "extracto"

    try:
        result = importar_extractos(
            session=session,
            ejercicio_id=ejercicio,
            file_bytes=file_bytes,
            filename=filename,
            ignorar_duplicados=ignorar_duplicados,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {e}") from e

    return result


@banco_router.get("/pendientes", response_model=list[MovimientoBancoOut])
def listar_pendientes(
    session: SessionDep,
    ejercicio: EjercicioDep,
    empresa: EmpresaDep,
    desde: date | None = None,
    hasta: date | None = None,
    codigo_banco: str | None = None,
    offset: int = 0,
    limit: int = 50,
):
    """Lista movimientos sin procesar (pendientes de conciliar)."""
    stmt = select(MovimientoBanco).where(
        MovimientoBanco.ejercicio_id == ejercicio,
        MovimientoBanco.procesado.is_(False),
    )
    if desde:
        stmt = stmt.where(MovimientoBanco.fecha_valor >= desde)
    if hasta:
        stmt = stmt.where(MovimientoBanco.fecha_valor <= hasta)
    if codigo_banco:
        stmt = stmt.where(MovimientoBanco.codigo_banco == codigo_banco)

    stmt = (
        stmt.order_by(MovimientoBanco.fecha_valor, MovimientoBanco.id)
        .offset(offset)
        .limit(limit)
    )

    return session.exec(stmt).all()


# =============================================================================
# REGLAS
# =============================================================================


@banco_router.get("/reglas", response_model=list[ReglaBancoOut])
def listar_reglas(
    session: SessionDep,
    empresa: EmpresaDep,
    ejercicio: EjercicioDep,
    activas_only: bool = True,
):
    """Lista reglas de auto-matching de la empresa."""
    stmt = select(ReglaBanco).where(ReglaBanco.empresa_id == empresa)
    if activas_only:
        stmt = stmt.where(ReglaBanco.activa.is_(True))
    stmt = stmt.order_by(ReglaBanco.prioridad.desc(), ReglaBanco.id)
    return session.exec(stmt).all()


@banco_router.post("/reglas", response_model=ReglaBancoOut, status_code=201)
def crear_regla(
    payload: ReglaBancoIn,
    session: SessionDep,
    empresa: EmpresaDep,
    ejercicio: EjercicioDep,
    usuario: UsuarioDep,
):
    """Crea una nueva regla de auto-matching."""
    validar_cuentas_regla(session, ejercicio, payload.cuenta_debe, payload.cuenta_haber)

    regla = ReglaBanco(
        empresa_id=empresa,
        nombre=payload.nombre,
        patron_regex=payload.patron_regex,
        cuenta_debe=payload.cuenta_debe,
        cuenta_haber=payload.cuenta_haber,
        importe_fijo=payload.importe_fijo,
        porcentaje=payload.porcentaje,
        prioridad=payload.prioridad,
        auto_asentar=payload.auto_asentar,
        activa=payload.activa,
    )
    session.add(regla)
    session.commit()
    session.refresh(regla)
    return regla


@banco_router.get("/reglas/{regla_id}", response_model=ReglaBancoOut)
def obtener_regla(regla_id: int, session: SessionDep, empresa: EmpresaDep):
    """Obtiene una regla por ID."""
    regla = session.get(ReglaBanco, regla_id)
    if not regla or regla.empresa_id != empresa:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return regla


@banco_router.put("/reglas/{regla_id}", response_model=ReglaBancoOut)
def actualizar_regla(
    regla_id: int,
    payload: ReglaBancoIn,
    session: SessionDep,
    empresa: EmpresaDep,
    ejercicio: EjercicioDep,
    usuario: UsuarioDep,
):
    """Actualiza una regla existente."""
    regla = session.get(ReglaBanco, regla_id)
    if not regla or regla.empresa_id != empresa:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    validar_cuentas_regla(session, ejercicio, payload.cuenta_debe, payload.cuenta_haber)

    regla.nombre = payload.nombre
    regla.patron_regex = payload.patron_regex
    regla.cuenta_debe = payload.cuenta_debe
    regla.cuenta_haber = payload.cuenta_haber
    regla.importe_fijo = payload.importe_fijo
    regla.porcentaje = payload.porcentaje
    regla.prioridad = payload.prioridad
    regla.auto_asentar = payload.auto_asentar
    regla.activa = payload.activa

    session.commit()
    session.refresh(regla)
    return regla


@banco_router.delete("/reglas/{regla_id}", status_code=204)
def borrar_regla(regla_id: int, session: SessionDep, empresa: EmpresaDep, usuario: UsuarioDep):
    """Borra una regla."""
    regla = session.get(ReglaBanco, regla_id)
    if not regla or regla.empresa_id != empresa:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    session.delete(regla)
    session.commit()


@banco_router.post("/reglas/{regla_id}/simular")
def simular_regla(
    regla_id: int,
    session: SessionDep,
    empresa: EmpresaDep,
    ejercicio: EjercicioDep,
    desde: date | None = None,
    hasta: date | None = None,
):
    """Simula quÃ© movimientos matcharÃ­an con la regla."""
    regla = session.get(ReglaBanco, regla_id)
    if not regla or regla.empresa_id != empresa:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    stmt = select(MovimientoBanco).where(
        MovimientoBanco.ejercicio_id == ejercicio,
        MovimientoBanco.procesado.is_(False),
    )
    if desde:
        stmt = stmt.where(MovimientoBanco.fecha_valor >= desde)
    if hasta:
        stmt = stmt.where(MovimientoBanco.fecha_valor <= hasta)

    matches = []
    for mov in session.exec(stmt).all():
        if not _regla_matches(regla, mov):
            continue
        matches.append(
            {
                "movimiento_id": mov.id,
                "fecha_operacion": mov.fecha_operacion,
                "fecha_valor": mov.fecha_valor,
                "concepto": mov.concepto,
                "importe": mov.importe,
                "saldo": mov.saldo,
                "cuenta_debe": regla.cuenta_debe,
                "cuenta_haber": regla.cuenta_haber,
                "importe_calculado": _calcular_importe(regla, mov),
            }
        )

    return {"matches": matches}


# =============================================================================
# PROCESAR AUTO-MATCHING
# =============================================================================


@banco_router.post("/procesar", response_model=ProcesarResponse)
def procesar_pendientes(
    session: SessionDep,
    ejercicio: EjercicioDep,
    empresa: EmpresaDep,
    usuario: UsuarioDep,
    desde: date | None = None,
    hasta: date | None = None,
):
    """Procesa movimientos pendientes aplicando reglas de auto-matching."""
    reglas = session.exec(
        select(ReglaBanco)
        .where(ReglaBanco.empresa_id == empresa, ReglaBanco.activa.is_(True))
        .order_by(ReglaBanco.prioridad.desc(), ReglaBanco.id)
    ).all()

    stmt = select(MovimientoBanco).where(
        MovimientoBanco.ejercicio_id == ejercicio,
        MovimientoBanco.procesado.is_(False),
    )
    if desde:
        stmt = stmt.where(MovimientoBanco.fecha_valor >= desde)
    if hasta:
        stmt = stmt.where(MovimientoBanco.fecha_valor <= hasta)

    movimientos = session.exec(stmt).all()

    creados = 0
    pendientes = 0
    fallidos = []
    reglas_aplicadas = []

    for mov in movimientos:
        regla = next((r for r in reglas if _regla_matches(r, mov)), None)
        if regla is None:
            pendientes += 1
            continue

        try:
            importe_calc = _calcular_importe(regla, mov)
            cuenta_debe_obj, cuenta_haber_obj = validar_cuentas_regla(
                session, mov.ejercicio_id, regla.cuenta_debe, regla.cuenta_haber
            )
            debe, haber = convertir_signo_banco_a_contable(importe_calc, mov.codigo_banco)

            asiento = svc_asientos.guardar_borrador(
                session,
                mov.ejercicio_id,
                mov.fecha_valor,
                mov.concepto,
                [
                    {"cuenta_id": cuenta_debe_obj.id, "debe": debe, "haber": haber},
                    {"cuenta_id": cuenta_haber_obj.id, "debe": haber, "haber": debe},
                ],
                usuario_id=usuario.id,
            )
            if regla.auto_asentar:
                svc_asientos.asentar(session, asiento, usuario_id=usuario.id)

            mov.procesado = True
            mov.asiento_id = asiento.id
            mov.regla_id = regla.id

            if regla.id not in reglas_aplicadas:
                reglas_aplicadas.append(regla.id)
            creados += 1
        except Exception as e:
            fallidos.append({"movimiento_id": mov.id, "error": str(e)})

    log = LogProcesamientoBanco(
        ejercicio_id=ejercicio,
        usuario_id=usuario.id,
        reglas_aplicadas_json=json.dumps(reglas_aplicadas),
        creados=creados,
        pendientes=pendientes,
        fallidos_json=json.dumps(fallidos),
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    return ProcesarResponse(
        creados=creados,
        pendientes=pendientes,
        fallidos=fallidos,
        log_id=log.id,
    )


# =============================================================================
# LOGS
# =============================================================================


@banco_router.get("/logs", response_model=list[LogProcesamientoOut])
def listar_logs(
    session: SessionDep,
    ejercicio: EjercicioDep,
    empresa: EmpresaDep,
    desde: date | None = None,
    hasta: date | None = None,
    offset: int = 0,
    limit: int = 50,
):
    """Lista logs de procesamiento de auto-matching."""
    stmt = select(LogProcesamientoBanco).where(LogProcesamientoBanco.ejercicio_id == ejercicio)
    if desde:
        stmt = stmt.where(LogProcesamientoBanco.timestamp >= desde)
    if hasta:
        stmt = stmt.where(LogProcesamientoBanco.timestamp <= hasta)

    stmt = stmt.order_by(LogProcesamientoBanco.timestamp.desc()).offset(offset).limit(limit)
    return session.exec(stmt).all()