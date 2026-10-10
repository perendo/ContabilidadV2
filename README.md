# ContabilidadV2

Núcleo contable multi-tenant (Fase 1): registro de **Plan General Contable (PGC) de España** y **asientos diarios** con partida doble, flujo borrador → asentado y Diario, sobre una API FastAPI y un cliente Next.js. Sobre esa base se añaden informes (**Libro Mayor** por cuenta y **listado global**, y **Balance de Sumas y Saldos**), **conciliación bancaria** con auto-matching y el diseño de los **módulos fiscales** (Libros Registro de IVA, retenciones IRPF e Impuesto sobre Sociedades).

La lógica contable (validaciones, cuadre, correlativos, cierres de periodo y aislamiento entre empresas) reside **exclusivamente en el backend**. El frontend calcula la diferencia Δ en tiempo real solo como ayuda de entrada; la autoridad del cuadre es el servidor. Reglas vinculantes en [`.specify/memory/constitution.md`](.specify/memory/constitution.md).

## Características (Fase 1)

- **Multi-tenant lógico**: Usuario → Empresa → Ejercicio → Cuenta / Asiento → Apunte. Contexto activo por cabeceras `X-Empresa-Id` / `X-Ejercicio-Id` con verificación de pertenencia.
- **Selección de contexto**: tras el login, pantalla `/seleccion` para elegir o **crear** empresa (solo `admin`) y ejercicio antes de operar.
- **Autenticación**: JWT (PyJWT) + hash argon2. Login devuelve `Authorization: Bearer` y cookie httpOnly `SameSite=Lax`. Rate limit de login `5/minute` por IP (slowapi).
- **Plan de cuentas** por ejercicio con **PGC base curado** (niveles 1-3, grupos 1-7) **sembrado automáticamente** al crear el ejercicio; el usuario añade **subcuentas** (nivel 4+) sobre él en vista de árbol. Códigos numéricos con unicidad `(ejercicio_id, codigo)`.
- **Asientos de 2 a N líneas** con flujo **borrador → asentado**: el borrador admite descuadre; el `asentar` exige ΣDebe = ΣHaber y asigna un número correlativo atómico sin huecos.
- **Inmutabilidad**: los asientos asentados no se editan ni eliminan (correcciones por extorno en fases posteriores).
- **Ejercicios cerrados**: bloquean cualquier escritura (409).
- **Concurrencia SQLite multipuesto**: `journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON`.
- **Esquema versionado con Alembic** (nunca `create_all`).
- **Frontend MD3**: tema claro/oscuro (MUI v6), selector global de Empresa/Ejercicio, formulario de asientos con Δ en tiempo real, Diario paginado/expandible con pestaña de borradores, y páginas de **Mayor** y **Balance** con export a CSV/PDF.
- **Informes** (spec 003): **Libro Mayor** por cuenta (saldo inicial, movimientos y saldo final, con filtro de fechas) y **listado global** de cuentas, más el **Balance de Sumas y Saldos**. La exportación CSV/PDF se genera en el servidor; el cálculo vive solo en el backend.
- **Conciliación bancaria** (spec 004): importación de extractos (**Excel Santander, CSV estándar, CSB/Cuaderno 43**, con detección de formato y de duplicados), **reglas de auto-matching** (regex sobre el concepto + importe fijo/porcentaje) que generan asientos **reutilizando el servicio contable** (borrador o asentado con correlativo y ΣDebe = ΣHaber), y cola de **movimientos pendientes**. Cada procesamiento queda trazado en `log_procesamiento_banco`.
- **Módulos fiscales** (spec 005, *en diseño*): Libros Registro de IVA, retenciones IRPF e Impuesto sobre Sociedades, con generación de ficheros AEAT de posiciones fijas (303/111/115/200) solo con periodos cerrados y sin presentación telemática.

## Stack

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.12 · FastAPI · SQLModel/SQLAlchemy 2 · Alembic · PyJWT · argon2-cffi · slowapi |
| Base de datos | SQLite en modo WAL |
| Frontend | Next.js 15 (App Router) · React 19 · MUI v6 · Emotion |
| Tests | pytest + httpx (backend) · vitest + Testing Library (frontend) |
| Calidad | ruff, black · ESLint, TypeScript, Prettier |

