# Quickstart — Validación end-to-end de 001-modulo-core-contable (Fase 1)

Guía de validación funcional del feature. Detalles de modelo y contratos en
`data-model.md` y `contracts/`. No sustituye a la suite de tests.

## Prerrequisitos

- Python 3.12 (`.venv` del repo), Node ≥ 18 para el frontend.
- Backend: `pip install -e ".[dev]"` desde `backend/` (FastAPI, SQLModel,
  Alembic, PyJWT, argon2-cffi, pytest, httpx).
- Frontend: `npm install` desde `frontend/`.

## Arranque (incluye migraciones Alembic)

Backend:

```text
cd backend
alembic upgrade head          # F.021: el esquema se crea/actualiza SIEMPRE vía migración
uvicorn app.main:app --reload --port 8000
# Swagger: http://127.0.0.1:8000/docs
```

Frontend:

```text
cd frontend
npm run dev   # http://127.0.0.1:3000
```

`GET /api/v1/health` debe devolver `{ "status": "ok", "db": "wal",
"migrations": "current" }` (confirma WAL, `busy_timeout=5000`,
`foreign_keys=ON` y que `alembic current` está al día).

**Regla de oro (FR-021)**: si cambia el esquema, se crea una revisión
Alembic (`alembic revision --autogenerate`) y se aplica; NUNCA se edita la
BD a mano ni se usa `create_all` en producción.

## Escenarios de validación (ordenados)

### S1. Contexto y pertenencia (SC-001)

1. Crear usuario A y B (registro/seed); login de A.
2. A crea empresa E1; B crea empresa E2.
3. A llama `GET /api/v1/ejercicios` con `X-Empresa-Id: E2` → **403**.
4. A y B operan en paralelo sobre E1 y E2 → ninguna consulta devuelve datos
   del otro.

**Esperado**: 403 en contexto ajeno; datos aislados.

### S2. Plan de cuentas por ejercicio (SC-004)

1. Crear ejercicio 2026 en E1 (`POST /api/v1/ejercicios`), `abierto`.
2. Crear ejercicio 2026 en E2 (mismo código de cuenta permitido).
3. `POST /api/v1/cuentas {codigo:'57200001', nivel:4}` en ambos → **201**.
4. Repetirlo en el mismo ejercicio → **409**.
5. `GET /api/v1/cuentas` solo devuelve cuentas del ejercicio activo.

### S3. Asiento múltiple, borrador y asentado (SC-002/SC-004)

1. Crear cuentas: 57200001 (bancos), 41000000 (proveedor), 47200000 (IVA
   soportado), 47200000b… usar 3 cuentas.
2. POST `/api/v1/asientos` (borrador) de **3 líneas descuadrado**
   (`debe 1210`, `debe 190`, `haber 1400` — falta el capital del haber) →
   **201**, `numero: null`, `estado: borrador`.
3. GET `/api/v1/asientos/borradores` → aparece el borrador con su Δ.
4. `POST /asientos/{id}/asentar` en el descuadrado → **422** con `Δ`; el
   número NO se consume.
5. `PUT /asientos/{id}` añadiendo la línea que completa el cuadre (haber 1000
   adicional) → **200**; `POST /asientos/{id}/asentar` → **200**, `numero: 1`,
   `estado: asentado`.
6. `PUT /asientos/{id}` sobre el asentado → **409/422** (inmutable).

**Esperado**: descuadre bloquea el asentado (no el borrador); correlativo
sin huecos; inmutabilidad de asentado.

### S4. Ejercicio cerrado (SC-003)

1. Marcar el ejercicio `cerrado` (sqlite directo en Fase 1; el API de cierre
   llega en Fase 2).
2. POST de borrador, PUT, asentar y POST de cuenta sobre ese ejercicio →
   **409** todos.
3. El Diario no expone PUT/DELETE de asentados (`/openapi.json`).

**Esperado**: 409 en cualquier escritura sobre cerrado.

### S5. Concurrencia WAL (SC-005)

1. Dos sesiones httpx en paralelo: preparar N borradores cuadrados y
   asentarlos de forma concurrente.
2. **Esperado**: cero "database is locked"; N números correlativos 1..N sin
   duplicados (UNIQUE + reintento).
3. Durante las escrituras, lecturas de Diario responden sin bloqueo.

### S6. Migraciones (FR-021)

1. Con la BD creada, ejecutar `alembic current` → apunta a la última
   revisión.
2. Modificar un modelo (p. ej. añadir columna) y generar
   `alembic revision --autogenerate -m "..."` seguido de `alembic upgrade
   head` → la columna aparece; el historial queda versionado.

**Esperado**: evolución de esquema exclusivamente vía Alembic.

## Verificación por criterio de aceptación

| # | Criterio | Escenario |
|---|----------|-----------|
| 1 | Aislamiento multi-usuario | S1, S5 |
| 2 | Prohibición de descuadre en asentado | S3 |
| 3 | Prohibición de escritura en cerrado | S4 |
| 4 | Correlativo independiente | S2 (cuentas), S3/S5 (asientos) |
| 5 | Sin "database is locked" con WAL | S5 |

## Automatización

La suite `pytest` (`backend/tests/`, BD temporal migrada con
`alembic upgrade head` en `conftest.py`) cubre S2–S6 como integración
(httpx over ASGI); S1 requiere dos usuarios (fixture). El frontend aporta
tests unitarios del cálculo Δ y del bloqueo de **asentar** (vitest). Puerta
de salida:

```text
python -m pytest backend/tests -q
cd frontend && npm test
```