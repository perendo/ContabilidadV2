# Plan Técnico: Módulos Fiscales (Libros IVA, Retenciones IRPF, Impuesto sobre Sociedades)

**Spec**: `specs/005-modulos-fiscales/spec.md`
**Fecha**: 2026-10-11
**Estado**: Borrador técnico
**Referencia normativa**: PGC España 2007 (estructura de cuentas), R.D. 1514/2007; modelos AEAT 111, 115 y 200 (datos base, sin presentación telemática).

---

## 1. Objetivos y Alcance del Módulo

### 1.1 Objetivos

1. **Facturación como documento estructurado**: registrar facturas de venta y compra con desglose IVA (y Recargo de Equivalencia) y, en su caso, retenciones IRPF.
2. **Asiento automático y atómico**: al persistir una factura se genera en la **misma transacción** el asiento contable asociado (partida doble garantizada, ΣDebe = ΣHaber).
3. **Libros Registro de IVA**: consulta y exportación de Repercutido y Soportado con totales por tipo.
4. **Libro Registro de Retenciones**: asociación de retenciones a facturas y resúmenes por CIF para modelos 111/115.
5. **Liquidación del Impuesto sobre Sociedades**: resultado contable + ajustes extracontables + tipo 25% + retenciones/pagos a cuenta → cuota diferencial.

### 1.2 Principios rectores (constitucionales)

- La lógica fiscal y los cálculos residen **solo** en el backend (Principio II).
- Partida doble e inmutabilidad: los asientos generados nacen cuadrados y, una vez asentados, son inmutables (Principio III).
- Los periodos cerrados bloquean la creación/modificación de facturas y liquidaciones (Principio III).
- Multi-tenant: todo aislado por empresa/ejercicio (vía `ejercicio_id` y cabeceras `X-Empresa-Id`/`X-Ejercicio-Id`).
- Precisión monetaria: `Decimal` en toda la cadena (modelos SQLModel, schemas Pydantic, servicios), nunca `float`.

### 1.3 Alcance (In Scope)

- Modelos `Factura`, `LineaFacturaIVA`, `LiquidacionImpuestoSociedades` (+ enums de tipos).
- Endpoints CRUD de facturas con generación de asiento automática.
- Endpoints de consulta/exportación de Libros de IVA y de Retenciones (resumen 111/115 por CIF).
- Endpoints de **vista de presentación AEAT** (resumen por bloques + detalle por casillas oficiales, desplegable) y de **generación/descarga del fichero de posiciones fijas** para 303/111/115/200, persistido en `impuestos/{empresa}/{ejercicio}` con un único fichero por modelo/periodo.
- Endpoints de liquidación del IS (crear/ver/modificar ajustes, calcular, cerrar).
- UI Next.js: alta/edición de facturas, listados y libros de IVA/IRPF, pantalla de IS.

### 1.4 Fuera de Alcance (Out of Scope)

- **Envío telemático a la AEAT** (firma electrónica y subida al portal): la presentación la realiza el usuario descargando el fichero y subiéndolo manualmente.
- Facturación electrónica y firma digital.
- Nóminas completas y modelo 190.
- Multidivisa / conversión de cambio.
- Regímenes especiales y consolidación fiscal.

---

## 2. Modelo de Datos Completo (SQLModel / Python)

### 2.1 Convenciones aplicadas

- **Decimal**: `Numeric(19, 2)` para importes, cuotas y saldos; `Numeric(5, 2)` para porcentajes (tipos de IVA/RE/retención). Nunca `Float`.
- **Enums**: definidos como `class X(str, enum.Enum)` y persistidos como `String` (patrón del proyecto: los estados son `str` en `contable.py`). La validación fuerte ocurre en schemas Pydantic y servicios.
- **FKs**: `ondelete` coherente con el dominio: herencia funcional (ejercicio) → `CASCADE`; referencias operativas (cuenta, asiento, usuario) → `RESTRICT` o `SET NULL`.
- **Unicidad**: restricciones `UniqueConstraint` a nivel de tabla (la fuente de verdad es la BD) + comprobación en servicio para devolver 409 con mensaje claro.
- **Trazabilidad**: campos `creado_por_usuario_id`, `created_at` (patrón de `Asiento`, Spec 2).

