# Guía de Validación Rápida: Spec 4 — Conciliación Bancaria con Auto-Matching

**Feature**: `004-conciliacion-bancaria`
**Fecha**: 2026-10-11

Guía para validar end-to-end la conciliación bancaria: importar extractos
(Excel Santander / CSV / CSB), reglas de auto-matching con simulador, procesado
batch, gestión manual de pendientes y trazabilidad. No contiene la implementación;
para detalles ver [spec.md](./spec.md) y [plan.md](./plan.md).

---

## Requisitos previos

- Python 3.12 y venv en la raíz del repo (`.venv`).
- Node 20+ para el frontend.
- Dependencias de banco: `openpyxl` y `pandas` (instalar desde `backend/` con
  `..\.venv\Scripts\python.exe -m pip install -e .`). El parser CSB es propio
  (no requiere `pybank43`).

```powershell
# desde backend/
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.seed
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```powershell
# desde frontend/
npm run dev
```

**Nota**: la migración `6b69941fa552` añade `movimiento_banco`, `regla_banco`,
`log_procesamiento_banco` y los campos `origen`/`regla_id` de `asiento`.

---

## 1. Backend — pruebas automatizadas

```powershell
# desde backend/
..\.venv\Scripts\python.exe -m ruff check app tests
..\.venv\Scripts\python.exe -m pytest -q
```

**Esperado**: `ruff` sin errores; `pytest` en verde, incluida
`tests/integration/test_banco.py`.

Escenarios cubiertos por los tests (mapeados a criterios de aceptación):

| Test | Comportamiento | Resultado esperado |
|------|----------------|--------------------|
| `TestImportarExtracto.test_importar_csv_crea_movimientos_pendientes` | CSV `;` decimal `,` | Movimiento pendiente con campos mapeados (SC-02/SC-05) |
| `TestImportarFormatos.test_importar_excel_santander_via_http` | Excel 7 filas cabecera + headers | 2 filas parseadas: fecha/importe/código/referencia (SC-01) |
| `TestImportarFormatos.test_importar_csb_cuaderno43_via_http` | CSB registros 01/02/03/99 | 2 movimientos, importe con signo y código (SC-03) |
| `TestImportarExtracto.test_importar_duplicado_no_reinserta` | Re-importar mismo hash | 0 importados, 1 duplicado (SC-04, AC-04) |
| `TestImportarFormatos.test_importar_empresa_ajena_403` | Contexto otra empresa | `403` Sin acceso (AC-06) |
| `TestImportarFormatos.test_importar_archivo_corrupto_422` | XLSX corrupto | `422` con detalle |
| `TestImportarFormatos.test_importar_ejercicio_cerrado_200` | Ejercicio cerrado | Importación e consulta `200` (solo lectura) |
| `TestPendientesFiltros.test_filtros_desde_hasta_codigo_y_paginacion` | `desde`/`hasta`/`codigo_banco`/offset/limit | Filtros y paginación correctos (SC-13) |
| `TestMultiTenant.test_reglas_aisladas_por_empresa` | Reglas en A y B | A no ve B ni viceversa (SC-06/AC-06) |
| `TestProcesar.test_procesar_auto_asienta_con_correlativo` | Auto-matching + `auto_asentar` | Asiento asentado, ΣDebe=ΣHaber, movimiento linkeado (SC-09/SC-10, AC-03) |
| `TestProcesar.test_procesar_sin_auto_asentar_crea_borrador` | `auto_asentar=False` | Asiento `borrador` sin correlativo |
| `TestProcesar.test_procesar_sin_reglas_deja_pendientes` | Sin reglas | Movimientos quedan pendientes, sin error (SC-11, AC-05) |
| `TestProcesar.test_procesar_cuenta_inexistente_registra_fallo` | Cuenta inválida en regla | Fallo logueado, movimiento sigue pendiente |
| `TestPrioridadReglas.test_prioridad_mayor_gana` | Dos reglas sobre el mismo concepto | Gana la de mayor prioridad y queda `regla_id` (SC-07) |
| `TestIdempotenciaBatch.test_procesar_2da_ejecucion_0_nuevos` | Re-ejecutar batch | `creados=0`, no duplica asientos (SC-12) |
| `TestMultiTenant.test_procesar_batch_aisla_empresa_b` | Batch en A con datos en B | Los pendientes de B quedan intactos (AC-06) |
| `TestPendientesManuales` | Asiento manual + `POST /movimientos/{id}/procesado` | `origen=manual`, movimiento procesado, 409 en re-proceso (SC-15) |
| `TestLogTrazabilidad.test_log_completo_del_procesamiento` | `GET /banco/logs` | usuario, reglas aplicadas, creados/pendientes/fallidos (SC-19) |
| `TestEdgeCases.test_crear_regla_regex_invalida_422` | Patrón regex inválido | `422` al crear la regla |
| `TestEdgeCases.test_procesar_importe_cero_no_crea_asiento` | Movimiento con importe 0 | Se salta, queda pendiente |
| `TestEdgeCases.test_importar_divisa_no_eur_avisa` | Divisa distinta de EUR | Importa y avisa en `errores` |
| `TestRendimiento` | AC-01 / AC-02 | Ver sección 5 |

---

## 2. Verificación manual (REST)

Autenticarse y guardar cookie (`POST /api/v1/auth/login`), luego usar las
cabeceras `X-Empresa-Id` y `X-Ejercicio-Id` en todo endpoint de negocio.

### 2.1 Importar extracto

```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/banco/importar" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1" `
  -F "file=@extracto.csv" -F "ignorar_duplicados=false"
```

