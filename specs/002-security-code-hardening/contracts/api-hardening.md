# Contrato de API (Fase 1): cambios de Spec 2

**Feature**: `002-security-code-hardening`
**Fecha**: 2026-10-09
**Prefijo**: `/api/v1`

Este contrato describe únicamente los cambios de comportamiento/contrato respecto a Fase 1. Convenciones generales sin cambios:

- Autenticación: `Authorization: Bearer <token>` **o** cookie httpOnly `access_token`.
- Endpoints de negocio: requieren cabeceras `X-Empresa-Id` y `X-Ejercicio-Id` (400 si faltan; 403 si no vinculado o empresa inactiva).
- Errores: `{"detail": "<mensaje>"}` con el código HTTP indicado.

---

## 1. Convención transversal: anti-CSRF (SEC-02)

Cuando la autenticación provenga de la **cookie** `access_token`, toda petición mutacional (`POST`/`PUT`/`DELETE`) DEBE incluir:

```http
X-Requested-With: XMLHttpRequest
```

| Caso | Respuesta |
|------|-----------|
| Falta la cabecera o su valor es distinto | `403` · `{"detail": "... CSRF ..."}` |
| Autenticación por `Authorization: Bearer` | La cabecera CSRF **no** es obligatoria |
| `GET`/`HEAD`/`OPTIONS` | No requiere la cabecera |

El frontend (`frontend/src/lib/api.ts`) la añade automáticamente en las peticiones mutacionales.

---

## 2. `POST /auth/login` (SEC-05)

- **Rate limit**: 5 peticiones/minuto por IP remota, contando aciertos y fallos.
- **Cuerpo** (sin cambios): `{ "username": string, "password": string }`.
- **Respuestas**:

| Código | Cuándo | Cuerpo |
|--------|--------|--------|
| `200` | Credenciales válidas | `LoginResponse` (token + datos usuario); set-cookie `access_token` |
| `401` | Credenciales inválidas o usuario inactivo | `{"detail": "Credenciales inválidas" \| "Usuario inactivo"}` |
| `429` | > 5 peticiones en < 1 min desde la misma IP | `{"detail": "..."} ` (SlowAPI) |

**Criterio**: la 6.ª petición desde la misma IP en < 1 min devuelve `429`, acierte o no.

---

## 3. `GET /health` (SEC-06)

- **Respuesta `200`** (contrato nuevo, exacto):

```json
{ "status": "ok" }
```

- **Eliminado del contrato**: `db`, `busy_timeout`, `foreign_keys`, `migrations`.

---

## 4. Endpoints de negocio: contexto de empresa (SEC-03)

Aplica a todos los endpoints que usan `X-Empresa-Id` (p. ej. `GET /ejercicios`, `/cuentas`, `/asientos`).

| Código | Cuándo | `detail` |
|--------|--------|----------|
| `400` | `X-Empresa-Id` ausente, vacío o no numérico | "Cabecera X-Empresa-Id requerida/inválida" |
| `404` | La empresa no existe | "Empresa no encontrada" |
| `403` | `Empresa.activa == False` | contiene "inactiva" |
| `403` | El usuario no está vinculado a la empresa | "Sin acceso a la empresa" |

---

## 5. `POST /ejercicios` (SEC-04)

- **Autorización**: solo `usuario.rol == "admin"`.
- **Respuestas**:

| Código | Cuándo | `detail` |
|--------|--------|----------|
| `201` | Creado por admin | `EjercicioOut` |
| `403` | Rol distinto de `admin` | contiene "admin" |

---

## 6. `POST /asientos/{id}/asentar` (CONT-01, LEGAL-01)

- **Reglas previas al asentado** (orden):
  1. Asiento del ejercicio y estado `borrador` (si no → `409`).
  2. Ejercicio `abierto` (si no → `409`).
  3. `len(apuntes) >= 2` (si no → `422`, `detail` contiene "al menos 2").
  4. Δ = ΣDebe − ΣHaber = 0 (si no → `422`).
- **Efectos al asentar**: asigna `numero` correlativo del ejercicio, `estado="asentado"`, `asentado_por_usuario_id`, `asentado_at`.
- **Respuestas**:

| Código | Cuándo |
|--------|--------|
| `200` | Asentado correctamente (`AsientoOut`) |
| `404` | Asiento no encontrado en el ejercicio |
| `409` | Ya asentado o ejercicio cerrado |
| `422` | < 2 apuntes o Δ ≠ 0 |

### `AsientoOut` (añadidos)

```jsonc
{
  "id": 1,
  "ejercicio_id": 3,
  "numero": 1,
  "fecha": "2026-05-10",
  "concepto": "...",
  "estado": "asentado",
  "apuntes": [ { "cuenta_id": 10, "cuenta_codigo": "57200001", "debe": "100.00", "haber": "0.00" } ]
}
```

> `AsientoOut` puede exponer opcionalmente `creado_por_usuario_id`, `asentado_por_usuario_id`, `created_at`, `asentado_at` para trazabilidad; el cliente de Spec 2 no los requiere.

---

## 7. Listados paginados (PERF-01)

`GET /asientos`, `GET /asientos/borradores`, `GET /cuentas` mantienen el sobre:

```jsonc
{ "total": 123, "offset": 0, "limit": 50, "items": [ /* ... */ ] }
```

- `total` se calcula con `COUNT` sobre los mismos filtros (sin materializar filas).
- `limit` acotado a `[1, 200]`; `offset >= 0`.

---

## 8. Efectos observables de rendimiento (PERF-02)

- `GET /asientos/{id}` devuelve los apuntes con `cuenta_codigo` en **una** consulta (JOIN), sin N+1.
- `GET /asientos` calcula `total_debe`/`total_haber` con agregación (`SUM`), sin recorrer apuntes en Python.