### 2.2 Tabla `factura`

```python
from datetime import date, datetime
from decimal import Decimal
import enum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.schema import UniqueConstraint
from sqlmodel import Field, SQLModel


class OrigenFactura(str, enum.Enum):
    VENTA = "venta"            # IVA repercutido (emisora 477, 430 clientes)
    COMPRA = "compra"          # IVA soportado (deducible 472, 400 proveedores)


class TipoRetencion(str, enum.Enum):
    TRABAJO_PROFESIONAL = "111"   # profesionales / trabajo → modelo 111
    ALQUILER = "115"              # arrendamientos → modelo 115


class Factura(SQLModel, table=True):
    __tablename__ = "factura"
    __table_args__ = (
        # Unicidad fiscal: CIF + Nº factura por ejercicio
        UniqueConstraint(
            "ejercicio_id", "tercero_cif", "numero",
            name="uq_factura_ejercicio_cif_numero",
        ),
        Index("ix_factura_ejercicio_fecha", "ejercicio_id", "fecha"),
        Index("ix_factura_ejercicio_tipo", "ejercicio_id", "origen"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ejercicio_id: int = Field(
        sa_column=Column("ejercicio_id", ForeignKey("ejercicio.id", ondelete="RESTRICT"), nullable=False)
    )
    origen: str = Field(nullable=False, max_length=10)      # OrigenFactura.VENTA / COMPRA
    numero: str = Field(nullable=False, max_length=50)
    fecha: date = Field(nullable=False)
    fecha_operacion: date | None = Field(default=None)       # devengo efectivo (opcional)

    # Tercero / Perceptor (denormalizado para agrupación por CIF en 111/115/303)
    tercero_cif: str = Field(nullable=False, max_length=9)
    tercero_razon_social: str = Field(nullable=False, max_length=200)
    solo_identificativo: bool = Field(default=False)          # factura sin actividad económica

    tipo_retencion: str | None = Field(default=None, max_length=3)  # TipoRetencion (111|115)
    estado: str = Field(default="registrada", max_length=20)  # registrada | anulada
    notas: str | None = Field(default=None, max_length=1000)

    # Trazabilidad
    asiento_id: int | None = Field(
        default=None,
        sa_column=Column("asiento_id", ForeignKey("asiento.id", ondelete="RESTRICT"), nullable=True),
    )
    creado_por_usuario_id: int = Field(
        sa_column=Column("creado_por_usuario_id", ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    )
    created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
```

### 2.3 Tabla `linea_factura_iva`

```python
class LineaFacturaIVA(SQLModel, table=True):
    __tablename__ = "linea_factura_iva"
    __table_args__ = (
        Index("ix_linea_factura_factura", "factura_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    factura_id: int = Field(
        sa_column=Column("factura_id", ForeignKey("factura.id", ondelete="CASCADE"), nullable=False)
    )
    numero_linea: int = Field(default=1, nullable=False)
    descripcion: str = Field(nullable=False, max_length=300)

    base_imponible: Decimal = Field(sa_column=Column(Numeric(19, 2), nullable=False))
    tipo_iva: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    cuota_iva: Decimal = Field(sa_column=Column(Numeric(19, 2), nullable=False))

    # Recargo de Equivalencia (opcional, % y cuota; deducible en compras → 472)
    tipo_re: Decimal | None = Field(default=None, sa_column=Column(Numeric(5, 2), nullable=True))
    cuota_re: Decimal | None = Field(default=None, sa_column=Column(Numeric(19, 2), nullable=True))
    operacion_exenta: bool = Field(default=False)  # base 0 / no sujeta: sin cuota IVA

    # Retención IRPF a nivel de línea (base = base_imponible)
    base_retencion: Decimal | None = Field(default=None, sa_column=Column(Numeric(19, 2), nullable=True))
    pct_retencion: Decimal | None = Field(default=None, sa_column=Column(Numeric(5, 2), nullable=True))
    cuota_retencion: Decimal | None = Field(default=None, sa_column=Column(Numeric(19, 2), nullable=True))
```

> **Cálculo (servicio)**: `cuota_iva = round(base × tipo_iva / 100, 2)` y `cuota_retencion = round(base_retencion × pct / 100, 2)`. El redondeo se aplica con `Decimal.quantize` hacia `0.01` (ROUND_HALF_UP) y el asiento puede absorber un céntimo en la cuenta de mayor/importe cuando proceda.

