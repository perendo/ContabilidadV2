# Implementation Plan: Conciliación Bancaria con Auto-Matching

**Branch**: `004-conciliacion-bancaria` | **Fecha**: 2026-10-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-conciliacion-bancaria/spec.md`

## Summary

Añadir módulo de conciliación bancaria que permita importar extractos en **3 formatos** (Excel Santander, CSV estándar, CSB/Cuaderno 43), aplicar **reglas de auto-matching** configurables (regex + 2 cuentas contables + prioridad) para generar asientos automáticamente, y gestionar **pendientes** manualmente. Todo integrado en la arquitectura actual de 2 apps (`backend/` FastAPI + `frontend/` Next.js).

Enfoque técnico: nueva tabla `MovimientoBanco` + `ReglaBanco` (migración Alembic), parser específico por formato (`openpyxl` para Excel Santander, `pandas`/`csv` para CSV, `pybank43` para CSB), endpoints bajo `/api/v1/banco/`, página `/banco` en frontend con 4 tabs.

## Technical Context

**Language/Version**: Python 3.12 (venv `.venv` en raíz); TypeScript 5.6 / Next.js 15 / React 19 / MUI v6

**Primary Dependencies**: 
- Backend: FastAPI, SQLModel, SQLAlchemy, Alembic, Pydantic v2, `openpyxl`, `pandas`, `pybank43` (nuevas)
- Frontend: `@mui/material` v6, `@mui/x-data-grid` (opcional para tablas), `react-hook-form`

**Storage**: SQLite (`backend/contabilidadv2.db`) en modo WAL; nuevas tablas `movimiento_banco`, `regla_banco`; índices en `ejercicio_id`, `hash_unicidad`, `procesado`

**Testing**: Backend `pytest` + `httpx`/`TestClient` sobre BD temporal migrada; Frontend `vitest` + `@testing-library/react`

**Target Platform**: Multipuesto Windows/Linux (despliegue local/pequeña empresa); navegadores de escritorio

**Project Type**: Aplicación web (dos apps: `backend/` FastAPI + `frontend/` Next.js)

**Performance Goals**: 
- Importar 1000 movimientos Excel/CSV en < 5s
- Procesar 1000 movimientos con 20 reglas en < 3s
- Parser Excel: detectar fila header automáticamente (buscar "Fecha Operación")

**Constraints**: 
- Solo asientos `asentado` en informes (regla contable vigente)
- Multi-tenant estricto por `X-Empresa-Id`/`X-Ejercicio-Id`
- Importes `Decimal` 2 decimales extremo a extremo
- CSV export: `;` + coma decimal + UTF-8 BOM (ya implementado en spec 3)
- Sin cambios en modelos contables existentes (`Asiento`/`Apunte`/`Cuenta`)

**Scale/Scope**: 
- Decenas de cuentas, hasta 10.000 asientos/ejercicio
- 3 formatos importación + auto-matching + UI pendientes
- Reglas por empresa (aisladas), ~20 reglas típicas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / Restricción | Estado | Justificación |
|-------------------------|--------|---------------|
| I. Slices Verticales Incrementales | ✅ PASS | Plan organizado en slices: (1) modelos+migración, (2) parsers Excel/CSV/CSB, (3) auto-matching service, (4) endpoints, (5) UI Importar, (6) UI Reglas, (7) UI Pendientes, (8) integración Diario |
| II. Separación Estricta Backend-Frontend | ✅ PASS | Parsers, matching, generación asientos en backend (`services/banco.py`); frontend solo UI + download |
| III. Integridad Contable Primaria | ✅ PASS | Asientos generados por reglas siempre cuadran (2 cuentas fijas); pendientes crean borradores normales; no modifica asientos asentados |
| IV. Arquitectura Tipada Robusta | ✅ PASS | Nuevos schemas Pydantic en `schemas/banco.py`; OpenAPI contrato; `Decimal` 2dp |
| V. Concurrencia SQLite MultiPuesto | ✅ PASS | WAL permite lecturas concurrentes; escrituras son inserts en `movimiento_banco` + `asiento` (existente) |
| R1. Restricciones técnicas (stack, PGC, invariantes) | ✅ PASS | Respeta PGC España (cuentas deben existir en ejercicio), invariante Debe=Haber (reglas definen 2 cuentas) |
| R2. Estándares (flujo Spec Kit + tests antes de liberar) | ✅ PASS | Plan por flujo Spec Kit; suite pytest de parsers/matching + quickstart |

**Gate result**: PASS — sin violaciones que justificar en `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/004-conciliacion-bancaria/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── banco.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                       # añadir openpyxl, pandas, pybank43
├── app/
│   ├── main.py                          # registrar banco_router
│   ├── api/
│   │   ├── deps.py                      # (existente) EjercicioDep/SessionDep/UsuarioDep
│   │   └── banco.py                     # NUEVO: /banco/importar, /pendientes, /procesar, /reglas CRUD
│   ├── schemas/
│   │   └── banco.py                     # NUEVO: MovimientoBancoIn/Out, ReglaBancoIn/Out, ImportResult...
│   ├── services/
│   │   └── banco.py                     # NUEVO: parsers (excel_santander, csv_std, csb), matching, crear_asiento_desde_regla
│   └── models/
│       └── contable.py                  # AÑADIR: MovimientoBanco, ReglaBanco
└── tests/
    └── integration/
        └── test_banco.py                # NUEVO: parsers, matching, import, multi-tenant

