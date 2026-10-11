import io
import json
from datetime import date
from decimal import Decimal

from openpyxl import Workbook
from sqlmodel import select

from app.models import Apunte, Asiento, Cuenta, MovimientoBanco, ReglaBanco
from app.services.seguridad import create_access_token


def _headers(ctx) -> dict[str, str]:
    return ctx["headers"] | {
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }


CSV_EXTRACTO = (
    "Fecha Operación;Fecha Valor;Concepto;Importe;Saldo;Código;Referencia 1\n"
    "01/02/2026;05/02/2026;Recibo nomina energia;1.000,50;5.000,50;572;REF-001\n"
)


def _importar(client, ctx, contenido: str = CSV_EXTRACTO, filename: str = "extracto.csv"):
    return client.post(
        "/api/v1/banco/importar",
        headers=_headers(ctx),
        files={"file": (filename, contenido.encode("utf-8"), "text/csv")},
        data={"ignorar_duplicados": "false"},
    )


def _crear_regla(client, ctx, **overrides):
    payload = {
        "nombre": "Nomina",
        "patron_regex": "nomina",
        "cuenta_debe": "57200001",
        "cuenta_haber": "41000000",
        "prioridad": 10,
        "auto_asentar": True,
        "activa": True,
    }
    payload.update(overrides)
    return client.post("/api/v1/banco/reglas", headers=_headers(ctx), json=payload)


def _importar_bytes(client, ctx, contenido: bytes, filename: str, content_type: str):
    return client.post(
        "/api/v1/banco/importar",
        headers=_headers(ctx),
        files={"file": (filename, contenido, content_type)},
        data={"ignorar_duplicados": "false"},
    )


def _xlsx_santander() -> bytes:
    """Excel Santander real: 7 filas de cabecera + headers en fila 8 + datos."""
    wb = Workbook()
    ws = wb.active
    for i in range(7):
        ws.append([f"Cabecera {i}"] + [None] * 11)
    ws.append(
        [
            "Fecha Operación", "Fecha Valor", "Concepto", "Importe", "Divisa", "Saldo",
            None, "Código", "Nº Doc", "Referencia 1", "Referencia 2", "Info",
        ]
    )
    ws.append(
        [date(2026, 2, 5), date(2026, 2, 10), "Recibo luz marzo", 1500.50, "EUR", 5000.50,
         None, "572", "DOC-1", "REF-LUZ", "RF2-1", "Detalle"]
    )
    ws.append(
        [date(2026, 2, 28), date(2026, 3, 1), "Ingreso ventas", 250.00, "EUR", 5250.50,
         None, "100", "DOC-2", "REF-VEN", "RF2-2", None]
    )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _csb_extracto() -> bytes:
    """CSB / Cuaderno 43: registros 01/02/03/99 de longitud fija (AEB)."""

    def r02(fecha_op, fecha_val, importe, concepto, codigo, ndoc, ref, ref2=""):
        signo = "-" if importe < 0 else "+"
        cuerpo = f"{abs(importe):016d}"  # 16 dígitos, los 2 últimos = decimales
        linea = "02" + fecha_op + fecha_val + signo + cuerpo + " "  # importe en [18:36]
        linea += concepto.ljust(35)[:35]  # [36:71]
        linea += codigo.ljust(3)[:3]  # [71:74]
        linea += ndoc.ljust(20)[:20]  # [74:94]
        linea += ref.ljust(20)[:20]  # [94:114]
        linea += ref2.ljust(20)[:20]  # [114:134]
        return linea

    relleno = " " * 74
    lineas = [
        "01" + relleno,
        r02("05022026", "10022026", 100050, "RECIBO LUZ MARZO", "572", "DOC-1", "REF-CSB-1", "RF2-CSB"),
        r02("06022026", "11022026", -7550, "CARGO COMISION", "071", "DOC-2", "REF-CSB-2", ""),
        "03" + relleno,
        "99" + relleno,
    ]
    return ("\n".join(lineas) + "\n").encode("utf-8")


