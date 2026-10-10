# Especificación: Conciliación Bancaria con Auto-Matching

**Feature**: `004-conciliacion-bancaria`
**Fecha**: 2026-10-10
**Estado**: Borrador

---

## Resumen

Permitir importar extractos bancarios (**Excel Santander, CSV estándar, CSB/Cuaderno 43**), aplicar reglas de auto-matching para generar asientos automáticamente (ej. "RECIBO UNION FENOSA" → Proveedores 410 / Tesorería 572), y dejar los movimientos sin match como pendientes para completar manualmente.

---

## Formatos de Importación Soportados

### 1. Excel Santander (.xlsx)
**Estructura detectada en `Data/1. MovimientosCuenta ene_feb26.xlsx`:**
- Filas 1-7: Cabecera informativa (titular, IBAN, saldos disponible/real)
- Fila 8: Headers → `Fecha Operación`, `Fecha Valor`, `Concepto`, `Importe`, `Divisa`, `Saldo`, `Divisa`, `Código`, `Número documento`, `Referencia 1`, `Referencia 2`, `Info adicional`
- Filas 9+: Datos
  - `Importe`: negativo = cargo (salida), positivo = abono (entrada)
  - `Código`: tipo operación (072=traspaso, 174=recibo, 135=liquidación, 071=transferencia, 043=ingreso efectivo, 100=préstamo)
  - `Referencia 1/2`: mandatos, números de recibo, IDs de operación

### 2. CSV Estándar Español
- Separador `;`, decimal `,`, encoding UTF-8/Latin1
- Mismas columnas que Excel (exportación directa del banco)
- Posible BOM UTF-8

### 3. CSB / Cuaderno 43 (AEB Norma 43)
- Formato texto plano, longitud fija por registro
- Registros: Tipo 01 (cabecera), Tipo 02 (movimientos), Tipo 03 (totales), Tipo 99 (final)
- Ejemplo registro 02: `02|20260227|20260227|-59500|072|TRASPASO...|REF1|REF2|...`
- Parser: `pybank43` o implementación propia según especificación AEB

---

## Contexto y Motivación

- **Problema actual**: Conciliación 100% manual. Cada movimiento del banco hay que buscar la factura, crear asiento, cuadrar.
- **Oportunidad**: 70-80% de movimientos son recurrentes (recibos, nóminas, alquileres, seguros). Patrones predecibles en `concepto` / `referencia`.
- **Objetivo**: Reducir trabajo manual a excepciones (movimientos sin regla o importes distintos).

---

## Alcance (In Scope)

1. **Importación** de extractos (CSV estándar español, MT940, N43) vía `POST /api/v1/banco/importar`
2. **Reglas de auto-matching** (configurables por empresa/ejercicio):
   - Patrones regex sobre `concepto` / `referencia`
   - Mapeo a 2 cuentas (debe/haber) + importe fijo o % del movimiento
   - Prioridad entre reglas
3. **Procesamiento batch**: Job que recorre `MovimientoBanco` sin procesar, aplica reglas, crea asientos en estado `borrador` o `asentado` (configurable)
4. **Pendientes**: Listado `GET /api/v1/banco/pendientes` con filtros, UI para completar (seleccionar cuentas, añadir líneas)
5. **Trazabilidad**: Link bidireccional `MovimientoBanco ↔ Asiento`

---

## Fuera de Alcance (Out of Scope)

- Conciliación contable formal (certificación bancaria)
- Matching por importe + fecha (fuzzy matching) — v2
- Reglas con IA/ML — v3
- Importación directa desde API bancaria (PSD2) — v2

---

## Historias de Usuario

### US1: Importar extracto bancario (P1)
**Como** contable
**Quiero** subir un Excel Santander / CSV / CSB del banco
**Para** tener los movimientos en la app

**Criterios de aceptación**:
- SC-01: Excel Santander (cabecera 7 filas + headers fila 8) → parse correcto, N movimientos creados
- SC-02: CSV con separador `;`, decimal `,`, encoding UTF-8/Latin1 → 200 OK, N movimientos creados
- SC-03: CSB/Cuaderno 43 (AEB Norma 43) → parse registros 01/02/03/99 correcto
- SC-04: Duplicados (misma fecha+importe+referencia → hash SHA256) → 409 o ignorados según flag
- SC-05: Movimientos guardados en `MovimientoBanco` con `procesado=False`, `fecha_valor`, `fecha_operacion`, `codigo_banco`, `referencia_1`, `referencia_2`

