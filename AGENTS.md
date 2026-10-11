# AGENTS.md

App de contabilidad multi-tenant: núcleo contable (PGC + asientos), informes (Libro Mayor y Balance), conciliación bancaria y módulos fiscales (facturas con IVA/RE/retenciones, Libros Registro de IVA, retenciones IRPF, Impuesto sobre Sociedades y presentaciones AEAT). Dos apps independientes:

- `backend/` — FastAPI + SQLModel + Alembic, Python 3.12 (venv en la **raíz** del repo `.venv`).
- `frontend/` — Next.js 15 (App Router) + React 19 + MUI v6.

La lógica contable vive **solo** en el backend; el cálculo de Δ del frontend es únicamente UX. Reglas vinculantes: `.specify/memory/constitution.md` (español, PGC España: ΣDebe=ΣHaber al `asentar`, asentados inmutables). Docs por feature en `specs/` (001 núcleo · 002 hardening · 003 mayor/balance · 004 bancos · 005 fiscales; specs 001-005 **implementadas**, cada una con su `tasks.md` de casillas `[X]`). Feature activa en `.specify/feature.json`; diseño técnico original de fiscales en `.specify/plans/01-modulos-fiscales.md`.

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
- **Módulos fiscales (spec 005, implementado)**: routers `/facturas` (factura con asiento automático `origen="factura"`, Libros Registro de IVA `repercutido`/`soportado` + export CSV, resumen de retenciones IRPF 111/115), `/is` (Liquidación del Impuesto sobre Sociedades: en `borrador` se recalcula al consultar y `PUT` actualiza; `cerrar` congela e inmuta → 409 en `PUT`/2º cierre) y `/presentaciones` (vista por modelo + fichero AEAT de posiciones fijas). La vista en pantalla está siempre disponible; el **fichero** se bloquea con 409 salvo que el ejercicio esté **cerrado** (303/111/115) o la liquidación IS esté **cerrada** (200). Los ficheros se persisten en `backend/impuestos/{empresa_id}/{anio}/{modelo}_{periodo}.txt` (gitignored: `backend/impuestos/*` + `!backend/impuestos/.gitkeep`) con trazabilidad SHA-256/usuario/fecha en `fichero_presentacion`; regenerar sobrescribe y refresca la trazabilidad.
- Auth acepta `Authorization: Bearer` O la cookie httpOnly `access_token`; el login establece ambos. Los endpoints de negocio además requieren las cabeceras `X-Empresa-Id` + `X-Ejercicio-Id` (400 si faltan, 403 si no está vinculado). El login tiene rate limit `5/minute` por IP (slowapi).
- Regla de rol (FR-003b): solo `admin` crea empresas **y** ejercicios; `contable` → 403. Los usuarios solo se crean por seed — no hay endpoint de registro.
- **`limiter` de slowapi vive en `app/rate_limit.py`**, no en `app.main` (`api/auth.py` lo importa → import circular si se define en `main`). Instalar dependencias con `pip install -e .` desde `backend/` si falta algún paquete declarado en `pyproject.toml`.
- **PGC base**: `services/identidad.crear_ejercicio` llama a `sembrar_pgc` (`app/pgc.py`) en el mismo commit (siembra grupos 1-7, niveles 1-3, `nivel=len(codigo)`); `app.seed` hace backfill **idempotente** de ejercicios sin cuentas. Códigos de cuenta **solo dígitos** (`max_length=10`); las subcuentas (nivel 4+) se crean sobre ese PGC vía `POST /cuentas`.
- **Fiscales (`is` es palabra reservada de Python)**: los módulos del Impuesto sobre Sociedades se llaman `impuesto_sociedades` (`models`/`schemas`/`services`/`api`) aunque el prefijo y tag HTTP sean `/is`. Redondeo monetario siempre con `services/fiscales_util.cuantizar2` (`ROUND_HALF_UP`, 2 dp) y validación real de CIF/NIF con `validar_cif` (p. ej. `B12345674` es válido; `B12345678` **no**). Los enums fiscales son `enum.StrEnum` (target py312, ruff UP042) persistidos como `String`. El asiento de la factura lo genera `services/facturas` reutilizando `guardar_borrador`/`asentar` (correlativo y ΣDebe=ΣHaber) y resolviendo las cuentas PGC por **código** dentro del ejercicio (cuenta ausente → 422; `4751` no está en el PGC base, hay que crearla).
- `backend/tests/conftest.py` migra una BD temporal con `alembic upgrade head` y llama a `get_settings.cache_clear()`. Ejecutar los tests desde `backend/` (las rutas de `pyproject.toml`/`alembic.ini` son relativas). El fixture `contexto` acepta `rol=` (por defecto `contable`); los tests que crean ejercicios vía API usan `contexto(rol="admin")` y los que esperan 403 por rol deben **vincular** el usuario a la empresa o recibirán "Sin acceso a la empresa" antes del chequeo de rol. El fixture autouse `_clean_tables` limpia `apunte/asiento/cuenta/ejercicio/empresausuario/empresa/usuario`, las de banco (`movimiento_banco/regla_banco/log_procesamiento_banco`) y las fiscales (`factura/linea_factura_iva/liquidacion_impuesto_sociedades/fichero_presentacion`). Para tests de facturas usar `contexto_fiscal` (PGC base completo + `4751`): `contexto()` crea 3 cuentas y `sembrar_pgc` se salta el ejercicio (idempotente), así que faltarían las cuentas contables. `backend/.env` alimenta `Settings()` en tests unitarios: para ignorar el dotenv usar `Settings(_env_file=None)`.
- Proxy de desarrollo del frontend: `next.config.mjs` reescribe `/api/v1/*` → `NEXT_PUBLIC_API_URL` (por defecto `http://127.0.0.1:8000`). `src/lib/api.ts` lee las cookies `empresa_id`/`ejercicio_id` como contexto. Alias de rutas `@/*` → `src/*`.
- vitest exige `esbuild.jsx: "automatic"` (ya configurado en `vitest.config.ts`); eslint está fijado a v8 porque Next 15 usa el `.eslintrc.json` legacy.
- Shell Windows/PowerShell: encadenar con `;` / `if ($?)`, no con `&&`. **No** usar `2>&1` con comandos nativos (`git`, `npm`, `npx`, `python`, …): PowerShell 5.1 convierte cada línea de stderr en un `NativeCommandError` decorado en rojo que parece un fallo, aunque el comando haya salido con código `0` (p. ej. `git push` escribe "To …/Everything up-to-date" en stderr y `npx` escribe avisos de npm). Da igual encadenarlo a `| Select-Object` o capturarlo en una variable (`$x = git … 2>&1`): se muestra igual; y `2>fichero` escribe el error decorado. Usar el comando **en plano** (su stderr se muestra normal) o silenciarlo con `2>$null`, y comprobar el resultado con `$LASTEXITCODE` (o `$?`).
- **Finales de línea**: `.gitattributes` fija el texto en **LF** (`* text=auto eol=lf`) y los scripts de Windows (`.bat`, `.cmd`, `.ps1`) en **CRLF**. Los colaboradores **no** necesitan configurar `core.autocrlf` (el atributo manda sobre él). En un clon nuevo los EOL salen correctos; para normalizar uno antiguo, borrar los ficheros y `git checkout -- .`.
- Editar docs con acentos (p. ej. `tasks.md`): escribir en UTF-8 usando las herramientas edit/Write o Python; `Set-Content` de PowerShell corrompe los acentos.

## Spec Kit

Los comandos del flujo son `/speckit.*` (ver `.opencode/commands/`): spec → plan → tasks → implement. Mantener actualizadas las casillas de `tasks.md` de cada feature en `specs/` y la feature activa en `.specify/feature.json`. `master` ya tiene commits y remoto en GitHub (`origin` → `perendo/ContabilidadV2`).