**Esperado**: `200` con `{"importados": N, "duplicados": 0, "errores": [], "formato_detectado": "csv"}`.
Formatos auto-detectados: `.xlsx`/`.xls` (Excel Santander), `.csv` (separador `;`),
`.csb`/`.txt`/`.43` (Cuaderno 43). Re-importar el mismo archivo → `duplicados: N`.

### 2.2 Pendientes

```powershell
curl "http://127.0.0.1:8000/api/v1/banco/pendientes?desde=2026-01-01&hasta=2026-12-31&offset=0&limit=50" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1"
```

**Esperado**: `200` con la lista (filtro opcional `codigo_banco`).

### 2.3 Reglas CRUD y simulador

```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/banco/reglas" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1" `
  -H "Content-Type: application/json" `
  -d '{"nombre":"Union Fenosa","patron_regex":"UNION FENOSA|FENOSA","cuenta_debe":"41000000","cuenta_haber":"57200001","prioridad":10,"auto_asentar":true,"activa":true}'

curl -X POST "http://127.0.0.1:8000/api/v1/banco/reglas/1/simular" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1"
```

**Esperado**: `201` al crear; `simular` devuelve los movimientos pendientes que
matchearían con las cuentas calculadas. Patrón regex inválido → `422`.

### 2.4 Procesar auto-matching

```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/banco/procesar" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1"
```

**Esperado**: `200` con `{creados, pendientes, fallidos, log_id}`. Re-ejecutar →
`creados: 0` (idempotente). Comprobar en el Diario los asientos con `origen=auto`
y `regla_id` poblado.

### 2.5 Logs de procesamiento

```powershell
curl "http://127.0.0.1:8000/api/v1/banco/logs" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1"
```

**Esperado**: `200` con timestamp, `usuario_id`, `reglas_aplicadas_json`,
`creados`, `pendientes`, `fallidos_json`.

### 2.6 Pendiente manual → asiento

Crear un asiento manual por `POST /api/v1/asientos` y enlazarlo:

```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/banco/movimientos/1/procesado" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1" `
  -H "Content-Type: application/json" -d '{"asiento_id": 5}'
