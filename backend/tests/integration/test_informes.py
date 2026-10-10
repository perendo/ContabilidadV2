from datetime import date
from decimal import Decimal

from app.models import Cuenta, Asiento, Apunte, Usuario, Empresa, Ejercicio, empresa_usuario
from app.services.seguridad import create_access_token


def _auth_headers(user: Usuario) -> dict[str, str]:
    token = create_access_token(user.username)
    return {"Authorization": f"Bearer {token}"}


def _crear_estructura_basica(session, user: Usuario, cif_suffix=""):
    cif = f"B1234567{cif_suffix}"
    empresa = Empresa(cif=cif, razon_social="Test SL")
    session.add(empresa)
    session.flush()
    session.execute(
        empresa_usuario.insert().values(usuario_id=user.id, empresa_id=empresa.id, rol_especifico="admin")
    )
    ejercicio = Ejercicio(
        empresa_id=empresa.id,
        anio=2026,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
        estado="abierto",
    )
    session.add(ejercicio)
    session.flush()

    c1 = Cuenta(ejercicio_id=ejercicio.id, codigo="570", nombre="Caja", nivel=3)
    c2 = Cuenta(ejercicio_id=ejercicio.id, codigo="572", nombre="Bancos", nivel=3)
    c3 = Cuenta(ejercicio_id=ejercicio.id, codigo="410", nombre="Proveedores", nivel=3)
    c4 = Cuenta(ejercicio_id=ejercicio.id, codigo="100", nombre="Capital", nivel=3)
    session.add_all([c1, c2, c3, c4])
    session.commit()

    return empresa, ejercicio, {"caja": c1, "banco": c2, "proveedor": c3, "capital": c4}


def _crear_asiento(session, ejercicio_id: int, usuario_id: int, fecha: date, numero: int, concepto: str, lineas: list[tuple[int, Decimal, Decimal]]):
    asiento = Asiento(
        ejercicio_id=ejercicio_id,
        fecha=fecha,
        numero=numero,
        concepto=concepto,
        estado="asentado",
        creado_por_usuario_id=usuario_id,
        asentado_por_usuario_id=usuario_id,
    )
    session.add(asiento)
    session.flush()
    for cuenta_id, debe, haber in lineas:
        session.add(Apunte(asiento_id=asiento.id, cuenta_id=cuenta_id, debe=debe, haber=haber))
    session.commit()
    return asiento


