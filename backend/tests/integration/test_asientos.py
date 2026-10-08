def _pago(cuentas, debe="1000.00", haber="900.00"):
    return {
        "fecha": "2026-03-01",
        "concepto": "Pago proveedor",
        "apuntes": [
            {"cuenta_id": cuentas["banco"].id, "debe": debe, "haber": "0.00"},
            {"cuenta_id": cuentas["proveedor"].id, "debe": "0.00", "haber": haber},
        ],
    }


def test_borrador_201_numero_null(contexto, client):
    ctx = contexto()
    r = client.post(
        "/api/v1/asientos",
        headers={
            **ctx["headers"],
            "X-Empresa-Id": str(ctx["empresa"].id),
            "X-Ejercicio-Id": str(ctx["ejercicio"].id),
        },
        json=_pago(ctx["cuentas"]),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["numero"] is None
    assert body["estado"] == "borrador"
    assert len(body["apuntes"]) == 2
    assert body["apuntes"][0]["cuenta_codigo"] == "57200001"


def test_asentar_descuadrado_422_con_delta(contexto, client):
    ctx = contexto()
    h = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }
    creado = client.post("/api/v1/asientos", headers=h, json=_pago(ctx["cuentas"])).json()
    r = client.post(f"/api/v1/asientos/{creado['id']}/asentar", headers=h)
    assert r.status_code == 422
    assert "Descuadre" in r.json()["detail"]
    assert "100.00" in r.json()["detail"]


def test_cuadrar_y_asentar_200_correlativo(contexto, client):
    ctx = contexto()
    h = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }
    pago = _pago(ctx["cuentas"], debe="1000.00", haber="1000.00")
    creado = client.post("/api/v1/asientos", headers=h, json=pago).json()
    r = client.post(f"/api/v1/asientos/{creado['id']}/asentar", headers=h)
    assert r.status_code == 200
    assert r.json()["estado"] == "asentado"
    assert r.json()["numero"] == 1


def test_put_asentado_409(contexto, client):
    ctx = contexto()
    h = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }
    pago = _pago(ctx["cuentas"], debe="1000.00", haber="1000.00")
    creado = client.post("/api/v1/asientos", headers=h, json=pago).json()
    client.post(f"/api/v1/asientos/{creado['id']}/asentar", headers=h)
    r = client.put(f"/api/v1/asientos/{creado['id']}", headers=h, json=pago)
    assert r.status_code == 409


def test_ejercicio_cerrado_bloquea_guardar_y_asentar(contexto, client, make_ejercicio, make_cuenta):
    ctx = contexto()
    cerrado = make_ejercicio(ctx["empresa"].id, anio=2027, estado="cerrado")
    c1 = make_cuenta(cerrado.id, "57200001", "Bancos", 4)
    c2 = make_cuenta(cerrado.id, "41000000", "Proveedores", 4)
    h = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(cerrado.id),
    }
    pago = {
        "fecha": "2027-03-01",
        "concepto": "Pago en cerrado",
        "apuntes": [
            {"cuenta_id": c1.id, "debe": "1000.00", "haber": "0.00"},
            {"cuenta_id": c2.id, "debe": "0.00", "haber": "1000.00"},
        ],
    }
    r = client.post("/api/v1/asientos", headers=h, json=pago)
    assert r.status_code == 409


def test_minimo_2_apuntes_422(contexto, client):
    ctx = contexto()
    h = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }
    mal = {
        "fecha": "2026-03-01",
        "concepto": "Uno solo",
        "apuntes": [{"cuenta_id": ctx["cuentas"]["banco"].id, "debe": "100", "haber": "0"}],
    }
    assert client.post("/api/v1/asientos", headers=h, json=mal).status_code == 422


def test_linea_mixta_422(contexto, client):
    ctx = contexto()
    h = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }
    mal = {
        "fecha": "2026-03-01",
        "concepto": "Mixta",
        "apuntes": [
            {"cuenta_id": ctx["cuentas"]["banco"].id, "debe": "100", "haber": "50"},
            {"cuenta_id": ctx["cuentas"]["proveedor"].id, "debe": "0", "haber": "150"},
        ],
    }
    assert client.post("/api/v1/asientos", headers=h, json=mal).status_code == 422


def test_cuenta_ajena_al_ejercicio_422(contexto, client, make_cuenta, make_ejercicio):
    ctx = contexto()
    otro = make_ejercicio(ctx["empresa"].id, anio=2027)
    cuenta_otro = make_cuenta(otro.id, "59900000", "Gastos otro ejercicio", 4)
    h = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }
    mal = {
        "fecha": "2026-03-01",
        "concepto": "Cuenta ajena",
        "apuntes": [
            {"cuenta_id": cuenta_otro.id, "debe": "100", "haber": "0"},
            {"cuenta_id": ctx["cuentas"]["banco"].id, "debe": "0", "haber": "100"},
        ],
    }
    assert client.post("/api/v1/asientos", headers=h, json=mal).status_code == 422


def test_correlativo_independiente_por_ejercicio(
    contexto, client, make_empresa, make_ejercicio, make_cuenta
):
    ctx = contexto()
    otra_empresa = make_empresa(ctx["usuario"], cif="C98765432", razon_social="Otra SL")
    otro_ej = make_ejercicio(otra_empresa.id, anio=2026)
    cuenta = make_cuenta(otro_ej.id, "57200001", "Bancos", 4)
    h1 = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }
    h2 = {**ctx["headers"], "X-Empresa-Id": str(otra_empresa.id), "X-Ejercicio-Id": str(otro_ej.id)}
    pago_ctx = _pago(ctx["cuentas"], debe="100.00", haber="100.00")
    pago_otro = {
        "fecha": "2026-03-01",
        "concepto": "Otro",
        "apuntes": [
            {"cuenta_id": cuenta.id, "debe": "50.00", "haber": "0.00"},
            {
                "cuenta_id": make_cuenta(otro_ej.id, "41000000", "Proveedores", 4).id,
                "debe": "0.00",
                "haber": "50.00",
            },
        ],
    }
    a1 = client.post("/api/v1/asientos", headers=h1, json=pago_ctx).json()
    a2 = client.post("/api/v1/asientos", headers=h2, json=pago_otro).json()
    assert client.post(f"/api/v1/asientos/{a1['id']}/asentar", headers=h1).json()["numero"] == 1
    assert client.post(f"/api/v1/asientos/{a2['id']}/asentar", headers=h2).json()["numero"] == 1