## Requisitos

- **Python 3.12**
- **Node.js ≥ 18.18** y npm

## Puesta en marcha

### 1. Backend

El entorno virtual vive en la **raíz del repositorio**.

```powershell
# Desde la raíz del repo
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
```

Configura el entorno (opcional; hay valores por defecto para desarrollo):

```powershell
Copy-Item backend\.env.example backend\.env
```

Aplica migraciones, crea usuarios de desarrollo y arranca el servidor (desde `backend/`):

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.seed
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- API: http://127.0.0.1:8000 · Swagger: http://127.0.0.1:8000/docs
- Estado: `GET /api/v1/health` → `{ "status": "ok" }` (liveness mínimo; los pragmas quedan solo en los logs de arranque, SEC-06)
- Usuarios seed: `admin` / `admin-2026` (crea empresas) y `contable` / `contable-2026`. El seed también siembra el **PGC base** en ejercicios existentes sin cuentas. Tras el login se abre `/seleccion` para elegir o crear empresa y ejercicio.

### 2. Frontend

```powershell
# Desde frontend/
Copy-Item .env.local.example .env.local
npm install
npm run dev
```

Cliente en http://127.0.0.1:3000. El dev server reescribe `/api/v1/*` hacia `NEXT_PUBLIC_API_URL` (por defecto `http://127.0.0.1:8000`), por lo que no hace falta CORS en desarrollo.

## Configuración

**Backend** (`backend/.env`, prefijo `APP_`):

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `APP_DATABASE_URL` | `sqlite:///./contabilidadv2.db` | URL de la base de datos |
| `APP_JWT_SECRET` | *(obligatorio)* | Sin defecto; en producción ≥ 32 chars y sin `change-me` |
| `APP_JWT_EXPIRES_SECONDS` | `3600` | Caducidad del token (máx. 1 h) |

**Frontend** (`frontend/.env.local`):

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Destino del rewrite `/api/v1/*` |

## API

Base path `/api/v1`. Cuerpos JSON; fechas `YYYY-MM-DD`; importes como cadena decimal de 2 decimales. Errores `{ "detail": "<mensaje>" }`. Los endpoints de negocio requieren autenticación y las cabeceras de contexto.

| Método | Ruta | Acción |
|--------|------|--------|
| POST | `/auth/login` | Iniciar sesión (Bearer + cookie) |
| GET | `/auth/me` | Perfil y empresas del usuario |
| POST | `/auth/logout` | Cerrar sesión (204) |
| GET | `/empresas` | Empresas del usuario |
| POST | `/empresas` | Crear empresa (**solo `admin`**) |
| GET | `/ejercicios` | Ejercicios de la empresa activa |
| POST | `/ejercicios` | Crear ejercicio (siembra el **PGC base**) |
| GET | `/cuentas` | Plan de cuentas del ejercicio (paginado/filtrable) |
| POST | `/cuentas` | Alta de cuenta / **subcuenta** (nivel 4+) |
| POST | `/asientos` | Guardar **borrador** (2..N líneas, admite descuadre) |
| PUT | `/asientos/{id}` | Editar borrador |
| POST | `/asientos/{id}/asentar` | Borrador → **asentado** (exige ΣDebe = ΣHaber) |
| GET | `/asientos` | Diario de asentados (paginado/filtrable) |
| GET | `/asientos/borradores` | Borradores del ejercicio |
| GET | `/asientos/{id}` | Detalle con apuntes |
| GET | `/informes/mayor` | Libro Mayor de una cuenta (fechas opcionales) |
| GET | `/informes/mayor/cuentas` | Listado global de cuentas con saldos |
| GET | `/informes/balance` | Balance de Sumas y Saldos |
| GET | `/informes/mayor/export` · `/informes/balance/export` | Export CSV/PDF (generado en el servidor) |
| POST | `/banco/importar` | Importar extracto (multipart; detecta formato y duplicados) |
| GET | `/banco/pendientes` | Movimientos pendientes de casar |
| GET/POST | `/banco/reglas` | Listar / crear reglas de auto-matching |
| GET/PUT/DELETE | `/banco/reglas/{id}` | Detalle / editar / borrar regla |
| POST | `/banco/reglas/{id}/simular` | Simular el match de una regla sin asentar |
| POST | `/banco/procesar` | Generar asientos de los pendientes aplicando reglas |
| GET | `/banco/logs` | Trazabilidad de los procesamientos |
| GET | `/health` | Liveness del servicio (`{"status":"ok"}`) |

