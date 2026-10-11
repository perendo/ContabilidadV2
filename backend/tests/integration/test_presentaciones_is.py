"""Tests de la Liquidación del IS (US5) y de la Presentación AEAT (US-PRES).

Cubre T039-T049: cálculo base/cuota/diferencial, inmutabilidad al cerrar,
generación de ficheros 303/111/115/200 de posiciones fijas validados contra la
plantilla, bloqueo en borrador (409) y trazabilidad en `impuestos/`.
"""

from decimal import Decimal
from pathlib import Path

from app.services import aeat

_IMPUESTOS_DIR = Path(__file__).resolve().parents[2] / "impuestos"


def _headers(ctx):
    return {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }


def _venta(numero="FV-001", cif="B12345674", base="1000.00", tipo="21.00", cuota="210.00", fecha="2026-02-10"):
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


def _compra_retencion(numero, cif="B12345674", base="1000.00", tipo_ret="111", pct="15.00", fecha="2026-02-10"):
    from decimal import ROUND_HALF_UP

    cuota = str((Decimal(base) * Decimal("0.21")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    rete = str((Decimal(base) * Decimal(pct) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
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
                "cuota_iva": cuota,
                "base_retencion": base,
                "pct_retencion": pct,
                "cuota_retencion": rete,
            }
        ],
    }


def _cerrar_ejercicio(session, ctx):
    ctx["ejercicio"].estado = "cerrado"
    session.commit()


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


# =============================================================================
# US5 — Liquidación del Impuesto sobre Sociedades
# =============================================================================


def test_is_calculo_base_cuota_diferencial(contexto_fiscal, client):
    """T039: resultado + ajustes -> base, cuota integra (25%) y diferencial."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    payload = {
        "resultado_contable": "100000.00",
        "ajustes": [
            {"concepto": "Multas y sanciones", "sentido": "aumento", "importe": "5000.00"},
            {"concepto": "Insolvencias deducibles", "sentido": "disminucion", "importe": "8000.00"},
        ],
        "tipo_gravamen": "25.00",
        "retenciones_pagos_cuenta": "4000.00",
    }
    r = client.post("/api/v1/is", headers=h, json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["estado"] == "borrador"

    r2 = client.get("/api/v1/is", headers=h)
    assert r2.status_code == 200
    liq = r2.json()
    assert liq["resultado_contable"] == "100000.00"
    assert liq["base_imponible"] == "97000.00"
    assert liq["cuota_integra"] == "24250.00"
    assert liq["cuota_diferencial"] == "20250.00"
    assert len(liq["ajustes"]) == 2


def test_is_a_devolver_cuota_negativa(contexto_fiscal, client):
    """T040: retenciones > cuota integra -> cuota diferencial negativa (a devolver)."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    r = client.post(
        "/api/v1/is",
        headers=h,
        json={
            "resultado_contable": "100000.00",
            "ajustes": [],
            "tipo_gravamen": "25.00",
            "retenciones_pagos_cuenta": "30000.00",
        },
    )
    assert r.status_code == 201, r.text
    liq = client.get("/api/v1/is", headers=h).json()
    assert liq["base_imponible"] == "100000.00"
    assert liq["cuota_integra"] == "25000.00"
    assert liq["cuota_diferencial"] == "-5000.00"


