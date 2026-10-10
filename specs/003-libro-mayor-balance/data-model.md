# Fase 1 — Modelo de Datos: Libro Mayor y Balance de Sumas y Saldos

**Feature**: `003-libro-mayor-balance`
**Fecha**: 2026-10-10

> **Sin cambios de esquema.** Esta feature es de **solo lectura**: los informes son
> vistas calculadas a partir de las tablas ya existentes (`Cuenta`, `Asiento`,
> `Apunte`). No se crean ni modifican tablas, columnas, índices ni migraciones
> Alembic.

---

## 1. Entidades existentes reutilizadas

### `Cuenta` (`backend/app/models/contable.py`)

Nodo del PGC dentro de un ejercicio.

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `ejercicio_id` | FK `ejercicio.id` | aísla por ejercicio |
| `codigo` | str(10) | solo dígitos; `nivel = len(codigo)` |
| `nombre` | str | denominación PGC |
| `nivel` | int | 1-5 (1 grupo, 2 subgrupo, 3 cuenta, 4-5 subcuentas) |

**Regla jerárquica**: una cuenta `A` es **ancestro** de `B` si `B.codigo`
empieza por `A.codigo` (p. ej. `57` es ancestro de `570` y de `5700`). El
subárbol de `A` incluye a `A` y a todas las cuentas con su prefijo.

### `Asiento` (`backend/app/models/contable.py`)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `ejercicio_id` | FK | |
| `fecha` | date | orden cronológico |
| `numero` | int | número correlativo dentro del ejercicio |
| `concepto` | str | |
| `estado` | `borrador` \| `asentado` | **solo `asentado`** entra en los informes (FR-006) |

### `Apunte` (`backend/app/models/contable.py`)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int PK | |
| `asiento_id` | FK | |
| `cuenta_id` | FK `cuenta.id` | índice existente |
| `debe` | `Decimal(12,2)` | una única columna con valor por línea |
| `haber` | `Decimal(12,2)` | la otra a 0.00 |

**Invariante** (ya garantizado al `asentar`): por asiento, `Σ debe = Σ haber`. Los
informes solo agregan asentados, por lo que el cuadre global se preserva.

---

## 2. Vistas calculadas (entidades de informe)

No se persisten; son la forma de la respuesta de la API y de las filas de
exportación. Definidas como schemas Pydantic en `backend/app/schemas/informes.py`.

### 2.1 `SumaCuenta` (agregado interno)

Resultado de la consulta SQL base, una fila por cuenta **con apuntes asentados**:

```
SumaCuenta(cuenta_id, suma_debe: Decimal, suma_haber: Decimal)
```

Consulta:

```sql
SELECT a.cuenta_id, SUM(a.debe) AS suma_debe, SUM(a.haber) AS suma_haber
FROM apunte a
JOIN asiento s ON s.id = a.asiento_id
WHERE s.ejercicio_id = :ejercicio_id
  AND s.estado = 'asentado'
  [AND s.fecha >= :desde]
  [AND s.fecha <= :hasta]
GROUP BY a.cuenta_id
```

A partir de este conjunto y de la lista de `Cuenta` del ejercicio se derivan, en
memoria, los acumulados de los grupos/subgrupos propagando por prefijo de código.

### 2.2 Línea de informe — Balance (`FilaBalance`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `codigo` | str | código PGC |
| `nombre` | str | denominación |
| `nivel` | int | 1-5 |
| `suma_debe` | Decimal(2) | Σ debe del subárbol |
| `suma_haber` | Decimal(2) | Σ haber del subárbol |
| `saldo_deudor` | Decimal(2) | `max(saldo, 0)` con `saldo = suma_debe − suma_haber` |
| `saldo_acreedor` | Decimal(2) | `max(−saldo, 0)` |

**Inclusión**: se emite una fila por cada cuenta cuyo subárbol tenga
`suma_debe > 0` o `suma_haber > 0`. Se incluyen cuentas **compensadas**
(saldo 0 con movimiento); se omiten las que no tienen ningún movimiento
(FR-004, edge cases).

**Orden**: por `codigo` ascendente (orden PGC), niveles 1-3 seguidos de las
cuentas de detalle.

