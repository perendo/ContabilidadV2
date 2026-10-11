"""Servicio de facturas (spec 005): registro atómico con asiento derivado,
Libros Registro de IVA y resumen de retenciones por perceptor (US1-US4).

La lógica de cálculo de cuotas/retenciones y el cuadre viven SOLO aquí (FR-003,
FR-024); el asiento se crea en la misma transacción que la factura (FR-004/005).
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.errors import ApiError
from app.models import Apunte, Asiento, Cuenta, Ejercicio, Factura, LineaFacturaIVA
from app.schemas.facturas import FacturaIn
from app.services.fiscales_util import cuantizar2, utcnow, validar_cif

_CIEN = Decimal("100")

__all__ = [
    "crear_factura",
    "listar_facturas",
    "obtener_factura",
    "generar_asiento_factura",
    "listar_libro_iva",
    "exportar_libro_iva",
    "resumen_retenciones",
]


def _cuenta_del_ejercicio(session: Session, ejercicio_id: int, codigo: str) -> Cuenta:
    cuenta = session.exec(
        select(Cuenta).where(Cuenta.ejercicio_id == ejercicio_id, Cuenta.codigo == codigo)
    ).first()
    if cuenta is None:
        raise ApiError(422, f"Cuenta {codigo} no existe en el ejercicio")
    return cuenta


def _validar_cuota_iva(linea, cuota: Decimal) -> None:
    if not linea.operacion_exenta and linea.cuota_iva is not None:
        if cuantizar2(linea.cuota_iva) != cuota:
            raise ApiError(422, "La cuota de IVA no coincide con base × tipo / 100")


def _procesar_lineas(payload: FacturaIn, session: Session, ejercicio_id: int) -> list[dict]:
    """Valida y normaliza cada línea (cuotas recalculadas a 2dp, R5)."""
    procesadas: list[dict] = []
    for ln in payload.lineas:
        exenta = ln.operacion_exenta
        tipo_iva = Decimal("0") if exenta else ln.tipo_iva
        cuota_iva = cuantizar2(ln.base_imponible * tipo_iva / _CIEN)
        _validar_cuota_iva(ln, cuota_iva)

        tipo_re: Decimal | None = None
        cuota_re: Decimal | None = None
        if ln.tipo_re is not None:
            if exenta:
                raise ApiError(422, "Una operación exenta no admite recargo de equivalencia")
            tipo_re = ln.tipo_re
            cuota_re = cuantizar2(ln.base_imponible * tipo_re / _CIEN)
            if ln.cuota_re is not None and cuantizar2(ln.cuota_re) != cuota_re:
                raise ApiError(422, "La cuota de recargo no coincide con base × tipo_re / 100")

        base_ret = pct_ret = cuota_ret = None
        tiene_retencion = any(
            x is not None for x in (ln.base_retencion, ln.pct_retencion, ln.cuota_retencion)
        )
        if tiene_retencion:
            if payload.origen != "compra":
                raise ApiError(422, "Las retenciones solo aplican a facturas de compra")
            if payload.tipo_retencion not in ("111", "115"):
                raise ApiError(422, "tipo_retencion (111/115) requerido para líneas con retención")
            if ln.base_retencion is None or ln.pct_retencion is None:
                raise ApiError(
                    422, "Retención incompleta: base_retencion y pct_retencion obligatorios"
                )
            if ln.pct_retencion > 100:
                raise ApiError(422, "pct_retencion no puede superar 100")
            base_ret = ln.base_retencion
            pct_ret = ln.pct_retencion
            cuota_ret = cuantizar2(base_ret * pct_ret / _CIEN)
            if ln.cuota_retencion is not None and cuantizar2(ln.cuota_retencion) != cuota_ret:
                raise ApiError(422, "La cuota de retención no coincide con base × pct / 100")

        procesadas.append(
            {
                "numero_linea": ln.numero_linea,
                "descripcion": ln.descripcion,
                "base_imponible": cuantizar2(ln.base_imponible),
                "tipo_iva": tipo_iva,
                "cuota_iva": cuota_iva,
                "tipo_re": tipo_re,
                "cuota_re": cuota_re,
                "operacion_exenta": exenta,
                "base_retencion": base_ret,
                "pct_retencion": pct_ret,
                "cuota_retencion": cuota_ret,
            }
        )
    return procesadas


def _apuntes_factura(
    session: Session,
    ejercicio_id: int,
    payload: FacturaIn,
    lineas: list[dict],
) -> list[dict]:
    """Construye los apuntes PGC del asiento derivado (FR-004, mapeo data-model)."""
    if payload.origen == "venta":
        c_tercero = _cuenta_del_ejercicio(session, ejercicio_id, "430").id
        c_ingreso = _cuenta_del_ejercicio(session, ejercicio_id, "700").id
        c_iva = _cuenta_del_ejercicio(session, ejercicio_id, "477").id
        total_debe = sum(
            (ln["base_imponible"] + ln["cuota_iva"] + (ln["cuota_re"] or Decimal("0")))
            for ln in lineas
        )
        apuntes = [{"cuenta_id": c_tercero, "debe": cuantizar2(total_debe), "haber": Decimal("0")}]
        apuntes.append(
            {
                "cuenta_id": c_ingreso,
                "debe": Decimal("0"),
                "haber": cuantizar2(sum(ln["base_imponible"] for ln in lineas)),
            }
        )
        # Una línea en 477 por cada tipo de IVA distinto (SC: desglose por tipo)
        por_tipo: dict[str, Decimal] = defaultdict(Decimal)
        for ln in lineas:
            por_tipo[ln["tipo_iva"]] += ln["cuota_iva"]
        for cuota in por_tipo.values():
            if cuota:
                apuntes.append({"cuenta_id": c_iva, "debe": Decimal("0"), "haber": cuota})
    else:  # compra
        c_gasto = _cuenta_del_ejercicio(session, ejercicio_id, "600").id
        c_iva = _cuenta_del_ejercicio(session, ejercicio_id, "472").id
        c_tercero = _cuenta_del_ejercicio(session, ejercicio_id, "400").id
        apuntes = []
        total_debe_gasto = sum(ln["base_imponible"] for ln in lineas)
        total_iva_debe = sum(
            ln["cuota_iva"] + (ln["cuota_re"] or Decimal("0"))
            for ln in lineas
            if not ln["operacion_exenta"]
        )
        total_haber_tercero = sum(
            ln["base_imponible"]
            + ln["cuota_iva"]
            + (ln["cuota_re"] or Decimal("0"))
            - (ln["cuota_retencion"] or Decimal("0"))
            for ln in lineas
        )
        if total_debe_gasto:
            apuntes.append(
                {"cuenta_id": c_gasto, "debe": cuantizar2(total_debe_gasto), "haber": Decimal("0")}
            )
        if total_iva_debe:
            apuntes.append(
                {"cuenta_id": c_iva, "debe": cuantizar2(total_iva_debe), "haber": Decimal("0")}
            )
        apuntes.append(
            {"cuenta_id": c_tercero, "debe": Decimal("0"), "haber": cuantizar2(total_haber_tercero)}
        )
        total_retencion = sum(ln["cuota_retencion"] or Decimal("0") for ln in lineas)
        if total_retencion:
            c_ret = _cuenta_del_ejercicio(session, ejercicio_id, "4751").id
            apuntes.append(
                {"cuenta_id": c_ret, "debe": Decimal("0"), "haber": cuantizar2(total_retencion)}
            )
    return apuntes


def generar_asiento_factura(
    session: Session,
    ejercicio_id: int,
    payload: FacturaIn,
    lineas: list[dict],
    usuario_id: int,
) -> Asiento:
    """Crea (sin commit) el asiento asentado con correlativo del ejercicio."""
    apuntes = _apuntes_factura(session, ejercicio_id, payload, lineas)
    delta = sum(ap["debe"] for ap in apuntes) - sum(ap["haber"] for ap in apuntes)
    if delta != 0:
        raise ApiError(422, f"Descuadre del asiento derivado: Δ={delta}")

    asiento = Asiento(
        ejercicio_id=ejercicio_id,
        numero=None,
        fecha=payload.fecha,
        concepto=f"Factura {payload.origen} {payload.numero}",
        estado="asentado",
        creado_por_usuario_id=usuario_id,
        asentado_por_usuario_id=usuario_id,
        asentado_at=utcnow(),
        version=1,
        origen="factura",
    )
    session.add(asiento)
    session.flush()
    max_num = session.exec(
        select(func.coalesce(func.max(Asiento.numero), 0)).where(
            Asiento.ejercicio_id == ejercicio_id
        )
    ).one()
    asiento.numero = (max_num or 0) + 1
    for ap in apuntes:
        session.add(
            Apunte(
                asiento_id=asiento.id,
                cuenta_id=ap["cuenta_id"],
                debe=ap["debe"],
                haber=ap["haber"],
            )
        )
    return asiento


def crear_factura(
    session: Session, ejercicio_id: int, payload: FacturaIn, usuario_id: int
) -> Factura:
    """Registra la factura y genera atómicamente el asiento cuadrado (FR-004/005)."""
    ejercicio = session.get(Ejercicio, ejercicio_id)
    if ejercicio is None:
        raise ApiError(400, "Ejercicio de contexto no encontrado")
    if ejercicio.estado != "abierto":
        raise ApiError(409, "El ejercicio está cerrado")
    if not (ejercicio.fecha_inicio <= payload.fecha <= ejercicio.fecha_fin):
        raise ApiError(422, "La fecha de la factura debe pertenecer al ejercicio")
    if not validar_cif(payload.tercero_cif):
        raise ApiError(422, "CIF/NIF del tercero inválido")

    lineas = _procesar_lineas(payload, session, ejercicio_id)
    asiento = generar_asiento_factura(session, ejercicio_id, payload, lineas, usuario_id)

    factura = Factura(
        ejercicio_id=ejercicio_id,
        origen=payload.origen,
        numero=payload.numero,
        fecha=payload.fecha,
        fecha_operacion=payload.fecha_operacion,
        tercero_cif=payload.tercero_cif,
        tercero_razon_social=payload.tercero_razon_social,
        solo_identificativo=payload.solo_identificativo,
        tipo_retencion=payload.tipo_retencion,
        estado="registrada",
        notas=payload.notas,
        asiento_id=asiento.id,
        creado_por_usuario_id=usuario_id,
    )
    session.add(factura)
    try:
        session.flush()  # aquí salta el duplicado CIF+número+ejercicio
        for ln in lineas:
            session.add(LineaFacturaIVA(factura_id=factura.id, **ln))
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ApiError(409, "Factura duplicada (CIF + número + ejercicio)") from None
    session.refresh(factura)
    return factura


def listar_facturas(
    session: Session,
    ejercicio_id: int,
    origen: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    tercero_cif: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[int, list[Factura]]:
    cond = [Factura.ejercicio_id == ejercicio_id]
    if origen:
        cond.append(Factura.origen == origen)
    if desde is not None:
        cond.append(Factura.fecha >= desde)
    if hasta is not None:
        cond.append(Factura.fecha <= hasta)
    if tercero_cif:
        cond.append(Factura.tercero_cif == tercero_cif)
    total = session.exec(select(func.count(Factura.id)).where(*cond)).one()
    facturas = session.exec(
        select(Factura).where(*cond).order_by(Factura.fecha, Factura.id).offset(offset).limit(limit)
    ).all()
    return total, facturas


def obtener_factura(session: Session, ejercicio_id: int, factura_id: int) -> Factura:
    factura = session.get(Factura, factura_id)
    if factura is None or factura.ejercicio_id != ejercicio_id:
        raise ApiError(404, "Factura no encontrada")
    return factura


def listar_libro_iva(
    session: Session, ejercicio_id: int, origen: str, desde: date, hasta: date
) -> dict:
    """Libro Registro de IVA (FR-009…011): detalle por línea + totales por tipo."""
    origen_factura = "venta" if origen == "repercutido" else "compra"
    filas = session.exec(
        select(LineaFacturaIVA, Factura)
        .join(Factura, LineaFacturaIVA.factura_id == Factura.id)
        .where(
            Factura.ejercicio_id == ejercicio_id,
            Factura.origen == origen_factura,
            Factura.estado == "registrada",
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
        )
        .order_by(Factura.fecha, Factura.numero, LineaFacturaIVA.numero_linea)
    ).all()

    operaciones = []
    totales: dict[str, dict] = defaultdict(lambda: {"base": Decimal("0"), "cuota": Decimal("0")})
    for linea, factura in filas:
        total = linea.base_imponible + linea.cuota_iva + (linea.cuota_re or Decimal("0"))
        operaciones.append(
            {
                "fecha": factura.fecha,
                "numero": factura.numero,
                "tercero_cif": factura.tercero_cif,
                "tercero_razon_social": factura.tercero_razon_social,
                "base_imponible": linea.base_imponible,
                "tipo_iva": linea.tipo_iva,
                "cuota_iva": linea.cuota_iva,
                "total": cuantizar2(total),
                "asiento_id": factura.asiento_id,
            }
        )
        totales[str(linea.tipo_iva)]["base"] += linea.base_imponible
        totales[str(linea.tipo_iva)]["cuota"] += linea.cuota_iva

    totales_por_tipo = [
        {"tipo_iva": Decimal(t), "base": cuantizar2(v["base"]), "cuota": cuantizar2(v["cuota"])}
        for t, v in sorted(totales.items(), key=lambda kv: Decimal(kv[0]))
    ]
    return {
        "origen": origen,
        "desde": desde,
        "hasta": hasta,
        "operaciones": operaciones,
        "totales_por_tipo": totales_por_tipo,
        "total_base": cuantizar2(sum(v["base"] for v in totales.values())),
        "total_cuota": cuantizar2(sum(v["cuota"] for v in totales.values())),
    }


def exportar_libro_iva(
    session: Session, ejercicio_id: int, origen: str, desde: date, hasta: date
) -> str:
    """CSV con ';' como separador, coma decimal y BOM UTF-8 (FR-012)."""
    libro = listar_libro_iva(session, ejercicio_id, origen, desde, hasta)
    cabecera = "fecha;numero;cif;nombre;base;tipo;cuota;total"
    lineas = [cabecera]
    for op in libro["operaciones"]:
        def f(v) -> str:
            return str(v).replace(".", ",")

        lineas.append(
            ";".join(
                [
                    op["fecha"].isoformat(),
                    op["numero"],
                    op["tercero_cif"],
                    op["tercero_razon_social"],
                    f(op["base_imponible"]),
                    f(op["tipo_iva"]),
                    f(op["cuota_iva"]),
                    f(op["total"]),
                ]
            )
        )
    return "\ufeff" + "\r\n".join(lineas)


def resumen_retenciones(
    session: Session, ejercicio_id: int, tipo: str, desde: date, hasta: date
) -> dict:
    """Agrega retenciones por CIF de perceptor para 111/115 (FR-016, FR-017)."""
    filas = session.exec(
        select(LineaFacturaIVA, Factura)
        .join(Factura, LineaFacturaIVA.factura_id == Factura.id)
        .where(
            Factura.ejercicio_id == ejercicio_id,
            Factura.origen == "compra",
            Factura.tipo_retencion == tipo,
            Factura.estado == "registrada",
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
            LineaFacturaIVA.base_retencion.is_not(None),
        )
        .order_by(Factura.tercero_cif, Factura.numero)
    ).all()

    grupos: dict[str, dict] = {}
    for linea, factura in filas:
        if not validar_cif(factura.tercero_cif):
            continue  # FR-017: sin CIF válido no entra en modelos oficiales
        acc = grupos.setdefault(
            factura.tercero_cif,
            {
                "tercero_cif": factura.tercero_cif,
                "tercero_razon_social": factura.tercero_razon_social,
                "base_retencion": Decimal("0"),
                "cuota_retencion": Decimal("0"),
                "facturas": set(),
            },
        )
        acc["base_retencion"] += linea.base_retencion or Decimal("0")
        acc["cuota_retencion"] += linea.cuota_retencion or Decimal("0")
        acc["facturas"].add(factura.id)

    por_perceptor = [
        {
            "tercero_cif": g["tercero_cif"],
            "tercero_razon_social": g["tercero_razon_social"],
            "base_retencion": cuantizar2(g["base_retencion"]),
            "cuota_retencion": cuantizar2(g["cuota_retencion"]),
            "numero_facturas": len(g["facturas"]),
        }
        for g in sorted(grupos.values(), key=lambda x: x["tercero_cif"])
    ]
    return {
        "tipo": tipo,
        "desde": desde,
        "hasta": hasta,
        "por_perceptor": por_perceptor,
        "total_base": cuantizar2(sum(p["base_retencion"] for p in por_perceptor)),
        "total_retencion": cuantizar2(sum(p["cuota_retencion"] for p in por_perceptor)),
    }