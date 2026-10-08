# Contrato: Empresas y Ejercicios

Base path: `/api/v1`. Todos los endpoints (salvo los marcados) requieren
`Authorization: Bearer`. Respuesta de error estándar `{ "detail": string }`.

## GET /api/v1/empresas

Lista las empresas a las que el usuario tiene acceso (`EmpresaUsuario`),
solo las `activa = true`.

Response 200:

```json
[
  {
    "id": 21,
    "cif": "B12345678",
    "razon_social": "Acme SL",
    "nombre_comercial": "Acme",
    "activa": true,
    "created_at": "2026-01-15T10:00:00Z"
  }
]
```

Errores: `401`.

## POST /api/v1/empresas

Crea una empresa y la asocia al usuario creador (`EmpresaUsuario` con
`rol_especifico = 'admin'`). Requiere rol global `admin` o `contable`.

Request:

```json
{
  "cif": "B12345678",
  "razon_social": "Acme SL",
  "nombre_comercial": "Acme"
}
```

Response 201: objeto `Empresa` como en GET.

Errores: `409` cif duplicado; `403` rol insuficiente; `422` validación.

## GET /api/v1/ejercicios

Lista los ejercicios de la empresa de contexto (`X-Empresa-Id`).

Response 200:

```json
[
  {
    "id": 5,
    "empresa_id": 21,
    "anio": 2026,
    "fecha_inicio": "2026-01-01",
    "fecha_fin": "2026-12-31",
    "estado": "abierto"
  }
]
```

Errores: `400` sin `X-Empresa-Id`; `403` sin acceso a la empresa.

## POST /api/v1/ejercicios

Abre un nuevo año contable dentro de la empresa de contexto.

Request:

```json
{
  "anio": 2026,
  "fecha_inicio": "2026-01-01",
  "fecha_fin": "2026-12-31"
}
```

Response 201: objeto `Ejercicio` (`estado` siempre `abierto` en Fase 1).

Errores: `409` anio duplicado en la empresa; `400/403` contexto inválido;
`422` fechas fuera de rango o anio no en [2000, 2100].