```

**Esperado**: `200` con el movimiento `procesado: true` y `asiento_id`; repetir → `409`.

### 2.7 Aislamiento multi-tenant

Repetir 2.1 o 2.3 con un `X-Empresa-Id` de otra empresa distinta a la del usuario.

**Esperado**: `403` ("Sin acceso a la empresa"), sin datos cruzados.

---

## 3. Frontend — pruebas y build

```powershell
# desde frontend/
npm test
npm run lint
npx tsc --noEmit
npm run build
```

**Esperado**:
- `tests/Banco.test.tsx` pasa (importar, reglas, simulador, pendientes).
- `lint`, `tsc` y `build` sin errores.

---

## 4. Verificación manual (UI)

1. Login → `/seleccion` (elegir empresa + ejercicio) → Panel → tarjeta
   **Conciliación Bancaria** (`/banco`).
2. **Tab 1 · Importar** (`/banco/importar`): arrastrar un extracto Excel/CSV/CSB,
   ver el preview con las primeras filas, opción "Ignorar duplicados" e Importar.
3. **Tab 2 · Reglas** (`/banco/reglas`): crear una regla (patrón, cuentas,
   prioridad, auto-asentar), pulsar **Simular** y comprobar los matches.
4. **Tab 3 · Pendientes** (`/banco/pendientes`): filtrar por fechas/código,
   pulsar **Procesar automático** (resumen creados/pendientes/fallidos) o
   **Crear asiento** en una fila para completar manualmente un movimiento.
5. **Tab 4 · Procesados** (`/banco/procesados`): historial de ejecuciones con
   creados/pendientes/fallidos y detalle JSON.
6. En el **Diario** (`/diario`), el botón **Pendientes de conciliar** enlaza a
   `/banco/pendientes`; los asientos de auto-matching muestran `origen`/`regla`.

---

## 5. Criterios de aceptación (resumen)

### Historias de usuario (SC-01..SC-19)

- [x] SC-01: Excel Santander (cabecera 7 filas + headers fila 8) → parse correcto.
- [x] SC-02: CSV `;` decimal `,` UTF-8/Latin1 → 200 OK, movimientos creados.
- [x] SC-03: CSB/Cuaderno 43 → registros 01/02/03/99 parseados.
- [x] SC-04: Duplicados por hash SHA256 → ignorados según flag.
- [x] SC-05: Movimientos guardados con `procesado=False` y todos los campos.
- [x] SC-05 (US2): CRUD de reglas por empresa.
- [x] SC-06: Regla con patrón, cuentas, importe fijo/%, prioridad, auto_asentar.
- [x] SC-07: Prioridad resuelve conflictos (mayor gana).
- [x] SC-08: "Simular" muestra qué movimientos matchearían.
- [x] SC-09: `POST /procesar` recorre pendientes, aplica reglas y crea asientos.
- [x] SC-10: Match → asiento (borrador/asentado), movimiento `procesado=True` y
  `asiento_id` link.
- [x] SC-11: Sin match → `procesado=False` (pendiente).
- [x] SC-12: Idempotente: re-ejecutar no duplica asientos.
- [x] SC-13: `GET /pendientes` con filtros y paginación.
- [x] SC-15: Crear asiento manual → movimiento procesado y linkeado.
- [x] SC-16: Acceso a pendientes desde el Diario (botón "Pendientes de conciliar").
- [x] SC-17: `AsientoOut.origen` (`auto` | `manual`).
- [x] SC-18: Si `auto` → `regla_id` que lo generó.
- [x] SC-19: Log de procesamiento (timestamp, reglas, N creados, N fallidos).

> SC-14 (buscar cuentas por código/nombre en el modal) se resolvió con un
> `NativeSelect` del plan de cuentas del ejercicio en `BancoPendientes`.

### Criterios globales (AC-01..AC-06)

- [x] AC-01: Importar 1000 movimientos CSV en < 5 s — **medido 0,62 s** (11/10/2026).
- [x] AC-02: Procesar 1000 movimientos con 20 reglas en < 3 s — **medido 2,29 s**
  (11/10/2026; medición con `auto_asentar=False`, que es el grosor del batch;
  `auto_asentar=True` conserva el commit de `asentar` por asiento).
- [x] AC-03: 0 asientos descuadrados (ΣDebe=ΣHaber) por auto-matching.
- [x] AC-04: Re-importar el mismo archivo → 0 duplicados.
- [x] AC-05: Sin regla configurada → movimientos quedan en pendientes (sin error).
- [x] AC-06: Multi-tenant: Empresa A no ve reglas/movimientos de Empresa B.