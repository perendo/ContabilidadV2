# Implementation Plan: Libro Mayor y Balance de Sumas y Saldos

**Branch**: `003-libro-mayor-balance` | **Fecha**: 2026-10-10 | **Spec**: [spec.md](./spec.md)

**Input**: Especificación de feature en `specs/003-libro-mayor-balance/spec.md` (con
aclaraciones de sesión 2026-10-10: jerarquía PGC, CSV `;`/coma/BOM, cuentas
compensadas, 10.000 asientos, formato de cuatro columnas, roles y encabezado de
exportación).

## Resumen

Añadir dos informes contables **de solo lectura** sobre el ejercicio activo:
el **Libro Mayor** (por cuenta individual y listado global de cuentas con
movimiento, con saldo acumulado) y el **Balance de Sumas y Saldos** (cuatro
columnas clásicas — Suma Debe, Suma Haber, Saldo Deudor, Saldo Acreedor — con
agregación jerárquica de los grupos/subgrupos del PGC y totales generales).

Enfoque técnico: toda la agregación y el cálculo de saldos se realizan en el
**backend** (Principio II) mediante un nuevo servicio `services/informes.py`
sobre las tablas existentes `Asiento`/`Apunte`/`Cuenta` (sin cambios de
esquema ni migración Alembic). Se exponen endpoints JSON y de **exportación**
CSV y PDF en un nuevo router `api/informes.py`; el CSV usa `;` + coma decimal
con UTF-8 BOM y el PDF se genera con **ReportLab**. El frontend añade las
páginas `/mayor` y `/balance` (MUI v6, MD3) con filtro de fechas y **un botón
independiente por formato** (CSV y PDF), descargando los ficheros vía `fetch`
con las cabeceras de contexto. Enfoque por slices verticales.

## Technical Context

**Language/Version**: Python 3.12 (venv `.venv`); TypeScript 5.6 / Next.js 15 / React 19 / MUI v6 (frontend).

**Primary Dependencies**: Backend FastAPI, Pydantic v2, SQLModel + SQLAlchemy, Alembic (sin cambios de esquema); **nueva**: `reportlab` (generación de PDF). Frontend: `@mui/material` 6.x (sin dependencias nuevas; descarga por `Blob` + `URL.createObjectURL`).

**Storage**: SQLite (`backend/contabilidadv2.db`) en modo WAL; los informes son consultas **de solo lectura** agregadas sobre `cuenta`, `asiento` y `apunte`. Sin tablas nuevas ni migraciones.

**Testing**: Backend `pytest` + `httpx`/`TestClient` sobre BD temporal migrada (`tests/conftest.py`, fixture `contexto`); nuevos `tests/integration/test_informes.py` (agregación, filtros de fecha, saldo acumulado, jerarquía, cuentas compensadas, CSV/PDF, multi-tenant). Frontend `vitest` + `@testing-library/react` (`frontend/tests/`); nuevo `tests/Informes.test.tsx`.

**Target Platform**: Multipuesto Windows/Linux (despliegue local/pequeña empresa); navegadores de escritorio.

**Project Type**: Aplicación web (dos apps: `backend/` y `frontend/`).

**Performance Goals**: generar cualquiera de los dos informes (pantalla, CSV o PDF) de un ejercicio de hasta **10.000 asientos** en **< 3 s**; agregación en base de datos (una consulta con `GROUP BY`) + asociación de prefijos en memoria proporcional al número de cuentas (decenas), no al de apuntes.

**Constraints**: solo asientos `asentado`; informes consultables también en ejercicio `cerrado` (solo lectura); aislamiento multi-tenant por `X-Empresa-Id`/`X-Ejercicio-Id`; importes `Decimal` a 2 decimales; CSV `;` + coma decimal + UTF-8 con BOM; PDF con encabezado (razón social + CIF, ejercicio, rango de fechas, fecha/hora); toda la lógica contable y de generación en el backend.

**Scale/Scope**: decenas de cuentas y hasta 10.000 asientos por ejercicio; 2 informes + 2 formatos de exportación + 2 pantallas frontend; sin comparación entre ejercicios.

## Constitution Check

*GATE: debe pasar antes de la Fase 0 y re-evaluarse tras el diseño de Fase 1.*

