"""Cuadro de cuentas base del PGC español (muestra curada, niveles 1-3).

Se siembra en cada ejercicio al crearlo para que el usuario solo tenga que
añadir las subcuentas (nivel 4+) que necesite. Los códigos son numéricos y el
nivel se deriva de su longitud: 1 dígito = grupo, 2 = subgrupo, 3 = cuenta.
"""

from sqlmodel import Session, select

from app.models import Cuenta

PGC_BASE: list[tuple[str, str]] = [
    # Grupo 1 — Financiación básica
    ("1", "Financiación básica"),
    ("10", "Capital"),
    ("100", "Capital social"),
    ("11", "Reservas"),
    ("110", "Prima de emisión o asunción"),
    ("112", "Reserva legal"),
    ("113", "Reservas voluntarias"),
    ("12", "Resultados pendientes de aplicación"),
    ("129", "Resultado del ejercicio"),
    ("17", "Deudas a largo plazo con entidades de crédito"),
    ("170", "Deudas a largo plazo con entidades de crédito"),
    ("18", "Pasivos por diferencias temporarias imponibles"),
    ("19", "Situaciones transitorias de financiación"),
    # Grupo 2 — Activo no corriente
    ("2", "Activo no corriente"),
    ("20", "Inmovilizaciones intangibles"),
    ("200", "Investigación"),
    ("201", "Desarrollo"),
    ("203", "Propiedad industrial"),
    ("206", "Aplicaciones informáticas"),
    ("21", "Inmovilizaciones materiales"),
    ("210", "Terrenos y bienes naturales"),
    ("211", "Construcciones"),
    ("212", "Instalaciones técnicas"),
    ("213", "Maquinaria"),
    ("216", "Mobiliario"),
    ("217", "Equipos para procesos de información"),
    ("218", "Elementos de transporte"),
    ("219", "Otro inmovilizado material"),
    ("28", "Amortización acumulada del inmovilizado"),
    ("280", "Amortización acumulada del inmovilizado intangible"),
    ("281", "Amortización acumulada del inmovilizado material"),
    ("29", "Deterioro de valor de activos no corrientes"),
    # Grupo 3 — Existencias
    ("3", "Existencias"),
    ("30", "Comerciales"),
    ("300", "Mercaderías A"),
    ("31", "Materias primas"),
    ("310", "Materias primas A"),
    ("32", "Productos en curso"),
    ("33", "Productos terminados"),
    ("39", "Deterioro de valor de las existencias"),
    # Grupo 4 — Acreedores y deudores por operaciones comerciales
    ("4", "Acreedores y deudores por operaciones comerciales"),
    ("40", "Proveedores"),
    ("400", "Proveedores"),
    ("401", "Proveedores, efectos comerciales a pagar"),
    ("41", "Acreedores y deudores, varias cuentas"),
    ("410", "Acreedores por prestaciones de servicios"),
    ("43", "Clientes"),
    ("430", "Clientes"),
    ("431", "Clientes, efectos comerciales a cobrar"),
    ("436", "Clientes de dudoso cobro"),
    ("44", "Deudores y acreedores varios"),
    ("440", "Deudores"),
    ("441", "Deudores, efectos comerciales a cobrar"),
    ("46", "Personal"),
    ("465", "Remuneraciones pendientes de pago"),
    ("47", "Administraciones públicas"),
    ("470", "Hacienda Pública, deudora"),
    ("472", "Hacienda Pública, IVA soportado"),
    ("473", "Hacienda Pública, retenciones y pagos a cuenta"),
    ("475", "Hacienda Pública, acreedora por conceptos fiscales"),
    ("476", "Organismos de la Seguridad Social, acreedores"),
    ("477", "Hacienda Pública, IVA repercutido"),
    # Grupo 5 — Cuentas financieras
    ("5", "Cuentas financieras"),
    ("52", "Deudas a corto plazo por préstamos recibidos"),
    ("520", "Deudas a corto plazo con entidades de crédito"),
    ("55", "Otras cuentas no bancarias"),
    ("57", "Tesorería"),
    ("570", "Caja, euros"),
    ("572", "Bancos e instituciones de crédito c/c vista, euros"),
    # Grupo 6 — Compras y gastos
    ("6", "Compras y gastos"),
    ("60", "Compras"),
    ("600", "Compras de mercaderías"),
    ("601", "Compras de materias primas"),
    ("62", "Servicios exteriores"),
    ("621", "Arrendamientos y cánones"),
    ("622", "Reparaciones y conservación"),
    ("623", "Servicios de profesionales independientes"),
    ("625", "Primas de seguros"),
    ("627", "Publicidad, propaganda y relaciones públicas"),
    ("628", "Suministros"),
    ("629", "Otros servicios"),
    ("63", "Tributos"),
    ("630", "Impuesto sobre beneficios"),
    ("631", "Otros tributos"),
    ("64", "Gastos de personal"),
    ("640", "Sueldos y salarios"),
    ("642", "Seguridad Social a cargo de la empresa"),
    ("66", "Gastos financieros"),
    ("662", "Intereses de deudas"),
    ("68", "Dotaciones para amortizaciones"),
    ("681", "Amortización del inmovilizado material"),
    # Grupo 7 — Ventas e ingresos
    ("7", "Ventas e ingresos"),
    ("70", "Ventas de mercaderías, de prestación de servicios y otros"),
    ("700", "Ventas de mercaderías"),
    ("705", "Prestación de servicios"),
    ("75", "Otros ingresos de gestión"),
    ("76", "Ingresos financieros"),
]


def sembrar_pgc(session: Session, ejercicio_id: int) -> int:
    """Añade el cuadro PGC base al ejercicio si aún no tiene cuentas.

    No hace commit (lo controla el llamante). Devuelve cuántas cuentas añadió.
    """
    ya = session.exec(
        select(Cuenta.id).where(Cuenta.ejercicio_id == ejercicio_id).limit(1)
    ).first()
    if ya is not None:
        return 0
    for codigo, nombre in PGC_BASE:
        session.add(
            Cuenta(
                ejercicio_id=ejercicio_id,
                codigo=codigo,
                nombre=nombre,
                nivel=len(codigo),
            )
        )
    return len(PGC_BASE)
