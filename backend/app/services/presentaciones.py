"""Servicio de Presentación AEAT (spec 005, US-PRES).

Vista en pantalla (resumen por bloques + casillas oficiales) disponible en
cualquier estado (FR-026); el fichero de posiciones fijas (FR-027/028) solo se
genera con la liquidación/periodo cerrados (409 en borrador, FR-029) y se
persiste en `impuestos/{empresa_id}/{anio}` con trazabilidad (FR-030/031).
"""

from calendar import monthrange
from datetime import date
from pathlib import Path

from sqlmodel import Session, select

from app.api.errors import ApiError
from app.models import Ejercicio, Empresa, FicheroPresentacion
from app.services import aeat, facturas
from app.services.fiscales_util import cuantizar2, utcnow
from app.services.impuesto_sociedades import ajustes_de, datos_visibles, obtener_liquidacion

_IMPUESTOS_DIR = Path(__file__).resolve().parents[2] / "impuestos"

MODELOS = ("303", "111", "115", "200")

__all__ = ["vista", "generar_fichero", "MODELOS"]


def _rango_periodo(periodo: str, ejercicio: Ejercicio) -> tuple[date, date]:
    anio = str(ejercicio.anio)
    if not periodo.startswith(anio):
        raise ApiError(422, "El periodo no pertenece al ejercicio")
    if periodo == anio:
        return ejercicio.fecha_inicio, ejercicio.fecha_fin
    if len(periodo) == 6 and periodo[4] == "T" and periodo[5] in "1234":
        t = int(periodo[5])
        mes_inicio = (t - 1) * 3 + 1
        mes_fin = mes_inicio + 2
        desde = date(ejercicio.anio, mes_inicio, 1)
        hasta = date(ejercicio.anio, mes_fin, monthrange(ejercicio.anio, mes_fin)[1])
        return desde, hasta
    raise ApiError(422, "Periodo inválido (anio para el 200; anioT1..T4 para 303/111/115)")


# ---------------------------------------------------------------------------
# Vistas por modelo
# ---------------------------------------------------------------------------


def _bloque_descarga(cerrada: bool) -> dict:
    return {
        "habilitado": cerrada,
        "motivo": (
            None if cerrada else "El modelo requiere liquidación/periodo cerrados para descargar"
        ),
    }


def _vista_303(session: Session, ejercicio: Ejercicio, periodo: str) -> dict:
    desde, hasta = _rango_periodo(periodo, ejercicio)
    rep = facturas.listar_libro_iva(session, ejercicio.id, "repercutido", desde, hasta)
    sop = facturas.listar_libro_iva(session, ejercicio.id, "soportado", desde, hasta)
    resultante = cuantizar2(rep["total_cuota"] - sop["total_cuota"])
    resumen = {
        "base_repercutida": rep["total_base"],
        "cuota_repercutida": rep["total_cuota"],
        "base_soportada": sop["total_base"],
        "cuota_soportada": sop["total_cuota"],
        "resultante": resultante,
    }
    casillas = [
        {
            "casilla": 1,
            "label": "Base imponible operaciones corrientes (repercutido)",
            "importe": rep["total_base"],
        },
        {
            "casilla": 3,
            "label": "Cuota devengada operaciones corrientes (repercutido)",
            "importe": rep["total_cuota"],
        },
        {
            "casilla": 26,
            "label": "Base imponible operaciones corrientes (soportado deducible)",
            "importe": sop["total_base"],
        },
        {
            "casilla": 27,
            "label": "Cuotas soportadas deducibles en operaciones corrientes",
            "importe": sop["total_cuota"],
        },
        {"casilla": 46, "label": "Resultado de la liquidación", "importe": resultante},
    ]
    return {
        "modelo": "303",
        "periodo": periodo,
        "cerrada": ejercicio.estado == "cerrado",
        "resumen": resumen,
        "casillas": casillas,
        "bloque_descarga": _bloque_descarga(ejercicio.estado == "cerrado"),
    }


