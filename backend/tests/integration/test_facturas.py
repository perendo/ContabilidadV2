"""Tests de facturas, Libros Registro de IVA y Retenciones (spec 005, US1-US4).

Los tests usan `contexto_fiscal` (PGC base + 4751) y verifican el asiento
derivado: ΣDebe=ΣHaber, cuentas 400/430/600/700/472/477/4751 y agregados al
céntimo (FR-003/005/006/016).
"""

from app.pgc import sembrar_pgc


def _headers(ctx):
    return {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }


def _venta(
    numero="FV-001",
    cif="B12345674",
    base="1000.00",
    tipo="21.00",
    cuota="210.00",
    fecha="2026-03-05",
    lineas_extra=None,
):
    lineas = [
        {
            "numero_linea": 1,
            "descripcion": "Servicio profesional",
            "base_imponible": base,
            "tipo_iva": tipo,
            "cuota_iva": cuota,
        }
    ]
    if lineas_extra:
        lineas.extend(lineas_extra)
    return {
        "origen": "venta",
        "numero": numero,
        "fecha": fecha,
        "tercero_cif": cif,
        "tercero_razon_social": "Cliente SL",
        "lineas": lineas,
    }


def _compra(
    numero="FC-001",
    cif="B12345674",
    base="500.00",
    tipo="21.00",
    cuota="105.00",
    fecha="2026-03-05",
    tipo_retencion=None,
    **linea_extra,
):
    linea = {
        "numero_linea": 1,
        "descripcion": "Mercancia comprada",
        "base_imponible": base,
        "tipo_iva": tipo,
        "cuota_iva": cuota,
    }
    linea.update(linea_extra)
    body = {
        "origen": "compra",
        "numero": numero,
        "fecha": fecha,
        "tercero_cif": cif,
        "tercero_razon_social": "Proveedor SL",
        "lineas": [linea],
    }
    if tipo_retencion:
        body["tipo_retencion"] = tipo_retencion
    return body