### 2.4 Tabla `liquidacion_impuesto_sociedades`

```python
class LiquidacionImpuestoSociedades(SQLModel, table=True):
    __tablename__ = "liquidacion_impuesto_sociedades"
    __table_args__ = (
        UniqueConstraint("ejercicio_id", name="uq_lis_ejercicio"),  # 1 por ejercicio
    )

    id: int | None = Field(default=None, primary_key=True)
    ejercicio_id: int = Field(
        sa_column=Column("ejercicio_id", ForeignKey("ejercicio.id", ondelete="RESTRICT"), nullable=False)
    )
    resultado_contable: Decimal = Field(sa_column=Column(Numeric(19, 2), nullable=False))
    # Ajustes extracontables (JSON inmutable): [{"concepto": str, "sentido": "aumento"|"disminucion", "importe": Decimal}]
    ajustes_json: str = Field(nullable=False, max_length=12000)
    tipo_gravamen: Decimal = Field(default=Decimal("25"), sa_column=Column(Numeric(5, 2), nullable=False))
    retenciones_pagos_cuenta: Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(19, 2), nullable=False))
    # Resultados calculados (guardados al cerrar, inmutables)
    base_imponible: Decimal | None = Field(default=None, sa_column=Column(Numeric(19, 2), nullable=True))
    cuota_integra: Decimal | None = Field(default=None, sa_column=Column(Numeric(19, 2), nullable=True))
    cuota_diferencial: Decimal | None = Field(default=None, sa_column=Column(Numeric(19, 2), nullable=True))  # >0 a ingresar, <0 a devolver
    estado: str = Field(default="borrador", max_length=20)  # borrador | cerrada
    asiento_id: int | None = Field(
        default=None,
        sa_column=Column("asiento_id", ForeignKey("asiento.id", ondelete="RESTRICT"), nullable=True)
    )
    creado_por_usuario_id: int = Field(
        sa_column=Column("creado_por_usuario_id", ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    )
    cerrado_por_usuario_id: int | None = Field(
        default=None,
        sa_column=Column("cerrado_por_usuario_id", ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=True),
    )
    created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    cerrado_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
```

**Fórmula de cálculo (backend, único lugar)**:

```
base_imponible = resultado_contable
               + Σ(ajustes.aumento) − Σ(ajustes.disminucion)
cuota_integra    = round(base_imponible × tipo_gravamen / 100, 2)
cuota_diferencial = cuota_integra − retenciones_pagos_cuenta   # + → ingresar, − → devolver
```

### 2.5 Mapeo de cuentas PGC para el asiento automático

| Concepto | Venta (repercutido) | Compra (soportado) |
|----------|--------------------|--------------------|
| Cliente / Proveedor | **430** Clientes | **400** Proveedores |
| Ingreso / Gasto | **700** Ventas | **600** Compras |
| IVA repercutido | **477** HP IVA repercutido | — |
| IVA soportado deducible | — | **472** HP IVA soportado |
| RE (compra con recargo) | — | **472** (RE deducible, línea separada) |
| Retención (profesional) | — | **473** HP, retenciones y pagos a cuenta |
| Retención (alquiler) | — | **473** (o 4751 según práctica) |
| Total apunte contrapartida | Debe 430 = total factura | Haber 400 = total factura |

**Estructura del asiento (venta a crédito con IVA):**

```
430  Clientes            Debe = base + cuota IVA
     700  Ventas                        Haber = base
     477  H.P. IVA repercutido          Haber = cuota IVA
ΣDebe = ΣHaber
```

**Con retención (compra profesional):**

```
600  Compras             Debe = base
472  H.P. IVA soportado   Debe = cuota IVA
     400  Proveedores                 Haber = base + cuota IVA − retención
     4751/473  Retenciones            Haber = cuota retención
```

### 2.6 Migración Alembic

`alembic revision --autogenerate` y después **corregir a mano** (gotcha del proyecto):