def _vista_retenciones(session: Session, ejercicio: Ejercicio, modelo: str, periodo: str) -> dict:
    desde, hasta = _rango_periodo(periodo, ejercicio)
    data = facturas.resumen_retenciones(session, ejercicio.id, modelo, desde, hasta)
    cerrada = ejercicio.estado == "cerrado"
    return {
        "modelo": modelo,
        "periodo": periodo,
        "cerrada": cerrada,
        "resumen": {
            "base_retenciones": data["total_base"],
            "cuota_retenciones": data["total_retencion"],
            "numero_perceptores": len(data["por_perceptor"]),
        },
        "casillas": [
            {
                "casilla": 1,
                "label": "Base de las retenciones practicadas",
                "importe": data["total_base"],
            },
            {
                "casilla": 2,
                "label": "Retenciones practicadas",
                "importe": data["total_retencion"],
            },
        ],
        "bloque_descarga": _bloque_descarga(cerrada),
    }


def _vista_200(session: Session, ejercicio: Ejercicio, periodo: str) -> dict:
    if periodo != str(ejercicio.anio):
        raise ApiError(422, "El modelo 200 requiere el periodo del ejercicio completo")
    liq = obtener_liquidacion(session, ejercicio.id)  # 404 si no existe
    base, cuota, diferencial = datos_visibles(liq)
    ajustes = ajustes_de(liq)
    aumentos = cuantizar2(sum(a.importe for a in ajustes if a.sentido == "aumento"))
    disminuciones = cuantizar2(sum(a.importe for a in ajustes if a.sentido == "disminucion"))
    resumen = {
        "resultado_contable": liq.resultado_contable,
        "aumentos": aumentos,
        "disminuciones": disminuciones,
        "base_imponible": base,
        "cuota_integra": cuota,
        "retenciones_pagos_cuenta": liq.retenciones_pagos_cuenta,
        "cuota_diferencial": diferencial,
    }
    casillas = [
        {"casilla": 100, "label": "Resultado contable", "importe": liq.resultado_contable},
        {"casilla": 201, "label": "Aumentos del resultado contable", "importe": aumentos},
        {"casilla": 202, "label": "Disminuciones del resultado contable", "importe": disminuciones},
        {"casilla": 300, "label": "Base imponible", "importe": base},
        {"casilla": 500, "label": "Cuota íntegra", "importe": cuota},
        {
            "casilla": 623,
            "label": "Retenciones y pagos a cuenta",
            "importe": liq.retenciones_pagos_cuenta,
        },
        {"casilla": 598, "label": "Cuota diferencial", "importe": diferencial},
    ]
    return {
        "modelo": "200",
        "periodo": periodo,
        "cerrada": liq.estado == "cerrada",
        "resumen": resumen,
        "casillas": casillas,
        "bloque_descarga": _bloque_descarga(liq.estado == "cerrada"),
    }


def vista(session: Session, ejercicio: Ejercicio, modelo: str, periodo: str) -> dict:
    if modelo not in MODELOS:
        raise ApiError(422, "Modelo no soportado (303/111/115/200)")
    if modelo == "303":
        return _vista_303(session, ejercicio, periodo)
    if modelo in ("111", "115"):
        return _vista_retenciones(session, ejercicio, modelo, periodo)
    return _vista_200(session, ejercicio, periodo)


# ---------------------------------------------------------------------------
# Fichero de posiciones fijas
# ---------------------------------------------------------------------------


def _cerrada(session: Session, ejercicio: Ejercicio, modelo: str) -> tuple[bool, str]:
    if modelo == "200":
        liq = obtener_liquidacion(session, ejercicio.id)
        if liq.estado != "cerrada":
            return False, "La liquidación del IS debe estar cerrada para descargar el 200"
        return True, ""
    if ejercicio.estado != "cerrado":
        return False, f"El periodo {modelo} debe estar cerrado para descargar"
    return True, ""


