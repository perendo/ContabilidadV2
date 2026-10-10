# Fase 0 — Research: Libro Mayor y Balance de Sumas y Saldos

**Feature**: `003-libro-mayor-balance`
**Fecha**: 2026-10-10

Resolución de incógnitas técnicas antes del diseño. Cada decisión indica el
enfoque elegido, la alternativa descartada y su justificación.

---

## R1. Generación de PDF (backend)

**Decisión**: usar **ReportLab** (`reportlab>=4.0`) en el backend para generar el PDF
de ambos informes (tamaño A4, fuente Helvetica, tablas con `platypus`).

**Rationale**:
- El Principio II exige que la generación de los informes viva en el backend; el
  frontend solo dispara la descarga.
- ReportLab usa las fuentes base (Helvetica) con soporte directo de Latin-1, por
  lo que los acentos y la `ñ/ç` del PGC y de las razones sociales se renderizan
  sin empaquetar ficheros TTF.
- Su API de tablas (`Table`/`TableStyle`/`SimpleDocTemplate`) permite reproducir
  con poco código el layout de columnas del Mayor (Fecha, Nº, Concepto, Debe,
  Haber, Saldo) y del Balance (Código, Nombre, Suma Debe, Suma Haber, Saldo
  Deudor, Saldo Acreedor).

**Alternativas consideradas**:
- **fpdf2**: más ligero, pero requiere una TTF Unicode para acentos correctos y
  su motor de tablas es más manual.
- **WeasyPrint**: excelente HTML→PDF, pero arrastra dependencias nativas
  (GTK/Pango) pesadas y frágiles en Windows; descartado por complejidad de
  despliegue multipuesto.
- **PDF en el frontend (jsPDF)**: viola el Principio II y duplicaría el formato;
  descartado.

**Impacto**: nueva dependencia declarada en `backend/pyproject.toml`; se instala
con `pip install -e .` desde `backend/`.

---

## R2. Formato del CSV (separador, decimales, codificación)

**Decisión**: CSV con separador **`;`**, decimal **coma (`,`)** y codificación
**UTF-8 con BOM** (`utf-8-sig`). Cada export (Mayor y Balance) abre con un bloque
de **encabezado** (razón social + CIF, ejercicio/año, rango de fechas, título del
informe, fecha/hora de generación) y luego la tabla, terminando con la fila de
**totales**.

**Rationale**:
- Es el formato que Excel en configuración regional española abre directamente
  sin asistente de importación, que es el uso real del usuario contable.
- El BOM evita que Excel malinterprete los acentos.
- `;` es obligatorio cuando el decimal es `,` para no ambigüar las columnas.

**Implementación**: se construye con `csv.writer(..., delimiter=";")` sobre un
`io.StringIO`, formateando cada `Decimal` con `f"{valor:.2f}".replace(".", ",")`
y devolviendo `StreamingResponse`/`Response` con
`Content-Type: text/csv; charset=utf-8` y `Content-Disposition: attachment;
filename="<informe>_<fechas>.csv"`.

**Alternativas consideradas**: separador `,` + decimal `.` (rompe expectativa del
usuario español); sin BOM (acentos corruptos en Excel). Descartadas.

---

## R3. Agregación y rendimiento (10.000 asientos < 3 s)

**Decisión**: una sola consulta SQL agregada con `GROUP BY apunte.cuenta_id`
(`SUM(debe)`, `SUM(haber)`) **filtrando por `asiento.estado = 'asentado'`,
`asiento.ejercicio_id = <ej>` y el rango de fechas**; el resto del trabajo
(asociar cada cuenta a su grupo/subgrupo por prefijo de código y propagar los
totales hacia arriba) se hace **en memoria** sobre el conjunto de cuentas
(decenas), no sobre los apuntes.

**Rationale**:
- El coste dominante es leer/filtrar apuntes; hacerlo en SQL con un índice sobre
  `apunte(cuenta_id)` y `asiento(ejercicio_id, fecha, estado)` evita traer 10.000
  filas a Python para sumar y cumple el objetivo de < 3 s holgadamente.
- La jerarquía PGC se deriva del **código** (longitud = nivel), establecida en
  `app/pgc.py`: un código es ancestro de otro si este último empieza por aquel.
  La propagación de sumas por prefijo es O(nº cuentas × profundidad) ≈ trivial.

**Alternativas consideradas**: sumar en Python iterando apuntes (más lento y más
memoria); `WITH RECURSIVE` en SQLite para el árbol (más complejo y sin ventaja
dado el bajo número de cuentas). Descartadas.

---

## R4. Saldo acumulado en el Libro Mayor (con y sin filtro de fechas)

