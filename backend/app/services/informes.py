import csv
import io
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.contable import Apunte, Asiento, Cuenta


def _dos_decimales(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"))


def sumas_por_cuenta(
    session: Session,
    ejercicio_id: int,
    desde: date | None = None,
    hasta: date | None = None,
) -> dict[int, tuple[Decimal, Decimal]]:
    stmt = (
        select(Apunte.cuenta_id, func.sum(Apunte.debe), func.sum(Apunte.haber))
        .join(Asiento, Asiento.id == Apunte.asiento_id)
        .where(Asiento.ejercicio_id == ejercicio_id)
        .where(Asiento.estado == "asentado")
    )
    if desde:
        stmt = stmt.where(Asiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(Asiento.fecha <= hasta)

    stmt = stmt.group_by(Apunte.cuenta_id)

    result = session.exec(stmt).all()
    return {
        cuenta_id: (_dos_decimales(debe or Decimal(0)), _dos_decimales(haber or Decimal(0)))
        for cuenta_id, debe, haber in result
    }


def _get_cuentas_dict(session: Session, ejercicio_id: int) -> dict[int, Cuenta]:
    cuentas = session.exec(select(Cuenta).where(Cuenta.ejercicio_id == ejercicio_id)).all()
    return {c.id: c for c in cuentas}


def _build_codigo_to_id(cuentas: dict[int, Cuenta]) -> dict[str, int]:
    return {c.codigo: c.id for c in cuentas.values()}


def propagar_jerarquia(
    cuentas: dict[int, Cuenta],
    sumas: dict[int, tuple[Decimal, Decimal]],
) -> dict[int, tuple[Decimal, Decimal]]:
    codigo_to_id = _build_codigo_to_id(cuentas)
    cuentas_ordenadas = sorted(cuentas.values(), key=lambda c: len(c.codigo), reverse=True)
    acumuladas = dict(sumas)

    for cuenta in cuentas_ordenadas:
        if cuenta.id in acumuladas:
            debe, haber = acumuladas[cuenta.id]
        else:
            debe, haber = Decimal(0), Decimal(0)

        if cuenta.nivel > 1:
            prefijo = cuenta.codigo[: cuenta.nivel - 1]
            if prefijo in codigo_to_id:
                ancestro_id = codigo_to_id[prefijo]
                if ancestro_id in acumuladas:
                    a_debe, a_haber = acumuladas[ancestro_id]
                else:
                    a_debe, a_haber = Decimal(0), Decimal(0)
                acumuladas[ancestro_id] = (a_debe + debe, a_haber + haber)

    return acumuladas


def clasificar_saldo(saldo: Decimal) -> Literal["deudor", "acreedor", "cero"]:
    if saldo > 0:
        return "deudor"
    if saldo < 0:
        return "acreedor"
    return "cero"


def _saldo_deudor_acreedor(saldo: Decimal) -> tuple[Decimal, Decimal]:
    if saldo > 0:
        return saldo, Decimal(0)
    if saldo < 0:
        return Decimal(0), -saldo
    return Decimal(0), Decimal(0)


def _get_subarbol_ids(session: Session, ejercicio_id: int, codigo_padre: str) -> list[int]:
    cuentas = session.exec(select(Cuenta).where(Cuenta.ejercicio_id == ejercicio_id)).all()
    return [c.id for c in cuentas if c.codigo.startswith(codigo_padre)]


def mayor_cuenta(
    session: Session,
    ejercicio_id: int,
    codigo: str,
    desde: date | None = None,
    hasta: date | None = None,
):
    cuenta = session.exec(
        select(Cuenta).where(Cuenta.ejercicio_id == ejercicio_id, Cuenta.codigo == codigo)
    ).first()
    if not cuenta:
        return None

    codigos_subarbol = _get_subarbol_ids(session, ejercicio_id, cuenta.codigo)

    saldo_inicial = Decimal(0)
    if desde:
        stmt_inicial = (
            select(
                func.sum(Apunte.debe).label("debe"),
                func.sum(Apunte.haber).label("haber"),
            )
            .join(Asiento, Asiento.id == Apunte.asiento_id)
            .where(Asiento.ejercicio_id == ejercicio_id)
            .where(Asiento.estado == "asentado")
            .where(Apunte.cuenta_id.in_(codigos_subarbol))
            .where(Asiento.fecha < desde)
        )
        res_inicial = session.exec(stmt_inicial).first()
        saldo_inicial = _dos_decimales(
            (res_inicial.debe or Decimal(0)) - (res_inicial.haber or Decimal(0))
        )

    stmt_mov = (
        select(Apunte, Asiento)
        .join(Asiento, Asiento.id == Apunte.asiento_id)
        .where(Asiento.ejercicio_id == ejercicio_id)
        .where(Asiento.estado == "asentado")
        .where(Apunte.cuenta_id.in_(codigos_subarbol))
    )
    if desde:
        stmt_mov = stmt_mov.where(Asiento.fecha >= desde)
    if hasta:
        stmt_mov = stmt_mov.where(Asiento.fecha <= hasta)

    stmt_mov = stmt_mov.order_by(Asiento.fecha, Asiento.numero, Apunte.id)

    movimientos = []
    saldo = saldo_inicial
    total_debe = Decimal(0)
    total_haber = Decimal(0)

    for apunte, asiento in session.exec(stmt_mov).all():
        d = _dos_decimales(apunte.debe)
        h = _dos_decimales(apunte.haber)
        total_debe += d
        total_haber += h
        saldo += d - h
        movimientos.append(
            {
                "fecha": asiento.fecha,
                "numero": asiento.numero,
                "asiento_id": asiento.id,
                "concepto": asiento.concepto,
                "debe": d,
                "haber": h,
                "saldo": _dos_decimales(saldo),
            }
        )

    return {
        "cuenta": {"codigo": cuenta.codigo, "nombre": cuenta.nombre, "nivel": cuenta.nivel},
        "desde": desde,
        "hasta": hasta,
        "saldo_inicial": _dos_decimales(saldo_inicial),
        "movimientos": movimientos,
        "total_debe": _dos_decimales(total_debe),
        "total_haber": _dos_decimales(total_haber),
        "saldo_final": _dos_decimales(saldo_inicial + total_debe - total_haber),
    }


def mayor_cuentas(
    session: Session,
    ejercicio_id: int,
    desde: date | None = None,
    hasta: date | None = None,
):
    sumas = sumas_por_cuenta(session, ejercicio_id, desde, hasta)
    cuentas_dict = _get_cuentas_dict(session, ejercicio_id)
    sumas_jerarquia = propagar_jerarquia(cuentas_dict, sumas)

    filas = []
    for cuenta_id, (suma_debe, suma_haber) in sumas_jerarquia.items():
        cuenta = cuentas_dict[cuenta_id]
        saldo = _dos_decimales(suma_debe - suma_haber)
        if suma_debe > 0 or suma_haber > 0:
            filas.append(
                {
                    "codigo": cuenta.codigo,
                    "nombre": cuenta.nombre,
                    "nivel": cuenta.nivel,
                    "suma_debe": _dos_decimales(suma_debe),
                    "suma_haber": _dos_decimales(suma_haber),
                    "saldo": saldo,
                    "saldo_tipo": clasificar_saldo(saldo),
                }
            )

    filas.sort(key=lambda x: x["codigo"])
    return {"ejercicio_id": ejercicio_id, "desde": desde, "hasta": hasta, "cuentas": filas}


def balance(
    session: Session,
    ejercicio_id: int,
    desde: date | None = None,
    hasta: date | None = None,
):
    sumas = sumas_por_cuenta(session, ejercicio_id, desde, hasta)
    cuentas_dict = _get_cuentas_dict(session, ejercicio_id)
    sumas_jerarquia = propagar_jerarquia(cuentas_dict, sumas)

    filas = []
    total_debe = Decimal(0)
    total_haber = Decimal(0)
    total_saldo_deudor = Decimal(0)
    total_saldo_acreedor = Decimal(0)

    for cuenta_id, (suma_debe, suma_haber) in sumas_jerarquia.items():
        cuenta = cuentas_dict[cuenta_id]
        if suma_debe == 0 and suma_haber == 0:
            continue
        saldo = _dos_decimales(suma_debe - suma_haber)
        s_deudor, s_acreedor = _saldo_deudor_acreedor(saldo)
        filas.append(
            {
                "codigo": cuenta.codigo,
                "nombre": cuenta.nombre,
                "nivel": cuenta.nivel,
                "suma_debe": _dos_decimales(suma_debe),
                "suma_haber": _dos_decimales(suma_haber),
                "saldo_deudor": s_deudor,
                "saldo_acreedor": s_acreedor,
            }
        )
        total_debe += _dos_decimales(suma_debe)
        total_haber += _dos_decimales(suma_haber)
        total_saldo_deudor += s_deudor
        total_saldo_acreedor += s_acreedor

    filas.sort(key=lambda x: x["codigo"])
    cuadra = total_debe == total_haber

    return {
        "ejercicio_id": ejercicio_id,
        "desde": desde,
        "hasta": hasta,
        "filas": filas,
        "total_debe": _dos_decimales(total_debe),
        "total_haber": _dos_decimales(total_haber),
        "total_saldo_deudor": _dos_decimales(total_saldo_deudor),
        "total_saldo_acreedor": _dos_decimales(total_saldo_acreedor),
        "cuadra": cuadra,
    }


def _generar_encabezado_csv(
    ejercicio_id: int,
    empresa_razon: str,
    empresa_cif: str,
    titulo: str,
    desde: date | None,
    hasta: date | None,
) -> list[list[str]]:
    lineas = []
    lineas.append([f"Empresa: {empresa_razon}"])
    lineas.append([f"CIF: {empresa_cif}"])
    lineas.append([f"Ejercicio: {ejercicio_id}"])
    rango = f"{desde.isoformat() if desde else 'Inicio'} - {hasta.isoformat() if hasta else 'Fin'}"
    lineas.append([f"Periodo: {rango}"])
    lineas.append([f"Informe: {titulo}"])
    lineas.append([f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    lineas.append([])
    return lineas


def _formato_numero(v: Decimal) -> str:
    return f"{v:.2f}".replace(".", ",")


def exportar_csv(
    session: Session,
    ejercicio_id: int,
    empresa_razon: str,
    empresa_cif: str,
    tipo: Literal["mayor", "balance"],
    **kwargs,
) -> bytes:
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")

    if tipo == "mayor":
        codigo = kwargs.get("cuenta")
        desde = kwargs.get("desde")
        hasta = kwargs.get("hasta")
        data = mayor_cuenta(session, ejercicio_id, codigo, desde, hasta)
        if not data:
            return b""

        writer.writerows(
            _generar_encabezado_csv(
                ejercicio_id, empresa_razon, empresa_cif, "Libro Mayor", desde, hasta
            )
        )
        writer.writerow(["Fecha", "Nº", "Concepto", "Debe", "Haber", "Saldo"])
        for m in data["movimientos"]:
            writer.writerow(
                [
                    m["fecha"].isoformat(),
                    str(m["numero"]),
                    m["concepto"],
                    _formato_numero(m["debe"]),
                    _formato_numero(m["haber"]),
                    _formato_numero(m["saldo"]),
                ]
            )
        writer.writerow(
            [
                "",
                "",
                "TOTALES",
                _formato_numero(data["total_debe"]),
                _formato_numero(data["total_haber"]),
                _formato_numero(data["saldo_final"]),
            ]
        )

    elif tipo == "balance":
        desde = kwargs.get("desde")
        hasta = kwargs.get("hasta")
        data = balance(session, ejercicio_id, desde, hasta)

        writer.writerows(
            _generar_encabezado_csv(
                ejercicio_id, empresa_razon, empresa_cif, "Balance de Sumas y Saldos", desde, hasta
            )
        )
        writer.writerow(
            [
                "Código",
                "Nombre",
                "Nivel",
                "Suma Debe",
                "Suma Haber",
                "Saldo Deudor",
                "Saldo Acreedor",
            ]
        )
        for f in data["filas"]:
            writer.writerow(
                [
                    f["codigo"],
                    f["nombre"],
                    str(f["nivel"]),
                    _formato_numero(f["suma_debe"]),
                    _formato_numero(f["suma_haber"]),
                    _formato_numero(f["saldo_deudor"]),
                    _formato_numero(f["saldo_acreedor"]),
                ]
            )
        writer.writerow(
            [
                "",
                "",
                "",
                _formato_numero(data["total_debe"]),
                _formato_numero(data["total_haber"]),
                _formato_numero(data["total_saldo_deudor"]),
                _formato_numero(data["total_saldo_acreedor"]),
            ]
        )

    return output.getvalue().encode("utf-8-sig")


def exportar_pdf(
    session: Session,
    ejercicio_id: int,
    empresa_razon: str,
    empresa_cif: str,
    tipo: Literal["mayor", "balance"],
    **kwargs,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    elements = []

    desde = kwargs.get("desde")
    hasta = kwargs.get("hasta")

    encabezado = [
        [f"Empresa: {empresa_razon}"],
        [f"CIF: {empresa_cif}"],
        [f"Ejercicio: {ejercicio_id}"],
        [f"Periodo: {desde.isoformat() if desde else 'Inicio'} - "
         f"{hasta.isoformat() if hasta else 'Fin'}"],
        [f"Informe: {'Libro Mayor' if tipo == 'mayor' else 'Balance de Sumas y Saldos'}"],
        [f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
    ]
    t_enc = Table(encabezado, colWidths=[18 * cm])
    t_enc.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elements.append(t_enc)
    elements.append(Table([[""]], colWidths=[18 * cm]))

    if tipo == "mayor":
        codigo = kwargs.get("cuenta")
        data = mayor_cuenta(session, ejercicio_id, codigo, desde, hasta)
        if not data:
            return b""

        head = [["Fecha", "Nº", "Concepto", "Debe", "Haber", "Saldo"]]
        rows = []
        for m in data["movimientos"]:
            rows.append(
                [
                    m["fecha"].isoformat(),
                    str(m["numero"]),
                    m["concepto"],
                    _formato_numero(m["debe"]),
                    _formato_numero(m["haber"]),
                    _formato_numero(m["saldo"]),
                ]
            )
        rows.append(
            [
                "",
                "",
                "TOTALES",
                _formato_numero(data["total_debe"]),
                _formato_numero(data["total_haber"]),
                _formato_numero(data["saldo_final"]),
            ]
        )
        table_data = head + rows
        col_widths = [2.5 * cm, 1 * cm, 7 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm]

    else:
        data = balance(session, ejercicio_id, desde, hasta)
        head = [
            [
                "Código",
                "Nombre",
                "Nivel",
                "Suma Debe",
                "Suma Haber",
                "Saldo Deudor",
                "Saldo Acreedor",
            ]
        ]
        rows = []
        for f in data["filas"]:
            rows.append(
                [
                    f["codigo"],
                    f["nombre"],
                    str(f["nivel"]),
                    _formato_numero(f["suma_debe"]),
                    _formato_numero(f["suma_haber"]),
                    _formato_numero(f["saldo_deudor"]),
                    _formato_numero(f["saldo_acreedor"]),
                ]
            )
        rows.append(
            [
                "",
                "",
                "",
                _formato_numero(data["total_debe"]),
                _formato_numero(data["total_haber"]),
                _formato_numero(data["total_saldo_deudor"]),
                _formato_numero(data["total_saldo_acreedor"]),
            ]
        )
        table_data = head + rows
        col_widths = [1.5 * cm, 6 * cm, 1 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm]

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ])
    t.setStyle(style)
    elements.append(t)

    doc.build(elements)
    return buffer.getvalue()