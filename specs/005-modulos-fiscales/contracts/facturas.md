# Contrato: Facturas, Libros de IVA y Retenciones

Base path: `/api/v1/facturas`. Requiere contexto `X-Empresa-Id` + `X-Ejercicio-Id`
(400 si faltan, 403 sin acceso). Los importes son strings decimales de 2 dígitos
(FR-003/022).

## POST /api/v1/facturas

Registra una factura y genera **atómicamente** (misma transacción) el asiento
contable cuadrado (400/430, 600/700, 472/477, 4751/473).

Request:

```json
{
  "origen": "venta",
  "numero": "FV-2026-001",
  "fecha": "2026-03-05",
  "tercero_cif": "B12345678",
  "tercero_razon_social": "Cliente S.L.",
  "tipo_retencion": null,
  "notas": null,
  "lineas": [
    { "numero_linea": 1, "descripcion": "Servicio", "base_imponible": "1000.00",
      "tipo_iva": "21.00", "cuota_iva": "210.00", "tipo_re": null, "cuota_re": null,
      "operacion_exenta": false, "base_retencion": null, "pct_retencion": null, "cuota_retencion": null }
  ]
}
```

- `origen=compra` con `tipo_retencion="111"` (profesional) o `"115"` (alquiler):
  las líneas pueden incluir `base_retencion`/`pct_retencion`/`cuota_retencion`.
- `cuota_iva`/`cuota_retencion` se recalculan y validan en el backend (FR-003):
  si el cliente envía un valor que no coincide con `base × tipo / 100` a 2dp →
  `422`.

Response 201 (factura + asiento generado):

```json
{
  "id": 41, "origen": "venta", "numero": "FV-2026-001", "fecha": "2026-03-05",
  "tercero_cif": "B12345678", "tercero_razon_social": "Cliente S.L.",
  "tipo_retencion": null, "estado": "registrada", "asiento_id": 388,
  "lineas": [ { "id": 1, "numero_linea": 1, "base_imponible": "1000.00", "tipo_iva": "21.00",
                "cuota_iva": "210.00", "tipo_re": null, "cuota_re": null, "operacion_exenta": false,
                "base_retencion": null, "pct_retencion": null, "cuota_retencion": null } ]
}
```

Errores: `409` duplicado (mismo `tercero_cif`+`numero`+ejercicio) o ejercicio
cerrado; `422` CIF inválido, tipo_retencion sin líneas con retención, pct > 100,
fecha fuera del ejercicio, cuotas incoherentes.

## GET /api/v1/facturas

Listado paginado. Query: `origen` (`venta`\|`compra`), `desde`, `hasta`
(YYYY-MM-DD), `tercero_cif`, `offset`, `limit` (default 50, max 200).

Response 200:

```json
{
  "total": 3, "offset": 0, "limit": 50,
  "items": [ { "id": 41, "origen": "venta", "numero": "FV-2026-001", "fecha": "2026-03-05",
               "tercero_cif": "B12345678", "tercero_razon_social": "Cliente S.L.",
               "tipo_retencion": null, "estado": "registrada", "asiento_id": 388 } ]
}
```

## GET /api/v1/facturas/{id}

Devuelve la factura con sus líneas. Errores: `404`.

## GET /api/v1/facturas/libros/iva

Libro Registro de IVA (FR-009…011). Query obligatoria: `origen=
soportado|repercutido`, `desde`, `hasta` (dentro del ejercicio).

Response 200 (detalle por factura + totales por tipo de IVA):

```json
{
  "origen": "repercutido", "desde": "2026-01-01", "hasta": "2026-03-31",
  "operaciones": [
    { "fecha": "2026-03-05", "numero": "FV-2026-001", "tercero_cif": "B12345678",
      "base_imponible": "1000.00", "tipo_iva": "21.00", "cuota_iva": "210.00", "total": "1210.00", "asiento_id": 388 }
  ],
  "totales_por_tipo": [ { "tipo_iva": "21.00", "base": "1000.00", "cuota": "210.00" } ],
  "total_base": "1000.00", "total_cuota": "210.00"
}
```

## GET /api/v1/facturas/libros/iva/exportar

Misma query que el anterior; devuelve CSV (`;` como separador, coma decimal,
UTF-8 BOM) con columnas: fecha, número, CIF, nombre, base, tipo, cuota, total.

## GET /api/v1/facturas/retenciones

Resumen de retenciones **agrupado por CIF** (FR-016). Query: `tipo` (`111`|`115`),
`desde`, `hasta`.

Response 200:

```json
{
  "tipo": "111", "desde": "2026-01-01", "hasta": "2026-03-31",
  "por_perceptor": [
    { "tercero_cif": "B12345678", "tercero_razon_social": "Profesional S.L.",
      "base_retencion": "3000.00", "cuota_retencion": "450.00", "numero_facturas": 3 }
  ],
  "total_base": "3000.00", "total_retencion": "450.00"
}
```

Solo perceptores con CIF válido (FR-017).