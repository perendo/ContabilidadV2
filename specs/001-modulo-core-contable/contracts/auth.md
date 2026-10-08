# Contrato: Contexto y Autenticación

Base path: `/api/v1/auth`.

## Cabeceras de contexto (obligatorias en endpoints de negocio)

| Cabecera | Requerida | Descripción |
|----------|-----------|-------------|
| `Authorization: Bearer <token>` | Sí | JWT emitido por `POST /auth/login` |
| `X-Empresa-Id` | Sí (negocio) | Empresa activa del usuario |
| `X-Ejercicio-Id` | Sí (plan de cuentas y asientos) | Ejercicio activo |

Validación de pertenencia (dependencia `deps.py`), en orden:

1. Token válido y usuario `activo` → si no, `401`.
2. Existe `EmpresaUsuario(usuario_id, empresa_id)` → si no, `403`.
3. Ejercicio existe y `ejercicio.empresa_id == X-Empresa-Id` → si no `400/403`.
4. Cabeceras `X-*` sin valor → `400`.

## POST /api/v1/auth/login

Autentica y emite el token de sesión.

Request:

```json
{ "username": "contable1", "password": "s3cret" }
```

Response 200:

```json
{
  "access_token": "<JWT>",
  "token_type": "bearer",
  "expires_in": 43200,
  "usuario": { "id": 1, "username": "contable1", "email": "a@x.es", "rol": "contable" }
}
```

Errores: `401` credenciales inválidas o usuario inactivo; `422` validación.

## GET /api/v1/auth/me

Perfil del usuario autenticado (sin cabeceras `X-*`).

Response 200:

```json
{
  "id": 1,
  "username": "contable1",
  "email": "a@x.es",
  "rol": "contable",
  "activo": true,
  "empresas": [21, 33]
}
```

`empresas`: ids de las empresas con acceso vía `EmpresaUsuario`.
Errores: `401` sin token o inválido.

## POST /api/v1/auth/logout

Invalida la sesión en cliente (borra cookie). Response `204`.

## Notas

- Emisión: PyJWT, expiración 43200 s (12 h), cookie httpOnly + SameSite=Lax
  (research D2).
- Política de contraseñas (FR-017): mínima longitud **8** caracteres; hash
  `argon2-cffi`; sin caducidad ni bloqueo en Fase 1. Nunca se devuelve
  `hashed_password` en respuestas.