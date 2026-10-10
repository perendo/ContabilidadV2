# Data Model — 005-modulos-fiscales

Fuente: `spec.md` (Key Entities + FR-001…FR-031) y decisiones de `research.md`
(sesión clarificación 2026-10-11). Convenciones: IDs enteros autoincrementales;
timestamps UTC; importes `NUMERIC(19,2)` con `Decimal` (nunca `float`);
porcentajes `NUMERIC(5,2)`; enums persistidos como `TEXT`/`String` (patrón del
proyecto). Esquema materializado solo vía **Alembic**.

## Diagrama de relaciones

```text
[Ejercicio] (existente)
   ├──< [Factura] ──< [LineaFacturaIVA]
   │        │
   │        └──► (genera) [Asiento] ──< [Apunte]   (existentes)
   │
   ├──< [LiquidacionImpuestoSociedades]  (1 por ejercicio)
   │
   └──< [FicheroPresentacion]            (1 por ejercicio+modelo+periodo)
```

## Entidades nuevas

### Factura

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | INTEGER PK | autoincremental |
| ejercicio_id | INTEGER FK → Ejercicio | RESTRICT, no nulo |
| origen | TEXT | `venta` \| `compra` (enum `OrigenFactura`) |
| numero | TEXT | ≤ 50, no nulo |
| fecha | DATE | no nulo, dentro del ejercicio |
| fecha_operacion | DATE | nullable (devengo efectivo) |
| tercero_cif | TEXT | 9 chars (validación CIF/NIF), no nulo |
| tercero_razon_social | TEXT | ≤ 200, no nulo |
| solo_identificativo | BOOLEAN | default `false` (operación sin actividad económica) |
| tipo_retencion | TEXT nullable | `111` \| `115` (enum `TipoRetencion`) |
| estado | TEXT | `registrada` \| `anulada`, default `registrada` |
| notas | TEXT | ≤ 1000, nullable |
| asiento_id | INTEGER FK → Asiento | RESTRICT, nullable (generado al crear) |
| creado_por_usuario_id | INTEGER FK → Usuario | RESTRICT, no nulo |
| created_at | DATETIME | UTC |

**Unicidad**: `UNIQUE(ejercicio_id, tercero_cif, numero)` → uq_factura_ejercicio_cif_numero
(FR-006; la comprobación en servicio devuelve 409, la BD es el backstop).
**Índices**: `ix_factura_ejercicio_fecha`, `ix_factura_ejercicio_origen`.

### LineaFacturaIVA

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | INTEGER PK | autoincremental |
| factura_id | INTEGER FK → Factura | CASCADE, no nulo |
| numero_linea | INTEGER | ≥ 1 |
| descripcion | TEXT | ≤ 300, no nulo |
| base_imponible | DECIMAL(19,2) | ≥ 0, no nulo |
| tipo_iva | DECIMAL(5,2) | ≥ 0, no nulo |
| cuota_iva | DECIMAL(19,2) | `base × tipo / 100`, 2dp (servicio) |
| tipo_re | DECIMAL(5,2) nullable | Recargo de Equivalencia %, ≥ 0 |
| cuota_re | DECIMAL(19,2) nullable | `base × tipo_re / 100`, 2dp |
| operacion_exenta | BOOLEAN | default `false` (base 0 / sin cuota) |
| base_retencion | DECIMAL(19,2) nullable | base de la retención (≤ base) |
| pct_retencion | DECIMAL(5,2) nullable | 0–100 |
| cuota_retencion | DECIMAL(19,2) nullable | `base_retencion × pct / 100`, 2dp |

**Índices**: `ix_linea_factura_factura`.
**Validaciones** (schema + servicio): si `operacion_exenta` → `tipo_iva = 0` y
`cuota_iva = 0`; si `cuota_retencion` presente → `tipo_retencion` en factura y
pct en 0–100; pct > 100 → 422.

