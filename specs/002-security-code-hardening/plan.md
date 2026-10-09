# Plan de Implementación: Spec 2 — Hardening de Seguridad y Código

**Branch**: `002-security-code-hardening` | **Fecha**: 2026-10-09 | **Spec**: [spec.md](./spec.md)

**Input**: Especificación de feature en `specs/002-security-code-hardening/spec.md` (informe de auditoría de seguridad sobre `001-modulo-core-contable`).

## Resumen

Endurecer el núcleo contable de Fase 1 corrigiendo 14 hallazgos de la auditoría, agrupados en seis slices verticales: (1) secretos de configuración, (2) integridad de partida doble y trazabilidad legal, (3) aislamiento multi-tenant y RBAC, (4) rendimiento de base de datos y mitigación de DoS, (5) autenticación (CSRF + rate limiting) y (6) precisión aritmética y UI en frontend.

Enfoque técnico: actuaciones quirúrgicas sobre el código existente (FastAPI + SQLModel + Alembic en backend; Next.js 15 + React 19 + MUI v6 en frontend), sin reescribir arquitectura. Toda la lógica contable permanece en el backend; el frontend solo añade una cabecera anti-CSRF y migra controles de UI. La única dependencia nueva de backend es `slowapi` (rate limiting).

## Contexto Técnico

**Lenguaje/Versión**: Python 3.12 (backend, venv raíz `.venv`); TypeScript 5.6 / React 19 / Next.js 15 (frontend).

**Dependencias principales**: FastAPI ≥0.115, SQLModel ≥0.0.22, SQLAlchemy ≥2.0, Alembic ≥1.14, PyJWT ≥2.9, argon2-cffi ≥23.1, pydantic-settings ≥2.6; **nueva**: `slowapi` (rate limiting). Frontend: `@mui/material` 6.x.

**Almacenamiento**: SQLite (`backend/contabilidadv2.db`) con WAL, `busy_timeout` y `foreign_keys` activados al conectar (`app/db.py`). Esquema gestionado **exclusivamente** con Alembic.

**Testing**: Backend `pytest` + `httpx`/`TestClient` (BD temporal migrada en `tests/conftest.py`); frontend `vitest` + `@testing-library/react` (`frontend/tests/`).

**Plataforma destino**: Multipuesto Windows/Linux (despliegue local/pequeña empresa).

**Tipo de proyecto**: Aplicación web (backend + frontend independientes).

**Objetivos de rendimiento**: Eliminar el volcado total de tablas (`len(session.exec().all())`) usando `func.count()`; eliminar el N+1 de apuntes con `JOIN`; latencia de páginas del Diario independiente del número de apuntes.

**Restricciones**: Cumplimiento PGC España; ΣDebe = ΣHaber al asentar; asentados inmutables; borradores editables; asientos solo dentro del periodo del ejercicio abierto.

**Escala/Alcance**: Fase 1 (núcleo contable). Sin paginación distribuida ni multi-región. La concurrencia SQLite se apoya en WAL + reintento de correlativo.

## Comprobación de la Constitución

*GATE: debe pasar antes de la Fase 0 y re-evaluarse tras el diseño de Fase 1.*

| Principio | Evaluación | Justificación |
|-----------|------------|---------------|
| I. Slices Verticales Incrementales (NO NEGOCIABLE) | ✅ PASS | La spec organiza el trabajo en 6 slices autocontenidos y validables por separado (sección 3). |
| II. Separación Estricta Backend-Frontend (NO NEGOCIABLE) | ✅ PASS | Todo el cálculo contable (Δ, cuadre, correlativo, trazabilidad) queda en backend. El frontend solo añade la cabecera `X-Requested-With` y migra controles de UI, sin calcular resultados contables. |
| III. Integridad Contable Primaria (NO NEGOCIABLE) | ✅ PASS | CONT-01 exige `len(apuntes) >= 2` y Δ = 0 en `asentar`; LEGAL-01 añade inmutabilidad y trazabilidad; se refuerza el cuadre como invariante de API. |
| IV. Arquitectura Tipada Robusta | ✅ PASS | Los cambios mantienen Pydantic en E/S y OpenAPI como contrato. |
| V. Concurrencia SQLite MultiPuesto | ⚠️ ATENCIÓN (justificado) | La asignación de correlativo se mantiene con `range(5)` + captura de `IntegrityError` (apoyo en la restricción única `uq_asiento_ejercicio_numero` y en el serializado de escritor único de SQLite). El `version` de concurrencia optimista se reserva para Fase 2 (ver Clarifications). Sin violación. |

**Resultado**: Sin violaciones injustificadas. `Complexity Tracking` no aplica.

## Estructura del Proyecto

### Documentación (esta feature)

```text
specs/002-security-code-hardening/
├── plan.md              # Este archivo (/speckit.plan)
├── research.md          # Salida de la Fase 0
├── data-model.md        # Salida de la Fase 1
├── quickstart.md        # Salida de la Fase 1
├── contracts/           # Salida de la Fase 1
│   └── api-hardening.md
└── tasks.md             # Salida de /speckit.tasks (NO lo crea este comando)
```

### Código fuente (raíz del repositorio)

```text
backend/
├── alembic/
│   └── versions/
│       ├── bb1c920e98ab_tablas_iniciales_identidad_y_contable.py   # existente
│       └── <nueva>_trazabilidad_auditoria_asientos.py              # Slice 2 (NUEVA)
├── app/
│   ├── config.py            # Slice 1: JWT obligatorio + validación producción
│   ├── db.py                # Slice 5: sanitizar estado de pragmas
│   ├── main.py              # Slice 5: /health mínimo + SlowAPI + middleware CSRF
│   ├── api/
│   │   ├── deps.py          # Slice 3: empresa activa + CSRF cookie-auth
│   │   ├── auth.py          # Slice 5: rate limit login
│   │   ├── asientos.py      # Slice 4: paginación con count()
│   │   ├── cuentas.py       # Slice 4: paginación con count()
│   │   └── empresas.py      # Slice 3: import ApiError + rol admin ejercicio
│   ├── models/
│   │   └── contable.py      # Slice 2: campos de auditoría + índices
│   └── services/
│       └── asientos.py      # Slice 2/4: partida doble >= 2, correlativo, JOIN
└── tests/
    ├── conftest.py          # Slice 1: APP_JWT_SECRET de prueba
    ├── integration/
    │   └── test_security_hardening.py   # Slice 2-5 (regresión)
    └── unit/
        └── test_cuadre.py

frontend/
├── src/
│   ├── lib/
│   │   └── api.ts           # Slice 6: cabecera X-Requested-With en mutaciones
│   └── components/
│       └── FormAsiento.tsx  # Slice 6: controles MUI v6 + aritmética en céntimos
└── tests/
    └── FormAsiento.test.tsx
```

**Decisión de estructura**: Se mantiene la estructura existente de la Fase 1 (dos apps `backend/` y `frontend/`). No se crean proyectos nuevos; los cambios se localizan en los archivos anteriores.

## Seguimiento de Complejidad

> No hay violaciones de la Constitución que justificar. Sección intencionadamente vacía.