class TestImportarExtracto:
    def test_importar_csv_crea_movimientos_pendientes(self, client, contexto):
        ctx = contexto()

        resp = _importar(client, ctx)
        assert resp.status_code == 200
        data = resp.json()
        assert data["importados"] == 1
        assert data["duplicados"] == 0
        assert data["formato_detectado"] == "csv"

        pend = client.get("/api/v1/banco/pendientes", headers=_headers(ctx))
        assert pend.status_code == 200
        movimientos = pend.json()
        assert len(movimientos) == 1
        assert movimientos[0]["concepto"] == "Recibo nomina energia"
        assert movimientos[0]["importe"] == "1000.50"
        assert movimientos[0]["procesado"] is False

    def test_importar_duplicado_no_reinserta(self, client, contexto):
        ctx = contexto()
        _importar(client, ctx)
        resp = _importar(client, ctx)

        assert resp.status_code == 200
        data = resp.json()
        assert data["importados"] == 0
        assert data["duplicados"] == 1


class TestProcesar:
    def test_procesar_auto_asienta_con_correlativo(self, client, session, contexto):
        ctx = contexto()
        assert _crear_regla(client, ctx).status_code == 201
        _importar(client, ctx)

        resp = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        assert resp.status_code == 200
        data = resp.json()
        assert data["creados"] == 1
        assert data["pendientes"] == 0
        assert data["fallidos"] == []
        assert data["log_id"] > 0

        asiento = session.exec(
            select(Asiento).where(Asiento.ejercicio_id == ctx["ejercicio"].id)
        ).one()
        assert asiento.estado == "asentado"
        assert asiento.numero == 1

        apuntes = session.exec(select(Apunte).where(Apunte.asiento_id == asiento.id)).all()
        assert sum(a.debe for a in apuntes) == Decimal("1000.50")
        assert sum(a.haber for a in apuntes) == Decimal("1000.50")

        mov = session.exec(select(MovimientoBanco)).one()
        assert mov.procesado is True
        assert mov.asiento_id == asiento.id

    def test_procesar_sin_auto_asentar_crea_borrador(self, client, session, contexto):
        ctx = contexto()
        assert _crear_regla(client, ctx, auto_asentar=False).status_code == 201
        _importar(client, ctx)

        resp = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        assert resp.status_code == 200
        assert resp.json()["creados"] == 1

        asiento = session.exec(select(Asiento)).one()
        assert asiento.estado == "borrador"
        assert asiento.numero is None

    def test_procesar_sin_reglas_deja_pendientes(self, client, contexto):
        ctx = contexto()
        _importar(client, ctx)

        resp = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        assert resp.status_code == 200
        data = resp.json()
        assert data["creados"] == 0
        assert data["pendientes"] == 1

    def test_procesar_cuenta_inexistente_registra_fallo(self, client, session, contexto):
        ctx = contexto()
        session.add(
            ReglaBanco(
                empresa_id=ctx["empresa"].id,
                nombre="Mala",
                patron_regex="nomina",
                cuenta_debe="999999",
                cuenta_haber="41000000",
                prioridad=1,
                auto_asentar=True,
                activa=True,
            )
        )
        session.commit()
        _importar(client, ctx)

        resp = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        assert resp.status_code == 200
        data = resp.json()
        assert data["creados"] == 0
        assert len(data["fallidos"]) == 1
        assert "999999" in data["fallidos"][0]["error"]

        mov = session.exec(select(MovimientoBanco)).one()
        assert mov.procesado is False


