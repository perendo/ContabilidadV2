# Implementation Plan: Módulo Core Contable Multi-Tenant (Fase 1)

**Branch**: `001-modulo-core-contable` | **Date**: 2026-10-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-modulo-core-contable/spec.md`
(con aclaraciones de sesión 2026-10-08: MD3/MUI, borrador editable,
multi-linea, Alembic, política de contraseñas, Diario expandible, estados UI)

## Summary

Construir el núcleo contable multipuesto de ContabilidadV2: base de datos
SQLite en modo WAL con esquema versionado por **Alembic** desde el inicio,
API FastAPI tipada con aislamiento lógico multi-tenant (Usuario →
EmpresaUsuario → Empresa → Ejercicio → Cuenta / Asiento → Apunte),
autenticación con JWT + argon2, Plan de Cuentas PGC por ejercicio y
asientos contables de **2 a N líneas** (asientos múltiples) con flujo
**borrador → asentado**: el borrador se guarda (puede ir descuadrado) y el
asentado exige Σ Debe = Σ Haber en servidor con número correlativo atómico.
Cliente Next.js con Material Design 3 (MUI v6), selector global de contexto,
formulario con Δ en tiempo real y Diario expandible (apuntes + borradores).
Enfoque por slices verticales.

## Technical Context

**Language/Version**: Python 3.12 (venv `.venv`, 3.12.10); TypeScript con
Next.js 15 / React 19

**Primary Dependencies**: FastAPI, Pydantic v2, SQLModel + **Alembic**
(migraciones), uvicorn, PyJWT, argon2-cffi, passlib; frontend: MUI v6,
React, SWR o fetch propio

**Storage**: SQLite con `journal_mode=WAL`, `busy_timeout=5000`,
`foreign_keys=ON`. Esquema versionado por migraciones Alembic (nada de
`create_all` en producción). BD única compartida con aislamiento lógico por
`empresa_id`/`ejercicio_id` (multi-tenant lógico)

**Testing**: pytest + httpx (`ASGITransport`) sobre BD temporal migrada con
Alembic; tests de unidad sobre cuadre N-líneas, correlativos y transiciones
borrador→asentado; integración para contexto/cierre. Frontend: vitest para
Δ del formulario y bloqueo de asentar

**Target Platform**: Windows en LAN (multipuesto), uvicorn único, navegadores
de escritorio

**Project Type**: web-service + web frontend (Option 2: `backend/` y
`frontend/`)

**Performance Goals**: p95 < 200 ms en asentar/guardar asiento en LAN;
Diario paginado < 300 ms con miles de asientos

**Constraints**: Σ Debe = Σ Haber obligatorio solo al `asentado`; asientos
asentados inmutables; ejercicios cerrados bloquean escrituras (409);
asientos múltiples de 2..N líneas sin límite en Fase 1; esquema bajo
Alembic; cuentas según PGC España; toda la lógica contable en el backend;
login obligatorio por sesión como única operación de arranque en primer
plano (el resto carga en segundo plano) y preselección de la
empresa/ejercicio de la última sesión (FR-011/011b)

**Scale/Scope**: decenas de usuarios concurrentes, decenas de empresas,
miles de asientos por ejercicio; endpoints: auth, empresas/ejercicios,
cuentas, asientos (crud borrador + asentar + diario)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principio / Restricción | Estado | Evidencia en el diseño |
|---|--------------------------|--------|------------------------|
| I | Slices verticales incrementales (NO NEGOCIABLE) | PASS | Slices: (1) BD/motor+Alembic, (2) identidad/empresa, (3) API contable (cuentas+asientos), (4) frontend; cada uno testeable por separado |
| II | Separación estricta backend-frontend (NO NEGOCIABLE) | PASS | Cuadre, correlativo, cierres y pertenencia viven en FastAPI; el Δ del formulario es solo ayuda de entrada (el servidor revalida al asentar) |
| III | Integridad contable primaria (NO NEGOCIABLE) | PASS | Σ Debe = Σ Haber validado en servidor al `asentar` (sobre las N líneas); asentado inmutable (sin PUT/DELETE de asentados); correcciones futuras por extorno; cuentas con codigo/nombre/nivel PGC; unicidad `(ejercicio_id, codigo)` y `(ejercicio_id, numero)`. El `borrador` es un estado previo descuadrado permitido por la propia spec (FR-007/FR-012) y NO es un asiento contable definitivo |
| IV | Arquitectura tipada robusta | PASS | FastAPI + Pydantic v2 en todos los schemas, SQLModel, Alembic para evolución controlada; Next.js Server/Client Components |
| V | Concurrencia SQLite multipuesto | PASS | WAL + `busy_timeout=5000` + UNIQUE; correlativo generado en la escritura (writer único en WAL) con reintento |
| R1 | Restricciones técnicas (stack, PGC, invariantes a nivel BD/API) | PASS | UNIQUE compuestos; `debe`/`haber` ≥ 0; bloqueo de estado `cerrado` en capa de servicio; migraciones Alembic como único camino de evolución de esquema |
| R2 | Estándares: flujo Spec Kit + tests de cuadre antes de liberar | PASS | Plan generado por el flujo; suite pytest de cuadre/transiciones/cierre/correlativo y quickstart como puerta de salida |

**Gate notes (no violations)**:

- La constitución incluye "consulta sencilla de Diario y Libro Mayor" en
  Fase 1: este feature entrega el Diario; el **Libro Mayor sencillo** se
  mantiene como slice pendiente dentro de Fase 1 (NO se difiere a Fase 2) y
  debe completarse antes de cerrar la Fase 1. Se registra como follow-up.
- El estado `borrador` (FR-007/FR-012 y spec sesión 2026-10-08) es una
  decisión de producto explícita; los borradores descuadrados no constituyen
  asientos del Diario y no contradicen la inmutabilidad de los `asentado`.
- El frontend calcula Δ en tiempo real solo como UX; la autoridad del cuadre
  es del backend (Principio II).

**Gate result**: PASS — sin violaciones que justificar en
`Complexity Tracking`.

**Post-design re-check (Fase 1)**: revisado tras `data-model.md`, `contracts/`
y `quickstart.md`. Diseño coherente con las aclaraciones (borrador editable,
asientos múltiples, Alembic, MUI v6 MD3): el cuadre N-líneas y las
transiciones borrador→asentado se validan en `services`; Alembic emite el
esquema inicial y las migraciones de Fase 2; el contrato expone `borrador`
y `asentado` sin edición de asentados. Sigue **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/001-modulo-core-contable/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py              # app FastAPI, lifespan (pragmas WAL), incluya router
│   ├── db.py                # motor SQLite, sesión, pragmas
│   ├── models/              # SQLModel: usuario, empresa_usuario, empresa, ejercicio, cuenta, asiento, apunte
│   ├── schemas/             # Pydantic: requests/responses
│   ├── api/
│   │   ├── deps.py          # auth + contexto X-Empresa-Id/X-Ejercicio-Id
│   │   ├── auth.py          # login, me, logout
│   │   ├── empresas.py      # empresas + ejercicios
│   │   ├── cuentas.py       # plan de cuentas
│   │   └── asientos.py      # borrador (guardar/actualizar), asentar, diario, detalle
│   └── services/            # lógica contable: cuadre N-líneas, correlativo, cierres, transiciones
├── alembic/
│   ├── env.py               # lee metadata de modelos, apunta a app.db
│   ├── versions/
│   └── alembic.ini
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py          # BD temporal migrada con alembic upgrade head
└── pyproject.toml

frontend/
├── src/
│   ├── app/                 # App Router
│   ├── components/          # selector contexto, formulario asientos, diario, states M3
│   ├── lib/                 # cliente API, contexto activo (cookies)
│   └── styles/
├── tests/
└── package.json
```

