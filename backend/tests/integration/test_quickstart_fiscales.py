"""Quickstart end-to-end de la spec 005 (T059).

Recorre en orden los 4 escenarios de `specs/005-modulos-fiscales/quickstart.md`
sobre la app real (ASGI + SQLite + migraciones Alembic) a través del API público:

1. Factura de venta con IVA y asiento automático (+ duplicado 409).
2. Factura de compra con retención + Libros de IVA y resumen de retenciones.
3. Liquidación del IS + vista de presentación del 200 (borrador → 409 fichero).
4. Cierre, vista habilitada, descarga del 200, directorio `impuestos/` y
   regeneración idempotente con trazabilidad actualizada.

Sirve como verificación extremo a extremo de la puerta de salida de la spec.
"""

from decimal import ROUND_HALF_UP, Decimal
from hashlib import sha256
from pathlib import Path

from sqlmodel import select

from app.models import FicheroPresentacion
from app.services import aeat

_IMPUESTOS_DIR = Path(__file__).resolve().parents[2] / "impuestos"


def _headers(ctx):
    return {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }


def _cuota(base: str, factor: str) -> str:
    return str(
        (Decimal(base) * Decimal(factor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def _venta(numero, cif, base, tipo, cuota, fecha="2026-03-05"):
    return {
        "origen": "venta",
        "numero": numero,
        "fecha": fecha,
        "tercero_cif": cif,
        "tercero_razon_social": "Cliente SL",
        "lineas": [
            {
                "numero_linea": 1,
                "descripcion": "Servicio",
                "base_imponible": base,
                "tipo_iva": tipo,
                "cuota_iva": cuota,
            }
        ],
    }


def _compra_retencion(numero, cif, base, tipo_ret="111", pct="15.00", fecha="2026-03-05"):
    return {
        "origen": "compra",
        "numero": numero,
        "fecha": fecha,
        "tercero_cif": cif,
        "tercero_razon_social": "Proveedor SL",
        "tipo_retencion": tipo_ret,
        "lineas": [
            {
                "numero_linea": 1,
                "descripcion": "Servicio profesional",
                "base_imponible": base,
                "tipo_iva": "21.00",
                "cuota_iva": _cuota(base, "0.21"),
                "base_retencion": base,
                "pct_retencion": pct,
                "cuota_retencion": _cuota(base, str(Decimal(pct) / Decimal("100"))),
            }
        ],
    }


def _apuntes(client, headers, asiento_id):
    return client.get(f"/api/v1/asientos/{asiento_id}", headers=headers).json()["apuntes"]


def _por_codigo(apuntes):
    acc: dict[str, list[float]] = {}
    for a in apuntes:
        d, h = acc.get(a["cuenta_codigo"], [0.0, 0.0])
        acc[a["cuenta_codigo"]] = [d + float(a["debe"]), h + float(a["haber"])]
    return {k: (f"{v[0]:.2f}", f"{v[1]:.2f}") for k, v in acc.items()}


def _cuadra(apuntes):
    return sum(float(a["debe"]) for a in apuntes) == sum(float(a["haber"]) for a in apuntes)


def _parse(modelo, linea):
    plantilla = aeat.MODELOS[modelo][linea[:2]]
    out = {}
    offset = 2
    for campo in plantilla.campos:
        out[campo.nombre] = linea[offset : offset + campo.longitud]
        offset += campo.longitud
    return out


def _importe(s: str) -> Decimal:
    neg = s.startswith("-")
    digits = s[1:] if neg else s
    valor = Decimal(int(digits)) / Decimal("100")
    return -valor if neg else valor


def test_quickstart_fiscales_extremo_a_extremo(contexto_fiscal, client, session):
    ctx = contexto_fiscal()
    h = _headers(ctx)
    anio = ctx["ejercicio"].anio

    # =====================================================================
    # Escenario 1 — Factura de venta con IVA y asiento automático
    # =====================================================================
    r = client.post(
        "/api/v1/facturas",
        headers=h,
        json=_venta("FV-001", "B12345674", "1000.00", "21.00", "210.00"),
    )
    assert r.status_code == 201, r.text
    venta = r.json()
    assert venta["asiento_id"] is not None

    apuntes = _apuntes(client, h, venta["asiento_id"])
    por_codigo = _por_codigo(apuntes)
    assert por_codigo["430"] == ("1210.00", "0.00")
    assert por_codigo["700"] == ("0.00", "1000.00")
    assert por_codigo["477"] == ("0.00", "210.00")
    assert _cuadra(apuntes)

    diario = client.get("/api/v1/asientos", headers=h).json()
    detalle = next(a for a in diario["items"] if a["id"] == venta["asiento_id"])
    assert detalle["estado"] == "asentado" and detalle["numero"] == 1

    # Duplicado mismo CIF+numero -> 409
    dup = client.post(
        "/api/v1/facturas",
        headers=h,
        json=_venta("FV-001", "B12345674", "1000.00", "21.00", "210.00"),
    )
    assert dup.status_code == 409

    # =====================================================================
    # Escenario 2 — Compra con retención 111 + Libros/Retenciones
    # =====================================================================
    r = client.post(
        "/api/v1/facturas",
        headers=h,
        json=_compra_retencion("FC-001", "B12345674", "1000.00"),
    )
    assert r.status_code == 201, r.text
    compra = r.json()
    apuntes = _apuntes(client, h, compra["asiento_id"])
    por_codigo = _por_codigo(apuntes)
    assert por_codigo["600"] == ("1000.00", "0.00")
    assert por_codigo["472"] == ("210.00", "0.00")
    assert por_codigo["400"] == ("0.00", "1060.00")
    assert por_codigo["4751"] == ("0.00", "150.00")
    assert _cuadra(apuntes)

    # 2ª factura del mismo CIF con retención
    assert (
        client.post(
            "/api/v1/facturas",
            headers=h,
            json=_compra_retencion("FC-002", "B12345674", "1000.00"),
        ).status_code
        == 201
    )

    ret = client.get(
        f"/api/v1/facturas/retenciones?tipo=111&desde={anio}-01-01&hasta={anio}-12-31",
        headers=h,
    )
    assert ret.status_code == 200, ret.text
    resumen = ret.json()
    assert len(resumen["por_perceptor"]) == 1
    assert resumen["por_perceptor"][0]["tercero_cif"] == "B12345674"
    assert resumen["total_base"] == "2000.00"
    assert resumen["total_retencion"] == "300.00"

    libro = client.get(
        f"/api/v1/facturas/libros/iva?origen=soportado&desde={anio}-01-01&hasta={anio}-12-31",
        headers=h,
    )
    assert libro.status_code == 200, libro.text
    assert len(libro.json()["operaciones"]) == 2
    assert libro.json()["total_base"] == "2000.00"

    # =====================================================================
    # Escenario 3 — Liquidación IS y vista de presentación (borrador)
    # =====================================================================
    r = client.post(
        "/api/v1/is",
        headers=h,
        json={
            "resultado_contable": "100000.00",
            "ajustes": [
                {"concepto": "Multas", "sentido": "aumento", "importe": "5000.00"},
                {"concepto": "Insolvencias", "sentido": "disminucion", "importe": "8000.00"},
            ],
            "tipo_gravamen": "25.00",
            "retenciones_pagos_cuenta": "4000.00",
        },
    )
    assert r.status_code == 201, r.text

    liq = client.get("/api/v1/is", headers=h).json()
    assert liq["base_imponible"] == "97000.00"
    assert liq["cuota_integra"] == "24250.00"
    assert liq["cuota_diferencial"] == "20250.00"

    vista = client.get(f"/api/v1/presentaciones/200?periodo={anio}", headers=h).json()
    assert vista["resumen"]["base_imponible"] == "97000.00"
    assert vista["casillas"] and all("casilla" in c for c in vista["casillas"])
    assert vista["bloque_descarga"]["habilitado"] is False

    r = client.get(f"/api/v1/presentaciones/200/fichero?periodo={anio}", headers=h)
    assert r.status_code == 409

    # =====================================================================
    # Escenario 4 — Cierre, vista habilitada, descarga y regeneración
    # =====================================================================
    r = client.post("/api/v1/is/cerrar", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "cerrada"

    # Tras cerrar, PUT -> 409 (inmutable, contrato is.md)
    assert (
        client.put(
            "/api/v1/is", headers=h, json={"resultado_contable": "0.00", "ajustes": []}
        ).status_code
        == 409
    )

    vista2 = client.get(f"/api/v1/presentaciones/200?periodo={anio}", headers=h).json()
    assert vista2["bloque_descarga"]["habilitado"] is True

    r = client.get(f"/api/v1/presentaciones/200/fichero?periodo={anio}", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("text/plain")
    assert f'filename="200_{anio}.txt"' in r.headers.get("content-disposition", "")

    lineas = r.text.splitlines()
    assert aeat.validar_formato("200", lineas) == []
    cabecera = _parse("200", lineas[0])
    assert cabecera["nif"] == ctx["empresa"].cif
    assert cabecera["razon_social"].strip() == ctx["empresa"].razon_social
    casillas = {
        int(_parse("200", ln)["casilla"]): _importe(_parse("200", ln)["importe"])
        for ln in lineas
        if ln[:2] == "02"
    }
    assert casillas[300] == Decimal("97000.00")
    assert casillas[500] == Decimal("24250.00")
    assert casillas[598] == Decimal("20250.00")

    ruta = _IMPUESTOS_DIR / str(ctx["empresa"].id) / str(anio) / f"200_{anio}.txt"
    assert ruta.exists()
    assert sha256(r.content).hexdigest() == sha256(ruta.read_bytes()).hexdigest()

    fila = session.exec(
        select(FicheroPresentacion).where(
            FicheroPresentacion.ejercicio_id == ctx["ejercicio"].id,
            FicheroPresentacion.modelo == "200",
        )
    ).one()
    generado_antes = fila.generado_at

    # Regenerar: borrar el fichero y repetir la descarga -> mismo nombre, fila única
    ruta.unlink()
    r2 = client.get(f"/api/v1/presentaciones/200/fichero?periodo={anio}", headers=h)
    assert r2.status_code == 200
    assert ruta.exists()
    session.expire_all()
    filas = session.exec(
        select(FicheroPresentacion).where(
            FicheroPresentacion.ejercicio_id == ctx["ejercicio"].id,
            FicheroPresentacion.modelo == "200",
        )
    ).all()
    assert len(filas) == 1
    assert filas[0].generado_at >= generado_antes
    assert r2.content == r.content