- Reemplazar `sqlmodel.sql.sqltypes.AutoString` por `sa.String(...)`.
- Añadir a mano los `ix_factura_*`, `ix_linea_factura_factura` e índices de FK.
- Verificar que los enums se persisten como `String` (no `sa.Enum` de SQLAlchemy) para mantener el patrón del proyecto.
- `alembic upgrade head`.

### 2.7 Fichero de presentación AEAT y organización en disco

**Estructura de directorios** (base configurable, p. ej. `backend/impuestos/`):

```
impuestos/
  {empresa_id}/
    {anio_ejercicio}/
      303_2026T4.txt         # modelo + periodo
      111_2026T4.txt
      115_2026T4.txt
      200_2026.txt
```

- **Aislamiento**: la ruta se deriva del `ejercicio.empresa_id` y del `anio`, garantizando que empresa A nunca colisiona con empresa B.
- **Idempotencia**: la regeneración del mismo modelo/periodo **reemplaza** el fichero (mismo nombre) y actualiza la trazabilidad; nunca duplica copias.
- **Contenido**: registros de **longitud fija** según la plantilla oficial de cada modelo (cabecera NIF/razón social, registros T/P según modelo, registros de totales y de fin), validador propio que comprueba longitudes, alineación y totales antes de persistir.
- **Solo con datos cerrados**: generación permitida únicamente con liquidación/periodo cerrado (409 en otro estado); la vista en pantalla no requiere cierre.

**Tabla de trazabilidad `fichero_presentacion`** (opcional en esta fase pero recomendada):

```python
class FicheroPresentacion(SQLModel, table=True):
    __tablename__ = "fichero_presentacion"
    __table_args__ = (
        UniqueConstraint("ejercicio_id", "modelo", "periodo", name="uq_fichero_ejercicio_modelo_periodo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    ejercicio_id: int = Field(sa_column=Column("ejercicio_id", ForeignKey("ejercicio.id", ondelete="RESTRICT"), nullable=False))
    modelo: str = Field(nullable=False, max_length=3)        # 303 | 111 | 115 | 200
    periodo: str = Field(nullable=False, max_length=8)       # p. ej. "2026T4" o "2026"
    ruta: str = Field(nullable=False, max_length=255)
    hash_sha256: str = Field(nullable=False, max_length=64)
    generado_por_usuario_id: int = Field(ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    generado_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
```

---

## 3. Desglose de Tareas & Vertical Slices

> Cada slice entrega una funcionalidad vertical completa, compilable, testeable y demostrable (Principio I). Verificar en orden: backend `ruff` → `pytest`; frontend `lint` → `tsc --noEmit` → `build`.

### Slice 1 — Modelos de BD y Migraciones (horizontal pero defendible como cimiento)

**Entregable**: ningún slice posterior usa `create_all`; la BD se evoluciona solo vía Alembic.

| Tarea | Descripción |
|-------|-------------|
| T1.1 | Definir enums `OrigenFactura`, `TipoRetencion` y estados en `backend/app/models/` (nuevo módulo `fiscal.py` o extensión de `contable.py`). |
| T1.2 | Definir `Factura` y `LineaFacturaIVA` (Decimal, FKs, `UniqueConstraint` CIF+numero+ejercicio) y `LiquidacionImpuestoSociedades`. |
| T1.3 | Migración Alembic (con correcciones manuales de `sa.String`/índices comentadas arriba). |
| T1.4 | Schemas Pydantic de entrada/salida (`FacturaIn`, `FacturaOut`, `LineaFacturaIVAIn`, `ListaFacturasOut`, `LiquidacionIS…`) con `model_config = ConfigDict(from_attributes=True)` y validadores de decimales a 2 cifras. |
| T1.5 | Tests de migración: `alembic upgrade head` en BD temporal (conftest) + smoke de los nuevos índices/constraints. |

**Criterio de slice**: `pytest` verde incluyendo la migración; unicidad violada a nivel BD lanza `IntegrityError`.

### Slice 2 — Endpoints FastAPI de Facturación y Cierre Fiscal

