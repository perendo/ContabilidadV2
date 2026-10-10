from decimal import Decimal

from sqlmodel import select

from app.models import Apunte, Asiento, MovimientoBanco, ReglaBanco


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