def test_is_una_por_ejercicio_y_cierre_inmutable(contexto_fiscal, client):
    """T041: 2o POST -> 409; cerrar congela; 2o cierre -> 409."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    payload = {"resultado_contable": "50000.00", "ajustes": [], "retenciones_pagos_cuenta": "0.00"}
    assert client.post("/api/v1/is", headers=h, json=payload).status_code == 201

    assert client.post("/api/v1/is", headers=h, json=payload).status_code == 409

    r = client.post("/api/v1/is/cerrar", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "cerrada"
    assert r.json()["base_imponible"] == "50000.00"

    assert client.post("/api/v1/is/cerrar", headers=h).status_code == 409


def test_is_put_actualiza_borrador_y_409_cerrada(contexto_fiscal, client):
    """PUT /is recalcula en borrador; tras cerrar -> 409 (inmutable, SC-007)."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    assert (
        client.post(
            "/api/v1/is", headers=h, json={"resultado_contable": "1000.00", "ajustes": []}
        ).status_code
        == 201
    )

    r = client.put(
        "/api/v1/is",
        headers=h,
        json={
            "resultado_contable": "2000.00",
            "ajustes": [{"concepto": "Ajuste", "sentido": "aumento", "importe": "100.00"}],
            "tipo_gravamen": "25.00",
            "retenciones_pagos_cuenta": "0.00",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["resultado_contable"] == "2000.00"
    assert r.json()["base_imponible"] == "2100.00"
    assert r.json()["cuota_integra"] == "525.00"

    assert client.post("/api/v1/is/cerrar", headers=h).status_code == 200
    r2 = client.put(
        "/api/v1/is", headers=h, json={"resultado_contable": "3000.00", "ajustes": []}
    )
    assert r2.status_code == 409


def test_is_put_sin_liquidacion_404(contexto_fiscal, client):
    """PUT /is sin liquidación -> 404 (contrato is.md)."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    r = client.put(
        "/api/v1/is", headers=h, json={"resultado_contable": "100.00", "ajustes": []}
    )
    assert r.status_code == 404


def test_ajustes_invalidos_422(contexto_fiscal, client):
    """Sentido inválido y tipo de gravamen no positivo -> 422."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    r = client.post(
        "/api/v1/is",
        headers=h,
        json={"resultado_contable": "100.00", "ajustes": [{"concepto": "x", "sentido": "raro", "importe": "1.00"}]},
    )
    assert r.status_code == 422
    r2 = client.post(
        "/api/v1/is",
        headers=h,
        json={"resultado_contable": "100.00", "ajustes": [], "tipo_gravamen": "0.00"},
    )
    assert r2.status_code == 422


# =============================================================================
# US-PRES — Presentación AEAT
# =============================================================================


def _registrar(client, headers, body):
    r = client.post("/api/v1/facturas", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_fichero_303_posiciones_fijas(contexto_fiscal, client, session):
    """T045: fichero 303 conforme a plantilla y totales correctos (periodo cerrado)."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    _registrar(client, h, _venta(numero="FV-1", base="1000.00", tipo="21.00", cuota="210.00"))
    _registrar(client, h, _venta(numero="FV-2", base="500.00", tipo="10.00", cuota="50.00", fecha="2026-03-01"))
    _cerrar_ejercicio(session, ctx)

    r = client.get("/api/v1/presentaciones/303/fichero?periodo=2026T1", headers=h)
    assert r.status_code == 200, r.text
    lineas = r.text.strip("\r\n").split("\r\n") if "\r\n" in r.text else r.text.splitlines()
    codigos = [ln[:2] for ln in lineas]
    assert codigos[0] == "01"
    assert codigos[-1] == "99"
    assert "03" in codigos
    assert all(len(ln) == aeat.MODELOS["303"][ln[:2]].longitud for ln in lineas)
    assert aeat.validar_formato("303", lineas) == []

    cabecera = _parse("303", lineas[0])
    assert cabecera["nif"] == ctx["empresa"].cif
    assert cabecera["periodo"].strip() == "2026T1"

    totales = _parse("303", next(ln for ln in lineas if ln[:2] == "03"))
    assert _importe(totales["total_base"]) == Decimal("1500.00")
    assert _importe(totales["total_cuota"]) == Decimal("260.00")

    detalles = [_parse("303", ln) for ln in lineas if ln[:2] == "02"]
    tipos = {_importe(d["tipo_iva"]): _importe(d["base"]) for d in detalles}
    assert tipos[Decimal("21.00")] == Decimal("1000.00")
    assert tipos[Decimal("10.00")] == Decimal("500.00")

    assert _parse("303", lineas[-1])["numero_registros"] == "000002"


def test_fichero_111_y_115_por_perceptor(contexto_fiscal, client, session):
    """T046: un registro por perceptor con las retenciones agregadas por CIF."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    _registrar(client, h, _compra_retencion("FC-1", cif="B12345674", base="1000.00"))
    _registrar(client, h, _compra_retencion("FC-2", cif="B12345674", base="1500.00"))
    _registrar(client, h, _compra_retencion("FC-3", cif="A28015865", base="800.00", tipo_ret="115", pct="19.00"))
    _cerrar_ejercicio(session, ctx)

    r = client.get("/api/v1/presentaciones/111/fichero?periodo=2026T1", headers=h)
    assert r.status_code == 200, r.text
    lineas = r.text.splitlines()
    assert aeat.validar_formato("111", lineas) == []
    detalles = [_parse("111", ln) for ln in lineas if ln[:2] == "02"]
    assert len(detalles) == 1
    assert detalles[0]["nif_perceptor"].strip() == "B12345674"
    assert _importe(detalles[0]["base"]) == Decimal("2500.00")
    assert _importe(detalles[0]["cuota"]) == Decimal("375.00")

    r115 = client.get("/api/v1/presentaciones/115/fichero?periodo=2026T1", headers=h)
    assert r115.status_code == 200, r115.text
    detalles115 = [_parse("115", ln) for ln in r115.text.splitlines() if ln[:2] == "02"]
    assert len(detalles115) == 1
    assert detalles115[0]["nif_perceptor"].strip() == "A28015865"
    assert _importe(detalles115[0]["cuota"]) == Decimal("152.00")


def test_fichero_200_casillas_de_liquidacion_cerrada(contexto_fiscal, client):
    """T047: el 200 refleja las casillas de la liquidación cerrada."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    client.post(
        "/api/v1/is",
        headers=h,
        json={
            "resultado_contable": "100000.00",
            "ajustes": [
                {"concepto": "Multas", "sentido": "aumento", "importe": "5000.00"},
                {"concepto": "Insolvencias", "sentido": "disminucion", "importe": "8000.00"},
            ],
            "retenciones_pagos_cuenta": "4000.00",
        },
    )
    assert client.post("/api/v1/is/cerrar", headers=h).status_code == 200

    r = client.get("/api/v1/presentaciones/200/fichero?periodo=2026", headers=h)
    assert r.status_code == 200, r.text
    lineas = r.text.splitlines()
    assert aeat.validar_formato("200", lineas) == []
    casillas = {int(_parse("200", ln)["casilla"]): _importe(_parse("200", ln)["importe"]) for ln in lineas if ln[:2] == "02"}
    assert casillas[300] == Decimal("97000.00")
    assert casillas[500] == Decimal("24250.00")
    assert casillas[598] == Decimal("20250.00")


def test_fichero_bloqueado_en_borrador_y_vista_disponible(contexto_fiscal, client):
    """T048: 200 en borrador -> fichero 409 y vista con descarga deshabilitada;
    111 con ejercicio abierto -> fichero 409."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    client.post(
        "/api/v1/is",
        headers=h,
        json={"resultado_contable": "100000.00", "ajustes": [], "retenciones_pagos_cuenta": "0.00"},
    )

    r = client.get("/api/v1/presentaciones/200/fichero?periodo=2026", headers=h)
    assert r.status_code == 409

    vista = client.get("/api/v1/presentaciones/200?periodo=2026", headers=h)
    assert vista.status_code == 200, vista.text
    assert vista.json()["cerrada"] is False
    assert vista.json()["bloque_descarga"]["habilitado"] is False

    r111 = client.get("/api/v1/presentaciones/111/fichero?periodo=2026T1", headers=h)
    assert r111.status_code == 409

    # Tras cerrar la liquidación, la vista habilita la descarga
    client.post("/api/v1/is/cerrar", headers=h)
    vista2 = client.get("/api/v1/presentaciones/200?periodo=2026", headers=h).json()
    assert vista2["cerrada"] is True
    assert vista2["bloque_descarga"]["habilitado"] is True


def test_fichero_trazabilidad_y_directorio(contexto_fiscal, client, session):
    """T049: fichero persistido, hash consistente, una fila por (ejercicio,modelo,periodo)."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    _registrar(client, h, _compra_retencion("FC-1", cif="B12345674", base="1000.00"))
    _cerrar_ejercicio(session, ctx)

    r1 = client.get("/api/v1/presentaciones/111/fichero?periodo=2026T1", headers=h)
    assert r1.status_code == 200, r1.text
    r2 = client.get("/api/v1/presentaciones/111/fichero?periodo=2026T1", headers=h)
    assert r2.status_code == 200
    assert r1.content == r2.content

    ruta = _IMPUESTOS_DIR / str(ctx["empresa"].id) / str(ctx["ejercicio"].anio) / "111_2026T1.txt"
    assert ruta.exists()

    from hashlib import sha256

    assert sha256(r1.content).hexdigest() == sha256(ruta.read_bytes()).hexdigest()

    from sqlmodel import select

    from app.models import FicheroPresentacion

    filas = session.exec(
        select(FicheroPresentacion).where(
            FicheroPresentacion.ejercicio_id == ctx["ejercicio"].id,
            FicheroPresentacion.modelo == "111",
            FicheroPresentacion.periodo == "2026T1",
        )
    ).all()
    assert len(filas) == 1
    assert filas[0].hash_sha256 == sha256(r1.content).hexdigest()

    # Otro modelo -> otra fila
    client.get("/api/v1/presentaciones/115/fichero?periodo=2026T1", headers=h)
    total = session.exec(
        select(FicheroPresentacion).where(FicheroPresentacion.ejercicio_id == ctx["ejercicio"].id)
    ).all()
    assert len(total) == 2