| Tarea | Descripción |
|-------|-------------|
| T2.1 | Servicio `services/facturas.py`: validación (CIF, tipos, rangos, ejercicio abierto), cálculo de cuotas/retenciones, **asiento atómico** (factura + asiento + apuntes en un solo `session.commit`), reutilizando `asientos.py` para la corrección del cuadre. |
| T2.2 | `POST /api/v1/facturas` (crea factura + asiento, devuelve ambos), `GET /api/v1/facturas` (filtros origen/fecha/tercero, paginado), `GET /api/v1/facturas/{id}`. |
| T2.3 | Antes de crear: comprobar CIF+Nº+ejercicio (servicio devuelve 409 con mensaje claro si existe; la `UniqueConstraint` de BD es el backstop). |
| T2.4 | `GET /api/v1/facturas/libros/iva?origen=soportado|repercutido&desde&hasta` → detalle por factura + totales por tipo de IVA. `GET /facturas/libros/iva/exportar` → CSV/Excel tabular. |
| T2.5 | `GET /api/v1/facturas/retenciones?desde&hasta&tipo=111|115` → resumen **agregado por `tercero_cif`** (base, cuota retención, nº facturas, razón social). |
| T2.6 | `POST /api/v1/is` (crear/recalcular liquidación borrador), `GET /api/v1/is`, `PUT /api/v1/is` (modificar ajustes en borrador), `POST /api/v1/is/cerrar` (congela resultados + genera asiento de cierre del IS si procede). |
| T2.7 | Permisos: rol `contable` puede operar; ejercicio cerrado → 409; ejercicio no vinculado al usuario → 403; cabeceras `X-Empresa-Id`/`X-Ejercicio-Id` obligatorias → 400. |
| T2.8 | Tests de integración (sección 4). |
| T2.9 | Servicio `services/aeat.py`: construir los registros de **posiciones fijas** por modelo (303/111/115/200) según las plantillas oficiales AEAT; validador de formato (longitudes, alineación, tipos, totales); persistencia idempotente en `impuestos/{empresa}/{ejercicio}`; trazabilidad en `fichero_presentacion`. |
| T2.10 | `GET /api/v1/facturas/presentaciones/{modelo}?periodo` → vista de presentación (resumen por bloques + casillas oficiales); `POST /api/v1/facturas/presentaciones/{modelo}?periodo` → genera y devuelve el fichero (409 si 303 con periodo abierto o 111/115/200 sin liquidación/periodo cerrado). |

**Criterio de slice**: todos los `pytest` de facturación/retenciones/IS verdes; OpenAPI documenta los endpoints; 0 asientos descuadrados en la BD de prueba.

### Slice 3 — Interfaz Next.js (entrada de facturas y libros)

| Tarea | Descripción |
|-------|-------------|
| T3.1 | Ruta `/facturas`: tabla de facturas (filtros origen/fecha/tercero), paginación, columna "Asiento" con link al Diario. |
| T3.2 | Formulario de alta/edición: tercero (CIF/razón social), número, fecha, origen; líneas dinámicas con base/tipo IVA/RE/retención; el frontend muestra el **preview calculado** del asiento pero el backend es la fuente del cálculo definitivo (Principio II). |
| T3.3 | Ruta `/fiscal/libros-iva` (o tabs en `/facturas`): vista Soportado/Repercutido con totales por tipo y botón de exportación. |
| T3.4 | Ruta `/fiscal/retenciones`: resumen por CIF para 111/115 (tabla de totales + detalle de facturas). |
| T3.5 | Ruta `/fiscal/is`: formulario de liquidación (resultado contable, ajustes aumento/disminución, retenciones/pagos a cuenta, tipo), calculador fiscal del IS y botón cerrar. |
| T3.6 | Manejo de errores (409 duplicado, 403/400 contexto, 409 ejercicio cerrado) con mensajes comprensibles. |
| T3.7 | Vista de **presentación AEAT** por modelo: resumen simplificado por bloques + detalle por casillas oficiales desplegable; botón "Generar fichero" deshabilitado hasta cierre de liquidación/periodo; tras generación, enlace de descarga del fichero persistido en `impuestos/{empresa}/{ejercicio}`. |

**Criterio de slice**: `npm run build` verde; flujo completo demostrable: alta factura con IVA → consulta Libro de IVA → resumen de retenciones → liquidación IS.

---

## 4. Casos de Prueba (Pytest / Integration)

Fixture `contexto(rol=...)` del `conftest` existente; crear ejercicio vía API con `contexto(rol="admin")` cuando el test no dependa de rol, y **vincular el usuario** a la empresa en tests que esperan 403 por rol.

