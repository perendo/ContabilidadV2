# Research — 005-modulos-fiscales (Phase 0)

Sesión de clarificación 2026-10-11 ya resuelta en spec.md (`## Clarifications`).
Este documento consolida las decisiones técnicas para las incógnitas del plan.

## R1 — Plantillas AEAT de posiciones fijas (303/111/115/200)

**Decision**: implementar un generador propio de ficheros de **longitud fija**
cuyas "plantillas" por modelo (parámetros de cada campo: offset, longitud,
alineación, tipo numérico/alnum, decimales implícitos) se definen como
**configuración** (JSON en el repo o constantes tipadas) extraída de las
**especificaciones oficiales AEAT** de cada modelo.

**Rationale**:
- El requisito FR-027 exige "seguir **estrictamente** la plantilla de posiciones fijas definida por la AEAT". Un generador parametrizado garantiza que un cambio de versión del modelo solo afecta a la configuración, no al código.
- Los ficheros oficiales de la AEAT usan **registros de longitud fija** (cabecera con NIF/razón social, registros de detalle por percepción/factura, registro de totales y registro de fin), con importes sin separador de miles y decimales implícitos.
- No se introduce dependencia de librerías de terceros (stdlib suficiente con `Decimal` + formateo manual).

**Alternatives considered**:
- Librería del ecosistema AEAT (ej. `py3fed`/`facturae`): orientadas a facturación electrónica/FacturaE, no a modelos de presentación. Descartada.
- Plantillas embebidas en código (hardcoded arrays): menos testable ante cambios de versión de un modelo. Descartada en favor de configuración explícita + validador.

**Decisión de implementación (shape)**: para cada modelo, una estructura de
registros `[{nombre, posicion, longitud, tipo: "N9"/"AN"/"D12,2", padding}]`
+ regla de agregación (303: totales por tipo; 111/115: un registro por
perceptor; 200: casillas por bloques). El validador recorre la plantilla y
comprueba longitudes y tipos antes de escribir el fichero.

## R2 — Codificación y formato de los ficheros

**Decision**: encoding y final de línea **parametrizables por plantilla**;
por defecto `UTF-8` y `CRLF` (compatible con el portal). Los importes se
escriben en posiciones fijas con **decimales implícitos** (sin punto ni coma),
con `{0:0}{1:0}`-style (dígitos a la derecha), relleno según la plantilla.

**Rationale**: el requisito es "posiciones fijas estrictas"; la AEAT históricamente
ha usado Latin-1 y los portales modernos aceptan UTF-8. Parametrizarlo evita
reabrir el formato si un modelo específico exige otra codificación.

## R3 — Persistencia y descarga de ficheros

**Decision**: los ficheros generados se escriben en
`backend/impuestos/{empresa_id}/{anio}/{modelo}_{periodo}.txt`, aislando por
empresa/ejercicio (FR-030). La **regeneración sobrescribe** el archivo (mismo
nombre) y actualiza `hash_sha256` y trazabilidad (`fichero_presentacion`),
nunca duplica copias (idempotente). La **descarga** (FR-027) devuelve el fichero
persistido vía `GET`; si no existe pero el periodo está cerrado, se regenera y
descarga en la misma petición; si el periodo/liquidación no está cerrado → **409**
(descarga denegada aunque la vista en pantalla sí esté disponible).

**Rationale**: respuesta directa a la clarificación "botón de descarga del fichero
para el usuario que lo pida, que no impide guardarlos en el directorio impuestos":
ambas operaciones coexisten — generación/descarga a petición + persistencia
organizada por empresa/ejercicio.

**Alternatives considered**: guardar el fichero como BLOB en SQLite (complica la
inspección manual y el diagnóstico); descartado por la petición explícita del
directorio. Streaming a petición sin persistir (contrarío a FR-030); descartado.

## R4 — Ajustes extracontables del IS: JSON vs tabla

**Decision**: `liquidacion_impuesto_sociedades.ajustes_json` (TEXT) validado por
un schema Pydantic `AjusteIS {concepto: str, sentido: "aumento"|"disminucion",
importe: Decimal}` (lista serializada). Una fila por ejercicio; la lista es
pequeña (decenas de ajustes).

**Rationale**: la información es esencialmente un documento de trabajo fiscal con
agregación simple (Σaumentos − Σdisminuciones); una tabla normalizada añadiría
complejidad sin beneficio de consulta en esta fase. Al **cerrar** la liquidación,
se congela `base_imponible`, `cuota_integra` y `cuota_diferencial` (inmutables).

## R5 — Redondeo de céntimos en el asiento derivado

**Decision**: cuotas y retenciones se calculan con
`Decimal.quantize(Decimal("0.01"), ROUND_HALF_UP)`; el posible céntimo residual
entre el total de la factura y la suma de cuotas se absorbe en la **cuenta de
impuesto/contrapartida** de esa factura, garantizando ΣDebe = ΣHaber en todos los
casos (FR-005).

**Rationale**: el requisito SC-002 exige 0 asientos descuadrados; la absorción del
redondeo en la propia factura es la práctica estándar y mantiene el libro de IVA
al céntimo.

**Alternatives considered**: usar el tipo exacto con más de 2 decimales en la línea
de IVA (complica el libro y desvía del requisito FR-003 de 2 decimales);
descartado.

## R6 — Cuenta de retención en el asiento

**Decision**: modelo 111 (profesionales/trabajo) → cuenta `4751`; modelo 115
(alquileres) → cuenta `4751` por defecto (configurable por ejercicio; algunas
prácticas usan `473` para soportadas). El mapeo se configura en el servicio de
asientos por ejercicio para no forzar posturas contables.

**Rationale**: FR-015 admite 4751/473; la configuración por ejercicio permite a
cada asesor seguir su criterio PGC sin cambiar código.

## R7 — Vista de presentación AEAT (resumen + casillas)

**Decision**: `GET /api/v1/presentaciones/{modelo}?periodo` devuelve una
estructura del backend con (a) **resumen por bloques** (bases, cuotas,
retenciones, pagos a cuenta, cuota) y (b) **detalle por casillas oficiales** con
el número de casilla del modelo (desplegable en UI). El frontend **nunca
calcula** ninguno de estos valores (Principio II); solo los renderiza.

**Rationale**: la clarificación de la sesión pidió exactamente ambas vistas; y
devolver los valores desde el backend garantiza que la vista previa coincida con
el fichero que se va a generar (una única fuente de cálculo).

## Decisiones dependientes del entorno del proyecto (confirmadas)

- Alembic para nuevas tablas (gotcha: reemplazar `AutoString` por `sa.String`,
  añadir índices `ix_*` a mano).
- `empresa_usuario` es `Table` sqlmodel (no clase): usar `session.execute(...)`
  en consultas de acceso por empresa.
- Schemas Pydantic con `model_config = ConfigDict(from_attributes=True)`.
- Auth: `Bearer` o cookie; endpoints de negocio exigen `X-Empresa-Id` +
  `X-Ejercicio-Id` (400/403).
- `limiter` de slowapi vive en `app/rate_limit.py` (no en `main`).
- Ejecutar tests desde `backend/`; conftest migra BD temporal con Alembic.