# ContabilidadV2

Núcleo contable multi-tenant (Fase 1): registro de **Plan General Contable (PGC) de España** y **asientos diarios** con partida doble, flujo borrador → asentado y Diario, sobre una API FastAPI y un cliente Next.js.

La lógica contable (validaciones, cuadre, correlativos, cierres de periodo y aislamiento entre empresas) reside **exclusivamente en el backend**. El frontend calcula la diferencia Δ en tiempo real solo como ayuda de entrada; la autoridad del cuadre es el servidor. Reglas vinculantes en [`.specify/memory/constitution.md`](.specify/memory/constitution.md).

## Características (Fase 1)

- **Multi-tenant lógico**: Usuario → Empresa → Ejercicio → Cuenta / Asiento → Apunte. Contexto activo por cabeceras `X-Empresa-Id` / `X-Ejercicio-Id` con verificación de pertenencia.
- **Autenticación**: JWT (PyJWT) + hash argon2. Login devuelve `Authorization: Bearer` y cookie httpOnly `SameSite=Lax`.
- **Plan de cuentas** por ejercicio (código PGC, nombre, nivel) con unicidad `(ejercicio_id, codigo)`.
- **Asientos de 2 a N líneas** con flujo **borrador → asentado**: el borrador admite descuadre; el `asentar` exige ΣDebe = ΣHaber y asigna un número correlativo atómico sin huecos.
- **Inmutabilidad**: los asientos asentados no se editan ni eliminan (correcciones por extorno en fases posteriores).
- **Ejercicios cerrados**: bloquean cualquier escritura (409).
- **Concurrencia SQLite multipuesto**: `journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON`.
- **Esquema versionado con Alembic** (nunca `create_all`).
- **Frontend MD3**: tema claro/oscuro (MUI v6), selector global de Empresa/Ejercicio, formulario de asientos con Δ en tiempo real y Diario paginado/expandible con pestaña de borradores.

## Stack

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.12 · FastAPI · SQLModel/SQLAlchemy 2 · Alembic · PyJWT · argon2-cffi |
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
- Estado: `GET /api/v1/health` → `{ "status": "ok", "db": "wal", ... }`
- Usuarios seed: `admin` / `admin-2026` (crea empresas) y `contable` / `contable-2026`.

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
| `APP_JWT_SECRET` | secreto de desarrollo | **Cambiar en producción** (≥ 32 bytes) |
| `APP_JWT_EXPIRES_SECONDS` | `43200` | Caducidad del token (12 h) |

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
| POST | `/ejercicios` | Crear ejercicio |
| GET | `/cuentas` | Plan de cuentas del ejercicio (paginado/filtrable) |
| POST | `/cuentas` | Alta de cuenta |
| POST | `/asientos` | Guardar **borrador** (2..N líneas, admite descuadre) |
| PUT | `/asientos/{id}` | Editar borrador |
| POST | `/asientos/{id}/asentar` | Borrador → **asentado** (exige ΣDebe = ΣHaber) |
| GET | `/asientos` | Diario de asentados (paginado/filtrable) |
| GET | `/asientos/borradores` | Borradores del ejercicio |
| GET | `/asientos/{id}` | Detalle con apuntes |
| GET | `/health` | Estado del servicio y pragmas |

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
│   │   ├── api/         # routers: auth, empresas, cuentas, asientos, deps, errors
│   │   ├── models/      # SQLModel: identidad y contable
│   │   ├── schemas/     # Pydantic (request/response)
│   │   ├── services/    # lógica contable: cuadre, correlativo, identidad, seguridad
│   │   ├── config.py    # settings (pydantic-settings)
│   │   ├── db.py        # motor SQLite + pragmas WAL
│   │   ├── main.py      # app FastAPI
│   │   └── seed.py      # usuarios de desarrollo
│   ├── alembic/         # migraciones (único camino de evolución del esquema)
│   ├── tests/           # unit/ e integration/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/         # App Router: layout, login, dashboard, asientos, diario, cuentas
│   │   ├── components/  # ContextSelector, FormAsiento, Diario, PlanCuentas
│   │   └── lib/         # api.ts (cliente + contexto), theme.ts, useCargar.ts
│   ├── tests/           # vitest
│   └── package.json
├── specs/001-modulo-core-contable/   # spec, plan, tasks, contratos, quickstart
└── .specify/            # constitución y flujo Spec Kit
```

## Documentación

- Constitución y principios: [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
- Feature y contratos: [`specs/001-modulo-core-contable/`](specs/001-modulo-core-contable/) (incluye `quickstart.md` para validación end-to-end)
- Guía para agentes: [`AGENTS.md`](AGENTS.md)

## Roadmap

- **Fase 1 (actual)**: PGC, asientos diarios, Diario. *Pendiente*: **Libro Mayor sencillo**.
- **Fase 2**: control de concurrencia y validaciones de cierre de periodo; Balance de Sumas y Saldos.
- **Fase 3**: gestión de IVA/impuestos, facturación básica y herramientas auxiliares.