class TestPendientesManuales:
    def test_crear_asiento_manual_y_marcar_procesado(self, client, session, contexto):
        ctx = contexto()
        _importar(client, ctx)

        pend = client.get("/api/v1/banco/pendientes", headers=_headers(ctx))
        assert pend.status_code == 200
        mov = pend.json()[0]

        cuenta_debe = session.exec(
            select(Cuenta).where(
                Cuenta.ejercicio_id == ctx["ejercicio"].id, Cuenta.codigo == "57200001"
            )
        ).one()
        cuenta_haber = session.exec(
            select(Cuenta).where(
                Cuenta.ejercicio_id == ctx["ejercicio"].id, Cuenta.codigo == "41000000"
            )
        ).one()

        resp = client.post(
            "/api/v1/asientos",
            headers=_headers(ctx),
            json={
                "fecha": "2026-02-05",
                "concepto": "Recibo nomina energia",
                "apuntes": [
                    {"cuenta_id": cuenta_debe.id, "debe": "1000.50", "haber": "0.00"},
                    {"cuenta_id": cuenta_haber.id, "debe": "0.00", "haber": "1000.50"},
                ],
            },
        )
        assert resp.status_code == 201
        asiento = resp.json()
        assert asiento["origen"] == "manual"
        assert asiento["regla_id"] is None

        proc = client.post(
            f"/api/v1/banco/movimientos/{mov['id']}/procesado",
            headers=_headers(ctx),
            json={"asiento_id": asiento["id"]},
        )
        assert proc.status_code == 200
        mov_out = proc.json()
        assert mov_out["procesado"] is True
        assert mov_out["asiento_id"] == asiento["id"]

        # Re-procesar el mismo movimiento → 409
        dup = client.post(
            f"/api/v1/banco/movimientos/{mov['id']}/procesado",
            headers=_headers(ctx),
            json={"asiento_id": asiento["id"]},
        )
        assert dup.status_code == 409

        # Movimiento inexistente → 404
        nf = client.post(
            "/api/v1/banco/movimientos/999999/procesado",
            headers=_headers(ctx),
            json={"asiento_id": asiento["id"]},
        )
        assert nf.status_code == 404

    def test_procesar_auto_marca_origen_y_regla(self, client, session, contexto):
        ctx = contexto()
        assert _crear_regla(client, ctx, auto_asentar=False).status_code == 201
        _importar(client, ctx)

        resp = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        assert resp.status_code == 200
        assert resp.json()["creados"] == 1

        asiento = session.exec(select(Asiento)).one()
        assert asiento.origen == "auto"
        assert asiento.regla_id is not None

        detalle = client.get(f"/api/v1/asientos/{asiento.id}", headers=_headers(ctx))
        assert detalle.status_code == 200
        assert detalle.json()["origen"] == "auto"


CSV_MULTI = (
    "Fecha Operación;Fecha Valor;Concepto;Importe;Saldo;Código;Referencia 1\n"
    "01/02/2026;01/02/2026;Mov A;10,00;10,00;572;REF-001\n"
    "05/02/2026;05/02/2026;Mov B;20,00;30,00;572;REF-002\n"
    "10/02/2026;10/02/2026;Mov C;30,00;60,00;174;REF-003\n"
)


def _csv2_rows():
    return (
        "Fecha Operación;Fecha Valor;Concepto;Importe;Saldo;Código;Referencia 1\n"
        "01/02/2026;05/02/2026;Recibo nomina energia;1.000,50;5.000,50;572;REF-001\n"
        "02/02/2026;06/02/2026;Recibo nomina energia;500,00;5.500,50;572;REF-002\n"
    )