def _cuota_str(base: str, factor: str = "0.21") -> str:
    from decimal import ROUND_HALF_UP, Decimal

    return str(
        (Decimal(base) * Decimal(factor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def _apuntes(client, headers, asiento_id):
    return client.get(f"/api/v1/asientos/{asiento_id}", headers=headers).json()["apuntes"]


def _total_por_codigo(apuntes):
    acc = {}
    for a in apuntes:
        d, h = acc.get(a["cuenta_codigo"], (0.0, 0.0))
        acc[a["cuenta_codigo"]] = (d + float(a["debe"]), h + float(a["haber"]))
    return {k: (f"{v[0]:.2f}", f"{v[1]:.2f}") for k, v in acc.items()}


def _cuadra(apuntes):
    return sum(float(a["debe"]) for a in apuntes) == sum(float(a["haber"]) for a in apuntes)


def _token(usuario):
    from app.services.seguridad import create_access_token

    return create_access_token(usuario.username)


def _registrar(client, headers, body):
    r = client.post("/api/v1/facturas", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


# =============================================================================
# US1 — Factura de venta con IVA repercutido
# =============================================================================


def test_factura_venta_asiento_cuadrado(contexto_fiscal, client):
    """T014: venta 1000 @21% -> 430 deb 1210 / 700 hab 1000 / 477 hab 210, cuadra."""
    ctx = contexto_fiscal()
    r = client.post("/api/v1/facturas", headers=_headers(ctx), json=_venta())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["origen"] == "venta"
    assert body["asiento_id"] is not None
    assert body["lineas"][0]["cuota_iva"] == "210.00"

    apuntes = _apuntes(client, _headers(ctx), body["asiento_id"])
    por_codigo = _total_por_codigo(apuntes)
    assert por_codigo["430"] == ("1210.00", "0.00")
    assert por_codigo["700"] == ("0.00", "1000.00")
    assert por_codigo["477"] == ("0.00", "210.00")
    assert _cuadra(apuntes)

    # El asiento aparece en el Diario con correlativo asignado
    diario = client.get("/api/v1/asientos", headers=_headers(ctx)).json()
    detalle = next(a for a in diario["items"] if a["id"] == body["asiento_id"])
    assert detalle["estado"] == "asentado"
    assert detalle["numero"] == 1


def test_duplicado_cif_numero_ejercicio_409(contexto_fiscal, client, session, make_ejercicio):
    """T015: 2o POST mismo CIF+numero -> 409 sin asiento; mismo n. otro ejercicio -> 201."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    assert client.post("/api/v1/facturas", headers=h, json=_venta()).status_code == 201

    r2 = client.post("/api/v1/facturas", headers=h, json=_venta())
    assert r2.status_code == 409

    diario = client.get("/api/v1/asientos", headers=h).json()
    assert diario["total"] == 1

    otro = make_ejercicio(ctx["empresa"].id, anio=2027, estado="abierto")
    sembrar_pgc(session, otro.id)
    session.commit()
    h2 = {**h, "X-Ejercicio-Id": str(otro.id)}
    r3 = client.post(
        "/api/v1/facturas", headers=h2, json=_venta(numero="FV-001", fecha="2027-03-05")
    )
    assert r3.status_code == 201, r3.text


def test_multi_tipo_iva_una_linea_por_tipo(contexto_fiscal, client):
    """T016: dos lineas 21% y 10% -> dos apuntes en 477 y el total cuadra."""
    ctx = contexto_fiscal()
    body = _venta(
        numero="FV-MULTI",
        lineas_extra=[
            {
                "numero_linea": 2,
                "descripcion": "Servicio reducido",
                "base_imponible": "500.00",
                "tipo_iva": "10.00",
                "cuota_iva": "50.00",
            }
        ],
    )
    r = client.post("/api/v1/facturas", headers=_headers(ctx), json=body)
    assert r.status_code == 201, r.text
    apuntes = _apuntes(client, _headers(ctx), r.json()["asiento_id"])
    por_codigo = _total_por_codigo(apuntes)
    assert por_codigo["430"] == ("1760.00", "0.00")
    assert por_codigo["700"] == ("0.00", "1500.00")
    assert por_codigo["477"] == ("0.00", "260.00")
    assert len([a for a in apuntes if a["cuenta_codigo"] == "477"]) == 2
    assert _cuadra(apuntes)


def test_factura_sin_contexto_400_sin_acceso_403(contexto_fiscal, client, make_usuario):
    """T017: faltan cabeceras -> 400; usuario no vinculado a la empresa -> 403."""
    ctx = contexto_fiscal()
    body = _venta()

    r = client.post("/api/v1/facturas", headers=ctx["headers"], json=body)
    assert r.status_code == 400

    ajeno = make_usuario("ajeno", rol="contable")
    headers_ajeno = _headers(ctx).copy()
    headers_ajeno["Authorization"] = f"Bearer {_token(ajeno)}"
    r2 = client.post("/api/v1/facturas", headers=headers_ajeno, json=body)
    assert r2.status_code == 403


# =============================================================================
# US2 — Factura de compra con IVA soportado y Recargo de Equivalencia
# =============================================================================


def test_factura_compra_cuadra(contexto_fiscal, client):
    """T022: compra 500 @21% -> 600 deb 500 / 472 deb 105 / 400 hab 605."""
    ctx = contexto_fiscal()
    r = client.post("/api/v1/facturas", headers=_headers(ctx), json=_compra())
    assert r.status_code == 201, r.text
    apuntes = _apuntes(client, _headers(ctx), r.json()["asiento_id"])
    por_codigo = _total_por_codigo(apuntes)
    assert por_codigo["600"] == ("500.00", "0.00")
    assert por_codigo["472"] == ("105.00", "0.00")
    assert por_codigo["400"] == ("0.00", "605.00")
    assert _cuadra(apuntes)


def test_recargo_equivalencia_se_registra(contexto_fiscal, client):
    """T023: tipo_re 5.20 -> cuota RE tambien en 472 y SumaDebe=SumaHaber."""
    ctx = contexto_fiscal()
    r = client.post(
        "/api/v1/facturas",
        headers=_headers(ctx),
        json=_compra(
            numero="FC-RE",
            base="500.00",
            tipo="21.00",
            cuota="105.00",
            tipo_re="5.20",
            cuota_re="26.00",
        ),
    )
    assert r.status_code == 201, r.text
    apuntes = _apuntes(client, _headers(ctx), r.json()["asiento_id"])
    por_codigo = _total_por_codigo(apuntes)
    assert por_codigo["600"] == ("500.00", "0.00")
    assert por_codigo["472"] == ("131.00", "0.00")  # IVA 105 + RE 26
    assert por_codigo["400"] == ("0.00", "631.00")
    assert _cuadra(apuntes)


def test_operacion_exenta_sin_cuota(contexto_fiscal, client):
    """T024: operacion exenta -> sin 472, asiento de gasto puro."""
    ctx = contexto_fiscal()
    r = client.post(
        "/api/v1/facturas",
        headers=_headers(ctx),
        json=_compra(
            numero="FC-EX", base="500.00", tipo="0.00", cuota="0.00", operacion_exenta=True
        ),
    )
    assert r.status_code == 201, r.text
    apuntes = _apuntes(client, _headers(ctx), r.json()["asiento_id"])
    por_codigo = _total_por_codigo(apuntes)
    assert por_codigo["600"] == ("500.00", "0.00")
    assert "472" not in por_codigo
    assert por_codigo["400"] == ("0.00", "500.00")
    assert _cuadra(apuntes)


# =============================================================================
# US3 — Libros Registro de IVA
# =============================================================================


def test_libro_iva_totales_por_tipo(contexto_fiscal, client):
    """T027: varios tipos -> agregados correctos y coincidentes con facturas."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    _registrar(client, h, _venta(numero="FV-1", base="1000.00", tipo="21.00", cuota="210.00"))
    _registrar(client, h, _venta(numero="FV-2", base="200.00", tipo="10.00", cuota="20.00"))
    _registrar(client, h, _compra(numero="FC-1", base="500.00", tipo="21.00", cuota="105.00"))

    r = client.get(
        "/api/v1/facturas/libros/iva?origen=repercutido&desde=2026-01-01&hasta=2026-12-31",
        headers=h,
    )
    assert r.status_code == 200, r.text
    libro = r.json()
    assert libro["origen"] == "repercutido"
    assert len(libro["operaciones"]) == 2
    assert libro["total_base"] == "1200.00"
    assert libro["total_cuota"] == "230.00"
    por_tipo = {t["tipo_iva"]: t for t in libro["totales_por_tipo"]}
    assert por_tipo["21.00"]["base"] == "1000.00"
    assert por_tipo["21.00"]["cuota"] == "210.00"
    assert por_tipo["10.00"]["base"] == "200.00"
    assert por_tipo["10.00"]["cuota"] == "20.00"

    r2 = client.get(
        "/api/v1/facturas/libros/iva?origen=soportado&desde=2026-01-01&hasta=2026-12-31",
        headers=h,
    )
    soportado = r2.json()
    assert soportado["total_base"] == "500.00"
    assert soportado["total_cuota"] == "105.00"


def test_libro_iva_exportar_csv(contexto_fiscal, client):
    """T028: cabeceras legales, ';' separador, coma decimal y BOM UTF-8."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    _registrar(client, h, _venta(numero="FV-1", base="1000.00", tipo="21.00", cuota="210.00"))

    r = client.get(
        "/api/v1/facturas/libros/iva/exportar?origen=repercutido&desde=2026-01-01&hasta=2026-12-31",
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("text/csv")
    texto = r.text
    assert texto.startswith("\ufeff")
    lineas = texto.lstrip("\ufeff").splitlines()
    assert lineas[0] == "fecha;numero;cif;nombre;base;tipo;cuota;total"
    fila = lineas[1].split(";")
    assert fila[0] == "2026-03-05"
    assert fila[1] == "FV-1"
    assert fila[2] == "B12345674"
    assert fila[3] == "Cliente SL"
    assert fila[4] == "1000,00"
    assert fila[5] == "21,00"
    assert fila[6] == "210,00"
    assert fila[7] == "1210,00"


# =============================================================================
# US4 — Retenciones IRPF y agrupacion por perceptor 111/115
# =============================================================================


def test_factura_compra_con_retencion_cuadra(contexto_fiscal, client):
    """T032: 1000 @21% ret 15% (111) -> 600/472/400/4751 exactos y cuadra."""
    ctx = contexto_fiscal()
    r = client.post(
        "/api/v1/facturas",
        headers=_headers(ctx),
        json=_compra(
            numero="FC-RET",
            base="1000.00",
            tipo="21.00",
            cuota="210.00",
            tipo_retencion="111",
            base_retencion="1000.00",
            pct_retencion="15.00",
            cuota_retencion="150.00",
        ),
    )
    assert r.status_code == 201, r.text
    apuntes = _apuntes(client, _headers(ctx), r.json()["asiento_id"])
    por_codigo = _total_por_codigo(apuntes)
    assert por_codigo["600"] == ("1000.00", "0.00")
    assert por_codigo["472"] == ("210.00", "0.00")
    assert por_codigo["400"] == ("0.00", "1060.00")
    assert por_codigo["4751"] == ("0.00", "150.00")
    assert _cuadra(apuntes)


def test_resumen_111_por_cif(contexto_fiscal, client):
    """T033: 3 facturas del mismo perceptor -> agregado exacto por CIF."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    for i, base in enumerate(("1000.00", "1000.00", "500.00"), start=1):
        _registrar(
            client,
            h,
            _compra(
                numero=f"FC-R-{i}",
                cif="B12345674",
                base=base,
                tipo="21.00",
                cuota=_cuota_str(base),
                tipo_retencion="111",
                base_retencion=base,
                pct_retencion="15.00",
                cuota_retencion=_cuota_str(base, "0.15"),
            ),
        )

    r = client.get(
        "/api/v1/facturas/retenciones?tipo=111&desde=2026-01-01&hasta=2026-12-31", headers=h
    )
    assert r.status_code == 200, r.text
    resumen = r.json()
    assert resumen["tipo"] == "111"
    assert len(resumen["por_perceptor"]) == 1
    perceptor = resumen["por_perceptor"][0]
    assert perceptor["tercero_cif"] == "B12345674"
    assert perceptor["base_retencion"] == "2500.00"
    assert perceptor["cuota_retencion"] == "375.00"
    assert perceptor["numero_facturas"] == 3
    assert resumen["total_base"] == "2500.00"
    assert resumen["total_retencion"] == "375.00"


def test_resumen_115_separa_alquileres(contexto_fiscal, client):
    """T034: alquileres (115) no aparecen en 111 y si en 115."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    _registrar(
        client,
        h,
        _compra(
            numero="FC-PROF",
            cif="B12345674",
            base="1000.00",
            tipo="21.00",
            cuota="210.00",
            tipo_retencion="111",
            base_retencion="1000.00",
            pct_retencion="15.00",
            cuota_retencion="150.00",
        ),
    )
    _registrar(
        client,
        h,
        _compra(
            numero="FC-ALQ",
            cif="A28015865",
            base="800.00",
            tipo="21.00",
            cuota=_cuota_str("800.00"),
            tipo_retencion="115",
            base_retencion="800.00",
            pct_retencion="19.00",
            cuota_retencion="152.00",
        ),
    )

    r111 = client.get(
        "/api/v1/facturas/retenciones?tipo=111&desde=2026-01-01&hasta=2026-12-31", headers=h
    ).json()
    assert [p["tercero_cif"] for p in r111["por_perceptor"]] == ["B12345674"]

    r115 = client.get(
        "/api/v1/facturas/retenciones?tipo=115&desde=2026-01-01&hasta=2026-12-31", headers=h
    ).json()
    assert [p["tercero_cif"] for p in r115["por_perceptor"]] == ["A28015865"]
    assert r115["por_perceptor"][0]["cuota_retencion"] == "152.00"


def test_perceptor_sin_cif_valido_excluido_y_pct_fuera_rango(contexto_fiscal, client):
    """T035: CIF invalido -> 422; pct_retencion > 100 -> 422."""
    ctx = contexto_fiscal()
    h = _headers(ctx)
    r = client.post(
        "/api/v1/facturas",
        headers=h,
        json=_compra(numero="FC-MAL-CIF", cif="1234", tipo_retencion="111"),
    )
    assert r.status_code == 422

    r2 = client.post(
        "/api/v1/facturas",
        headers=h,
        json=_compra(
            numero="FC-MAL-PCT",
            cif="B12345674",
            base="1000.00",
            tipo="21.00",
            cuota="210.00",
            tipo_retencion="111",
            base_retencion="1000.00",
            pct_retencion="101.00",
            cuota_retencion="1010.00",
        ),
    )
    assert r2.status_code == 422