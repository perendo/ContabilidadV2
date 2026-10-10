---

description: "Task list for Libro Mayor y Balance de Sumas y Saldos (Spec 3)"
---

# Tasks: Libro Mayor y Balance de Sumas y Saldos

**Input**: Design documents from `/specs/003-libro-mayor-balance/` (plan.md, spec.md, data-model.md, contracts/informes.md, research.md, quickstart.md)

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Incluidos — la constitución (R2) exige cobertura de cálculo y cuadre antes de liberar; los criterios SC-001...SC-006 y el "Independent Test" de cada historia son validables por tests (pytest + vitest).

**Organization**: Tareas agrupadas por user story, independientemente implementables y testeables. Prioridades del spec: **US1 = P1 (MVP)** y **US2 = P1**, **US3 = P2**. Sin cambios de esquema (no hay migración Alembic).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3 (del spec.md)
- Paths según plan.md (aplicación web: `backend/` + `frontend/`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencia de PDF y registro del router de informes

- [ ] T001 Añadir la dependencia `reportlab>=4.0` a `backend/pyproject.toml` e instalar con `..\.venv\Scripts\python.exe -m pip install -e .` (desde `backend/`), verificando que el import funciona
- [ ] T002 Crear el esqueleto de router en `backend/app/api/informes.py` (`APIRouter(prefix="/informes", tags=["informes"])`, sin endpoints aún) y registrarlo en `backend/app/main.py` con `app.include_router(informes_router, prefix="/api/v1")`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Esquemas de respuesta y primitivas de agregación compartidas por US1 y US2. NINGUNA user story puede arrancar hasta completar esta fase.

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Definir los schemas Pydantic de respuesta en `backend/app/schemas/informes.py` con los campos y constraints exactos de data-model.md: `CuentaRef{codigo,nombre,nivel}`, `MovimientoMayor{fecha:date,numero:int,asiento_id:int,concepto:str,debe:Decimal(2),haber:Decimal(2),saldo:Decimal(2)}`, `FilaBalance{codigo,nombre,nivel,suma_debe,suma_haber,saldo_deudor,saldo_acreedor}` (Decimal 2dp, `saldo_deudor=max(saldo,0)`, `saldo_acreedor=max(-saldo,0)`), `FilaMayorCuenta{codigo,nombre,nivel,suma_debe,suma_haber,saldo,saldo_tipo}` con `saldo_tipo ∈ {"deudor","acreedor","cero"}`, `MayorCuentaOut{cuenta,desde,hasta,saldo_inicial,movimientos,total_debe,total_haber,saldo_final}`, `MayorGlobalOut{ejercicio_id,desde,hasta,cuentas}`, `BalanceOut{ejercicio_id,desde,hasta,filas,total_debe,total_haber,total_saldo_deudor,total_saldo_acreedor,cuadra:bool}`
- [ ] T004 [P] Implementar las primitivas de agregación compartidas en `backend/app/services/informes.py`: `sumas_por_cuenta(session, ejercicio_id, desde, hasta)` (consulta `GROUP BY apunte.cuenta_id` con `JOIN asiento`, `estado='asentado'` y rango `fecha` opcional, importes en `Decimal`), `propagar_jerarquia(cuentas, sumas)` (acumulado de suma_debe/suma_haber por prefijo de `codigo`, incluyendo la propia cuenta) y `clasificar_saldo(saldo)` (`deudor`/`acreedor`/`cero`). Sin endpoints; solo lógica reutilizable.

**Checkpoint**: Foundation ready — US1 y US2 pueden implementarse (en paralelo si hay equipo)

---

## Phase 3: User Story 1 - Consultar el Libro Mayor (Priority: P1) — MVP

**Goal**: Libro Mayor del ejercicio activo en ambos modos: (a) mayor de una cuenta por código/nombre con apuntes asentados en orden cronológico y saldo acumulado, y (b) listado global de cuentas con movimiento navegable al detalle. Con filtro de fechas desde/hasta.

**Independent Test**: con una cuenta con varios apuntes asentados, abrir su Mayor y comprobar que el `saldo_final` coincide con el saldo de esa cuenta en el Balance; probar `saldo_inicial` con `desde`, cuenta de grupo que agrega subcuentas, cuenta sin apuntes (estado vacío) y listado global (US1 escenarios 1-4).

### Tests for User Story 1 (requeridos por constitución R2)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T005 [US1] Tests de integración del Mayor en `backend/tests/integration/test_informes.py`: cuenta hoja con movimientos ordenados (fecha, numero) y saldo acumulado correcto; `saldo_inicial` con `desde` (FR-007); cuenta de grupo (nivel 1-3) agrega subcuentas por prefijo (FR-002); cuenta sin apuntes → `200` con `movimientos: []` y totales `"0.00"`; `GET /informes/mayor/cuentas` lista solo cuentas con movimiento; contexto de ejercicio ajeno → `403` (FR-008, SC-006)

### Implementation for User Story 1

- [ ] T006 [US1] Implementar `mayor_cuenta(session, ejercicio_id, codigo, desde, hasta)` en `backend/app/services/informes.py`: resolver la cuenta del ejercicio (404 si no existe), calcular el subárbol por prefijo de código, obtener `saldo_inicial` (`Σ(debe−haber)` con `fecha < desde`), listar movimientos ordenados por `fecha`, `numero`, `apunte.id` y acumular el saldo línea a línea (FR-001/003/007)
- [ ] T007 [US1] Implementar `mayor_cuentas(session, ejercicio_id, desde, hasta)` en `backend/app/services/informes.py`: listado de cuentas con movimiento ordenado por `codigo`, con `suma_debe`, `suma_haber`, `saldo` y `saldo_tipo`; incluir compensadas (saldo 0), omitir sin movimiento (FR-002)
- [ ] T008 [US1] Implementar los endpoints `GET /informes/mayor` (query `cuenta` obligatorio, `desde`, `hasta`) y `GET /informes/mayor/cuentas` (query `desde`, `hasta`) en `backend/app/api/informes.py` usando `EjercicioDep`+`SessionDep` y `mayor_cuenta`/`mayor_cuentas`; devolver `422` si `desde > hasta`, `404` si la cuenta no existe (contracts/informes.md §1-2)
- [ ] T009 [US1] Añadir en `frontend/src/lib/api.ts` los tipos (`MayorCuenta`, `MovimientoMayor`, `MayorGlobal`, `FilaMayorCuenta`) y los métodos `api.mayor(cuenta, {desde, hasta})` y `api.mayorCuentas({desde, hasta})` reutilizando el helper de cabeceras de contexto existente
- [ ] T010 [US1] Crear el componente `Mayor` en `frontend/src/components/Mayor.tsx`: selector de cuenta por código/nombre, filtros `desde`/`hasta`, tabla de movimientos (Fecha, Nº, Concepto, Debe, Haber, Saldo acumulado) y listado global con navegación al detalle; estados de carga, vacío y error con MUI v6 (FR-011)
- [ ] T011 [US1] Crear la página `frontend/src/app/mayor/page.tsx` (client component con `Suspense`) montando el componente `Mayor`
- [ ] T012 [US1] Añadir la tarjeta "Libro Mayor" (href `/mayor`) al panel en `frontend/src/app/page.tsx`, siguiendo el patrón de `accesos`
- [ ] T013 [US1] Test de frontend del Mayor en `frontend/tests/Informes.test.tsx`: render de la tabla con el saldo acumulado, estado vacío informativo y listado global

**Checkpoint**: El Libro Mayor es funcional y testeable de forma independiente (cuenta + listado global)

---

## Phase 4: User Story 2 - Generar el Balance de Sumas y Saldos (Priority: P1)

**Goal**: Balance de Sumas y Saldos del ejercicio activo con agregación jerárquica del PGC (niveles 1-3 acumulan sus subcuentas), cuatro columnas clásicas (Suma Debe, Suma Haber, Saldo Deudor, Saldo Acreedor) y totales generales con cuadre visible.

**Independent Test**: registrar asientos asentados en varias cuentas y verificar sumas por cuenta, clasificación de saldos, totales generales `ΣDebe = ΣHaber` (`cuadra: true`) y exclusión de borradores (US2 escenarios 1-2).

### Tests for User Story 2 (requeridos por constitución R2)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [US2] Tests de integración del Balance en `backend/tests/integration/test_informes.py`: cuatro columnas con saldo clasificado en una sola columna y `cuadra: true` (FR-004/005, SC-002); exclusión total de asientos `borrador` (FR-006, SC-003); cuenta compensada (saldo 0 con movimiento) incluida y cuenta sin movimiento omitida; agregación jerárquica por prefijo (grupo/subgrupo = acumulado de subárbol); precisión de dos decimales sin pérdida de céntimos (FR-012)

### Implementation for User Story 2

- [ ] T015 [US2] Implementar `balance(session, ejercicio_id, desde, hasta)` en `backend/app/services/informes.py`: derivar las filas jerárquicas ordenadas por `codigo` (niveles 1-3 con acumulado de subárbol, luego cuentas de detalle), clasificar el saldo en `saldo_deudor`/`saldo_acreedor`, totalizar `total_debe`/`total_haber`/`total_saldo_deudor`/`total_saldo_acreedor` y calcular `cuadra = (total_debe == total_haber)` (FR-004/005)
- [ ] T016 [US2] Implementar el endpoint `GET /informes/balance` (query `desde`, `hasta`) en `backend/app/api/informes.py` usando `EjercicioDep`+`SessionDep` y `balance`; `422` si `desde > hasta` (contracts/informes.md §3)
- [ ] T017 [US2] Añadir en `frontend/src/lib/api.ts` los tipos (`Balance`, `FilaBalance`) y el método `api.balance({desde, hasta})`
- [ ] T018 [US2] Crear el componente `Balance` en `frontend/src/components/Balance.tsx`: tabla de cuatro columnas (Suma Debe, Suma Haber, Saldo Deudor, Saldo Acreedor), indentación/nombre por nivel y código, fila de totales y aviso visible si `cuadra === false`; filtros `desde`/`hasta`; estados de carga, vacío y error (FR-004/005/011)
- [ ] T019 [US2] Crear la página `frontend/src/app/balance/page.tsx` (client component con `Suspense`) montando el componente `Balance`
- [ ] T020 [US2] Añadir la tarjeta "Balance de Sumas y Saldos" (href `/balance`) al panel en `frontend/src/app/page.tsx`
- [ ] T021 [US2] Test de frontend del Balance en `frontend/tests/Informes.test.tsx`: render de las cuatro columnas, jerarquía con totales y estado vacío

**Checkpoint**: US1 y US2 son funcionales e independientemente testeables; el saldo del Mayor de una cuenta coincide con su saldo en el Balance (SC-001)

---

## Phase 5: User Story 3 - Filtrar por periodo y exportar los informes (Priority: P2)

**Goal**: Acotar ambos informes a un rango de fechas y exportarlos a CSV y PDF, con un botón independiente por formato, incluyendo encabezado identificativo (razón social + CIF, ejercicio, rango de fechas, fecha/hora de generación).

**Independent Test**: generar un informe con un rango de fechas, exportarlo a CSV y a PDF y comprobar que el contenido descargado reproduce exactamente lo mostrado (SC-005; US3 escenarios 1-2).

### Tests for User Story 3 (requeridos por constitución R2)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T022 [US3] Tests de integración de exportación en `backend/tests/integration/test_informes.py`: CSV con separador `;`, decimal coma, BOM UTF-8 y bloque de encabezado + totales (FR-010/014); PDF con `Content-Type: application/pdf` y encabezado identificativo; `formato` inválido → `422`; el filtro `desde`/`hasta` afecta a Mayor y Balance y coincide con la respuesta JSON de pantalla (SC-005)

### Implementation for User Story 3

- [ ] T023 [US3] Implementar el helper de encabezado y `exportar_csv(informe)` en `backend/app/services/informes.py`: BOM UTF-8, separador `;`, decimal coma (`f"{v:.2f}".replace(".", ",")`), encabezado con razón social + CIF, ejercicio (año), rango de fechas, título y fecha/hora de generación, seguido de la tabla y la fila de totales (FR-010/014, R2)
- [ ] T024 [US3] Implementar `exportar_pdf(informe)` en `backend/app/services/informes.py` con ReportLab (A4, Helvetica, `SimpleDocTemplate` + `Table`): encabezado identificativo (FR-014) y tabla con las mismas columnas/filas que la pantalla (R1)
- [ ] T025 [US3] Implementar los endpoints `GET /informes/mayor/export` y `GET /informes/balance/export` (query `formato ∈ {csv,pdf}`; `cuenta` obligatorio en el mayor; `desde`/`hasta`) en `backend/app/api/informes.py`, devolviendo `Content-Type` y `Content-Disposition` (attachment) según contracts/informes.md §4; `422` si `formato` no es `csv`/`pdf`
- [ ] T026 [US3] Añadir en `frontend/src/lib/api.ts` el helper `api.descargarInforme(tipo, formato, params)` que hace `fetch` con las cabeceras `X-Empresa-Id`/`X-Ejercicio-Id` y credenciales, obtiene el `Blob` y el nombre de `Content-Disposition`, y dispara la descarga (R7)
- [ ] T027 [US3] Añadir botones independientes "Exportar CSV" y "Exportar PDF" en `frontend/src/components/Mayor.tsx` (usando `api.descargarInforme` con el rango de fechas y la cuenta activos)
- [ ] T028 [US3] Añadir botones independientes "Exportar CSV" y "Exportar PDF" en `frontend/src/components/Balance.tsx` (usando `api.descargarInforme` con el rango de fechas activo)
- [ ] T029 [US3] Test de frontend de exportación en `frontend/tests/Informes.test.tsx`: cada botón (CSV y PDF) dispara la descarga con el `formato` correcto

**Checkpoint**: Las tres historias funcionan de forma independiente; la exportación reproduce la pantalla

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verificación end-to-end, rendimiento, precisión y edge cases

- [ ] T030 [P] Recorrer y validar la guía `specs/003-libro-mayor-balance/quickstart.md` (REST + UI) y marcar las casillas de criterios de aceptación
- [ ] T031 Ejecutar backend desde `backend/`: `..\.venv\Scripts\python.exe -m ruff check app tests` y `..\.venv\Scripts\python.exe -m pytest -q`; corregir hasta dejar todo en verde
- [ ] T032 Ejecutar frontend desde `frontend/`: `npm run lint`, `npx tsc --noEmit` y `npm run build`; corregir hasta dejar todo sin errores
- [ ] T033 [P] Verificar SC-004 (10.000 asientos asentados por ejercicio generan ambos informes en < 3 s) y FR-012 (suma exacta en `Decimal`, sin pérdida de céntimos)
- [ ] T034 [P] Verificar edge cases: ejercicio `cerrado` consultable en solo lectura, ejercicio sin asentados (estados vacíos y `cuadra: true`), y distinción entre cuenta compensada (incluida) y cuenta sin movimiento (omitida)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — puede empezar de inmediato
- **Foundational (Phase 2)**: Depende de Setup — BLOQUEA todas las user stories
- **User Stories (Phase 3+)**: dependen de Foundational
  - US1 (P1) y US2 (P1) pueden ir en paralelo (equipos distintos), aunque comparten `services/informes.py`
  - US3 (P2) depende de que existan los informes base (parte de las respuestas y de los componentes de US1/US2)
- **Polish (Phase 6)**: depende de completar las historias deseadas

### User Story Dependencies

- **US1 (P1, MVP)**: arranca tras Foundational; sin dependencias de otras historias
- **US2 (P1)**: arranca tras Foundational; reutiliza las primitivas de T004 pero su endpoint/UI son independientes de US1
- **US3 (P2)**: arranca tras Foundational; su exportación reutiliza la lógica de `mayor_*` (T006/T007) y `balance` (T015) y edita los componentes de T010/T018

### Within Each User Story

- Tests (T005/T014/T022) se escriben y FALLAN antes de implementar
- Servicios antes que endpoints; endpoints antes que UI
- UI antes que el test frontend correspondiente

### Parallel Opportunities

- T003 y T004 (Phase 2) en paralelo
- T001 y T002: T002 puede adelantarse, pero T001 (dependencia) conviene resolverla primero
- US1 y US2 pueden desarrollarse en paralelo una vez completada la Fase 2 (ojo: T006/T007 y T015 editan el mismo `services/informes.py`, por lo que requieren coordinación/secuencia de merge)
- Los tests backend de distintas historias comparten `test_informes.py`: no paralelizar escritura del mismo archivo
- T030, T033, T034 en paralelo en la fase Polish

---

## Parallel Example: User Story 1

```bash
# Foundational en paralelo (archivos distintos):
Task: "Definir schemas de respuesta en backend/app/schemas/informes.py"
Task: "Implementar primitivas de agregación en backend/app/services/informes.py"

# US1 — UI en paralelo con la página (tras existir el componente):
Task: "Crear componente Mayor en frontend/src/components/Mayor.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Completar Fase 1 (Setup)
2. Completar Fase 2 (Foundational) — CRÍTICO
3. Completar Fase 3 (US1 — Libro Mayor)
4. **PARAR y VALIDAR**: probar US1 de forma independiente (cuenta + listado global + filtro de fechas)
5. Demostrar/desplegar si está listo

### Incremental Delivery

1. Setup + Foundational → base lista
2. US1 → validar → demo (MVP)
3. US2 → validar el cuadre y la jerarquía del Balance → demo
4. US3 → validar exportación CSV/PDF → demo
5. Polish → rendimiento, edge cases y verificación end-to-end

### Parallel Team Strategy

Con varios desarrolladores: completar Setup + Foundational en equipo y luego repartir US1 (Mayor) y US2 (Balance); US3 en cuanto US1/US2 estén listos (exportación).

---

## Notes

- [P] = archivos distintos y sin dependencias
- [Story] mapea la tarea a su user story para trazabilidad
- **Sin migración Alembic**: la feature es de solo lectura; no modificar el esquema
- Toda agregación y generación CSV/PDF permanece en el backend (Constitución II)
- Verificar que los tests fallan antes de implementar
- Hacer commit tras cada tarea o grupo lógico
