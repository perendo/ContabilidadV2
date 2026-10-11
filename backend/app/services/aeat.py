"""Generador de ficheros AEAT de posiciones fijas (spec 005, R1/R2).

Las plantillas por modelo (303/111/115/200) son **configuración** tipada:
cada campo declara su longitud, tipo (AN alfanumérico, N numérico con
decimales implícitos, SN firmado) y relleno. El validador recorre la plantilla
y comprueba longitudes y tipos antes de escribir el fichero (FR-028).

Encoding y final de línea parametrizables por modelo (R2); por defecto
UTF-8 y CRLF. Importes sin separador de miles y con decimales implícitos.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Literal

from app.services.fiscales_util import cuantizar2

__all__ = [
    "CampoPlantilla",
    "RegistroPlantilla",
    "MODELOS",
    "formatear_campo",
    "construir_registros",
    "validar_formato",
    "generar_contenido",
    "persistir_fichero",
]

TipoCampo = Literal["AN", "N", "SN"]

# Registros AEAT habituales: 01 cabecera, 02 detalle, 03 totales, 99 fin.
_ANCHO_NIF = 9
_ANCHO_RAZON = 40
_ANCHO_IMPORTE = 15  # 2 decimales implícitos


@dataclass(frozen=True)
class CampoPlantilla:
    nombre: str
    longitud: int
    tipo: TipoCampo = "AN"
    decimales: int = 0  # decimales implícitos para tipos numéricos
    padding: str = " "  # relleno AN; para N/SN se usa "0"


@dataclass(frozen=True)
class RegistroPlantilla:
    codigo: str  # "01" | "02" | "03" | "99"
    nombre: str
    campos: tuple[CampoPlantilla, ...] = field(default_factory=tuple)

    @property
    def longitud(self) -> int:
        # longitud total = código de registro (2) + suma de campos
        return 2 + sum(c.longitud for c in self.campos)


def _cabecera() -> RegistroPlantilla:
    return RegistroPlantilla(
        codigo="01",
        nombre="cabecera",
        campos=(
            CampoPlantilla("nif", _ANCHO_NIF, "AN"),
            CampoPlantilla("razon_social", _ANCHO_RAZON, "AN"),
            CampoPlantilla("periodo", 8, "AN"),
        ),
    )


def _totales() -> RegistroPlantilla:
    return RegistroPlantilla(
        codigo="03",
        nombre="totales",
        campos=(
            CampoPlantilla("total_base", _ANCHO_IMPORTE, "N", 2),
            CampoPlantilla("total_cuota", _ANCHO_IMPORTE, "N", 2),
        ),
    )


def _fin() -> RegistroPlantilla:
    return RegistroPlantilla(
        codigo="99",
        nombre="fin",
        campos=(CampoPlantilla("numero_registros", 6, "N", 0),),
    )


def _plantillas_detalle_tipos() -> dict[str, RegistroPlantilla]:
    """303: un registro de detalle por tipo de IVA del periodo."""
    return {
        "01": _cabecera(),
        "02": RegistroPlantilla(
            codigo="02",
            nombre="detalle_tipo",
            campos=(
                CampoPlantilla("tipo_iva", 5, "N", 2),
                CampoPlantilla("base", _ANCHO_IMPORTE, "N", 2),
                CampoPlantilla("cuota", _ANCHO_IMPORTE, "N", 2),
            ),
        ),
        "03": _totales(),
        "99": _fin(),
    }


def _plantillas_detalle_perceptor() -> dict[str, RegistroPlantilla]:
    """111/115: un registro de detalle por perceptor (CIF)."""
    return {
        "01": _cabecera(),
        "02": RegistroPlantilla(
            codigo="02",
            nombre="detalle_perceptor",
            campos=(
                CampoPlantilla("nif_perceptor", _ANCHO_NIF, "AN"),
                CampoPlantilla("razon_social", _ANCHO_RAZON, "AN"),
                CampoPlantilla("base", _ANCHO_IMPORTE, "N", 2),
                CampoPlantilla("cuota", _ANCHO_IMPORTE, "N", 2),
            ),
        ),
        "03": _totales(),
        "99": _fin(),
    }


def _plantillas_200() -> dict[str, RegistroPlantilla]:
    """200: un registro de detalle por casilla oficial del IS (cantidades firmadas)."""
    return {
        "01": _cabecera(),
        "02": RegistroPlantilla(
            codigo="02",
            nombre="detalle_casilla",
            campos=(
                CampoPlantilla("casilla", 4, "N", 0),
                CampoPlantilla("concepto", 30, "AN"),
                CampoPlantilla("importe", 16, "SN", 2),
            ),
        ),
        "03": RegistroPlantilla(
            codigo="03",
            nombre="totales",
            campos=(
                CampoPlantilla("total_base", _ANCHO_IMPORTE, "N", 2),
                CampoPlantilla("total_cuota", _ANCHO_IMPORTE, "N", 2),
                CampoPlantilla("total_diferencial", 16, "SN", 2),
            ),
        ),
        "99": _fin(),
    }


MODELOS: dict[str, dict[str, RegistroPlantilla]] = {
    "303": _plantillas_detalle_tipos(),
    "111": _plantillas_detalle_perceptor(),
    "115": _plantillas_detalle_perceptor(),
    "200": _plantillas_200(),
}


def formatear_campo(valor: object, campo: CampoPlantilla) -> str:
    """Da formato a un valor según el campo de la plantilla (posiciones fijas)."""
    if campo.tipo == "AN":
        s = "" if valor is None else str(valor)
        if len(s) > campo.longitud:
            s = s[: campo.longitud]
        return s.ljust(campo.longitud, campo.padding)
    d = cuantizar2(Decimal(0) if valor is None else Decimal(str(valor)))
    if campo.decimales:
        d = cuantizar2(d * (Decimal(10) ** campo.decimales))
    entero = int(d)
    if campo.tipo == "SN" and entero < 0:
        return "-" + str(-entero).rjust(campo.longitud - 1, "0")
    return str(entero).rjust(campo.longitud, "0")


def formatear_registro(datos: dict, plantilla: RegistroPlantilla) -> str:
    return plantilla.codigo + "".join(
        formatear_campo(datos.get(c.nombre), c) for c in plantilla.campos
    )


def construir_registros(
    modelo: str, datos: dict, encabezado: dict, fin_n: int
) -> list[str]:
    """Construye la secuencia de registros: cabecera, detalles, totales, fin.

    - `datos["detalles"]`: lista de dicts con los campos del registro 02.
    - `datos["totales"]`: dict con los campos del registro 03.
    """
    plantillas = MODELOS[modelo]
    lineas = [formatear_registro(encabezado, plantillas["01"])]
    for detalle in datos["detalles"]:
        lineas.append(formatear_registro(detalle, plantillas["02"]))
    lineas.append(formatear_registro(datos["totales"], plantillas["03"]))
    lineas.append(formatear_registro({"numero_registros": fin_n}, plantillas["99"]))
    return lineas


def validar_formato(modelo: str, registros: list[str]) -> list[str]:
    """Valida la secuencia de registros contra la plantilla del modelo.

    Devuelve la lista de errores (vacía si el fichero es conforme, FR-028):
    longitudes exactas, tipos numéricos con solo dígitos (o signo en SN).
    """
    plantillas = MODELOS[modelo]
    errores: list[str] = []
    for i, linea in enumerate(registros, start=1):
        codigo = linea[:2]
        plantilla = plantillas.get(codigo)
        if plantilla is None:
            errores.append(f"Registro {i}: tipo de registro desconocido '{codigo}'")
            continue
        if len(linea) != plantilla.longitud:
            errores.append(
                f"Registro {i} ({plantilla.nombre}): longitud {len(linea)} != {plantilla.longitud}"
            )
            continue
        offset = 2  # tras el código de registro
        for campo in plantilla.campos:
            trozo = linea[offset : offset + campo.longitud]
            offset += campo.longitud
            if campo.tipo == "N" and not trozo.isdigit():
                errores.append(
                    f"Registro {i} ({plantilla.nombre}): campo '{campo.nombre}' "
                    f"no numérico ('{trozo}')"
                )
            elif campo.tipo == "SN":
                valido = trozo.isdigit() or (
                    trozo.startswith("-") and trozo[1:].isdigit()
                )
                if not valido:
                    errores.append(
                        f"Registro {i} ({plantilla.nombre}): campo '{campo.nombre}' "
                        f"no numérico firmado ('{trozo}')"
                    )
    return errores


def generar_contenido(
    modelo: str, datos: dict, encabezado: dict, fin_n: int, encoding: str = "utf-8"
) -> tuple[bytes, str]:
    """Genera el contenido del fichero validado y su hash SHA-256 (FR-028/031)."""
    registros = construir_registros(modelo, datos, encabezado, fin_n)
    errores = validar_formato(modelo, registros)
    if errores:
        raise ValueError("Fichero no conforme a la plantilla AEAT: " + "; ".join(errores[:5]))
    contenido = "\r\n".join(registros) + "\r\n"
    data = contenido.encode(encoding)
    return data, sha256(data).hexdigest()


def persistir_fichero(
    base_dir: Path, empresa_id: int, anio: int, modelo: str, periodo: str, contenido: bytes
) -> str:
    """Escribe el fichero en `impuestos/{empresa_id}/{anio}/` (FR-030).

    Sobrescribe el mismo `{modelo}_{periodo}.txt` (idempotente). Devuelve la
    ruta relativa al directorio `impuestos/` para la trazabilidad.
    """
    directorio = base_dir / str(empresa_id) / str(anio)
    directorio.mkdir(parents=True, exist_ok=True)
    nombre = f"{modelo}_{periodo}.txt"
    (directorio / nombre).write_bytes(contenido)
    return f"{empresa_id}/{anio}/{nombre}"