### LiquidacionImpuestoSociedades

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | INTEGER PK | autoincremental |
| ejercicio_id | INTEGER FK → Ejercicio | RESTRICT, no nulo; `UNIQUE` → 1/ejercicio |
| resultado_contable | DECIMAL(19,2) | no nulo |
| ajustes_json | TEXT | JSON `[{concepto, sentido: aumento\|disminucion, importe}]` validado por Pydantic |
| tipo_gravamen | DECIMAL(5,2) | default 25, > 0 |
| retenciones_pagos_cuenta | DECIMAL(19,2) | default 0, ≥ 0 |
| base_imponible | DECIMAL(19,2) nullable | calculado al cerrar (congelado) |
| cuota_integra | DECIMAL(19,2) nullable | calculado al cerrar (congelado) |
| cuota_diferencial | DECIMAL(19,2) nullable | calculado al cerrar; negativo = a devolver |
| estado | TEXT | `borrador` \| `cerrada`, default `borrador` |
| asiento_id | INTEGER FK → Asiento nullable | asiento de cierre del IS (opcional) |
| creado_por_usuario_id | INTEGER FK → Usuario | RESTRICT, no nulo |
| cerrado_por_usuario_id | INTEGER FK → Usuario nullable | |
| created_at / cerrado_at | DATETIME | UTC |

**Cálculo (servicio IS, único lugar)**:
`base_imponible = resultado + Σaumentos − Σdisminuciones`;
`cuota_integra = base × tipo / 100`; `cuota_diferencial = cuota_integra − retenciones_pagos_cuenta`.
**Transición**: `borrador —(cerrar: ejercicio abierto, congelar resultados)—> cerrada`
(una vez `cerrada` es inmutable → 409 a modificaciones).

### FicheroPresentacion (trazabilidad, 1 por ejercicio+modelo+periodo)

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | INTEGER PK | |
| ejercicio_id | INTEGER FK → Ejercicio | RESTRICT, no nulo |
| modelo | TEXT | `303` \| `111` \| `115` \| `200` |
| periodo | TEXT | `2026T1`…`2026T4` o `2026` |
| ruta | TEXT | ≤ 255, relativa a `impuestos/` |
| hash_sha256 | TEXT | 64 hex |
| generado_por_usuario_id | INTEGER FK → Usuario | RESTRICT |
| generado_at | DATETIME | UTC |

**Unicidad**: `UNIQUE(ejercicio_id, modelo, periodo)` → regenerar sobrescribe
(ruta + hash) sin duplicar (FR-030).

**Organización en disco** (FR-030, decisión R3):

```text
backend/impuestos/{empresa_id}/{anio}/{modelo}_{periodo}.txt   (gitignored)
```

## Enums compartidos

- `OrigenFactura`: `venta` | `compra`
- `TipoRetencion`: `111` (profesionales/trabajo) | `115` (alquileres)
- `EstadoFactura`: `registrada` | `anulada`
- `EstadoLiquidacionIS`: `borrador` | `cerrada`

## Mapeo de cuentas PGC (asiento derivado)

| Operación | Cuenta | Posición |
|-----------|--------|----------|
| Venta a crédito | 430 Clientes | Debe = base + cuota IVA (todas las líneas) |
| Venta | 700 Ventas | Haber = Σ bases |
| Venta | 477 HP IVA repercutido | Haber = Σ cuotas IVA |
| Compra | 600 Compras / 621…630 | Debe = Σ bases |
| Compra | 472 HP IVA soportado | Debe = Σ cuotas IVA (+ cuota RE en línea 472) |
| Compra | 400 Proveedores | Haber = total ≥ 0 |
| Retención 111 | 4751 HP acreedora retenciones | Haber = Σ cuota_retencion |
| Retención 115 | 4751 (config por ejercicio) | Haber = Σ cuota_retencion |
| Compra con RE | 472 (RE soportado deducible) | Debe = Σ cuota_re |

**Configuración por ejercicio**: un pequeño mapa `cuentas_config` (service-level,
por defecto los códigos PGC anteriores) permite a cada empresa/asesor ajustar la
cuenta de retención (4751/473) y de RE sin cambiar código.

## Transiciones de estado

```text
Factura:   [registrada] ──(anular)→ [anulada]          (asiento generado queda inmutable;
                                                         la anulación crea asiento rectificativo o marca estado)
Liquidación IS: [borrador] ──(cerrar)→ [cerrada]        (inmutable; genera/actualiza fichero 200)
Fichero:   (re)generación sobreescribe en el mismo (modelo,periodo)
```