frontend/
├── package.json                         # añadir pybank43 no necesario (solo backend)
├── src/
│   ├── app/
│   │   ├── page.tsx                     # añadir acceso a /banco
│   │   └── banco/
│   │       ├── page.tsx                 # NUEVO (client component con Suspense)
│   │       ├── importar/page.tsx        # NUEVO (Tab 1)
│   │       ├── reglas/page.tsx          # NUEVO (Tab 2)
│   │       ├── pendientes/page.tsx      # NUEVO (Tab 3)
│   │       └── procesados/page.tsx      # NUEVO (Tab 4)
│   ├── components/
│   │   ├── BancoImportar.tsx            # NUEVO (drag&drop, preview, detectar formato)
│   │   ├── BancoReglas.tsx              # NUEVO (CRUD tabla + modal simular)
│   │   ├── BancoPendientes.tsx          # NUEVO (tabla filtrable + modal crear asiento)
│   │   └── BancoProcesados.tsx          # NUEVO (historial con link asiento)
│   └── lib/
│       └── api.ts                       # AÑADIR: tipos banco + métodos api.banco.*
└── tests/
    └── Banco.test.tsx                   # NUEVO: render tabs, importar, simular regla
```

**Structure Decision**: se mantiene la estructura de dos apps de la Fase 1 (`backend/` FastAPI + `frontend/` Next.js). No se crean proyectos nuevos; toda la nueva lógica de conciliación se localiza en `backend/app/services/banco.py`, expuesta por `backend/app/api/banco.py`, y consumida por la página `/banco` frontend. Requiere migración Alembic para 2 tablas nuevas.

## Complexity Tracking

> No hay violaciones de la Constitución que justificar. Sección intencionadamente vacía.

---

## Phase 0: Research (pendiente)

Incógnitas técnicas a resolver antes del diseño:

| # | Incógnita | Decisión tentativa |
|---|-----------|-------------------|
| R1 | Parser CSB: `pybank43` vs implementación propia | `pybank43` si existe en PyPI y soporta AEB Norma 43; si no, parser propio (registros 01/02/03/99 longitud fija) |
| R2 | Detección automática formato en importación | Por extensión + sniffing primeras líneas (Excel: `PK` header; CSV: `;` en primera línea; CSB: empieza con `01`) |
| R3 | Background job para `/procesar` | MVP síncrono (< 3s para 1000 movs); v2: Celery/RQ si supera timeout HTTP |
| R4 | Validación cuentas en regla | Al crear regla: verificar que `cuenta_debe` y `cuenta_haber` existen en ejercicio activo de la empresa |
| R5 | Signo importe en reglas | Banco: negativo=cargo. Regla define cuentas contables (debe/haber positivo). Service convierte signo al crear asiento |

---

*Next: ejecutar `/speckit.tasks` para desglose en tareas, luego implementación.*