### 2.3 Línea de informe — Mayor (`MovimientoMayor`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `fecha` | date | fecha del asiento |
| `numero` | int | número de asiento |
| `asiento_id` | int | referencia a la cabecera |
| `concepto` | str | |
| `debe` | Decimal(2) | importe en Debe (0.00 si no aplica) |
| `haber` | Decimal(2) | importe en Haber (0.00 si no aplica) |
| `saldo` | Decimal(2) | saldo acumulado **tras** este movimiento |

**Orden**: `fecha`, luego `numero`, luego `apunte.id` (determinista).
**Saldo acumulado**: parte del saldo inicial (`Σ(debe−haber)` de los apuntes con
`fecha < desde`, 0 si no hay `desde`) y acumula línea a línea (FR-007, R4).

### 2.4 Fila de listado global del Mayor (`FilaMayorCuenta`)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `codigo` | str | código PGC |
| `nombre` | str | denominación |
| `nivel` | int | |
| `suma_debe` | Decimal(2) | Σ del subárbol |
| `suma_haber` | Decimal(2) | Σ del subárbol |
| `saldo` | Decimal(2) | `suma_debe − suma_haber` |
| `saldo_tipo` | `deudor` \| `acreedor` \| `cero` | clasificación |

Misma regla de inclusión que el Balance (con movimiento).

---

## 3. Contenedores de respuesta

### `BalanceOut`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `ejercicio_id` | int | |
| `desde` | date \| null | filtro aplicado |
| `hasta` | date \| null | filtro aplicado |
| `filas` | `list[FilaBalance]` | ordenadas por código |
| `total_debe` | Decimal(2) | Σ de todas las sumas del debe del ejercicio/periodo |
| `total_haber` | Decimal(2) | Σ de todas las sumas del haber |
| `total_saldo_deudor` | Decimal(2) | Σ de saldos deudores |
| `total_saldo_acreedor` | Decimal(2) | Σ de saldos acreedores |
| `cuadra` | bool | `total_debe == total_haber` (FR-005) |

### `MayorCuentaOut` (mayor de una cuenta)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cuenta` | `CuentaRef` | `{codigo, nombre, nivel}` |
| `desde` / `hasta` | date \| null | filtro aplicado |
| `saldo_inicial` | Decimal(2) | saldo de apertura del periodo |
| `movimientos` | `list[MovimientoMayor]` | |
| `total_debe` / `total_haber` | Decimal(2) | del periodo |
| `saldo_final` | Decimal(2) | `saldo_inicial + (total_debe − total_haber)` |

### `MayorGlobalOut` (listado de cuentas con movimiento)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `ejercicio_id` | int | |
| `desde` / `hasta` | date \| null | |
| `cuentas` | `list[FilaMayorCuenta]` | ordenadas por código |

---

## 4. Reglas de agregación (resumen formal)

1. **Fuente**: apuntes de asientos con `estado = 'asentado'`, `ejercicio_id =`
   ejercicio del contexto `X-Ejercicio-Id`, y `fecha` dentro de `[desde, hasta]`
   si se indican.
2. **Restricción multi-tenant**: el ejercicio debe pertenecer a la empresa del
   contexto `X-Empresa-Id` (FR-008); en otro caso 400/403.
3. **Acumulado jerárquico**: `suma_debe(A) = Σ suma_debe(c)` para toda cuenta `c`
   cuyo `codigo` empieza por `A.codigo` (incluida `A`).
4. **Saldo**: `saldo = suma_debe − suma_haber`; se clasifica en Deudor/Acreedor
   como en `FilaBalance`.
5. **Cuadre**: por el invariante de partida doble, `total_debe == total_haber`;
   `cuadra` lo expone y la UI lo resalta si fuese `false`.
6. **Precisión**: todos los importes son `Decimal` con 2 decimales; la suma se
   realiza en `Decimal` (nunca en `float`) para no perder céntimos (FR-012).

---

## 5. Modelo de exportación

- **CSV** (por informe): bloque de encabezado (razón social + CIF, ejercicio,
  rango de fechas, título, fecha/hora de generación) + tabla + fila de totales.
  Separador `;`, decimal coma, UTF-8 con BOM (R2).
- **PDF** (por informe): A4, encabezado identificativo (FR-014) y tabla con las
  mismas columnas/filas que la pantalla, generada con ReportLab (R1).

Ambos formatos derivan de la **misma estructura de datos** que la respuesta JSON,
garantizando que la exportación reproduce la pantalla (SC-005).