class TestImportarFormatos:
    def test_importar_excel_santander_via_http(self, client, contexto):
        ctx = contexto()
        resp = _importar_bytes(
            client, ctx, _xlsx_santander(), "extracto.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["importados"] == 2
        assert data["duplicados"] == 0
        assert data["formato_detectado"] == "excel"

        pend = client.get("/api/v1/banco/pendientes", headers=_headers(ctx)).json()
        assert len(pend) == 2
        primero = pend[0]
        assert primero["fecha_operacion"] == "2026-02-05"
        assert primero["fecha_valor"] == "2026-02-10"
        assert primero["concepto"] == "Recibo luz marzo"
        assert Decimal(primero["importe"]) == Decimal("1500.50")
        assert primero["codigo_banco"] == "572"
        assert primero["referencia"] == "REF-LUZ"
        assert primero["procesado"] is False

    def test_importar_csb_cuaderno43_via_http(self, client, contexto):
        ctx = contexto()
        resp = _importar_bytes(client, ctx, _csb_extracto(), "extracto.csb", "text/plain")
        assert resp.status_code == 200
        data = resp.json()
        assert data["importados"] == 2
        assert data["formato_detectado"] == "csb"

        pend = client.get("/api/v1/banco/pendientes", headers=_headers(ctx)).json()
        assert len(pend) == 2
        primero = pend[0]
        assert primero["fecha_operacion"] == "2026-02-05"
        assert primero["concepto"] == "RECIBO LUZ MARZO"
        assert Decimal(primero["importe"]) == Decimal("1000.50")
        assert primero["codigo_banco"] == "572"
        assert primero["referencia"] == "REF-CSB-1"
        segundo = pend[1]
        assert Decimal(segundo["importe"]) == Decimal("-75.50")
        assert segundo["codigo_banco"] == "071"

    def test_importar_archivo_corrupto_422(self, client, contexto):
        ctx = contexto()
        resp = _importar_bytes(client, ctx, b"\x00\x01\x02garbage", "extracto.xlsx", "application/octet-stream")
        assert resp.status_code == 422
        assert "corrupt" in resp.json()["detail"].lower() or "corrupto" in resp.json()["detail"].lower()

    def test_importar_empresa_ajena_403(self, client, contexto, make_usuario, make_empresa):
        ctx = contexto()
        otro = make_usuario("otro1")
        make_empresa(otro, cif="B55555555", razon_social="Otra SL", nombre="Otra")
        h = {
            "Authorization": f"Bearer {create_access_token('otro1')}",
            "X-Empresa-Id": str(ctx["empresa"].id),
            "X-Ejercicio-Id": str(ctx["ejercicio"].id),
        }
        resp = client.post(
            "/api/v1/banco/importar",
            headers=h,
            files={"file": ("extracto.csv", CSV_EXTRACTO.encode("utf-8"), "text/csv")},
            data={"ignorar_duplicados": "false"},
        )
        assert resp.status_code == 403
        assert "acceso" in resp.json()["detail"].lower()

    def test_importar_ejercicio_cerrado_200(self, client, make_usuario, make_empresa, make_ejercicio):
        user = make_usuario("cerrado1")
        emp = make_empresa(user, cif="B11111111")
        ej = make_ejercicio(emp.id, estado="cerrado")
        h = {
            "Authorization": f"Bearer {create_access_token('cerrado1')}",
            "X-Empresa-Id": str(emp.id),
            "X-Ejercicio-Id": str(ej.id),
        }
        resp = client.post(
            "/api/v1/banco/importar",
            headers=h,
            files={"file": ("extracto.csv", CSV_EXTRACTO.encode("utf-8"), "text/csv")},
            data={"ignorar_duplicados": "false"},
        )
        assert resp.status_code == 200
        assert resp.json()["importados"] == 1

        pend = client.get("/api/v1/banco/pendientes", headers=h)
        assert pend.status_code == 200
        assert len(pend.json()) == 1


class TestMultiTenant:
    def test_reglas_aisladas_por_empresa(
        self, client, contexto, make_usuario, make_empresa, make_ejercicio, make_cuenta
    ):
        ctx = contexto()
        assert _crear_regla(client, ctx).status_code == 201

        otro = make_usuario("otro1")
        otra = make_empresa(otro, cif="B55555555", razon_social="Otra SL", nombre="Otra")
        ej_b = make_ejercicio(otra.id)
        make_cuenta(ej_b.id, "57200001", "Bancos c/c B", 4)
        make_cuenta(ej_b.id, "41000000", "Proveedores B", 4)
        h_b = {
            "Authorization": f"Bearer {create_access_token('otro1')}",
            "X-Empresa-Id": str(otra.id),
            "X-Ejercicio-Id": str(ej_b.id),
        }

        # Empresa B no ve la regla de A
        assert client.get("/api/v1/banco/reglas", headers=h_b).json() == []
        # A sigue viendo la suya
        reglas_a = client.get("/api/v1/banco/reglas", headers=_headers(ctx)).json()
        assert len(reglas_a) == 1
        assert reglas_a[0]["empresa_id"] == ctx["empresa"].id

        # Crear una regla en B: B solo ve la suya y A solo la suya
        resp_b = client.post(
            "/api/v1/banco/reglas",
            headers=h_b,
            json={
                "nombre": "Nomina B",
                "patron_regex": "nomina",
                "cuenta_debe": "57200001",
                "cuenta_haber": "41000000",
                "prioridad": 1,
                "auto_asentar": False,
                "activa": True,
            },
        )
        assert resp_b.status_code == 201
        assert client.get("/api/v1/banco/reglas", headers=h_b).json()[0]["empresa_id"] == otra.id
        assert len(client.get("/api/v1/banco/reglas", headers=_headers(ctx)).json()) == 1

    def test_procesar_batch_aisla_empresa_b(
        self, client, session, contexto, make_usuario, make_empresa, make_ejercicio, make_cuenta
    ):
        ctx = contexto()  # Empresa A: regla + movimiento
        assert _crear_regla(client, ctx).status_code == 201
        _importar(client, ctx)

        # Empresa B: movimiento sin regla
        otro = make_usuario("otro1")
        otra = make_empresa(otro, cif="B55555555", razon_social="Otra SL", nombre="Otra")
        ej_b = make_ejercicio(otra.id)
        make_cuenta(ej_b.id, "57200001", "Bancos c/c B", 4)
        make_cuenta(ej_b.id, "41000000", "Proveedores B", 4)
        h_b = {
            "Authorization": f"Bearer {create_access_token('otro1')}",
            "X-Empresa-Id": str(otra.id),
            "X-Ejercicio-Id": str(ej_b.id),
        }
        import_b = client.post(
            "/api/v1/banco/importar",
            headers=h_b,
            files={"file": ("extracto.csv", CSV_EXTRACTO.encode("utf-8"), "text/csv")},
            data={"ignorar_duplicados": "false"},
        )
        assert import_b.status_code == 200
        assert import_b.json()["importados"] == 1

        # Procesar solo en A
        proc = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        assert proc.status_code == 200
        assert proc.json()["creados"] == 1

        # Los pendientes de B siguen intactos y los de A vacíos
        assert len(client.get("/api/v1/banco/pendientes", headers=h_b).json()) == 1
        assert client.get("/api/v1/banco/pendientes", headers=_headers(ctx)).json() == []


class TestPrioridadReglas:
    def test_prioridad_mayor_gana(self, client, session, contexto):
        ctx = contexto()
        assert _crear_regla(
            client, ctx, nombre="Nomina Baja", patron_regex="NOMINA",
            cuenta_debe="57200001", cuenta_haber="41000000", prioridad=1, auto_asentar=False,
        ).status_code == 201
        assert _crear_regla(
            client, ctx, nombre="Nomina Alta", patron_regex="NOMINA",
            cuenta_debe="57000000", cuenta_haber="41000000", prioridad=10, auto_asentar=False,
        ).status_code == 201
        _importar(client, ctx)

        resp = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        assert resp.status_code == 200
        assert resp.json()["creados"] == 1
        assert resp.json()["fallidos"] == []

        asiento = session.exec(select(Asiento)).one()
        cuentas = [
            a.cuenta_id
            for a in session.exec(select(Apunte).where(Apunte.asiento_id == asiento.id)).all()
        ]
        # Gana la regla de prioridad 10 (cuenta 57000000 caja), no la de 57200001
        assert ctx["cuentas"]["caja"].id in cuentas
        assert ctx["cuentas"]["banco"].id not in cuentas

        regla_alta = session.exec(
            select(ReglaBanco).where(ReglaBanco.prioridad == 10)
        ).one()
        mov = session.exec(select(MovimientoBanco)).one()
        assert mov.regla_id == regla_alta.id
        assert asiento.regla_id == regla_alta.id


class TestIdempotenciaBatch:
    def test_procesar_2da_ejecucion_0_nuevos(self, client, session, contexto):
        ctx = contexto()
        assert _crear_regla(client, ctx).status_code == 201

        resp_imp = client.post(
            "/api/v1/banco/importar",
            headers=_headers(ctx),
            files={"file": ("extracto.csv", _csv2_rows().encode("utf-8"), "text/csv")},
            data={"ignorar_duplicados": "false"},
        )
        assert resp_imp.json()["importados"] == 2

        primera = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        assert primera.json()["creados"] == 2
        assert primera.json()["pendientes"] == 0

        segunda = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        assert segunda.status_code == 200
        assert segunda.json()["creados"] == 0
        assert segunda.json()["pendientes"] == 0

        # No se duplican asientos
        assert len(session.exec(select(Asiento)).all()) == 2
        # Ni movimientos procesados
        movs = session.exec(select(MovimientoBanco)).all()
        assert all(m.procesado for m in movs)


class TestPendientesFiltros:
    def test_filtros_desde_hasta_codigo_y_paginacion(self, client, contexto):
        ctx = contexto()
        resp = client.post(
            "/api/v1/banco/importar",
            headers=_headers(ctx),
            files={"file": ("multi.csv", CSV_MULTI.encode("utf-8"), "text/csv")},
            data={"ignorar_duplicados": "false"},
        )
        assert resp.json()["importados"] == 3

        def pendientes(**params):
            r = client.get("/api/v1/banco/pendientes", headers=_headers(ctx), params=params)
            assert r.status_code == 200
            return r.json()

        assert len(pendientes(desde="2026-02-05")) == 2
        assert len(pendientes(hasta="2026-02-05")) == 2
        assert len(pendientes(codigo_banco="572")) == 2
        assert len(pendientes(desde="2026-02-02", hasta="2026-02-09")) == 1
        assert [m["concepto"] for m in pendientes(desde="2026-02-02", hasta="2026-02-09")] == ["Mov B"]
        # Paginación
        assert len(pendientes(offset=0, limit=2)) == 2
        assert len(pendientes(offset=2, limit=2)) == 1


class TestLogTrazabilidad:
    def test_log_completo_del_procesamiento(self, client, session, contexto):
        ctx = contexto()
        regla = _crear_regla(client, ctx, auto_asentar=False)
        assert regla.status_code == 201
        regla_id = regla.json()["id"]

        csv = (
            "Fecha Operación;Fecha Valor;Concepto;Importe;Saldo;Código;Referencia 1\n"
            "01/02/2026;05/02/2026;Recibo nomina energia;1.000,50;5.000,50;572;REF-001\n"
            "02/02/2026;06/02/2026;Jardineria mensual;80,00;5.080,50;572;REF-002\n"
        )
        resp = client.post(
            "/api/v1/banco/importar",
            headers=_headers(ctx),
            files={"file": ("log.csv", csv.encode("utf-8"), "text/csv")},
            data={"ignorar_duplicados": "false"},
        )
        assert resp.json()["importados"] == 2

        proc = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        assert proc.json()["creados"] == 1
        assert proc.json()["pendientes"] == 1
        assert proc.json()["fallidos"] == []

        logs = client.get("/api/v1/banco/logs", headers=_headers(ctx))
        assert logs.status_code == 200
        log = logs.json()[0]
        assert log["usuario_id"] == ctx["usuario"].id
        assert log["creados"] == 1
        assert log["pendientes"] == 1
        assert json.loads(log["reglas_aplicadas_json"]) == [regla_id]
        assert json.loads(log["fallidos_json"]) == []


class TestEdgeCases:
    def test_crear_regla_regex_invalida_422(self, client, contexto):
        ctx = contexto()
        resp = _crear_regla(client, ctx, patron_regex="(nomina")
        assert resp.status_code == 422

    def test_crear_regla_cuenta_inexistente_422(self, client, contexto):
        # ERR-06: una regla de dominio (ValueError) debe responder 422, no 500.
        ctx = contexto()
        resp = _crear_regla(client, ctx, cuenta_debe="99999999")
        assert resp.status_code == 422

    def test_procesar_importe_cero_no_crea_asiento(self, client, session, contexto):
        ctx = contexto()
        assert _crear_regla(client, ctx).status_code == 201
        csv_cero = (
            "Fecha Operación;Fecha Valor;Concepto;Importe;Saldo;Código;Referencia 1\n"
            "01/02/2026;05/02/2026;Nomina cero;0,00;100,00;572;REF-000\n"
        )
        resp_imp = client.post(
            "/api/v1/banco/importar",
            headers=_headers(ctx),
            files={"file": ("cero.csv", csv_cero.encode("utf-8"), "text/csv")},
            data={"ignorar_duplicados": "false"},
        )
        assert resp_imp.json()["importados"] == 1

        proc = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        assert proc.status_code == 200
        assert proc.json()["creados"] == 0
        assert proc.json()["pendientes"] == 1
        assert session.exec(select(Asiento)).all() == []
        mov = session.exec(select(MovimientoBanco)).one()
        assert mov.procesado is False

    def test_importar_divisa_no_eur_avisa(self, client, contexto):
        ctx = contexto()
        csv_usd = (
            "Fecha Operación;Fecha Valor;Concepto;Importe;Saldo;Código;Referencia 1;Divisa\n"
            "01/02/2026;05/02/2026;Pago proveedor;10,00;10,00;572;REF-USD;USD\n"
        )
        resp = client.post(
            "/api/v1/banco/importar",
            headers=_headers(ctx),
            files={"file": ("usd.csv", csv_usd.encode("utf-8"), "text/csv")},
            data={"ignorar_duplicados": "false"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["importados"] == 1
        assert any("divisa" in e.lower() for e in data["errores"])


def _bulk_csv(n, concepto="Pago proveedor GEN"):
    rows = ["Fecha Operación;Fecha Valor;Concepto;Importe;Saldo;Código;Referencia 1"]
    rows += [
        f"01/02/2026;05/02/2026;{concepto} {i:04d};{(1000 + i)},50;5000,00;572;REF-{i:04d}"
        for i in range(n)
    ]
    return ("\n".join(rows) + "\n").encode("utf-8")


class TestRendimiento:
    """AC-01 (importar 1000 movs < 5s) y AC-02 (procesar 1000 movs con 20 reglas < 3s)."""

    def test_ac01_importar_1000_csv_menos_5s(self, client, contexto):
        import time

        ctx = contexto()
        t0 = time.perf_counter()
        resp = _importar_bytes(client, ctx, _bulk_csv(1000), "bulk.csv", "text/csv")
        elapsed = time.perf_counter() - t0
        assert resp.status_code == 200
        data = resp.json()
        assert data["importados"] == 1000
        assert data["duplicados"] == 0
        assert elapsed < 5.0, f"AC-01 superado: importar 1000 movs tardó {elapsed:.2f}s"

    def test_ac02_procesar_1000_movs_20_reglas_menos_3s(self, client, session, contexto):
        import time

        ctx = contexto()
        for i in range(20):
            resp = _crear_regla(
                client, ctx, nombre=f"Regla {i}", patron_regex="GEN",
                cuenta_debe="57200001", cuenta_haber="41000000",
                prioridad=10, auto_asentar=False,
            )
            assert resp.status_code == 201, resp.text
        imp = _importar_bytes(client, ctx, _bulk_csv(1000), "bulk.csv", "text/csv")
        assert imp.status_code == 200
        assert imp.json()["importados"] == 1000

        t0 = time.perf_counter()
        proc = client.post("/api/v1/banco/procesar", headers=_headers(ctx))
        elapsed = time.perf_counter() - t0
        assert proc.status_code == 200
        data = proc.json()
        assert data["creados"] == 1000
        assert data["fallidos"] == []
        assert elapsed < 3.0, f"AC-02 superado: procesar 1000 movs con 20 reglas tardó {elapsed:.2f}s"
