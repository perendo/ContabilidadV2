import hashlib
import io
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

import openpyxl
import pandas as pd
from sqlmodel import Session, select

from app.models.contable import (
    Cuenta,
    MovimientoBanco,
)
from app.schemas.banco import (
    ImportResponse,
    MovimientoBancoIn,
)

# =============================================================================
# Utilidades compartidas
# =============================================================================

def calcular_hash_unicidad(fecha_valor: date, importe: Decimal, referencia: str | None) -> str:
    """Calcula SHA256 para deduplicación de movimientos."""
    base = f"{fecha_valor.isoformat()}|{importe:.2f}|{referencia or ''}"
    return hashlib.sha256(base.encode()).hexdigest()


def validar_cuentas_regla(
    session: Session, ejercicio_id: int, cuenta_debe: str, cuenta_haber: str
) -> tuple[Cuenta, Cuenta]:
    """Valida que las cuentas existan en el ejercicio activo."""
    cuenta_debe_obj = session.exec(
        select(Cuenta).where(Cuenta.ejercicio_id == ejercicio_id, Cuenta.codigo == cuenta_debe)
    ).first()
    if not cuenta_debe_obj:
        raise ValueError(f"Cuenta debe '{cuenta_debe}' no existe en el ejercicio {ejercicio_id}")

    cuenta_haber_obj = session.exec(
        select(Cuenta).where(Cuenta.ejercicio_id == ejercicio_id, Cuenta.codigo == cuenta_haber)
    ).first()
    if not cuenta_haber_obj:
        raise ValueError(f"Cuenta haber '{cuenta_haber}' no existe en el ejercicio {ejercicio_id}")

    return cuenta_debe_obj, cuenta_haber_obj


def convertir_signo_banco_a_contable(
    importe: Decimal, codigo_banco: str | None
) -> tuple[Decimal, Decimal]:
    """
    Convierte importe con signo bancario a debe/haber contable.
    Banco: negativo = cargo (salida), positivo = abono (entrada).
    Regla define cuentas contables (debe/haber positivo).
    """
    if importe < 0:
        return abs(importe), Decimal("0")
    return Decimal("0"), importe


# =============================================================================
# Detección de formato
# =============================================================================

def detectar_formato(file_bytes: bytes, filename: str) -> Literal["excel", "csv", "csb"]:
    """Detecta el formato del archivo por extensión y contenido."""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext in ("xlsx", "xls"):
        return "excel"
    if ext in ("csv",):
        return "csv"
    if ext in ("csb", "txt", "43"):
        return "csb"

    # Sniffing por contenido
    if (
        file_bytes.startswith(b"PK\x03\x04")
        or file_bytes.startswith(b"PK\x05\x06")
        or file_bytes.startswith(b"PK\x07\x08")
    ):
        return "excel"
    if b";" in file_bytes[:200] and b"," in file_bytes[:200]:
        return "csv"
    if file_bytes[:2] in (b"01", b"02", b"03", b"99"):
        return "csb"

    # Default
    return "csv"


# =============================================================================
# Parsers
# =============================================================================

