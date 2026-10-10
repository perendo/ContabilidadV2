# Guía de Validación Rápida: Spec 3 — Libro Mayor y Balance de Sumas y Saldos

**Feature**: `003-libro-mayor-balance`
**Fecha**: 2026-10-10

Guía para validar end-to-end que los informes de Mayor y Balance funcionan. No
contiene la implementación; para detalles ver [data-model.md](./data-model.md) y
[contracts/informes.md](./contracts/informes.md).

---

## Requisitos previos

- Python 3.12 y venv en la raíz del repo (`.venv`).
- Node 20+ para el frontend.
- Dependencia nueva `reportlab`: instalar desde `backend/` con
  `..\.venv\Scripts\python.exe -m pip install -e .`.

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

**Nota**: esta feature no añade migraciones; `alembic upgrade head` solo asegura
el esquema base.

---

## 1. Backend — pruebas automatizadas

```powershell
# desde backend/
..\.venv\Scripts\python.exe -m ruff check app tests
..\.venv\Scripts\python.exe -m pytest -q
```

**Esperado**: `ruff` sin errores; `pytest` en verde, incluida
`tests/integration/test_informes.py`.

Escenarios que deben cubrir los tests (mapeados a criterios de aceptación):

| Test | Comportamiento | Resultado esperado |
|------|----------------|--------------------|
| `test_mayor_cuenta_hoja_saldo_acumulado` | Mayor de cuenta con apuntes | Movimientos ordenados y `saldo_final` correcto |
| `test_mayor_incluye_saldo_inicial_con_desde` | Filtro `desde` | Primer movimiento parte del saldo previo (FR-007) |
| `test_mayor_cuenta_grupo_agrega_subcuentas` | Cuenta nivel 1-3 | Suma de subcuentas (FR-002) |
| `test_mayor_cuenta_sin_apuntes_estado_vacio` | Cuenta sin apuntes | `200`, `movimientos: []`, totales `0.00` |
| `test_mayor_global_lista_cuentas_con_movimiento` | Listado global | Solo cuentas con movimiento; compensadas incluidas |
| `test_balance_cuatro_columnas_y_cuadre` | Balance | `cuadra: true`, ΣDebe=ΣHaber (FR-004/005) |
| `test_balance_excluye_borradores` | Asiento borrador | No aparece en el informe (FR-006, SC-003) |
| `test_balance_cuenta_compensada_saldo_cero_incluida` | Cuenta saldo 0 con movimiento | Fila presente; cuenta sin movimiento omitida |
| `test_balance_agregacion_jerarquica_por_prefijo` | Grupos/subgrupos | Acumulados de subárbol correctos |
| `test_export_csv_formato_espanol` | Export CSV | `;`, coma decimal, BOM UTF-8, encabezado (FR-010/014) |
| `test_export_pdf_content_type_y_encabezado` | Export PDF | `application/pdf` y texto de encabezado |
| `test_informes_aislamiento_multi_tenant` | Contexto ajeno | `403`; no mezcla ejercicios (FR-008, SC-006) |
| `test_informes_precision_dos_decimales` | Sumas | Sin pérdida de céntimos (FR-012) |

---

## 2. Verificación manual (REST)

Autenticarse y guardar cookie (`POST /api/v1/auth/login`), luego usar las
cabeceras `X-Empresa-Id` y `X-Ejercicio-Id`.

### 2.1 Mayor de una cuenta

```powershell
curl "http://127.0.0.1:8000/api/v1/informes/mayor?cuenta=570&desde=2026-09-01&hasta=2026-10-31" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1"
```

**Esperado**: `200` con `movimientos` ordenados y `saldo_inicial` + acumulado.

### 2.2 Listado global del Mayor

```powershell
curl "http://127.0.0.1:8000/api/v1/informes/mayor/cuentas" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1"
```

**Esperado**: `200` con solo cuentas con movimiento; incluye compensadas.

### 2.3 Balance de Sumas y Saldos

```powershell
curl "http://127.0.0.1:8000/api/v1/informes/balance" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1"
```

**Esperado**: `200`, `cuadra: true`, filas ordenadas por código con jerarquía.

### 2.4 Exportación CSV y PDF

```powershell
curl -o balance.csv "http://127.0.0.1:8000/api/v1/informes/balance/export?formato=csv" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1"
curl -o balance.pdf "http://127.0.0.1:8000/api/v1/informes/balance/export?formato=pdf" `
  -b "access_token=<COOKIE>" -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1"
```

**Esperado**: `balance.csv` con BOM, `;` y coma decimal, encabezado + totales;
`balance.pdf` abre con el mismo contenido y encabezado identificativo.

### 2.5 Aislamiento (FR-008)

Repetir 2.3 con un `X-Ejercicio-Id` de otra empresa.

**Esperado**: `403` ("Sin acceso al ejercicio"), sin datos cruzados.

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
- `tests/Informes.test.tsx` pasa (render de tablas, estados vacío/error y disparo
  de descarga CSV y PDF).
- `lint`, `tsc` y `build` sin errores.

---

## 4. Verificación manual (UI)

1. Login → `/seleccion` (elegir empresa + ejercicio) → Panel.
2. Abrir **Libro Mayor** (`/mayor`): seleccionar cuenta por código/nombre,
   aplicar rango de fechas y comprobar el saldo acumulado por línea.
3. Ver el **listado global** y entrar al detalle de una cuenta.
4. Abrir **Balance de Sumas y Saldos** (`/balance`): comprobar las cuatro
   columnas, la jerarquía y el cuadre destacado.
5. Pulsar los **botones independientes** CSV y PDF en cada informe y comprobar
   la descarga con el encabezado (razón social + CIF, ejercicio, fechas, hora).
6. Comprobar que un ejercicio `cerrado` sigue mostrando informes en solo lectura.

---

## 5. Criterios de aceptación (resumen)

- [ ] SC-001: el saldo final del Mayor de una cuenta = su saldo en el Balance.
- [ ] SC-002: `.cuadra == true` (ΣDebe = ΣHaber) en todas las consultas.
- [ ] SC-003: los asientos `borrador` quedan excluidos al 100%.
- [ ] SC-004: informe de 10.000 asientos en < 3 s.
- [ ] SC-005: el CSV/PDF reproduce exactamente lo mostrado (0 diferencias).
- [ ] SC-006: 0 accesos cruzados entre empresas/ejercicios.
- [ ] FR-002: Mayor en ambos modos (cuenta y listado global) y por cualquier nivel.
- [ ] FR-004: Balance con jerarquía, cuatro columnas e inclusión de compensadas.
- [ ] FR-010: botones independientes CSV y PDF en ambos informes.
- [ ] FR-014: encabezado identificativo en las exportaciones.
