# Contrato: Liquidación del Impuesto sobre Sociedades

Base path: `/api/v1/is`. Requiere contexto `X-Empresa-Id` + `X-Ejercicio-Id`.
El cálculo (base, cuota íntegra, cuota diferencial) vive **solo** en el backend
(FR-024); el cliente nunca lo calcula.

## GET /api/v1/is

Devuelve la liquidación del ejercicio (o `404` si no existe).

Response 200:

```json
{
  "id": 12, "ejercicio_id": 7,
  "resultado_contable": "100000.00",
  "ajustes": [
    { "concepto": "Multas y sanciones", "sentido": "aumento", "importe": "5000.00" },
    { "concepto": "Insolvencias deducibles", "sentido": "disminucion", "importe": "8000.00" }
  ],
  "tipo_gravamen": "25.00", "retenciones_pagos_cuenta": "4000.00",
  "base_imponible": "97000.00", "cuota_integra": "24250.00", "cuota_diferencial": "20250.00",
  "estado": "borrador", "asiento_id": null
}
```

> `base_imponible`/`cuota_integra`/`cuota_diferencial` vuelven `null` en `borrador`
> (se recalculan al consultar) y **congelados** cuando `estado="cerrada"`.

## POST /api/v1/is

Crea la liquidación del ejercicio (1 por ejercicio → 409 si ya existe).

Request:

```json
{
  "resultado_contable": "100000.00",
  "ajustes": [
    { "concepto": "Multas y sanciones", "sentido": "aumento", "importe": "5000.00" },
    { "concepto": "Insolvencias deducibles", "sentido": "disminucion", "importe": "8000.00" }
  ],
  "tipo_gravamen": "25.00",
  "retenciones_pagos_cuenta": "4000.00"
}
```

Response 201 → objeto como GET con `estado: "borrador"`.
Errores: `409` ya existe o ejercicio cerrado; `422` `tipo_gravamen ≤ 0`,
`retenciones < 0`, ajuste con `sentido` inválido o `importe` negativo.

## PUT /api/v1/is

Actualiza la liquidación **solo si `estado="borrador"`** (si `cerrada` → 409:
inmutable, FR (SC-007)). Mismo body que POST.

## POST /api/v1/is/cerrar

Cierra la liquidación: congelar `base_imponible`/`cuota_integra`/
`cuota_diferencial` y, si procede, generar el asiento de cierre del IS (fica
`asiento_id`) y el fichero 200 queda disponible. Solo si el ejercicio está
`abierto`.

Response 200 → objeto con `estado: "cerrada"` y resultados congelados.
Errores: `404` no existe; `409` ya cerrada o ejercicio cerrado.

## Cálculo (backend, único lugar)

```
base_imponible    = resultado_contable + Σ(aumentos) − Σ(disminuciones)
cuota_integra     = round(base_imponible × tipo_gravamen / 100, 2)
cuota_diferencial = cuota_integra − retenciones_pagos_cuenta    # + a ingresar, − a devolver
```