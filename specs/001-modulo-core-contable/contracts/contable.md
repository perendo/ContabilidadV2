# Contrato: Plan de Cuentas y Asientos Contables

Base path: `/api/v1`. Requiere `Authorization: Bearer` + `X-Empresa-Id` +
`X-Ejercicio-Id` (ver `contracts/auth.md`). Todo el filtrado es estricto por
`ejercicio_id` del contexto.

## GET /api/v1/cuentas

Lista/busca cuentas del ejercicio activo.

Query: `query` (codigo/nombre, opcional), `nivel` (1–5, opcional),
`offset`, `limit` (default 50, max 200).

Response 200:

```json
{
  "total": 34, "offset": 0, "limit": 50,
  "items": [ { "id": 7, "ejercicio_id": 5, "codigo": "57200001", "nombre": "Bancos c/c", "nivel": 4 } ]
}
```

Errores: `400` contexto; `403` sin acceso.

## POST /api/v1/cuentas

Crea una cuenta en el ejercicio activo (solo si `abierto`).

Request: `{ "codigo": "57200001", "nombre": "Bancos c/c", "nivel": 4 }`
Response 201: objeto `Cuenta`.

Errores: `409` código duplicado o ejercicio cerrado; `422` formato/longitud.

## POST /api/v1/asientos — Guardar borrador

Crea un asiento en estado `borrador`. Permite descuadres (FR-007).

Request:

```json
{
  "fecha": "2026-03-01",
  "concepto": "Pago proveedor",
  "apuntes": [
    { "cuenta_id": 7, "debe": "1000.00", "haber": "0.00" },
    { "cuenta_id": 12, "debe": "0.00", "haber": "900.00" }
  ]
}
```

`numero` NO se envía: es `NULL` en borrador y se asigna al asentar.

Validaciones al guardar borrador: ejercicio `abierto` (409); `fecha` en el
ejercicio (422); mínimo 2 apuntes (422); por línea exactamente un importe
> 0 (422); cuentas del ejercicio activo (422). El descuadre del conjunto se
**permite**.

Response 201:

```json
{
  "id": 88, "ejercicio_id": 5, "numero": null, "fecha": "2026-03-01",
  "concepto": "Pago proveedor", "estado": "borrador",
  "apuntes": [ { "cuenta_id": 7, "cuenta_codigo": "57200001", "debe": "1000.00", "haber": "0.00" },
               { "cuenta_id": 12, "cuenta_codigo": "41000000", "debe": "0.00", "haber": "900.00" } ]
}
```

## PUT /api/v1/asientos/{id} — Editar borrador

Sustituye `fecha`/`concepto`/`apuntes` del asiento **solo si `estado =
'borrador'`** (los `asentado` son inmutables → 409/422). Mismas validaciones
de línea que en POST; el descuadre se permite.

Response 200: objeto `Asiento` como en POST.

Errores: `404` no existe; `409` asentado o ejercicio cerrado.

## POST /api/v1/asientos/{id}/asentar — Asentar borrador

Convierte `borrador` → `asentado` **si y solo si** el conjunto cuadra y el
ejercicio está `abierto`.

Validaciones (orden):

1. Asiento existe y `estado = 'borrador'` → 404/409.
2. Ejercicio `abierto` → 409.
3. **Σ debe − Σ haber = 0** sobre todas las líneas (cálculo `Decimal`) →
   422 con `Δ` en el detalle (p. ej. `"detail": "Descuadre del asiento: Δ=-100.00"`).
4. Se asigna `numero = MAX(numero)+1` del ejercicio (transacción con
   UNIQUE); se marca `asentado`.

Response 200: `Asiento` con `numero` y `estado: "asentado"`.

Nota de conmutatividad: si el cliente envía el mismo asiento con
`debe=1000/haber=1000` en un PUT y luego asienta, la transición es idéntica;
el borrador descuadrado simplemente no se puede asentar hasta cuadrar.

## GET /api/v1/asientos — Diario (asentados) del ejercicio

Asientos con `estado = 'asentado'`, ordenados por `numero`.

Query: `since`/`until` (fechas, opcionales), `offset`, `limit` (max 200).

Response 200:

```json
{
  "total": 140, "offset": 0, "limit": 50,
  "items": [
    { "id": 88, "ejercicio_id": 5, "numero": 12, "fecha": "2026-03-01",
      "concepto": "Pago proveedor", "estado": "asentado",
      "total_debe": "1000.00", "total_haber": "1000.00" }
  ]
}
```

`total_debe`/`total_haber` los calcula el backend (Principio II).

## GET /api/v1/asientos/borradores — Lista de borradores

Asientos con `estado = 'borrador'` del ejercicio activo (FR-018), ordenados
por `fecha desc`. Misma estructura de paginación que el Diario; incluyen
`numero: null` y el `Δ` calculado (útil para que la UI marque cuáles están
listos para asentar).

Query: `offset`, `limit` (max 200).

## GET /api/v1/asientos/{id} — Detalle (apuntes)

Asiento del ejercicio activo con sus apuntes expandidos (FR-018), tanto
asentado como borrador.

Response 200: objeto `Asiento` con `apuntes[]` (idem POST).

Errores: `404`; `400/403` contexto.

Evento futuro no expuesto en Fase 1: cierre de ejercicio (Fase 2).