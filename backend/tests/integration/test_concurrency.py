"""Concurrencia en modo WAL (SC-005): N escritores asentando en paralelo.

Los números correlativos deben asignarse 1..N sin duplicados y no debe
producirse ningún error "database is locked".
"""

from datetime import date
from concurrent.futures import ThreadPoolExecutor

from app.db import engine
from app.services.asientos import asentar
from app.models import Asiento


def _crear_y_asentar(ejercicio_id, usuario_id, c1, c2, errores, resultados):
    from sqlmodel import Session

    try:
        with Session(engine) as s:
            from decimal import Decimal
            from app.models import Apunte
            asiento = Asiento(
                ejercicio_id=ejercicio_id,
                numero=None,
                fecha=date(2026, 3, 1),
                concepto="Concurrencia",
                estado="borrador",
                creado_por_usuario_id=usuario_id,
            )
            s.add(asiento)
            s.commit()
            s.refresh(asiento)
            s.add(
                Apunte(
                    asiento_id=asiento.id,
                    cuenta_id=c1,
                    debe=Decimal("10.00"),
                    haber=Decimal("0.00"),
                )
            )
            s.add(
                Apunte(
                    asiento_id=asiento.id,
                    cuenta_id=c2,
                    debe=Decimal("0.00"),
                    haber=Decimal("10.00"),
                )
            )
            s.commit()
            asentar(s, asiento, usuario_id=usuario_id)
            resultados.append(asiento.numero)
    except Exception as e:  # noqa: BLE001
        if "locked" in str(e).lower():
            errores["locked"] += 1
        else:
            errores["otros"] += 1
            errores["msgs"].append(str(e))


def test_asentado_paralelo_correlativos_sin_duplicados(contexto):
    ctx = contexto()
    ejercicio_id = ctx["ejercicio"].id
    usuario_id = ctx["usuario"].id
    c1 = ctx["cuentas"]["banco"]
    c2 = ctx["cuentas"]["proveedor"]

    N = 8
    errores = {"locked": 0, "otros": 0, "msgs": []}
    resultados: list[int] = []

    with ThreadPoolExecutor(max_workers=N) as pool:
        futures = [
            pool.submit(
                _crear_y_asentar, ejercicio_id, usuario_id, c1.id, c2.id, errores, resultados
            )
            for _ in range(N)
        ]
        for f in futures:
            f.result()

    assert errores["locked"] == 0, f"database is locked: {errores['msgs']}"
    assert errores["otros"] == 0, errores["msgs"]
    assert sorted(resultados) == list(range(1, N + 1))