def parse_excel_santander(file_bytes: bytes) -> list[MovimientoBancoIn]:
    """
    Parsea Excel Santander (formato real detectado en Data/1. MovimientosCuenta ene_feb26.xlsx):
    - 7 filas de cabecera informativa
    - Fila 8: headers
    - Filas 9+: datos
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active

    # Buscar fila de headers (contiene "Fecha Operación")
    header_row = None
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True), 1):
        if row and row[0] and "Fecha Operaci" in str(row[0]):
            header_row = i
            break

    if header_row is None:
        raise ValueError("No se encontró fila de headers en Excel Santander")

    # Leer datos desde la fila siguiente
    datos = []
    for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row, values_only=True):
        if not row or not row[0]:
            continue
        if not isinstance(row[0], (date, datetime)):
            continue

        fecha_operacion = (
            row[0]
            if isinstance(row[0], date)
            else datetime.strptime(str(row[0]), "%d/%m/%Y").date()
        )
        fecha_valor = (
            row[1]
            if isinstance(row[1], date)
            else datetime.strptime(str(row[1]), "%d/%m/%Y").date()
        )

        # Importe puede venir como float o string
        importe_raw = row[3]
        if isinstance(importe_raw, str):
            importe_raw = importe_raw.replace(".", "").replace(",", ".")
        importe = Decimal(str(importe_raw))

        saldo_raw = row[5]
        if isinstance(saldo_raw, str):
            saldo_raw = saldo_raw.replace(".", "").replace(",", ".")
        saldo = Decimal(str(saldo_raw))

        datos.append(MovimientoBancoIn(
            fecha_operacion=fecha_operacion,
            fecha_valor=fecha_valor,
            concepto=str(row[2] or ""),
            importe=importe,
            saldo=saldo,
            divisa=str(row[4] or "EUR"),
            codigo_banco=str(row[7] or ""),
            numero_documento=str(row[8] or "") if row[8] else None,
            referencia=str(row[9] or "") if row[9] else None,
            referencia_2=str(row[10] or "") if row[10] else None,
            info_adicional=str(row[11] or "") if row[11] else None,
            hash_unicidad="",  # se calcula luego
            origen_archivo="excel",
        ))

    return datos


def parse_csv_estandar(file_bytes: bytes) -> list[MovimientoBancoIn]:
    """
    Parsea CSV estándar español (separador ;, decimal ,, encoding UTF-8/Latin1).
    """
    # Detectar encoding
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")

    # Usar pandas para parseo robusto
    df = pd.read_csv(io.StringIO(text), sep=";", decimal=",", encoding="utf-8", dtype=str)

    # Normalizar nombres de columnas
    df.columns = [
        c.strip().lower().replace(" ", "_").replace("ó", "o").replace("á", "a")
        for c in df.columns
    ]

    # Mapear columnas esperadas
    col_map = {
        "fecha_operacion": [
            "fecha_operacion",
            "fecha_operación",
            "fecha operacion",
            "fecha operación",
        ],
        "fecha_valor": ["fecha_valor", "fecha valor"],
        "concepto": ["concepto"],
        "importe": ["importe"],
        "divisa": ["divisa"],
        "saldo": ["saldo"],
        "codigo_banco": ["codigo", "código", "codigo_banco", "código_banco"],
        "numero_documento": ["numero_documento", "número_documento", "nº_documento"],
        "referencia": ["referencia_1", "referencia1"],
        "referencia_2": ["referencia_2", "referencia2"],
        "info_adicional": ["info_adicional", "informacion_adicional", "información_adicional"],
    }

    # Encontrar columnas reales
    real_cols = {}
    for std_col, candidates in col_map.items():
        for c in candidates:
            if c in df.columns:
                real_cols[std_col] = c
                break

    required = ["fecha_operacion", "fecha_valor", "concepto", "importe", "saldo"]
    for r in required:
        if r not in real_cols:
            raise ValueError(f"Columna requerida no encontrada en CSV: {r}")

    datos = []
    for _, row in df.iterrows():
        try:
            fecha_operacion = datetime.strptime(
                str(row[real_cols["fecha_operacion"]]).strip(), "%d/%m/%Y"
            ).date()
            fecha_valor = datetime.strptime(
                str(row[real_cols["fecha_valor"]]).strip(), "%d/%m/%Y"
            ).date()
            concepto = str(row[real_cols["concepto"]]).strip()
            importe = Decimal(
                str(row[real_cols["importe"]]).replace(".", "").replace(",", ".")
            )
            saldo = Decimal(str(row[real_cols["saldo"]]).replace(".", "").replace(",", "."))

            datos.append(
                MovimientoBancoIn(
                    fecha_operacion=fecha_operacion,
                    fecha_valor=fecha_valor,
                    concepto=concepto,
                    importe=importe,
                    saldo=saldo,
                    divisa=str(row.get(real_cols.get("divisa", ""), "EUR")).strip(),
                    codigo_banco=(
                        str(row.get(real_cols.get("codigo_banco", ""), "")).strip() or None
                    ),
                    numero_documento=(
                        str(row.get(real_cols.get("numero_documento", ""), "")).strip() or None
                    ),
                    referencia=(
                        str(row.get(real_cols.get("referencia", ""), "")).strip() or None
                    ),
                    referencia_2=(
                        str(row.get(real_cols.get("referencia_2", ""), "")).strip() or None
                    ),
                    info_adicional=(
                        str(row.get(real_cols.get("info_adicional", ""), "")).strip() or None
                    ),
                    hash_unicidad="",
                    origen_archivo="csv",
                )
            )
        except Exception:  # noqa: S112 - se descartan filas mal formadas a propósito
            continue

    return datos


def parse_csb_cuaderno43(file_bytes: bytes) -> list[MovimientoBancoIn]:
    """
    Parsea CSB / Cuaderno 43 (AEB Norma 43).
    Formato: registros de longitud fija, tipo 01=cabecera, 02=movimientos, 03=totales, 99=final.
    Registro 02 (movimiento): posiciones fijas según especificación AEB.
    """
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")

    datos = []
    lines = text.strip().split("\n")

    for line in lines:
        if not line:
            continue
        tipo = line[:2]
        if tipo != "02":
            continue  # Solo procesar registros de movimiento (tipo 02)

        # Parser según AEB Norma 43 (registro tipo 02)
        # Posiciones aproximadas (ajustar según spec exacta):
        # 0-1: tipo (02)
        # 2-9: fecha operación (DDMMAAAA)
        # 10-17: fecha valor (DDMMAAAA)
        # 18-25: importe (15 enteros + 2 decimales, con signo)
        # ...
        # Como la especificación exacta varía, implementamos parser básico
        try:
            fecha_operacion = datetime.strptime(line[2:10], "%d%m%Y").date()
            fecha_valor = datetime.strptime(line[10:18], "%d%m%Y").date()

            # Importe en posición 18-35 (18 dígitos: 15 enteros + 2 decimales + signo)
            importe_str = line[18:36].strip()
            if importe_str.startswith("-"):
                signo = -1
                importe_str = importe_str[1:]
            else:
                signo = 1
            if len(importe_str) >= 2:
                importe = Decimal(importe_str[:-2] + "." + importe_str[-2:]) * signo
            else:
                importe = Decimal("0")

            # Concepto: posición 36-70 (35 chars)
            concepto = line[36:71].strip()

            # Resto de campos según especificación
            datos.append(MovimientoBancoIn(
                fecha_operacion=fecha_operacion,
                fecha_valor=fecha_valor,
                concepto=concepto,
                importe=importe,
                saldo=Decimal("0"),  # No viene en registro 02 estándar
                divisa="EUR",
                codigo_banco=line[71:74].strip() or None,
                numero_documento=line[74:94].strip() or None,
                referencia=line[94:114].strip() or None,
                referencia_2=line[114:134].strip() or None,
                info_adicional=None,
                hash_unicidad="",
                origen_archivo="csb",
            ))
        except Exception:  # noqa: S112 - se descartan registros mal formados a propósito
            continue

    return datos


# =============================================================================
# Importación principal
# =============================================================================

def importar_extractos(
    session: Session,
    ejercicio_id: int,
    file_bytes: bytes,
    filename: str,
    ignorar_duplicados: bool = False,
) -> ImportResponse:
    """
    Importa extracto bancario detectando formato automáticamente.
    Deduplica por hash_unicidad (fecha_valor + importe + referencia).
    """
    formato = detectar_formato(file_bytes, filename)

    if formato == "excel":
        movimientos = parse_excel_santander(file_bytes)
    elif formato == "csv":
        movimientos = parse_csv_estandar(file_bytes)
    elif formato == "csb":
        movimientos = parse_csb_cuaderno43(file_bytes)
    else:
        raise ValueError(f"Formato no soportado: {formato}")

    importados = 0
    duplicados = 0
    errores = []

    for mov in movimientos:
        # Calcular hash de unicidad
        mov.hash_unicidad = calcular_hash_unicidad(mov.fecha_valor, mov.importe, mov.referencia)

        # Verificar duplicado
        existente = session.exec(
            select(MovimientoBanco).where(
                MovimientoBanco.ejercicio_id == ejercicio_id,
                MovimientoBanco.hash_unicidad == mov.hash_unicidad,
            )
        ).first()

        if existente:
            duplicados += 1
            if not ignorar_duplicados:
                errores.append(f"Duplicado: {mov.fecha_valor} {mov.importe} {mov.referencia}")
            continue

        # Insertar
        mov_obj = MovimientoBanco(
            ejercicio_id=ejercicio_id,
            fecha_operacion=mov.fecha_operacion,
            fecha_valor=mov.fecha_valor,
            concepto=mov.concepto,
            referencia=mov.referencia,
            referencia_2=mov.referencia_2,
            importe=mov.importe,
            saldo=mov.saldo,
            divisa=mov.divisa,
            codigo_banco=mov.codigo_banco,
            numero_documento=mov.numero_documento,
            info_adicional=mov.info_adicional,
            procesado=False,
            hash_unicidad=mov.hash_unicidad,
            origen_archivo=mov.origen_archivo,
        )
        session.add(mov_obj)
        importados += 1

    session.commit()
    return ImportResponse(
        importados=importados,
        duplicados=duplicados,
        errores=errores,
        formato_detectado=formato,
    )