from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from app.api.errors import ApiError
from app.models import Apunte, Asiento, Cuenta, Ejercicio


def _cant_dp(value: Decimal) -> int:
    return value.as_tuple().exponent


def validar_lineas(apuntes: list[dict[str, Any]]) -> Decimal:
    """Valida el conjunto de líneas y devuelve su descuadre Δ (debe − haber)."""
    if len(apuntes) < 2:
        raise ValueError("Un asiento requiere al menos 2 apuntes")
    total_debe = Decimal("0")
    total_haber = Decimal("0")
    for linea in apuntes:
        debe = linea["debe"]
        haber = linea["haber"]
        try:
            debe = Decimal(debe)
            haber = Decimal(haber)
        except (InvalidOperation, TypeError):
            raise ValueError("Importe no numérico") from None
        if debe < 0 or haber < 0:
            raise ValueError("Los importes no pueden ser negativos")
        if _cant_dp(debe) < -2 or _cant_dp(haber) < -2:
            raise ValueError("Importes con más de 2 decimales")
        if (debe > 0) == (haber > 0):
            raise ValueError(
                "Cada línea exige exactamente un importe (debe o haber) mayor que cero"
            )
        total_debe += debe
        total_haber += haber
    return total_debe - total_haber


def calcular_delta(apuntes: list[dict[str, Any]]) -> Decimal:
    total_debe = sum((Decimal(ap["debe"]) for ap in apuntes), Decimal("0"))
    total_haber = sum((Decimal(ap["haber"]) for ap in apuntes), Decimal("0"))
    return total_debe - total_haber


def _verificar_cuentas_del_ejercicio(
    session: Session, ejercicio_id: int, cuenta_ids: list[int]
) -> None:
    cuentas = session.exec(select(Cuenta).where(Cuenta.id.in_(cuenta_ids))).all()
    ajenas = [c.id for c in cuentas if c.ejercicio_id != ejercicio_id]
    if ajenas or len(cuentas) != len(set(cuenta_ids)):
        raise ApiError(422, "Todas las cuentas deben pertenecer al ejercicio activo")


def _ejercicio_abierto(session: Session, ejercicio_id: int, fecha=None) -> None:
    ejercicio = session.get(Ejercicio, ejercicio_id)
    if ejercicio is None:
        raise ApiError(400, "Ejercicio de contexto no encontrado")
    if ejercicio.estado != "abierto":
        raise ApiError(409, "El ejercicio está cerrado")
    if fecha is not None and not (ejercicio.fecha_inicio <= fecha <= ejercicio.fecha_fin):
        raise ApiError(422, "La fecha del asiento debe pertenecer al ejercicio")


def guardar_borrador(
    session: Session,
    ejercicio_id: int,
    fecha,
    concepto: str,
    apuntes_recibidos: list[dict[str, Any]],
    usuario_id: int | None = None,
) -> Asiento:
    validar_lineas(apuntes_recibidos)
    _verificar_cuentas_del_ejercicio(
        session, ejercicio_id, [a["cuenta_id"] for a in apuntes_recibidos]
    )
    _ejercicio_abierto(session, ejercicio_id, fecha)

    uid = usuario_id or 1
    asiento = Asiento(
        ejercicio_id=ejercicio_id,
        numero=None,
        fecha=fecha,
        concepto=concepto,
        estado="borrador",
        creado_por_usuario_id=uid,
        version=1,
    )
    session.add(asiento)
    session.flush()
    for linea in apuntes_recibidos:
        session.add(
            Apunte(
                asiento_id=asiento.id,
                cuenta_id=linea["cuenta_id"],
                debe=Decimal(linea["debe"]),
                haber=Decimal(linea["haber"]),
            )
        )
    session.commit()
    session.refresh(asiento)
    return asiento


def editar_borrador(
    session: Session,
    asiento: Asiento,
    fecha,
    concepto: str,
    apuntes_recibidos: list[dict[str, Any]],
    usuario_id: int | None = None,
) -> Asiento:
    if asiento.estado != "borrador":
        raise ApiError(409, "Los asientos asentados son inmutables")
    validar_lineas(apuntes_recibidos)
    _verificar_cuentas_del_ejercicio(
        session, asiento.ejercicio_id, [a["cuenta_id"] for a in apuntes_recibidos]
    )
    _ejercicio_abierto(session, asiento.ejercicio_id, fecha)
    for ap in session.exec(select(Apunte).where(Apunte.asiento_id == asiento.id)):
        session.delete(ap)
    session.flush()
    asiento.fecha = fecha
    asiento.concepto = concepto
    asiento.version += 1
    for linea in apuntes_recibidos:
        session.add(
            Apunte(
                asiento_id=asiento.id,
                cuenta_id=linea["cuenta_id"],
                debe=Decimal(linea["debe"]),
                haber=Decimal(linea["haber"]),
            )
        )
    session.commit()
    session.refresh(asiento)
    return asiento


def asentar(session: Session, asiento: Asiento, usuario_id: int | None = None) -> Asiento:
    if asiento.estado != "borrador":
        raise ApiError(409, "El asiento ya está asentado")
    _ejercicio_abierto(session, asiento.ejercicio_id)

    apuntes_db = session.exec(select(Apunte).where(Apunte.asiento_id == asiento.id)).all()

    # Invariante contable (CONT-01): mínimo 2 apuntes
    if len(apuntes_db) < 2:
        raise ApiError(422, "Un asiento contable requiere al menos 2 líneas de apunte")

    validar_lineas([{"debe": a.debe, "haber": a.haber} for a in apuntes_db])
    delta = calcular_delta([{"debe": a.debe, "haber": a.haber} for a in apuntes_db])
    if delta != Decimal("0"):
        raise ApiError(422, f"Descuadre del asiento: Δ={delta}")

    for _intento in range(5):
        max_num = session.exec(
            select(func.coalesce(func.max(Asiento.numero), 0)).where(
                Asiento.ejercicio_id == asiento.ejercicio_id
            )
        ).one()
        nuevo_numero = (max_num or 0) + 1
        asiento.numero = nuevo_numero
        asiento.estado = "asentado"
        if usuario_id is not None:
            asiento.asentado_por_usuario_id = usuario_id
        asiento.asentado_at = datetime.now(UTC)
        asiento.version += 1
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            asiento.estado = "borrador"
            asiento.numero = None
            continue
        session.refresh(asiento)
        return asiento
    raise ApiError(409, "No se pudo asignar un correlativo único")


def obtener_apuntes(session: Session, asiento_id: int) -> list[dict]:
    # Optimización PERF-02: JOIN explícito en consulta única sin N+1
    stmt = (
        select(Apunte, Cuenta.codigo)
        .join(Cuenta, Apunte.cuenta_id == Cuenta.id)
        .where(Apunte.asiento_id == asiento_id)
    )
    filas = session.exec(stmt).all()
    resultado = []
    for ap, codigo in filas:
        resultado.append(
            {
                "cuenta_id": ap.cuenta_id,
                "cuenta_codigo": codigo,
                "debe": str(ap.debe),
                "haber": str(ap.haber),
            }
        )
    return resultado
