# Guía de Validación Rápida: Spec 2 — Hardening de Seguridad y Código

**Feature**: `002-security-code-hardening`
**Fecha**: 2026-10-09

Guía para validar end-to-end que los hallazgos de la auditoría quedan resueltos. No contiene la implementación; para detalles ver [data-model.md](./data-model.md) y [contracts/api-hardening.md](./contracts/api-hardening.md).

---

## Requisitos previos

- Python 3.12 y venv en la raíz del repo (`.venv`).
- Node 20+ para el frontend.
- Variables de entorno: `APP_JWT_SECRET` **obligatoria** (≥ 32 caracteres en producción). Para pruebas, `conftest.py` la define automáticamente.

```powershell
# desde backend/
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.seed
```

---

## 1. Backend — pruebas automatizadas

```powershell
# desde backend/
..\.venv\Scripts\python.exe -m ruff check app tests
..\.venv\Scripts\python.exe -m pytest -q
```

**Esperado**: `ruff` sin errores; `pytest` en verde, incluida `tests/integration/test_security_hardening.py`.

Escenarios que deben cubrir los tests (mapeados a criterios de aceptación):

| Test | Hallazgo | Resultado esperado |
|------|----------|--------------------|
| `test_asentar_asiento_sin_apuntes_retorna_422` | CONT-01 | `422`, `detail` contiene "al menos 2" |
| `test_empresa_inactiva_retorna_403` | SEC-03 | `403`, `detail` contiene "inactiva" |
| `test_usuario_contable_no_puede_crear_ejercicio_403` | SEC-04 | `403`, `detail` contiene "admin" |
| `test_paginacion_utiliza_count_y_limita_items` | PERF-01 | `200`, `total` presente, `items` ≤ limit |
| `test_mutacion_con_cookie_sin_cabecera_csrf_rechazada` | SEC-02 | `403`, `detail` contiene "csrf" |
| `test_health_no_expone_detalles_internos` | SEC-06 | `200`, sin `journal_mode`/`busy_timeout`, `status=="ok"` |
| rate limit login | SEC-05 | 6.ª petición en < 1 min → `429` |

---

## 2. Verificación manual (curl / REST)

### 2.1 Secretos (SEC-01)

```powershell
# Arrancar SIN APP_JWT_SECRET debe fallar de forma explícita
Remove-Item Env:\APP_JWT_SECRET -ErrorAction SilentlyContinue
..\.venv\Scripts\python.exe -c "from app.config import get_settings; get_settings.cache_clear(); get_settings()"
```

**Esperado**: error de validación (no arranca con un secreto por defecto).

### 2.2 Health sanitizado (SEC-06)

```powershell
curl http://127.0.0.1:8000/api/v1/health
```

**Esperado**: `{"status":"ok"}` exactamente; sin pragmas ni `migrations`.

### 2.3 Multi-tenant inactivo (SEC-03)

1. Autenticarse (`POST /api/v1/auth/login`) y guardar la cookie.
2. Desactivar una empresa vinculada (`UPDATE empresa SET activa=0 ...`).
3. `GET /api/v1/ejercicios` con `X-Empresa-Id` de esa empresa.

**Esperado**: `403` con "inactiva".

### 2.4 CSRF cookie-auth (SEC-02)

```powershell
# Con cookie access_token y SIN X-Requested-With
curl -X POST http://127.0.0.1:8000/api/v1/cuentas `
  -H "X-Empresa-Id: 1" -H "X-Ejercicio-Id: 1" `
  -b "access_token=<COOKIE>" -H "Content-Type: application/json" `
  -d '{"codigo":"572001","nombre":"Banco Prueba","nivel":4}'
```

**Esperado**: `403` con "CSRF". Repetir **con** `-H "X-Requested-With: XMLHttpRequest"` → `201`.

### 2.5 Partida doble (CONT-01)

Crear un asiento vacío por BD y llamar `POST /api/v1/asientos/{id}/asentar`.

**Esperado**: `422` con "al menos 2".

### 2.6 Rate limit login (SEC-05)

Ejecutar 6 `POST /api/v1/auth/login` seguidos desde la misma IP.

**Esperado**: las 5 primeras procesan (`200`/`401`); la 6.ª devuelve `429`.

---

## 3. Frontend — pruebas y build

```powershell
# desde frontend/
npm test
npm run lint
npx tsc --noEmit
npm run build
```

**Esperado**:
- Los tests de `FormAsiento.test.tsx` pasan (incluida la aritmética en céntimos del Δ).
- La cabecera `X-Requested-With: XMLHttpRequest` se envía en `POST`/`PUT`/`DELETE` (test de `src/lib/api.ts`).
- `lint`, `tsc` y `build` sin errores.

---

## 4. Migración de auditoría (LEGAL-01)

```powershell
# desde backend/
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic downgrade -1
..\.venv\Scripts\python.exe -m alembic upgrade head
```

**Esperado**: la migración aplica y revierte sin error; en una BD sin asientos el backfill no altera filas; tras crear y asentar un asiento, `creado_por_usuario_id`, `created_at`, `asentado_por_usuario_id` y `asentado_at` quedan poblados.

---

## 5. Criterios de aceptación (resumen)

- [ ] Criterio 1: asentar con < 2 líneas → `422`.
- [ ] Criterio 2: el asiento asentado persiste `asentado_por_usuario_id` y `asentado_at`.
- [ ] Criterio 3: petición con empresa `activa=False` → `403`.
- [ ] Criterio 4: 6.ª petición a `/auth/login` en < 1 min desde la misma IP → `429`.
- [ ] SEC-02: mutación con cookie sin `X-Requested-With` → `403` "CSRF".
- [ ] SEC-06: `/health` devuelve solo `{"status":"ok"}`.
- [ ] PERF-01/02: paginación con `COUNT` y apuntes sin N+1.
- [ ] FRONT-01: Δ calculado en céntimos enteros.
- [ ] FRONT-02: controles de `FormAsiento` migrados a MUI v6 conservando `data-testid`.