class TestMayorCuenta:
    def test_mayor_cuenta_hoja_saldo_acumulado(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 12, "Cobro auditoría", [(cuentas["caja"].id, Decimal("30.00"), Decimal("0"))])
        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 13, "Pago proveedor", [(cuentas["caja"].id, Decimal("0"), Decimal("30.00"))])

        resp = client.get(
            "/api/v1/informes/mayor?cuenta=570",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cuenta"]["codigo"] == "570"
        assert len(data["movimientos"]) == 2
        assert data["movimientos"][0]["saldo"] == "30.00"
        assert data["movimientos"][1]["saldo"] == "0.00"
        assert data["total_debe"] == "30.00"
        assert data["total_haber"] == "30.00"
        assert data["saldo_final"] == "0.00"
        assert data["saldo_inicial"] == "0.00"

    def test_mayor_incluye_saldo_inicial_con_desde(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        _crear_asiento(session, ejercicio.id, user.id, date(2026, 9, 15), 1, "Saldo anterior", [(cuentas["caja"].id, Decimal("100.00"), Decimal("0"))])
        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 12, "Cobro", [(cuentas["caja"].id, Decimal("30.00"), Decimal("0"))])
        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 10), 13, "Pago", [(cuentas["caja"].id, Decimal("0"), Decimal("20.00"))])

        resp = client.get(
            "/api/v1/informes/mayor?cuenta=570&desde=2026-10-01&hasta=2026-10-31",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["saldo_inicial"] == "100.00"
        assert len(data["movimientos"]) == 2
        assert data["movimientos"][0]["saldo"] == "130.00"
        assert data["movimientos"][1]["saldo"] == "110.00"
        assert data["saldo_final"] == "110.00"

    def test_mayor_cuenta_grupo_agrega_subcuentas(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        c57 = Cuenta(ejercicio_id=ejercicio.id, codigo="57", nombre="Tesorería", nivel=2)
        session.add(c57)
        session.commit()

        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 1, "Cobro caja", [(cuentas["caja"].id, Decimal("50.00"), Decimal("0"))])
        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 10), 2, "Ingreso banco", [(cuentas["banco"].id, Decimal("200.00"), Decimal("0"))])

        resp = client.get(
            "/api/v1/informes/mayor?cuenta=57",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cuenta"]["codigo"] == "57"
        assert data["total_debe"] == "250.00"
        assert data["total_haber"] == "0.00"
        assert data["saldo_final"] == "250.00"

    def test_mayor_cuenta_sin_apuntes_estado_vacio(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        resp = client.get(
            "/api/v1/informes/mayor?cuenta=410",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["movimientos"] == []
        assert data["total_debe"] == "0.00"
        assert data["total_haber"] == "0.00"
        assert data["saldo_final"] == "0.00"

    def test_mayor_global_lista_cuentas_con_movimiento(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 1, "Cobro", [(cuentas["caja"].id, Decimal("30.00"), Decimal("0"))])
        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 2, "Pago", [(cuentas["caja"].id, Decimal("0"), Decimal("30.00"))])

        resp = client.get(
            "/api/v1/informes/mayor/cuentas",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        codigos = [c["codigo"] for c in data["cuentas"]]
        assert "570" in codigos
        assert "572" not in codigos
        assert "410" not in codigos
        assert "100" not in codigos
        caja = next(c for c in data["cuentas"] if c["codigo"] == "570")
        assert caja["saldo_tipo"] == "cero"
        assert caja["suma_debe"] == "30.00"
        assert caja["suma_haber"] == "30.00"


class TestMayorAislamiento:
    def test_informes_aislamiento_multi_tenant(self, client, session, make_usuario):
        user1 = make_usuario("user1", rol="contable")
        user2 = make_usuario("user2", rol="contable")
        empresa1, ejercicio1, c1 = _crear_estructura_basica(session, user1, "1")
        empresa2, ejercicio2, c2 = _crear_estructura_basica(session, user2, "2")

        _crear_asiento(session, ejercicio1.id, user1.id, date(2026, 10, 9), 1, "Asiento emp1", [(c1["caja"].id, Decimal("100.00"), Decimal("0"))])

        resp = client.get(
            "/api/v1/informes/mayor?cuenta=570",
            headers=_auth_headers(user1) | {"X-Empresa-Id": str(empresa2.id), "X-Ejercicio-Id": str(ejercicio2.id)},
        )
        assert resp.status_code == 403


class TestMayorValidacion:
    def test_mayor_cuenta_no_existe_404(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, _ = _crear_estructura_basica(session, user)

        resp = client.get(
            "/api/v1/informes/mayor?cuenta=999",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 404

    def test_mayor_desde_mayor_que_hasta_422(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, _ = _crear_estructura_basica(session, user)

        resp = client.get(
            "/api/v1/informes/mayor?cuenta=570&desde=2026-12-31&hasta=2026-01-01",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 422


class TestBalance:
    def test_balance_cuatro_columnas_y_cuadre(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        # Asiento balanceado: Capital 1000 haber, Caja 1000 debe
        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 1, "Capital", [(cuentas["capital"].id, Decimal("0"), Decimal("1000.00")), (cuentas["caja"].id, Decimal("1000.00"), Decimal("0"))])

        resp = client.get(
            "/api/v1/informes/balance",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cuadra"] is True
        assert data["total_debe"] == "1000.00"
        assert data["total_haber"] == "1000.00"
        # Verificar 4 columnas
        assert "filas" in data
        for fila in data["filas"]:
            assert "suma_debe" in fila
            assert "suma_haber" in fila
            assert "saldo_deudor" in fila
            assert "saldo_acreedor" in fila

    def test_balance_excluye_borradores(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 1, "Asentado", [(cuentas["caja"].id, Decimal("100.00"), Decimal("0"))])
        # Borrador - no debe aparecer
        asiento_borrador = Asiento(
            ejercicio_id=ejercicio.id,
            fecha=date(2026, 10, 10),
            numero=2,
            concepto="Borrador",
            estado="borrador",
            creado_por_usuario_id=user.id,
        )
        session.add(asiento_borrador)
        session.flush()
        session.add(Apunte(asiento_id=asiento_borrador.id, cuenta_id=cuentas["banco"].id, debe=Decimal("500.00"), haber=Decimal("0")))
        session.commit()

        resp = client.get(
            "/api/v1/informes/balance",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_debe"] == "100.00"
        assert data["total_haber"] == "0.00"

    def test_balance_cuenta_compensada_saldo_cero_incluida(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 1, "Compensada", [(cuentas["caja"].id, Decimal("50.00"), Decimal("50.00"))])

        resp = client.get(
            "/api/v1/informes/balance",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        codigos = [f["codigo"] for f in data["filas"]]
        assert "570" in codigos  # Cuenta compensada incluida
        # Cuenta sin movimiento (410) no debe estar
        assert "410" not in codigos

    def test_balance_agregacion_jerarquica_por_prefijo(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        # Añadir cuentas de grupo
        c1 = Cuenta(ejercicio_id=ejercicio.id, codigo="1", nombre="Financiación básica", nivel=1)
        c10 = Cuenta(ejercicio_id=ejercicio.id, codigo="10", nombre="Capital", nivel=2)
        session.add_all([c1, c10])
        session.commit()

        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 1, "Capital", [(cuentas["capital"].id, Decimal("0"), Decimal("1000.00"))])

        resp = client.get(
            "/api/v1/informes/balance",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        codigos = [f["codigo"] for f in data["filas"]]
        assert "1" in codigos
        assert "10" in codigos
        assert "100" in codigos
        # Verificar que el grupo 1 acumula el 100
        grupo1 = next(f for f in data["filas"] if f["codigo"] == "1")
        assert grupo1["suma_haber"] == "1000.00"
        assert grupo1["saldo_acreedor"] == "1000.00"

    def test_balance_precision_dos_decimales(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        # Importes con decimales que podrían causar problemas de punto flotante
        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 1, "Test", [(cuentas["caja"].id, Decimal("0.10"), Decimal("0"))])
        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 2, "Test", [(cuentas["caja"].id, Decimal("0.20"), Decimal("0"))])
        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 3, "Test", [(cuentas["caja"].id, Decimal("0"), Decimal("0.30"))])

        resp = client.get(
            "/api/v1/informes/balance",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_debe"] == "0.30"
        assert data["total_haber"] == "0.30"
        assert data["cuadra"] is True


class TestExport:
    def test_export_csv_formato_espanol(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 1, "Capital", [(cuentas["capital"].id, Decimal("0"), Decimal("1000.00")), (cuentas["caja"].id, Decimal("1000.00"), Decimal("0"))])

        resp = client.get(
            "/api/v1/informes/balance/export?formato=csv",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in resp.headers["content-disposition"]
        content = resp.content.decode("utf-8-sig")
        # Verificar BOM, separador ;, decimal coma, encabezado
        assert content.startswith("\ufeff")
        assert ";" in content
        assert "1.000,00" in content or "1000,00" in content  # decimal coma
        assert "Test SL" in content
        assert "B1234567" in content
        assert "Balance de Sumas y Saldos" in content

    def test_export_pdf_content_type_y_encabezado(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 1, "Capital", [(cuentas["capital"].id, Decimal("0"), Decimal("1000.00")), (cuentas["caja"].id, Decimal("1000.00"), Decimal("0"))])

        resp = client.get(
            "/api/v1/informes/balance/export?formato=pdf",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert "attachment" in resp.headers["content-disposition"]
        assert len(resp.content) > 100  # PDF generado

    def test_export_mayor_csv(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 1, "Cobro", [(cuentas["caja"].id, Decimal("50.00"), Decimal("0"))])

        resp = client.get(
            "/api/v1/informes/mayor/export?formato=csv&cuenta=570",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        content = resp.content.decode("utf-8-sig")
        assert ";" in content
        assert "Cobro" in content
        assert "50,00" in content  # decimal coma

    def test_export_formato_invalido_422(self, client, session, make_usuario):
        user = make_usuario(rol="contable")
        empresa, ejercicio, cuentas = _crear_estructura_basica(session, user)

        _crear_asiento(session, ejercicio.id, user.id, date(2026, 10, 9), 1, "Test", [(cuentas["caja"].id, Decimal("100.00"), Decimal("0"))])

        resp = client.get(
            "/api/v1/informes/balance/export?formato=xyz",
            headers=_auth_headers(user) | {"X-Empresa-Id": str(empresa.id), "X-Ejercicio-Id": str(ejercicio.id)},
        )
        assert resp.status_code == 422