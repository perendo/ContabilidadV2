# Contrato de API — Informes: Libro Mayor y Balance de Sumas y Saldos

**Feature**: `003-libro-mayor-balance`
**Fecha**: 2026-10-10
**Base URL**: `/api/v1`

Todos los endpoints requieren autenticación (`Authorization: Bearer <jwt>` **o**
cookie httpOnly `access_token`) y el contexto de negocio mediante las cabeceras
`X-Empresa-Id` y `X-Ejercicio-Id`. Al ser todos `GET` (solo lectura), no se exige
la cabecera anti-CSRF `X-Requested-With`.

Errores comunes (definidos en `backend/app/api/deps.py`):

| Código | Cuándo |
|--------|--------|
| `400` | Falta `X-Empresa-Id` o `X-Ejercicio-Id`, o tiene formato inválido; o rango de fechas inconsistente (`desde > hasta`) |
| `401` | No autenticado / token inválido |
| `403` | Empresa inactiva, ejercicio no perteneciente a la empresa, o usuario no vinculado |
| `404` | Cuenta indicada no existe en el ejercicio |

Los importes se serializan como **string decimal con punto y dos decimales**
(p. ej. `"30.00"`), coherente con `AsientoOut`/`ApunteOut` existentes.

---

## 1. `GET /informes/mayor`

Mayor de **una cuenta** concreta (por código o por nombre). Si la cuenta es de
grupo/subgrupo (nivel 1-3) agrega los apuntes de todas sus subcuentas (FR-002).

**Query parameters**

| Parámetro | Tipo | Obligatorio | Descripción |
|-----------|------|-------------|-------------|
| `cuenta` | string | Sí | Código exacto de la cuenta (solo dígitos). |
| `desde` | date (`YYYY-MM-DD`) | No | Inicio del rango; si se omite, sin límite inferior. |
| `hasta` | date (`YYYY-MM-DD`) | No | Fin del rango; si se omite, sin límite superior. |

**Respuesta `200`**

```json
{
  "cuenta": { "codigo": "570", "nombre": "Caja", "nivel": 3 },
  "desde": "2026-09-01",
  "hasta": "2026-10-31",
  "saldo_inicial": "0.00",
  "movimientos": [
    {
      "fecha": "2026-10-09",
      "numero": 12,
      "asiento_id": 40,
      "concepto": "Cobro auditoría - Daniel Urrutia",
      "debe": "30.00",
      "haber": "0.00",
      "saldo": "30.00"
    },
    {
      "fecha": "2026-10-09",
      "numero": 13,
      "asiento_id": 41,
      "concepto": "Bizum - Daniel Urrutia",
      "debe": "0.00",
      "haber": "30.00",
      "saldo": "0.00"
    }
  ],
  "total_debe": "30.00",
  "total_haber": "30.00",
  "saldo_final": "0.00"
}
```

- Cuenta sin apuntes asentados → `200` con `movimientos: []` y totales `"0.00"`
  (estado vacío informativo, escenario US1.4).
- `saldo_inicial` = `Σ(debe − haber)` de apuntes con `fecha < desde` (FR-007).
- Orden de `movimientos`: `fecha`, `numero`, `apunte.id`.

**Errores**: `404` si la cuenta no existe en el ejercicio activo; `422` si
`desde > hasta`; `400/403` según el contexto (FR-008).

---

## 2. `GET /informes/mayor/cuentas`

Listado global: todas las cuentas **con movimiento** en el ejercicio/periodo, con
sus sumas y saldo, para navegar al detalle (FR-002).

**Query parameters**

| Parámetro | Tipo | Obligatorio | Descripción |
|-----------|------|-------------|-------------|
| `desde` | date | No | Inicio del rango. |
| `hasta` | date | No | Fin del rango. |

**Respuesta `200`**

```json
{
  "ejercicio_id": 1,
  "desde": null,
  "hasta": null,
  "cuentas": [
    { "codigo": "100", "nombre": "Capital social", "nivel": 3,
      "suma_debe": "0.00", "suma_haber": "5000.00",
      "saldo": "-5000.00", "saldo_tipo": "acreedor" },
    { "codigo": "570", "nombre": "Caja", "nivel": 3,
      "suma_debe": "30.00", "suma_haber": "30.00",
      "saldo": "0.00", "saldo_tipo": "cero" }
  ]
}
```

- `saldo_tipo`: `deudor` (`saldo > 0`), `acreedor` (`saldo < 0`), `cero`.
- Se incluyen cuentas compensadas (`cero` con movimiento); se omiten las cuentas
  sin movimiento.