| Principio / Restricción | Estado | Justificación |
|-------------------------|--------|---------------|
| I. Slices Verticales Incrementales (NO NEGOCIABLE) | ✅ PASS | El plan se organiza en slices autocontenidos y validables por separado: (1) agregación backend Mayor, (2) agregación backend Balance, (3) export CSV, (4) export PDF, (5) UI Mayor, (6) UI Balance, (7) panel/quickstart. |
| II. Separación Estricta Backend-Frontend (NO NEGOCIABLE) | ✅ PASS | Todo el cálculo (saldos acumulados, sumas, clasificación deudor/acreedor, agregación jerárquica) y la generación de CSV/PDF viven en el backend; el frontend solo presenta los datos y dispara la descarga. |
| III. Integridad Contable Primaria (NO NEGOCIABLE) | ✅ PASS | Informes estrictamente de solo lectura sobre asientos `asentado` (los `borrador` se excluyen); no se modifica ningún dato; agregación fiel al PGC (grupos/subgrupos por prefijo de código) y cuadre global Debe=Haber evidenciado. |
| IV. Arquitectura Tipada Robusta | ✅ PASS | Nuevos schemas Pydantic (`schemas/informes.py`) en las respuestas; OpenAPI como contrato; `Decimal` de 2 decimales; el router se registra en `main.py` como los existentes. |
| V. Concurrencia SQLite MultiPuesto | ✅ PASS | Los informes son lecturas; WAL permite lecturas concurrentes sin bloqueo con las escrituras normales. Sin escrituras nuevas. |
| R1. Restricciones técnicas (stack, PGC, invariantes) | ✅ PASS | Se respeta PGC España (jerarquía de cuentas), invariante Debe=Haber (solo se agregan asentados, que ya cuadran) y no se altera el esquema. |
| R2. Estándares (flujo Spec Kit + tests antes de liberar) | ✅ PASS | Plan por flujo Spec Kit; suite pytest de agregación/exportación y quickstart como puerta de salida. |

**Gate result**: PASS — sin violaciones que justificar en `Complexity Tracking`.

**Post-design re-check (Fase 1)**: revisado tras `data-model.md`, `contracts/informes.md`
y `quickstart.md`. El diseño confirma que **no hay cambios de esquema** (los
informes son vistas calculadas), que el CSV/PDF se generan en backend y que el
frontend no calcula resultados contables. Sigue **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/003-libro-mayor-balance/
├── plan.md              # Este archivo (/speckit.plan)
├── research.md          # Salida de la Fase 0
├── data-model.md        # Salida de la Fase 1
├── quickstart.md        # Salida de la Fase 1
├── contracts/           # Salida de la Fase 1
│   └── informes.md
└── tasks.md             # Salida de /speckit.tasks (NO lo crea este comando)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                       # añadir dependencia reportlab
├── app/
│   ├── main.py                          # registrar informes_router
│   ├── api/
│   │   ├── deps.py                      # (existente) EjercicioDep/SessionDep/UsuarioDep
│   │   └── informes.py                  # NUEVO: /informes/mayor, /informes/balance y export CSV/PDF
│   ├── schemas/
│   │   └── informes.py                  # NUEVO: MayorOut, MayorCuentaOut, BalanceOut, FilaBalance...
│   └── services/
│       └── informes.py                  # NUEVO: agregación por cuenta/prefijo, saldo acumulado, export CSV/PDF
└── tests/
    └── integration/
        └── test_informes.py             # NUEVO: Mayor, Balance, export, aislamiento

frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx                     # añadir accesos a /mayor y /balance
│   │   ├── mayor/page.tsx               # NUEVO
│   │   └── balance/page.tsx             # NUEVO
│   ├── components/
│   │   ├── Mayor.tsx                    # NUEVO (modos cuenta + listado global, filtros y botones CSV/PDF)
│   │   └── Balance.tsx                  # NUEVO (tabla de 4 columnas, filtros y botones CSV/PDF)
│   └── lib/
│       └── api.ts                       # NUEVO: tipos de informe + descarga de ficheros (Blob)
└── tests/
    └── Informes.test.tsx                # NUEVO: render de tablas y disparo de exportación
```

**Structure Decision**: se mantiene la estructura de dos apps de la Fase 1
(`backend/` FastAPI + `frontend/` Next.js). No se crean proyectos nuevos; toda
la nueva lógica contable se localiza en `backend/app/services/informes.py`,
expuesta por `backend/app/api/informes.py`, y consumida por dos pantallas
frontend. No hay cambios en modelos ni migraciones Alembic.

## Complexity Tracking

> No hay violaciones de la Constitución que justificar. Sección intencionadamente vacía.
