# Implementation Plan: Módulos Fiscales (Libros IVA, Retenciones IRPF, Impuesto sobre Sociedades)

**Branch**: `005-modulos-fiscales` | **Fecha**: 2026-10-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-modulos-fiscales/spec.md`
(con clarificaciones de las sesiones 2026-10-11: fichero de posiciones fijas AEAT
para 303/111/115/200, vista de presentación resumen + casillas oficiales,
descarga solo con liquidación/periodo cerrados, directorio `impuestos`, botón
de descarga independiente del guardado).

## Summary

Añadir al núcleo contable los módulos fiscales: **facturas** (venta/compra) con
desglose de IVA (+ Recargo de Equivalencia) y retenciones IRPF que **generan de
forma atómica** el asiento contable (400/430, 600/700, 472/477, 4751/473);
**Libros Registro de IVA** (Soportado/Repercutido) consultables y exportables;
**resúmenes de retenciones por CIF** para modelos 111/115; **Liquidación del
Impuesto sobre Sociedades** (resultado + ajustes + 25% + retenciones → cuota
diferencial); y **presentación AEAT**: vista en pantalla (resumen por bloques +
casillas oficiales) con botón de **generación y descarga** del **fichero de
posiciones fijas** (303/111/115/200), persistido en `impuestos/{empresa}/{anio}`.

Enfoque técnico: 3 tablas nuevas (`factura`, `linea_factura_iva`,
`liquidacion_impuesto_sociedades`) + tabla opcional de trazabilidad
(`fichero_presentacion`) vía migración Alembic; servicios `services/facturas.py`,
`services/aeat.py` (plantillas de posiciones fijas configurables); endpoints bajo
`/api/v1/facturas/...`, `/api/v1/presentaciones/...` y `/api/v1/is`; página frontend
`/facturas` y rutas `/fiscal/*`.

## Technical Context

**Language/Version**: Python 3.12 (venv `.venv` en raíz); TypeScript 5.6 / Next.js 15 / React 19 / MUI v6

**Primary Dependencies**:
- Backend: FastAPI, SQLModel, SQLAlchemy, Alembic, Pydantic v2 (existentes); sin dependencias nuevas previstas (generación de fichero con stdlib + templates JSON propios)
- Frontend: `@mui/material` v6 (existente); tabla/paginado con componentes propios o `@mui/x-data-grid` opcional

**Storage**: SQLite (`backend/contabilidadv2.db`) modo WAL; nuevas tablas `factura`, `linea_factura_iva`, `liquidacion_impuesto_sociedades`, `fichero_presentacion`; ficheros generados en `backend/impuestos/{empresa_id}/{anio}/` (gitignored)

**Testing**: Backend `pytest` + `TestClient` sobre BD temporal migrada (conftest existente); Frontend `vitest` + `@testing-library/react`

**Target Platform**: Multipuesto Windows/Linux (pymes); navegadores de escritorio

**Project Type**: Aplicación web (dos apps: `backend/` FastAPI + `frontend/` Next.js)

**Performance Goals**:
- Registro de factura con generación de asiento < 300 ms p95 (LAN)
- Libro de IVA de un trimestre (≤ 500 facturas) totalizado por tipo < 3 s
- Vista de presentación AEAT < 3 s; generación del fichero de posiciones fijas < 2 s

**Constraints**:
- Σ Debe = Σ Haber siempre (asiento derivado nace cuadrado); asentados inmutables
- Ejercicio/periodo cerrado bloquea escrituras y fichero (409)
- Unicidad CIF + Nº factura + ejercicio (BD + API 409)
- `Decimal` (19,2) extremo a extremo; porcentajes `Decimal` (5,2); nunca `float`
- Ficheros AEAT = plantilla oficial de posiciones fijas (configuración + validador), persistidos en `impuestos/` y descargables por el usuario
- Multi-tenant estricto por `X-Empresa-Id`/`X-Ejercicio-Id`; sólo admin crea ejercicios

**Scale/Scope**: decenas de empresas, miles de facturas/ejercicio, ~500
facturas/trimestre típicas; modelos 303/111/115/200; 1 liquidación IS por ejercicio

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / Restricción | Estado | Justificación |
|-------------------------|--------|---------------|
| I. Slices Verticales Incrementales | ✅ PASS | 3 slices: (1) modelos+migración+schemas, (2) servicios+endpoints facturas/libros/retenciones, (3) presentación AEAT (view+fichero) y UI. Cada slice testeable y demonstrable |
| II. Separación Estricta Backend-Frontend | ✅ PASS | Cálculo de cuotas/retenciones/IS, cuadre y generación de ficheros de posiciones fijas SOLO en backend (`services/facturas.py`, `services/aeat.py`). Frontend solo presenta y dispara descargas |
| III. Integridad Contable Primaria | ✅ PASS | Asiento derivado en la misma transacción que la factura con ΣDebe=ΣHaber (reusa `services/asientos.py`); facturas en asiento generan borrador/asentado inmutable; descarga de fichero solo con cierre |
| IV. Arquitectura Tipada Robusta | ✅ PASS | Schemas Pydantic con `from_attributes=True`; `Decimal` con 2dp; OpenAPI como contrato; validadores de CIF/tipos/redondeo |
| V. Concurrencia SQLite MultiPuesto | ✅ PASS | Asiento+factura en una transacción WAL; un UniqueConstraint evita duplicados concurrentes; correlativo de asiento ya atómico (Spec 1) |
| R1. Restricciones técnicas (stack, PGC, invariantes) | ✅ PASS | Cuentas 400/430/600/700/472/477/4751/473 del PGC; los ajustes IS se suman con signo; no `create_all` (Alembic) |
| R2. Estándares (flujo Spec Kit + tests antes de liberar) | ✅ PASS | Plan vía Spec Kit; suite pytest de cuadre/retenciones/unicidad/IS/ficheros + quickstart; verificación ruff→pytest→lint→tsc→build |

**Gate result (pre-Phase 0)**: PASS — sin violaciones que justificar.

**Re-check post-Phase 1**: PASS. El diseño (data-model + contracts) mantiene: la
lógica fiscal en servicios backend (Principio II), ΣDebe=ΣHaber en el mismo commit
que la factura (Principio III), fichero AEAT solo desde datos congelados y en
`impuestos/` (III + V), y tipos `Decimal` en esquema/contratos (IV). No se requieren
excepciones en `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/005-modulos-fiscales/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── facturas.md
│   ├── presentaciones.md
│   └── is.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                          # registrar routers facturas/presentaciones/is
│   ├── api/
│   │   ├── deps.py                      # (existente) EjercicioDep/SessionDep/UsuarioDep/Contexto
│   │   ├── facturas.py                  # NUEVO: facturas CRUD + libros IVA + retenciones
│   │   ├── presentaciones.py            # NUEVO: vista AEAT + generar/descargar fichero
│   │   └── is.py                        # NUEVO: liquidación IS CRUD + cerrar
│   ├── schemas/
│   │   ├── facturas.py                  # NUEVO: FacturaIn/Out, LineaFacturaIVAIn, LibroIVARow, ResumenRetencion
│   │   ├── presentaciones.py            # NUEVO: PresentacionVista, FicheroOut
│   │   └── is.py                        # NUEVO: LiquidacionISIn/Out, AjusteIS
│   ├── services/
│   │   ├── facturas.py                  # NUEVO: cálculo cuotas/retenciones, cuadre, asiento atómico, unicidad, libros, resumen 111/115
│   │   └── aeat.py                      # NUEVO: plantillas posiciones fijas 303/111/115/200, generador, validador, persistencia impuestos/
│   └── models/
│       └── fiscal.py                    # NUEVO: Factura, LineaFacturaIVA, LiquidacionImpuestoSociedades, FicheroPresentacion, enums
└── tests/
    └── integration/
        ├── test_facturas.py             # NUEVO: cuadre IVA/RE/retenciones, duplicados, libros
        └── test_presentaciones_is.py    # NUEVO: vista AEAT, fichero posiciones fijas, IS, cierre

frontend/
├── src/
│   ├── app/
│   │   ├── facturas/
│   │   │   ├── page.tsx                 # NUEVO: listado + alta/edición facturas
│   │   │   └── nueva/page.tsx           # NUEVO: formulario (o modal)
│   │   ├── fiscal/
│   │   │   ├── libros-iva/page.tsx      # NUEVO
│   │   │   ├── retenciones/page.tsx     # NUEVO
│   │   │   └── is/page.tsx              # NUEVO: liquidación IS
│   │   └── presentaciones/page.tsx      # NUEVO: vista AEAT + botón generar/descargar
│   ├── components/
│   │   ├── FormFactura.tsx              # NUEVO: líneas dinámicas base/tipo/retención + preview asiento (UX)
│   │   ├── LibroIVA.tsx                 # NUEVO
│   │   ├── ResumenRetenciones.tsx       # NUEVO
│   │   ├── LiquidacionIS.tsx            # NUEVO
│   │   └── PresentacionAEAT.tsx         # NUEVO: resumen + casillas + botón descarga
│   └── lib/
│       └── api.ts                       # AÑADIR: tipos y métodos api.facturas/presentaciones/is
└── tests/
    └── fiscales.test.tsx                # NUEVO (vitest)
```

**Structure Decision**: se mantienen las dos apps de la Fase 1. La lógica fiscal se
localiza en `backend/app/models/fiscal.py` + `services/facturas.py` y
`services/aeat.py`, expuesta por `api/facturas.py`, `api/presentaciones.py` y
`api/is.py`. Los ficheros AEAT se guardan bajo `backend/impuestos/` (gitignored),
organizados por empresa y ejercicio. Requiere 2 migraciones Alembic (fiscal +
fichero_presentacion). No se añaden proyectos nuevos.

## Complexity Tracking

> No hay violaciones de la Constitución que justificar. Sección intencionadamente vacía.

---

## Phase 0: Research — COMPLETADA (ver `research.md`)

Decisiones consolidadas en [`research.md`](./research.md): plantillas AEAT de
posiciones fijas configurables (R1), encodings parametrizables (R2), persistencia
`impuestos/` + descarga con regeneración (R3), ajustes IS en JSON validado (R4),
redondeo HALF_UP con absorción del céntimo (R5), cuenta de retención configurable
4751/473 (R6) y vista de presentación calculada en backend (R7).

## Phase 1: Design & Contracts — COMPLETADA

- [`data-model.md`](./data-model.md) — entidades `Factura`, `LineaFacturaIVA`,
  `LiquidacionImpuestoSociedades`, `FicheroPresentacion`, enums, mapeo PGC y
  transiciones de estado.
- [`contracts/`](./contracts/) — `facturas.md`, `presentaciones.md`, `is.md`,
  `README.md` (contratos HTTP de los endpoints).
- [`quickstart.md`](./quickstart.md) — guía de validación end-to-end (4
  escenarios + comandos de verificación).

---

*Next: ejecutar `/speckit.tasks` para desglose en tareas, luego implementación.*