Códigos: `400` contexto/firma inválida · `401` no autenticado · `403` sin acceso · `404` inexistente · `409` conflicto de estado/unicidad · `422` validación/descuadre.

## Tests

```powershell
# Backend (desde backend/)
..\.venv\Scripts\python.exe -m ruff check app tests
..\.venv\Scripts\python.exe -m pytest -q

# Frontend (desde frontend/)
npm run lint
npx tsc --noEmit
npm test
```

`backend/tests/conftest.py` crea una BD temporal migrada con `alembic upgrade head`; por eso los tests deben ejecutarse desde `backend/`. Verificación completa de release: `ruff` → `pytest` → `lint` → `tsc --noEmit` → `build`.

## Estructura

```text
ContabilidadV2/
├── backend/
│   ├── app/
│   │   ├── api/         # routers: auth, empresas, cuentas, asientos, informes, banco, deps, errors
│   │   ├── models/      # SQLModel: identidad, contable y banco
│   │   ├── schemas/     # Pydantic: identidad, contable, informes y banco
│   │   ├── services/    # lógica: cuadre, correlativo, identidad, seguridad, informes, banco
│   │   ├── pgc.py       # PGC base curado (niveles 1-3) + siembra por ejercicio
│   │   ├── config.py    # settings (pydantic-settings)
│   │   ├── db.py        # motor SQLite + pragmas WAL
│   │   ├── main.py      # app FastAPI
│   │   ├── rate_limit.py # Limiter de slowapi (evita import circular con api/auth)
│   │   └── seed.py      # usuarios de desarrollo + backfill del PGC base
│   ├── alembic/         # migraciones (único camino de evolución del esquema)
│   ├── tests/           # unit/ e integration/ (incluye informes y banco)
│   ├── impuestos/       # ficheros AEAT (spec 005, planificado; gitignored)
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/         # App Router: login, seleccion, asientos, diario, cuentas, mayor, balance
│   │   ├── components/  # ContextSelector, FormAsiento, Diario, PlanCuentas, Mayor, Balance
│   │   └── lib/         # api.ts (cliente + contexto), theme.ts, useCargar.ts
│   ├── tests/           # vitest
│   └── package.json
├── specs/               # 001 núcleo · 002 hardening · 003 mayor/balance · 004 bancos · 005 fiscales
└── .specify/            # constitución, feature.json y planes (`plans/01-modulos-fiscales.md`)
```

## Documentación

- Constitución y principios: [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
- Specs por feature (cada una con `spec.md`, `plan.md`, `tasks.md` y, cuando aplica, `contracts/` y `quickstart.md`):
  - `001-modulo-core-contable` · `002-security-code-hardening` · `003-libro-mayor-balance` · `004-conciliacion-bancaria` · `005-modulos-fiscales` → [`specs/`](specs/)
- Plan de diseño de los módulos fiscales: [`.specify/plans/01-modulos-fiscales.md`](.specify/plans/01-modulos-fiscales.md)
- Guía para agentes: [`AGENTS.md`](AGENTS.md)

## Roadmap

- **Fase 1 (completada)**: PGC base + subcuentas, asientos diarios (borrador → asentado), Diario y contexto multi-tenant.
- **Fase 1.1 (completada)**: informe de **Libro Mayor** y **listado global** + **Balance de Sumas y Saldos** con export CSV/PDF (spec 003).
- **Fase 1.2 (completada)**: **conciliación bancaria** con importación de extractos y reglas de auto-matching (spec 004).
- **Fase 1.3 (diseño)**: **módulos fiscales** — Libros Registro de IVA, retenciones IRPF e Impuesto sobre Sociedades, con ficheros AEAT (spec 005).