- Orden por `codigo` ascendente.

---

## 3. `GET /informes/balance`

Balance de Sumas y Saldos con agregación jerárquica y cuatro columnas (FR-004).

**Query parameters**

| Parámetro | Tipo | Obligatorio | Descripción |
|-----------|------|-------------|-------------|
| `desde` | date | No | Inicio del rango. |
| `hasta` | date | No | Fin del rango. |

**Respuesta `200`**

```json
{
  "ejercicio_id": 1,
  "desde": null,
  "hasta": null,
  "filas": [
    { "codigo": "1", "nombre": "Financiación básica", "nivel": 1,
      "suma_debe": "0.00", "suma_haber": "5000.00",
      "saldo_deudor": "0.00", "saldo_acreedor": "5000.00" },
    { "codigo": "100", "nombre": "Capital social", "nivel": 3,
      "suma_debe": "0.00", "suma_haber": "5000.00",
      "saldo_deudor": "0.00", "saldo_acreedor": "5000.00" }
  ],
  "total_debe": "5000.00",
  "total_haber": "5000.00",
  "total_saldo_deudor": "0.00",
  "total_saldo_acreedor": "5000.00",
  "cuadra": true
}
```

- Los niveles 1-3 se emiten con el **acumulado de su subárbol**; las cuentas de
  detalle con sus propios apuntes, todo ordenado por `codigo`.
- `cuadra = (total_debe == total_haber)`; si fuese `false`, la UI lo resalta de
  forma visible (FR-005, US2.2).
- Ejercicio sin asentados → `200` con `filas: []` y totales `"0.00"`, `cuadra: true`.

---

## 4. Exportación

### 4.1 `GET /informes/mayor/export`

### 4.2 `GET /informes/balance/export`

Generan el fichero descargable del informe correspondiente (FR-010, FR-014).

**Query parameters** (además de los propios de cada informe)

| Parámetro | Tipo | Obligatorio | Descripción |
|-----------|------|-------------|-------------|
| `formato` | `csv` \| `pdf` | Sí | Formato de salida. Cualquier otro valor → `422`. |
| `cuenta` | string | Sí (solo mayor) | Cuenta del mayor a exportar. |
| `desde` / `hasta` | date | No | Rango aplicado; se refleja en el encabezado. |

**Respuesta `200`**

- **CSV**:
  - `Content-Type: text/csv; charset=utf-8`
  - `Content-Disposition: attachment; filename="mayor_570_20260901-20261031.csv"`
  - Cuerpo: BOM UTF-8 + bloque de encabezado + tabla con separador `;` y decimal
    coma + fila de totales.
- **PDF**:
  - `Content-Type: application/pdf`
  - `Content-Disposition: attachment; filename="balance_20260101-20261231.pdf"`
  - Cuerpo: PDF A4 con encabezado identificativo y tabla.

**Encabezado de ambos formatos** (FR-014):
razón social y CIF de la empresa, ejercicio (año), rango de fechas aplicado,
título del informe y fecha/hora de generación.

**Errores**: mismos `400/403/404/422` que el informe base.

---

## 5. Matriz de trazabilidad FR ↔ endpoint

| FR | Endpoint / comportamiento |
|----|---------------------------|
| FR-001 | `GET /informes/mayor` (movimientos con saldo acumulado) |
| FR-002 | `GET /informes/mayor` (cuenta) + `GET /informes/mayor/cuentas` (global) + agregación por nivel |
| FR-003 | Cálculo backend en `services/informes.py` |
| FR-004 | `GET /informes/balance` (jerarquía + 4 columnas + compensadas) |
| FR-005 | `balance.total_debe/haber` + `cuadra` |
| FR-006 | Filtro `estado = 'asentado'` en la consulta base |
| FR-007 | `desde`/`hasta` + `saldo_inicial` en el mayor |
| FR-008 | Cabeceras de contexto y validación en `deps.py` |
| FR-009 | Toda agregación/formato en backend |
| FR-010 | `.../export?formato=csv\|pdf` (más botones independientes en la UI) |
| FR-011 | Páginas `/mayor` y `/balance` en MUI v6 (MD3) |
| FR-012 | `Decimal` 2 decimales extremo a extremo |
| FR-013 | Autorización por contexto empresa/ejercicio (admin y contable) |
| FR-014 | Encabezado identificativo en CSV y PDF |