**Structure Decision**: Option 2 (web application). `backend/` (FastAPI +
SQLModel + Alembic), `frontend/` (Next.js + MUI v6). La separación física
refuerza el Principio II: el frontend solo consume la API REST/OpenAPI.

## Complexity Tracking

> No aplica: el Constitution Check no detectó violaciones (ver gate notes).

## Gate Note Final (Fase 1 core)

- **Estado**: **Fase 1 core completada** (T001–T042). Validación 2026-10-08:
  `python -m pytest -q` → **40 passed**; `npm test` (vitest) → **3 passed**;
  `next lint` y `tsc --noEmit` sin errores; `next build` compila las 6 rutas
  (`/`, `/login`, `/asientos`, `/cuentas`, `/diario`, `/_not-found`).
- **Escenarios quickstart S1–S6** cubiertos por la suite de integración
  (`test_identidad` S1, `test_cuentas` S2, `test_asientos` S3/S4,
  `test_concurrency` S5, `test_health` S6) y por el test de componente Δ/
  bloqueo de asentar (vitest). Sin desviaciones abiertas.
- **Follow-up pendiente (NO diferido a Fase 2)**: el **Libro Mayor sencillo**
  continúa como slice pendiente dentro de la Fase 1 y debe completarse antes
  de cerrar la Fase 1 (ver gate notes).
- **Restricciones confirmadas**: solo `admin` crea empresas (`contable` → 403,
  FR-003b); auth por `Authorization: Bearer` con fallback a cookie httpOnly
  SameSite=Lax; nadie expone `hashed_password`; escrituras en ejercicio
  `cerrado` → 409; asentados inmutables; esquema solo vía Alembic
  (`bb1c920e98ab`).