### 4.1 Cuadre de IVA y asiento automático

- `test_factura_venta_genera_asiento_cuadrado`: venta 1.000 € al 21% → apuntes (430 deb 1.210 / 700 hab 1.000 / 477 hab 210); ΣDebe = ΣHaber; `Factura.asiento_id` poblado; nº correlativo de asiento asignado.
- `test_factura_compra_con_iva_y_retencion_cuadra`: 1.000 €, IVA 21%, retención 15% → 600 deb 1.000 / 472 deb 210 / 400 hab 1.060 / 4751 hab 150.
- `test_multi_tipo_iva_una_linea_por_tipo`: base 21% + base 10% → dos líneas en 477, total cuadra.
- `test_recargo_equivalencia_se_registra`: compra con RE 5,2% → cuota RE en línea/472 y total cuadra.
- `test_redondeo_2_decimales`: base con 3 decimales → cuotas cuantizadas a 2 decimales y ΣDebe=ΣHaber (absorbe céntimo).
- `test_operacion_exenta_sin_cuota`: base 0 / exenta → sin línea 472, asiento de gasto puro.

### 4.2 Unicidad y duplicados

- `test_duplicado_cif_numero_ejercicio_409`: mismo CIF+Nº en el mismo ejercicio → HTTP 409; segundo registro no crea asiento.
- `test_mismo_numero_distintos_ejercicios_ok`: mismo CIF+Nº en ejercicio distinto → 201.
- `test_unicidad_bd_integrity`: inserción directa duplicada → `IntegrityError` (salvaguarda a nivel BD).

### 4.3 Retenciones y agrupación por CIF

- `test_resumen_111_por_cif`: 3 facturas de un profesional (retención 15%) → resumen agrega bases y cuotas por CIF; total = Σ facturas al céntimo.
- `test_resumen_115_separa_alquileres`: facturas de alquiler → aparecen en tipo 115 y no en 111.
- `test_perceptor_sin_cif_valido_excluido`: CIF mal formado → excluido de resúmenes (validación previa en schema).
- `test_retencion_fuera_de_rango_400`: pct > 100 o cuota≠base×pct → 422/400.

### 4.4 Impuesto sobre Sociedades

- `test_is_base_y_cuota`: resultado 100.000, aumentos 5.000, disminuciones 8.000, tipo 25% → base 97.000, cuota íntegra 24.250, cuota diferencial 20.250 (retenciones 4.000).
- `test_is_a_devolver`: retenciones > cuota íntegra → cuota diferencial negativa (devolución).
- `test_is_una_por_ejercicio`: segunda liquidación en el mismo ejercicio → 409.
- `test_is_cerrada_inmutable`: tras cerrar, modificaciones → 409; resultado congelado.
- `test_is_ejercicio_cerrado_409`: liquidación o factura en ejercicio cerrado → 409.

### 4.5 Multi-tenant y seguridad

- `test_aislamiento_empresas`: empresa A no ve facturas/retenciones/IS de empresa B.
- `test_contexto_faltante_400` y `test_sin_acceso_empresa_403` (patrón ya existente en el proyecto).

### 4.6 Fichero de presentación AEAT (posiciones fijas)

- `test_fichero_303_posiciones_fijas`: genera el fichero 303 de un trimestre y valida longitudes, alineación y totales contra la plantilla oficial.
- `test_fichero_111_115_por_cif`: el fichero 111/115 contiene un registro por perceptor con retenciones correctas en posiciones fijas.
- `test_fichero_200_is`: el fichero del IS reproduce las casillas oficiales (resultado, base, cuota íntegra, diferencial) calculadas en el test 4.4.
- `test_fichero_solo_con_periodo_cerrado_409`: `POST` de fichero con periodo/liquidación en borrador → 409; botón deshabilitado en la API de vista.
- `test_directorio_impuestos_por_empresa_ejercicio`: el fichero se persiste en `impuestos/{empresa}/{anio}`; regenerar el mismo modelo/periodo reemplaza el fichero (mismo nombre), sin duplicados.
- `test_trazabilidad_fichero_registrada`: `fichero_presentacion` guarda modelo, periodo, ruta, hash y usuario/fecha de generación.
- `test_regeneracion_recalcula_hash`: regenerar tras cambios en datos cerrados actualiza el fichero y su hash.