def _datos_aeat(
    session: Session, ejercicio: Ejercicio, empresa: Empresa, modelo: str, periodo: str
) -> tuple[dict, dict, int]:
    encabezado = {
        "nif": empresa.cif,
        "razon_social": empresa.razon_social,
        "periodo": periodo,
    }
    if modelo == "303":
        desde, hasta = _rango_periodo(periodo, ejercicio)
        rep = facturas.listar_libro_iva(session, ejercicio.id, "repercutido", desde, hasta)
        detalles = [
            {
                "tipo_iva": t["tipo_iva"],
                "base": t["base"],
                "cuota": t["cuota"],
            }
            for t in rep["totales_por_tipo"]
        ]
        datos = {
            "detalles": detalles,
            "totales": {"total_base": rep["total_base"], "total_cuota": rep["total_cuota"]},
        }
        return datos, encabezado, len(detalles)
    if modelo in ("111", "115"):
        desde, hasta = _rango_periodo(periodo, ejercicio)
        data = facturas.resumen_retenciones(session, ejercicio.id, modelo, desde, hasta)
        detalles = [
            {
                "nif_perceptor": p["tercero_cif"],
                "razon_social": p["tercero_razon_social"],
                "base": p["base_retencion"],
                "cuota": p["cuota_retencion"],
            }
            for p in data["por_perceptor"]
        ]
        datos = {
            "detalles": detalles,
            "totales": {
                "total_base": data["total_base"],
                "total_cuota": data["total_retencion"],
            },
        }
        return datos, encabezado, len(detalles)
    # 200
    liq = obtener_liquidacion(session, ejercicio.id)
    base, cuota, diferencial = datos_visibles(liq)
    detalles = [
        {"casilla": 100, "concepto": "Resultado contable", "importe": liq.resultado_contable},
        {"casilla": 300, "concepto": "Base imponible", "importe": base},
        {"casilla": 500, "concepto": "Cuota integra", "importe": cuota},
        {
            "casilla": 623,
            "concepto": "Retenciones y pagos a cuenta",
            "importe": liq.retenciones_pagos_cuenta,
        },
        {"casilla": 598, "concepto": "Cuota diferencial", "importe": diferencial},
    ]
    datos = {
        "detalles": detalles,
        "totales": {
            "total_base": base,
            "total_cuota": cuota,
            "total_diferencial": diferencial,
        },
    }
    return datos, encabezado, len(detalles)


def generar_fichero(
    session: Session,
    ejercicio: Ejercicio,
    empresa: Empresa,
    usuario,
    modelo: str,
    periodo: str,
) -> tuple[bytes, FicheroPresentacion]:
    if modelo not in MODELOS:
        raise ApiError(422, "Modelo no soportado (303/111/115/200)")
    cerrada, motivo = _cerrada(session, ejercicio, modelo)
    if not cerrada:
        raise ApiError(409, motivo)

    datos, encabezado, fin_n = _datos_aeat(session, ejercicio, empresa, modelo, periodo)
    contenido, hash_sha256 = aeat.generar_contenido(modelo, datos, encabezado, fin_n)
    ruta_rel = aeat.persistir_fichero(
        _IMPUESTOS_DIR, empresa.id, ejercicio.anio, modelo, periodo, contenido
    )

    fichero = session.exec(
        select(FicheroPresentacion).where(
            FicheroPresentacion.ejercicio_id == ejercicio.id,
            FicheroPresentacion.modelo == modelo,
            FicheroPresentacion.periodo == periodo,
        )
    ).first()
    if fichero is None:
        fichero = FicheroPresentacion(
            ejercicio_id=ejercicio.id,
            modelo=modelo,
            periodo=periodo,
            ruta=ruta_rel,
            hash_sha256=hash_sha256,
            generado_por_usuario_id=usuario.id,
        )
        session.add(fichero)
    else:
        fichero.ruta = ruta_rel
        fichero.hash_sha256 = hash_sha256
        fichero.generado_por_usuario_id = usuario.id
        fichero.generado_at = utcnow()
    session.commit()
    session.refresh(fichero)
    return contenido, fichero