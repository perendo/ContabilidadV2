# AGENTS.md

App de contabilidad núcleo multi-tenant (Fase 1). Dos apps independientes:

- `backend/` — FastAPI + SQLModel + Alembic, Python 3.12 (venv en la **raíz** del repo `.venv`).
- `frontend/` — Next.js 15 (App Router) + React 19 + MUI v6.

La lógica contable vive **solo** en el backend; el cálculo de Δ del frontend es únicamente UX. Reglas vinculantes: `.specify/memory/constitution.md` (español, PGC España: ΣDebe=ΣHaber al `asentar`, asentados inmutables). Docs del feature + tracker de progreso: `specs/001-modulo-core-contable/` (`tasks.md` usa `[X]`).

El cuadro de cuentas arranca con un **PGC base curado** (`backend/app/pgc.py`, niveles 1-3, grupos 1-7) que se **siembra al crear cada ejercicio**; el usuario solo añade las **subcuentas** (nivel 4+) que necesite. Tras el login, la segunda pantalla es `/seleccion` (elegir/crear empresa + ejercicio).

## Comandos

Backend — ejecutar desde `backend/`, usando el python del venv raíz:

- Tests: `..\.venv\Scripts\python.exe -m pytest -q`
- Un solo test: `..\.venv\Scripts\python.exe -m pytest tests/integration/test_asientos.py::test_cuadrar_y_asentar_200_correlativo -q`
- Lint: `..\.venv\Scripts\python.exe -m ruff check app tests`
- Migrar: `..\.venv\Scripts\python.exe -m alembic upgrade head`
- Seed usuarios de desarrollo: `..\.venv\Scripts\python.exe -m app.seed` (`admin/admin-2026`, `contable/contable-2026`; además rellena el PGC base en ejercicios existentes sin cuentas)
- Servidor de desarrollo: `..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`

Frontend — ejecutar desde `frontend/`:

- `npm test` (vitest) · un solo archivo `npx vitest run tests/FormAsiento.test.tsx`
- `npm run lint` · `npx tsc --noEmit` · `npm run build` · `npm run dev`

Verificar en orden: backend `ruff` → `pytest`; frontend `lint` → `tsc --noEmit` → `build`.

La BD SQLite es `backend/contabilidadv2.db` (gitignored). Los pragmas WAL/busy_timeout/foreign_keys se aplican al conectar; `/api/v1/health` los reporta.

## Gotchas

- **Esquema solo vía Alembic**, nunca `create_all`. `alembic revision --autogenerate` emite `sqlmodel.sql.sqltypes.AutoString` sin import y omite los índices FK — reemplazar por `sa.String(...)` y añadir los `ix_*` a mano, luego `alembic upgrade head`.
- `empresa_usuario` es un `sqlmodel Table`, no una clase. `session.exec(select(empresa_usuario))` devuelve solo la primera columna; usar `session.execute(...)` + `row._mapping["col"]`.
- Los schemas Pydantic que validan objetos ORM necesitan `model_config = ConfigDict(from_attributes=True)`.
- Auth acepta `Authorization: Bearer` O la cookie httpOnly `access_token`; el login establece ambos. Los endpoints de negocio además requieren las cabeceras `X-Empresa-Id` + `X-Ejercicio-Id` (400 si faltan, 403 si no está vinculado).
- Regla de rol (FR-003b): solo `admin` crea empresas; `contable` → 403. Los usuarios solo se crean por seed — no hay endpoint de registro.
- **PGC base**: `services/identidad.crear_ejercicio` llama a `sembrar_pgc` (`app/pgc.py`) en el mismo commit (siembra grupos 1-7, niveles 1-3, `nivel=len(codigo)`); `app.seed` hace backfill **idempotente** de ejercicios sin cuentas. Códigos de cuenta **solo dígitos** (`max_length=10`); las subcuentas (nivel 4+) se crean sobre ese PGC vía `POST /cuentas`.
- `backend/tests/conftest.py` migra una BD temporal con `alembic upgrade head` y llama a `get_settings.cache_clear()`. Ejecutar los tests desde `backend/` (las rutas de `pyproject.toml`/`alembic.ini` son relativas).
- Proxy de desarrollo del frontend: `next.config.mjs` reescribe `/api/v1/*` → `NEXT_PUBLIC_API_URL` (por defecto `http://127.0.0.1:8000`). `src/lib/api.ts` lee las cookies `empresa_id`/`ejercicio_id` como contexto. Alias de rutas `@/*` → `src/*`.
- vitest exige `esbuild.jsx: "automatic"` (ya configurado en `vitest.config.ts`); eslint está fijado a v8 porque Next 15 usa el `.eslintrc.json` legacy.
- Shell Windows/PowerShell: encadenar con `;` / `if ($?)`, no con `&&`.
- Editar docs con acentos (p. ej. `tasks.md`): escribir en UTF-8 usando las herramientas edit/Write o Python; `Set-Content` de PowerShell corrompe los acentos.

## Spec Kit

Los comandos del flujo son `/speckit.*` (ver `.opencode/commands/`): spec → plan → tasks → implement. Mantener actualizadas las casillas de `specs/001-modulo-core-contable/tasks.md`. `master` ya tiene commits y remoto en GitHub (`origin` → `perendo/ContabilidadV2`).