---

## 5. Criterios de Aceptación y Validación

### 5.1 Criterios funcionales (mapeo a Success Criteria de la spec)

| ID | Criterio | Verificación |
|----|----------|--------------|
| AC-01 | Factura con IVA genera asiento cuadrado automático | Test 4.1 cuadre + revisión del asiento en Diario |
| AC-02 | 0 asientos descuadrados generados desde facturas | Suite completa de cuadre en CI |
| AC-03 | Duplicados CIF+Nº+ejercicio rechazados (HTTP 409) | Test 4.2 |
| AC-04 | Libro IVA consultable y totalizado por tipo (< 3 s con 500 facturas) | Test de carga + consulta 4.x |
| AC-05 | Resumen retenciones por CIF coincide al céntimo con Σ facturas | Test 4.3 |
| AC-06 | Liquidación IS reproducible y correcta (base, cuota íntegra, diferencial) | Test 4.4 |
| AC-07 | Ejercicios cerrados bloquean escritura | Test 4.4/4.5 |
| AC-08 | Tipos 21/10/4/0/RE soportados sin romper cuadre | Test 4.1 |
| AC-09 | Ficheros 303/111/115/200 100% conformes a la plantilla oficial de posiciones fijas AEAT | Test 4.6 |
| AC-10 | Ficheros organizados por empresa/ejercicio, un único por modelo/periodo, con trazabilidad | Test 4.6 |
| AC-11 | Vista de presentación (resumen + casillas oficiales) y descarga denegada hasta cierre | Test 4.6 (409) + UI T3.7 |

### 5.2 Calidad y normativa

- `ruff` y `pytest` del backend verdes; `lint` + `tsc --noEmit` + `build` del frontend verdes.
- Los asientos automáticos son **inmutables** tras asentarse (solo rectificación/estorno; no edición).
- `Decimal` en el 100% de columnas y schemas monetarios/porcentuales (grep de `Float`/`float` en modelos → 0).
- Trazabilidad completada: `creado_por_usuario_id`/`created_at` en facturas y liquidaciones.
- Cumplimiento PGC: cuentas mapeadas (400/430/600/700/472/477/4751/473) verificadas contra el PGC sembrado en el test de integración.

### 5.3 Criterios de "listo para producción" del slice

Cada slice cierra con: código formateado + tests verdes + documentación de endpoint (OpenAPI) + demo funcional ejecutable. No se integra un slice parcial o con tests de cuadre rojos.

---

## 6. Riesgos y Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Céntimos de redondeo descuadran asiento | Media | Alto | Redondeo HALF_UP centralizado + prueba dedicada por combinación de tipos |
| Duplicado de factura por reintento (doble POST) | Media | Alto | `UniqueConstraint` BD + chequeo 409 + idempotencia documentada |
| Tipo de IVA/RE no contemplado | Media | Medio | Validación por `TipoIVA`/RE configurable (tabla de tipos o enum extensible) |
| CIF inválido arruina resúmenes AEAT | Media | Medio | Validación sintáctica CIF (schema) + exclusión explícita del agregado |
| Asiento automático con cuenta inexistente en el ejercicio | Baja | Alto | Validar cuentas PGC con `sembrar_pgc` al crear factura (las 3 últimas dígitos deben existir; si no, 422) |
| Modificación de factura tras asentar | Baja | Alto | Factura `registrada` → asiento inmutable; cambios solo vía factura rectificativa/anulación |
| Cambio de plantilla oficial AEAT (nueva versión de modelo) | Media | Alto | Parametrizar plantillas (longitudes/campos/totales) como configuración; tests de conformidad contra la plantilla vigente |

---

## 7. Próximos Pasos

1. `/speckit.plan` (formal) y `/speckit.tasks` para convertir este documento en tareas con casillas `[X]`.
2. Implementar **Slice 1** (modelos + migración + schemas) y validar.
3. Implementar **Slice 2** (servicios + endpoints) y validar con la suite de integración.
4. Implementar **Slice 3** (UI Next.js) y validar `build`.
5. Actualizar `specs/001-modulo-core-contable/tasks.md` y las casillas del feature.