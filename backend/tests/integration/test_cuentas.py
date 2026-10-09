def _h(contexto, ejercicio=None):
    ej = ejercicio or contexto["ejercicio"]
    return {
        **contexto["headers"],
        "X-Empresa-Id": str(contexto["empresa"].id),
        "X-Ejercicio-Id": str(ej.id),
    }


def test_crear_cuenta_201(contexto, client):
    ctx = contexto()
    r = client.post(
        "/api/v1/cuentas",
        headers=_h(ctx),
        json={"codigo": "43000000", "nombre": "Clientes", "nivel": 4},
    )
    assert r.status_code == 201
    assert r.json()["ejercicio_id"] == ctx["ejercicio"].id


def test_codigo_duplicado_mismo_ejercicio_409(contexto, client):
    ctx = contexto()
    r = client.post(
        "/api/v1/cuentas",
        headers=_h(ctx),
        json={"codigo": "57200001", "nombre": "Duplicado", "nivel": 4},
    )
    assert r.status_code == 409


def test_mismo_codigo_otro_ejercicio_201(
    contexto, client, make_empresa, make_ejercicio, make_cuenta
):
    ctx = contexto()
    otra = make_empresa(ctx["usuario"], cif="C09876543")
    otro_ej = make_ejercicio(otra.id, anio=2027)
    headers = {
        **ctx["headers"],
        "X-Empresa-Id": str(otra.id),
        "X-Ejercicio-Id": str(otro_ej.id),
    }
    r = client.post(
        "/api/v1/cuentas",
        headers=headers,
        json={"codigo": "57200001", "nombre": "Bancos otro", "nivel": 4},
    )
    assert r.status_code == 201


def test_filtrado_estricto_por_ejercicio(
    contexto, client, make_empresa, make_ejercicio, make_cuenta
):
    ctx = contexto()
    otra = make_empresa(ctx["usuario"], cif="D11112222")
    otro_ej = make_ejercicio(otra.id, anio=2027)
    make_cuenta(otro_ej.id, "59999999", "Cuenta ajena", 4)
    r = client.get("/api/v1/cuentas", headers=_h(ctx))
    assert r.status_code == 200
    codigos = [c["codigo"] for c in r.json()["items"]]
    assert "59999999" not in codigos
    assert all(c["ejercicio_id"] == ctx["ejercicio"].id for c in r.json()["items"])


def test_creacion_en_ejercicio_cerrado_409(contexto, client, make_ejercicio, make_cuenta):
    ctx = contexto()
    cerrado = make_ejercicio(ctx["empresa"].id, anio=2028, estado="cerrado")
    r = client.post(
        "/api/v1/cuentas",
        headers=_h(ctx, cerrado),
        json={"codigo": "43000000", "nombre": "Clientes", "nivel": 4},
    )
    assert r.status_code == 409


def test_codigo_invalido_422(contexto, client):
    ctx = contexto()
    for bad in ("12AB", "12345678901", "abc12345"):
        r = client.post(
            "/api/v1/cuentas",
            headers=_h(ctx),
            json={"codigo": bad, "nombre": "Mal", "nivel": 4},
        )
        assert r.status_code == 422, bad


def test_subcuenta_nivel4_sobre_cuenta_pgc(contexto, client):
    ctx = contexto(rol="admin")
    h = {**ctx["headers"], "X-Empresa-Id": str(ctx["empresa"].id)}
    r = client.post(
        "/api/v1/ejercicios",
        headers=h,
        json={"anio": 2030, "fecha_inicio": "2030-01-01", "fecha_fin": "2030-12-31"},
    )
    assert r.status_code == 201
    headers = {**h, "X-Ejercicio-Id": str(r.json()["id"])}
    r2 = client.post(
        "/api/v1/cuentas",
        headers=headers,
        json={"codigo": "43000001", "nombre": "Cliente ACME SL", "nivel": 4},
    )
    assert r2.status_code == 201
    assert r2.json()["nivel"] == 4