### US2: Configurar reglas de auto-matching (P1)
**Como** contable
**Quiero** definir reglas: "si concepto contiene X → cuenta D / cuenta H"
**Para** que los recibos recurrentes se apunten solos

**Criterios de aceptación**:
- SC-05: CRUD reglas por empresa (`POST/GET/PUT/DELETE /api/v1/banco/reglas`)
- SC-06: Regla = {patron_regex, cuenta_debe, cuenta_haber, importe_fijo|null, porcentaje|null, prioridad, auto_asentar:bool}
- SC-07: Prioridad resuelve conflictos (mayor prioridad gana)
- SC-08: Test de regla en UI: "Simular" muestra qué movimientos matcharían

### US3: Procesar auto-matching y generar asientos (P1)
**Como** contable
**Quiero** lanzar el proceso y que cree los asientos
**Para** no tener que hacerlo a mano

**Criterios de aceptación**:
- SC-09: `POST /api/v1/banco/procesar` → recorre pendientes, aplica reglas por prioridad, crea asientos
- SC-10: Match exitoso → `Asiento` (borrador/asentado), `MovimientoBanco.procesado=True`, `asiento_id` link
- SC-11: No match → queda `procesado=False` (pendiente)
- SC-12: Idempotente: re-ejecutar no duplica asientos

### US4: Gestionar pendientes manualmente (P1)
**Como** contable
**Quiero** ver los movimientos sin match y completarlos
**Para** cerrar la conciliación

**Criterios de aceptación**:
- SC-13: `GET /api/v1/banco/pendientes?desde&hasta&cuenta` → lista paginada
- SC-14: UI muestra: Fecha, Concepto, Importe, Saldo, [Buscar cuenta D] [Buscar cuenta H] [Crear asiento]
- SC-15: Al crear asiento → marca movimiento como procesado, link al asiento
- SC-16: Filtro "solo pendientes" por defecto en Diario

### US5: Trazabilidad y auditoría (P2)
**Como** auditor
**Quiero** ver qué regla generó cada asiento y cuáles fueron manuales
**Para** verificar la conciliación

**Criterios de aceptación**:
- SC-17: En `AsientoOut` campo `origen: "auto" | "manual" | "importado"`
- SC-18: Si `auto` → `regla_id` que lo generó
- SC-19: Log de procesamiento: timestamp, reglas aplicadas, N creados, N fallidos

---

## Modelo de Datos (Nuevo)

### `MovimientoBanco`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| ejercicio_id | FK | Aísla por ejercicio |
| fecha_operacion | date | Fecha operación (banco) |
| fecha_valor | date | Fecha valor (contable) |
| concepto | str(300) | Texto crudo del banco |
| referencia | str(100) | Nº recibo, Nº operación (Referencia 1) |
| referencia_2 | str(100) | Referencia 2 (mandato, etc.) |
| importe | Decimal(19,2) | Negativo=cargo, Positivo=abono |
| saldo | Decimal(19,2) | Saldo tras movimiento |
| divisa | str(3) | Default EUR |
| codigo_banco | str(10) | Código operación banco (072, 174, 135, 071, 043, 100...) |
| numero_documento | str(50) | Nº documento banco |
| info_adicional | str(500) | Campo libre banco |
| procesado | bool | Default False |
| asiento_id | FK(Asiento) | Nullable, link si generó asiento |
| regla_id | FK(ReglaBanco) | Nullable, regla que matchó |
| hash_unicidad | str(64) | SHA256(fecha_valor+importe+referencia) para dedup |
| origen_archivo | str(20) | `excel` | `csv` | `csb` |

