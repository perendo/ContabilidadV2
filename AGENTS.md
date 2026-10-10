# AGENTS.md

App de contabilidad multi-tenant: núcleo contable (PGC + asientos), informes (Libro Mayor y Balance), conciliación bancaria y diseño de módulos fiscales. Dos apps independientes:

- `backend/` — FastAPI + SQLModel + Alembic, Python 3.12 (venv en la **raíz** del repo `.venv`).
- `frontend/` — Next.js 15 (App Router) + React 19 + MUI v6.

La lógica contable vive **solo** en el backend; el cálculo de Δ del frontend es únicamente UX. Reglas vinculantes: `.specify/memory/constitution.md` (español, PGC España: ΣDebe=ΣHaber al `asentar`, asentados inmutables). Docs por feature en `specs/` (001 núcleo · 002 hardening · 003 mayor/balance · 004 bancos · 005 fiscales; cada uno con `tasks.md` de casillas `[X]`). Feature activa en `.specify/feature.json`; diseño técnico de fiscales en `.specify/plans/01-modulos-fiscales.md`.

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

La BD SQLite es `backend/contabilidadv2.db` (gitignored). Los pragmas WAL/busy_timeout/foreign_keys se aplican al conectar y quedan solo en los logs de arranque (`lifespan`); `/api/v1/health` devuelve únicamente `{"status":"ok"}` (SEC-06, sin detalles de infraestructura).

## Gotchas

- **Esquema solo vía Alembic**, nunca `create_all`. `alembic revision --autogenerate` emite `sqlmodel.sql.sqltypes.AutoString` sin import y omite los índices FK — reemplazar por `sa.String(...)` y añadir los `ix_*` a mano, luego `alembic upgrade head`.
- `empresa_usuario` es un `sqlmodel Table`, no una clase. `session.exec(select(empresa_usuario))` devuelve solo la primera columna; usar `session.execute(...)` + `row._mapping["col"]`.
- Los schemas Pydantic que validan objetos ORM necesitan `model_config = ConfigDict(from_attributes=True)`.
- **`select` debe importarse de `sqlmodel`, no de `sqlalchemy`**, en cualquier módulo que use `Session.exec(...)`: `sqlalchemy.select` + `Session.exec` devuelve filas `Row` (tuplas) en vez de objetos ORM y rompe los `response_model` (`[(MovimientoBanco(...),)]` en vez de `[MovimientoBanco(...)]`). Revisar `api/banco.py`/`services/banco.py`.
- **Informes y banco**: routers `/informes` (Libro Mayor por cuenta, listado global, Balance de Sumas y Saldos y export CSV/PDF generado en el servidor) y `/banco` (importar extracto `multipart` con detección de formato Excel Santander/CSV/CSB-43 y de duplicados; CRUD de reglas de auto-matching por **empresa**; `simular`; `procesar`; `logs`). El auto-matching reutiliza `services/asientos.guardar_borrador`/`asentar`, así que respeta correlativo y ΣDebe=ΣHaber.
- **`backend/impuestos/`** (spec 005, aún **no implementado**) será el destino de los ficheros AEAT de posiciones fijas (303/111/115/200) y está previsto gitignored; la descarga solo se permitirá con la liquidación/periodo cerrados (409). Actualmente el 005 cuenta solo con spec/plan/tasks.
- Auth acepta `Authorization: Bearer` O la cookie httpOnly `access_token`; el login establece ambos. Los endpoints de negocio además requieren las cabeceras `X-Empresa-Id` + `X-Ejercicio-Id` (400 si faltan, 403 si no está vinculado). El login tiene rate limit `5/minute` por IP (slowapi).
- Regla de rol (FR-003b): solo `admin` crea empresas **y** ejercicios; `contable` → 403. Los usuarios solo se crean por seed — no hay endpoint de registro.
- **`limiter` de slowapi vive en `app/rate_limit.py`**, no en `app.main` (`api/auth.py` lo importa → import circular si se define en `main`). Instalar dependencias con `pip install -e .` desde `backend/` si falta algún paquete declarado en `pyproject.toml`.
- **PGC base**: `services/identidad.crear_ejercicio` llama a `sembrar_pgc` (`app/pgc.py`) en el mismo commit (siembra grupos 1-7, niveles 1-3, `nivel=len(codigo)`); `app.seed` hace backfill **idempotente** de ejercicios sin cuentas. Códigos de cuenta **solo dígitos** (`max_length=10`); las subcuentas (nivel 4+) se crean sobre ese PGC vía `POST /cuentas`.
- `backend/tests/conftest.py` migra una BD temporal con `alembic upgrade head` y llama a `get_settings.cache_clear()`. Ejecutar los tests desde `backend/` (las rutas de `pyproject.toml`/`alembic.ini` son relativas). El fixture `contexto` acepta `rol=` (por defecto `contable`); los tests que crean ejercicios vía API usan `contexto(rol="admin")` y los que esperan 403 por rol deben **vincular** el usuario a la empresa o recibirán "Sin acceso a la empresa" antes del chequeo de rol. El fixture autouse `_clean_tables` limpia `apunte/asiento/cuenta/ejercicio/empresausuario/empresa/usuario` y también `movimiento_banco/regla_banco/log_procesamiento_banco`. `backend/.env` alimenta `Settings()` en tests unitarios: para ignorar el dotenv usar `Settings(_env_file=None)`.
- Proxy de desarrollo del frontend: `next.config.mjs` reescribe `/api/v1/*` → `NEXT_PUBLIC_API_URL` (por defecto `http://127.0.0.1:8000`). `src/lib/api.ts` lee las cookies `empresa_id`/`ejercicio_id` como contexto. Alias de rutas `@/*` → `src/*`.
- vitest exige `esbuild.jsx: "automatic"` (ya configurado en `vitest.config.ts`); eslint está fijado a v8 porque Next 15 usa el `.eslintrc.json` legacy.
- Shell Windows/PowerShell: encadenar con `;` / `if ($?)`, no con `&&`.
- Editar docs con acentos (p. ej. `tasks.md`): escribir en UTF-8 usando las herramientas edit/Write o Python; `Set-Content` de PowerShell corrompe los acentos.

## Spec Kit

Los comandos del flujo son `/speckit.*` (ver `.opencode/commands/`): spec → plan → tasks → implement. Mantener actualizadas las casillas de `tasks.md` de cada feature en `specs/` y la feature activa en `.specify/feature.json`. `master` ya tiene commits y remoto en GitHub (`origin` → `perendo/ContabilidadV2`).