**Decisión**: para el Mayor por cuenta, el **saldo inicial** es la suma de
`(debe − haber)` de los apuntes de las cuentas del subárbol con
`asiento.fecha < desde` (0 si no hay `desde`); los **movimientos** se listan
cronológicamente (por `fecha`, luego `asiento.numero`, luego `apunte.id`) y el
**saldo acumulado por línea** se calcula en Python partiendo del saldo inicial.

**Rationale**:
- Coherente con la semántica contable: el mayor con rango de fechas debe arrancar
  del saldo de apertura del periodo, no de cero.
- Ordenar por `numero` de asiento como desempate hace determinista el acumulado
  cuando hay varios asientos en la misma fecha.

**Nota**: si la cuenta seleccionada es un grupo/subgrupo (nivel 1-3), el Mayor
agrega los apuntes de **todas sus subcuentas** (prefijo de código), incluyendo las
cuentas compensadas (saldo 0 pero con movimiento), tal como se aclaró.

---

## R5. Criterio de inclusión y exclusión de cuentas

**Decisión**: el Balance y el listado global del Mayor **incluyen** toda cuenta
con movimiento (Σdebe > 0 o Σhaber > 0) en el periodo, **aunque su saldo sea 0**
(cuenta compensada), y **omiten** las cuentas sin ningún movimiento. Las cuentas
de grupo/subgrupo se muestran con el acumulado de su subárbol.

**Rationale**: refleja la aclaración de la spec (una cuenta con debe y haber
iguales sigue siendo informativa) y evita ruido de filas con todos los importes a
cero.

---

## R6. Clasificación deudor/acreedor y cuadre

**Decisión**: `saldo = Σdebe − Σhaber`. Si `saldo > 0` → **Saldo Deudor** = saldo
y Saldo Acreedor = 0; si `saldo < 0` → **Saldo Acreedor** = −saldo y Saldo Deudor
= 0; `saldo = 0` → ambas columnas a 0. Los totales generales suman ΣDebe y ΣHaber
de todo el ejercicio (o periodo) y ambos **deben coincidir** (solo hay asentados,
que ya cuadran); la respuesta JSON incluye un booleano `cuadra` para que la UI lo
evidencie.

**Rationale**: es la presentación clásica de cuatro columnas solicitada y expone
el invariante contable (Principio III).

---

## R7. Transporte del contexto multi-tenant en las descargas

**Decisión**: los botones de exportación **no** usan navegación directa
(`window.location`), sino `fetch` con las cabeceras `X-Empresa-Id`,
`X-Ejercicio-Id` (leídas de las cookies de contexto) y credenciales incluidas;
la respuesta se convierte a `Blob` y se descarga con `URL.createObjectURL` usando
el nombre del `Content-Disposition`.

**Rationale**: el contexto de empresa/ejercicio viaja por cabeceras personalizadas
(no por URL), y una navegación directa no las enviaría. `fetch`+`Blob` reutiliza
el mismo mecanismo que el resto de llamadas (`src/lib/api.ts`) y respeta el modelo
de auth por cookie httpOnly.

**Alternativas consideradas**: pasar `empresa_id`/`ejercicio_id` como query params
(duplica el contexto y debilita el aislamiento); generar el fichero en el cliente
(viola Principio II). Descartadas.

---

## R8. Impacto en el modelo de datos y Alembic

**Decisión**: **ningún** cambio de esquema. Los informes son vistas calculadas
sobre `cuenta`, `asiento` y `apunte`; no se crean tablas, columnas ni índices
nuevos y por tanto **no hay migración Alembic** asociada a esta feature.

**Rationale**: la información ya está íntegra en el modelo actual; añadir tablas de
informe introduciría redundancia y riesgo de desincronización. Los índices
existentes (FK sobre `apunte.cuenta_id`/`asiento_id`) son suficientes para el
objetivo de rendimiento.

---

## Resumen de decisiones

| # | Incógnita | Decisión |
|---|-----------|----------|
| R1 | Motor de PDF | ReportLab (backend) |
| R2 | Formato CSV | `;` + coma decimal + UTF-8 BOM + encabezado |
| R3 | Rendimiento | Agregación SQL `GROUP BY` + propagación por prefijo en memoria |
| R4 | Saldo acumulado | Saldo inicial pre-`desde` + acumulado en Python por orden cronológico |
| R5 | Cuentas incluidas | Con movimiento (aunque saldo 0); se omiten las de saldo/movimiento nulo |
| R6 | Cuadre / 4 columnas | saldo = debe−haber, clasificado; totales Debe=Haber + `cuadra` |
| R7 | Descarga con contexto | `fetch` con cabeceras + `Blob` |
| R8 | Modelo de datos | Sin cambios de esquema ni migración |