### `ReglaBanco`
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| empresa_id | FK | Aísla por empresa |
| nombre | str(100) | "Recibo Union Fenosa" |
| patron_regex | str(200) | `UNION FENOSA|FENOSA` |
| cuenta_debe | str(10) | Código cuenta (debe existir en ejercicio) |
| cuenta_haber | str(10) | Código cuenta |
| importe_fijo | Decimal | Null = usar importe del movimiento |
| porcentaje | Decimal(5,2) | Null = 100% |
| prioridad | int | Default 0, mayor = antes |
| auto_asentar | bool | Default False (crea borrador) |
| activa | bool | Default True |

---

## Reglas de Negocio

1. **Signo del importe**: Banco usa signo contrario a contabilidad (cargo = negativo). Regla define cuentas contables estándar (debe/haber positivo).
2. **Partida doble garantizada**: Cada regla define exactamente 2 cuentas → asiento siempre cuadra.
3. **Multi-empresa**: Reglas y movimientos aislados por `empresa_id` (vía `ejercicio_id`).
4. **Idempotencia**: `hash_unicidad` evita duplicados en re-importaciones.
5. **Orden de match**: Prioridad DESC → primera regla que matcha gana.

---

## Endpoints API

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/banco/importar` | Subir archivo (formato auto-detectado: excel/csv/csb), devuelve {importados, duplicados, errores, formato_detectado} |
| GET | `/api/v1/banco/pendientes` | Lista paginada movimientos sin procesar |
| POST | `/api/v1/banco/procesar` | Ejecuta auto-matching batch |
| GET | `/api/v1/banco/reglas` | Listar reglas |
| POST | `/api/v1/banco/reglas` | Crear regla |
| PUT | `/api/v1/banco/reglas/{id}` | Actualizar regla |
| DELETE | `/api/v1/banco/reglas/{id}` | Borrar regla |
| POST | `/api/v1/banco/reglas/{id}/simular` | Test: devuelve movimientos que matcharían |

---

## UI (Frontend)

### Página `/banco` (nueva ruta)
- **Tab 1: Importar** — Drag & drop archivo (Excel `.xlsx`, CSV `.csv`, CSB `.txt`/.`csb`), auto-detección de formato, preview tabla (primeras 20 filas), botón "Importar"
- **Tab 2: Reglas** — Tabla CRUD, botón "Simular" abre modal con preview de matches
- **Tab 3: Pendientes** — Tabla filtrable, botón "Crear asiento" por fila (modal con selector cuentas + líneas)
- **Tab 4: Procesados** — Historial con link al asiento generado

### Integración Diario (`/diario`)
- Filtro "Origen: Auto / Manual / Todos"
- Columna "Regla" en tabla si `origen=auto`

---

## Criterios de Aceptación Globales

| ID | Criterio |
|----|----------|
| AC-01 | Importar 1000 movimientos CSV en < 5s |
| AC-02 | Procesar 1000 movimientos con 20 reglas en < 3s |
| AC-03 | 0 asientos descuadrados generados por auto-matching |
| AC-04 | Re-importar mismo archivo → 0 duplicados (hash) |
| AC-05 | Usuario sin regla configurada → movimientos quedan en pendientes (no error) |
| AC-06 | Multi-tenant: Empresa A no ve reglas/movimientos de Empresa B |

---

## Dependencias Técnicas

- **Backend**: Nueva tabla + migración Alembic
  - Excel: `openpyxl` (parser Santander específico)
  - CSV: `pandas` / `csv` stdlib (separador `;`, decimal `,`, encoding detection)
  - CSB: `pybank43` o parser propio según AEB Norma 43
  - MT940: `mt940` lib (opcional, v2)
- **Frontend**: Nueva página `/banco`, componentes `ImportarExtracto`, `ReglaForm`, `PendientesTable`
- **Jobs**: `POST /procesar` síncrono (MVP) → futuro: background task (Celery/RQ)

---

## Riesgos y Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Regex mal escrita matcha de más | Media | Alto | Simulador obligatorio antes de guardar regla |
| Cambio formato banco rompe parser | Baja | Medio | Tests con samples reales, logging raw lines |
| Regla genera asiento en cuenta inexistente | Baja | Alto | Validar cuentas al crear regla (existen en ejercicio activo) |

---

## Próximos Pasos

1. `/speckit.plan` → generar plan técnico
2. `/speckit.tasks` → desglose en tareas
3. Implementar migración + modelos + endpoints + UI