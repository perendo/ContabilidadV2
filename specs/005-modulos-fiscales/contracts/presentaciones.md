# Contrato: Presentación AEAT (vista + fichero de posiciones fijas)

Base path: `/api/v1/presentaciones`. Requiere contexto `X-Empresa-Id` +
`X-Ejercicio-Id`. Los ficheros 303/111/115/200 siguen **estrictamente** la
plantilla oficial de posiciones fijas de la AEAT (FR-027/028) y se persisten en
`impuestos/{empresa}/{anio}` (FR-030).

## GET /api/v1/presentaciones/{modelo}?periodo=

Vista de presentación en **pantalla** (FR-026): resumen por bloques + detalle por
casillas oficiales. `modelo` ∈ `303` | `111` | `115` | `200`; `periodo` =
`2026T1`…`2026T4` (303/111/115) o `2026` (200). Disponible en cualquier estado
(no requiere cierre), los valores los calcula el backend.

Response 200 (ejemplo modelo 200):

```json
{
  "modelo": "200", "periodo": "2026", "cerrada": false,
  "resumen": {
    "resultado_contable": "100000.00", "aumentos": "5000.00", "disminuciones": "8000.00",
    "base_imponible": "97000.00", "cuota_integra": "24250.00",
    "retenciones_pagos_cuenta": "4000.00", "cuota_diferencial": "20250.00"
  },
  "casillas": [
    { "casilla": 100, "label": "Resultado contable del ejercicio", "importe": "100000.00" },
    { "casilla": 201, "label": "Ajustes positivos", "importe": "5000.00" },
    { "casilla": 202, "label": "Ajustes negativos", "importe": "-8000.00" },
    { "casilla": 300, "label": "Base imponible", "importe": "97000.00" },
    { "casilla": 500, "label": "Cuota íntegra", "importe": "24250.00" },
    { "casilla": 623, "label": "Cuota diferencial", "importe": "20250.00" }
  ],
  "bloque_descarga": { "habilitado": false, "motivo": "Liquidación sin cerrar; el fichero se habilita al cerrarla" }
}
```

El `bloque_descarga.habilitado` será `false` cuando el periodo/liquidación no esté
cerrado (FR-029): el frontend deshabilita el botón y muestra `motivo`.

## GET /api/v1/presentaciones/{modelo}/fichero?periodo=

Devuelve el fichero de posiciones fijas (`Content-Type: text/plain`, attachment).

- Si el periodo/liquidación **no está cerrado** → `409` (descarga denegada; la
  vista en pantalla sí existe).
- Si está cerrado y el fichero ya existe en `impuestos/` → se devuelve el
  persistido (con su trazabilidad) sin regenerar.
- Si está cerrado y no existe → se regenera, se persiste y se descarga en la
  misma petición (la **descarga a petición** coexiste con el **guardado**
  en el directorio `impuestos`, FR-027/030).

Errores: `404` modelo/periodo sin datos; `409` no cerrado.

## Nota técnica (formato)

Un fichero = secuencia de registros de longitud fija (UTF-8, CRLF):
cabecera (NIF y razón social de la empresa, ejercicio), registros de detalle
(percepción/factura para 111/115; agregados por tipo para 303; casillas para 200),
registro de totales y registro de fin. Las plantillas están versionadas como
configuración (decisión R1/R2 de `research.md`); importes sin separador de miles
y con decimales implícitos. `POST` de generación explícita no es necesario: la
generación se dispara al descargar y al cerrar