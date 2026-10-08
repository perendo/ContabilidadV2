---

description: "Task list for Módulo Core Contable Multi-Tenant (Fase 1)"
---

# Tasks: Módulo Core Contable Multi-Tenant (Fase 1)

**Input**: Design documents from `/specs/001-modulo-core-contable/` (plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md)

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Incluidos — la constitución (R2) exige cobertura de cálculo y cuadre antes de liberar; los criterios SC-001...SC-005 son validables por tests.

**Organization**: Tasks grouped by user story (independientemente implementables y testeables). Prioridades del spec: **US1 = P1** (MVP), US2/US3 = P2, US4 = P3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3, US4 (del spec.md)
- Paths según plan.md (Option 2: `backend/` + `frontend/`)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicialización de proyectos backend y frontend

- [x] T001 Crear estructura de repositorio del plan.md (`backend/` con `app/`, `tests/`, `alembic/`, `pyproject.toml`; `frontend/` con `src/`, `tests/`, `package.json`)
- [x] T002 Inicializar proyecto Python 3.12 en `backend/pyproject.toml` con dependencias: fastapi, uvicorn, sqlmodel, sqlalchemy, alembic, pydantic-settings, pyjwt, argon2-cffi; dev: pytest, httpx
- [x] T003 [P] Inicializar proyecto Next.js 15 + TypeScript con MUI v6 en `frontend/package.json` (App Router, dependencias `@mui/material`, `@emotion/react`, `@emotion/styled`)
- [x] T004 [P] Configurar tooling: ruff + black en `backend/pyproject.toml`; eslint + prettier en `frontend/`; gestor de entorno `.env` (pydantic-settings backend, dotenv frontend)
- [x] T005 Crear app FastAPI esqueleto: `backend/app/main.py` con lifespan (pragmas), montaje de routers y `GET /api/v1/health` que devuelva `{"status":"ok","db":"wal","migrations":"current"}`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Motor de BD + migraciones + auth/contexto. NINGUNA user story puede arrancar hasta completar esta fase.

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Implementar motor SQLite en `backend/app/db.py` con `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, `PRAGMA foreign_keys=ON` (FR-001); sesión SQLModel sin `create_all` en producción (FR-021)
- [x] T007 Inicializar Alembic en `backend/alembic/` + `backend/alembic.ini` con `env.py` enlazado al metadata de los modelos (FR-021)
- [x] T008 [P] Crear modelos SQLModel `Usuario`, `Empresa`, `EmpresaUsuario` en `backend/app/models/identidad.py` con las restricciones literales de data-model.md: `username` TEXT UNIQUE no nulo 3–50 chars; `email` UNIQUE formato válido; `hashed_password` no nulo (argon2); `rol` enum `admin|contable`; `activo` BOOLEAN default `true`; `cif` 9 chars UNIQUE; `razon_social` no nulo â‰¤120; `nombre_comercial` nullable â‰¤120; `activa` default `true`; `created_at` DATETIME UTC default now; `EmpresaUsuario(usuario_id, empresa_id)` PK compuesta FK CASCADE y `rol_especifico` enum `admin|contable|lectura` nullable
- [x] T009 [P] Crear modelos SQLModel `Ejercicio`, `Cuenta`, `Asiento`, `Apunte` en `backend/app/models/contable.py` con restricciones literales: `anio` INTEGER 2000–2100 y `UNIQUE(empresa_id, anio)`; `estado` enum `abierto|cerrado` default `abierto`; `cuenta.codigo` TEXT dígitos 1–10 con `UNIQUE(ejercicio_id, codigo)`; `nivel` 1–5; `asiento.numero` INTEGER NULL `UNIQUE(ejercicio_id, numero)` y â‰¥1; `estado` enum `borrador|asentado`; `apunte.debe`/`apunte.haber` NUMERIC â‰¥0 2dp default 0; FKs con CASCADE (apunte→asiento, cuenta→ejercicio) o RESTRICT (apunte→cuenta, asiento→ejercicio)
- [x] T010 Generar revisión Alembic inicial (`backend/alembic/versions/`) que materialice data-model.md completo: entidades, índices `empresa_usuario(usuario_id)`, `empresa_usuario(empresa_id)`, `ejercicio(empresa_id)`, `cuenta(ejercicio_id, codigo)` UNIQUE, `asiento(ejercicio_id, numero)` UNIQUE, `asiento(ejercicio_id, fecha)`, `apunte(asiento_id)`, `apunte(cuenta_id)` (FR-021)
- [x] T011 [P] Implementar manejo central de errores y logging en `backend/app/api/errors.py` con respuestas `400/401/403/404/409/422` en formato `{"detail": "..."}` (ver contract README) y sin filtrar `hashed_password`
- [x] T012 [P] Implementar dependencias de autenticación y contexto en `backend/app/api/deps.py`: `get_current_user` (JWT de cookie httpOnly), cabeceras `X-Empresa-Id`/`X-Ejercicio-Id` con validación de pertenencia (usuario→empresa vía `EmpresaUsuario`; ejercicio→empresa) devolviendo 400/403 según FR-005
- [x] T013 [P] Implementar utilidades de seguridad en `backend/app/services/seguridad.py`: hash/verify argon2-cffi, generación/verificación JWT (PyJWT, expiración 43200 s), validación de contraseña mínima 8 chars (FR-017)
- [x] T014 Crear scaffolding pytest en `backend/tests/conftest.py`: BD SQLite temporal aplicada con `alembic upgrade head` (valida migraciones), cliente httpx `ASGITransport`, fixtures de usuario/empresa/ejercicio/cuentas para tests

**Checkpoint**: Foundation ready — los 4 user stories pueden implementarse (en paralelo si hay equipo)

---

## Phase 3: User Story 1 - Registro de asientos con partida doble (Priority: P1) — MVP

**Goal**: API de asientos: guardar borrador (descuadrado OK, 2..N líneas), editar borrador, asentar (exige Σ Debe = Σ Haber en servidor, correlativo atómico), Diario y detalle.

**Independent Test**: con fixtures de contexto (empresa/ejercicio/cuentas sembradas por conftest) más el arranque de `GET /api/v1/health` (no necesita US2/US3): crear borrador descuadrado → 201 `numero:null`; asentar → 422 con `Δ`; cuadrar vía PUT y asentar → 200 con `numero:1`; PUT sobre asentado → 409. El e2e por API público completo (creando empresa/ejercicio/cuentas vía endpoints) se cierra cuando existan US2/US3.

### Tests for User Story 1 (requeridos por constitución R2)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T015 [P] [US1] Tests unitarios de cuadre N-líneas en `backend/tests/unit/test_cuadre.py`: Σ Debe=Σ Haber sobre conjunto (no por pares); descuadrado rechazado al asentar; línea mixta o en ceros rechazada (422); mínimo 2 apuntes; importes 2dp con Decimal (FR-007/FR-020)
- [x] T016 [P] [US1] Tests de integración de asientos en `backend/tests/integration/test_asientos.py`: borrador 201 `numero:null`; asentar descuadrado 422; cuadrar+asentar 200 correlativo; PUT asentado 409; ejercicio cerrado bloquea guardar/asentar (409); correlativo independiente por ejercicio (FR-007...010, SC-002/003/004)
- [x] T016b [P] [US1] Test de concurrencia WAL en `backend/tests/integration/test_concurrency.py`: N escritores en paralelo asentando asientos cuadrados + lecturas simultáneas del Diario; tolerancia de errores "database is locked" = 0 y números correlativos 1..N sin duplicados (SC-005)

### Implementation for User Story 1

- [x] T017 [P] [US1] Implementar servicio contable en `backend/app/services/asientos.py`: validación de cuadre en Decimal, transición borrador→asentado, correlativo `MAX(numero)+1` por ejercicio dentro de la transacción con reintento ante colisión UNIQUE, y transaccionalidad atómica asiento+apuntes (FR-007/009/010)
- [x] T018 [P] [US1] Crear esquemas Pydantic de asientos en `backend/app/schemas/asientos.py`: request (fecha `YYYY-MM-DD` dentro del ejercicio, concepto â‰¤300, apuntes 2..N con `debe`/`haber` Decimal â‰¥0 2dp), response incluye `total_debe`/`total_haber`/`cuenta_codigo` y `Δ` en errores de descuadre
- [x] T019 [US1] Implementar router de asientos en `backend/app/api/asientos.py` según contracts/contable.md: `POST /asientos` (borrador), `PUT /asientos/{id}` (solo borrador), `POST /asientos/{id}/asentar`, `GET /asientos` (Diario asentados paginado/filtrable), `GET /asientos/borradores`, `GET /asientos/{id}` (detalle con apuntes); bloqueo por ejercicio cerrado (409); sin PUT/DELETE sobre asentados (inmutabilidad, Constitución III)
- [x] T020 [US1] Registrar router de asientos en `backend/app/main.py` y validar respuesta de descuadre 422 con `Δ` según contract

**Checkpoint**: At this point, User Story 1 es funcional y testeable de forma independiente (fixtures + health)

---

## Phase 4: User Story 2 - Gestión de Usuarios, Empresas y Ejercicios (Priority: P2)

**Goal**: Autenticación (login/me/logout con cookie httpOnly) y gestión de empresas + ejercicios con aislamiento por contexto.

**Independent Test**: dos usuarios creados (seed), cada uno crea su empresa y un ejercicio; el usuario A obteniendo `X-Empresa-Id` de B recibe 403; al crear una empresa, `EmpresaUsuario` asocia al creador; anio duplicado en la misma empresa → 409.

### Tests for User Story 2

- [x] T021 [P] [US2] Tests unitarios de seguridad en `backend/tests/unit/test_seguridad.py`: hash argon2 (no plaintext), JWT expiración, contraseña <8 rechazada con 422 (FR-017)
- [x] T022 [P] [US2] Tests de integración de identidad en `backend/tests/integration/test_identidad.py`: login 200 / credenciales inválidas 401 / usuario inactivo 401; `POST /empresas` 201 crea `EmpresaUsuario` rol admin; rol `contable` en `POST /empresas` → 403 (FR-003b); `GET /empresas` solo las propias; contexto ajeno 403; `POST /ejercicios` 201 `abierto` y anio duplicado 409 (FR-003/004/005/FR-003b, US2 acceptance)

### Implementation for User Story 2

- [x] T023 [P] [US2] Crear esquemas Pydantic de identidad en `backend/app/schemas/identidad.py`: login, perfil (`empresas: [ids]`), empresa (CIF validado, `razon_social`, `nombre_comercial`), ejercicio (anio rangos 2000–2100, fechas, estado) según contracts/identidad.md y auth.md
- [x] T024 [P] [US2] Implementar servicios de identidad en `backend/app/services/identidad.py`: creación de empresa + vínculo `EmpresaUsuario(admin)`, apertura de ejercicio con `fecha_inicio`/`fecha_fin` del anio y estado `abierto`
- [x] T025 [US2] Implementar endpoints de auth en `backend/app/api/auth.py`: `POST /auth/login` (verifica argon2, emite JWT en cookie httpOnly SameSite=Lax), `GET /auth/me`, `POST /auth/logout` (borra cookie) — contratos en contracts/auth.md
- [x] T026 [US2] Implementar endpoints de empresas/ejercicios en `backend/app/api/empresas.py`: `GET/POST /empresas`, `GET/POST /ejercicios` con validación de pertenencia 403 y unicidades 409; `POST /empresas` restringida a rol `admin` (403 si `contable`, FR-003b) — contracts/identidad.md
- [x] T027 [US2] Crear script de seed `backend/app/seed.py` que cree usuarios iniciales (admin y contable) con contraseñas â‰¥8 chars hasheadas con argon2 y usuarios de prueba para S1 del quickstart

**Checkpoint**: At this point, User Stories 1 AND 2 deben funcionar de forma independiente

---

## Phase 5: User Story 3 - Plan de Cuentas por Ejercicio (Priority: P2)

**Goal**: Consulta/búsqueda y alta de cuentas PGC aisladas por ejercicio, código único por ejercicio.

**Independent Test**: crear el mismo código `57200001` en dos ejercicios de empresas distintas → 201 ambos; repetir en el mismo ejercicio → 409; `GET /cuentas` devuelve solo cuentas del `ejercicio_id` activo.

### Tests for User Story 3

- [x] T028 [P] [US3] Tests de integración de cuentas en `backend/tests/integration/test_cuentas.py`: POST 201; código duplicado mismo ejercicio 409; mismo código otro ejercicio 201; filtrado estricto por ejercicio activo; creación en ejercicio cerrado 409 (FR-006/014, US3 acceptance)

### Implementation for User Story 3

- [x] T029 [P] [US3] Crear esquemas Pydantic de cuentas en `backend/app/schemas/cuentas.py`: `codigo` (solo dígitos, 1–10 chars), `nombre` â‰¤200, `nivel` 1–5; response con `ejercicio_id` (data-model.md)
- [x] T030 [US3] Implementar router de cuentas en `backend/app/api/cuentas.py`: `GET /cuentas` (filtro estricto por `ejercicio_id` del contexto; query `query`/`nivel`/`offset`/`limit` max 200) y `POST /cuentas` (409 si ejercicio `cerrado` o código duplicado; 422 formato) — contracts/contable.md

**Checkpoint**: Todas las user stories backend ya son funcionales de forma independiente

---

## Phase 6: User Story 4 - Interfaz Multipuesto con Selector de Contexto (Priority: P3)

**Goal**: Frontend Next.js con Material Design 3 (MUI v6): selector global Empresa/Ejercicio persistido en cookies, Plan de Cuentas, formulario de asientos (borrador/asentar, Δ en tiempo real) y Diario expandible con borradores.

**Independent Test**: cambiar el selector de ejercicio recarga Plan de Cuentas y Diario del nuevo contexto; con asiento descuadrado el botón **asentar** está deshabilitado (el backend también rechaza 422); dos pestañas en contextos distintos no se interfieren.

### Tests for User Story 4

- [x] T031 [P] [US4] Tests de componente en `frontend/tests/FormAsiento.test.tsx` (vitest): cálculo de Δ en tiempo real sobre N líneas; botón **asentar** bloqueado si Δâ‰ 0 o ejercicio cerrado; permitido guardar borrador con Δâ‰ 0 (FR-012/020)

### Implementation for User Story 4

- [x] T032 [P] [US4] Configurar tema Material Design 3 en `frontend/src/lib/theme.ts` (createTheme MUI v6 con tokens de color/tipografía/elevación, scheme claro/oscuro) y `ThemeProvider` en el layout de App Router (FR-015/016)
- [x] T033 [P] [US4] Implementar cliente API con contexto en `frontend/src/lib/api.ts`: cookies `empresa_id`/`ejercicio_id` (no httpOnly, SameSite=Lax) como fuente de verdad, inyección de cabeceras `X-Empresa-Id`/`X-Ejercicio-Id`, manejo de estados loading/error; toda carga posterior al login se dispara de forma asíncrona en segundo plano sin bloquear la interfaz (FR-011/011b/019)
- [x] T033b [P] [US4] Implementar página de login obligatoria en `frontend/src/app/login/page.tsx`: única pantalla bloqueante del arranque (llama `POST /auth/login`, guarda cookie httpOnly, redirige al dashboard al autenticarse); solo esta pantalla espera respuesta "sobre la marcha" (FR-011b)
- [x] T034 [P] [US4] Implementar selector global Empresa/Ejercicio en `frontend/src/components/ContextSelector.tsx` (barra superior, desplegables, persiste en cookies, usa `GET /empresas` y `GET /ejercicios`); al entrar preselecciona la última empresa/ejercicio de la sesión anterior y solo solicita selección si no existe contexto previo (FR-011)
- [x] T035 [P] [US4] Implementar vista Plan de Cuentas en `frontend/src/components/PlanCuentas.tsx`: búsqueda/lista del ejercicio activo y alta de cuenta (skeletons y empty state, snackbar de errores) (FR-019)
- [x] T036 [P] [US4] Implementar formulario de asientos en `frontend/src/components/FormAsiento.tsx`: filas dinámicas 2..N con navegación por teclado, Δ en tiempo real, acciones **guardar borrador** y **asentar** (bloqueado si Δâ‰ 0 o cerrado), loading/error M3 (FR-012/020)
- [x] T037 [P] [US4] Implementar vista Diario en `frontend/src/components/Diario.tsx`: tabla paginada/filtrable de asentados con filas expandibles vía `GET /asientos/{id}` y pestaña de borradores (`GET /asientos/borradores`) con reapertura para editar/asentar (FR-013/018/019)
- [x] T038 [US4] Montar rutas de App Router en `frontend/src/app/`: dashboard con `ContextSelector` + páginas Plan de Cuentas, Introducción de Asientos y Diario (depende de T033–T037)

**Checkpoint**: Los 4 user stories son funcionales; el e2e completo (formulario → Diario) es demostrable

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validación final, puerta de salida y hardening. **Fase 1 no se cierra sin el Libro Mayor sencillo** (constitución, gate note): se registrará como slice pendiente de Fase 1 (no de Fase 2) junto a este package.

- [x] T039 [P] Ejecutar quickstart.md end-to-end (S1–S6: aislamiento, cuentas, borrador→asentado multi-línea, cerrado, concurrencia WAL, migraciones) y fijar cualquier desviación en `backend/tests/` o `frontend/tests/`
- [x] T040 Ejecutar suites completas `python -m pytest backend/tests -q` y `cd frontend && npm test` hasta pase total (SC-001...SC-005, puerta de salida R2)
- [x] T041 [P] Hardening de seguridad: revisar que ninguna response expone `hashed_password`, cookies con flags correctos (httpOnly, SameSite), y códigos 4xx sin leaks de detalles internos
- [x] T042 Registrar gate note final en `specs/001-modulo-core-contable/plan.md`: confirmar Libro Mayor sencillo como slice pendiente de Fase 1 y actualizar estado a "Fase 1 core completada" tras validación

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias — arranca ya
- **Foundational (Phase 2)**: Depende de Setup — BLOQUEA todos los user stories
- **User Stories (Phase 3+)**: Dependen de Foundational
  - US1 (P1) es el MVP: tras ella se puede validar el núcleo contable con fixtures
  - US2/US3 (P2) habilitan el e2e por API público de US1
  - US4 (P3) consume la API completa (US1+US2+US3)
- **Polish (Final Phase)**: Depende de que las stories deseadas estén completas

### User Story Dependencies

- **US1 (P1)**: Tras Foundational; los tests usan fixtures de contexto (conftest T014) y no requieren US2/US3. El e2e vía API público se cierra al existir US2+US3.
- **US2 (P2)**: Tras Foundational (auth/contexto en deps T012/T013). Independiente de US1.
- **US3 (P2)**: Tras Foundational (contexto + ejercicio). Independiente.
- **US4 (P3)**: Requiere la API de US1, US2, US3 (cliente `api.ts` + selectores consumen esos endpoints).

### Within Each User Story

- Tests (incluidos por constitución) se escriben y fallan ANTES de la implementación
- Models antes que services; services antes que endpoints; integración al final
- Story completa antes de pasar a la siguiente prioridad

### Parallel Opportunities

- T003–T005 (Setup [P]) en paralelo; T008–T013 (Foundational [P]) en paralelo
- Tras Foundational: US1/US2/US3 en paralelo (equipos distintos)
- Dentro de cada story: los tests para cada story en paralelo; modelos/schemas [P] en paralelo
- En US4: T032–T037 (componentes y tema) en paralelo; T038 las integra

---

## Parallel Example: User Story 1

```bash
# Tests de US1 juntos (fallan antes de implementar):
Task: "Tests unitarios de cuadre N-líneas en backend/tests/unit/test_cuadre.py"
Task: "Tests de integración de asientos en backend/tests/integration/test_asientos.py"

# Implementación de US1 en paralelo (archivos distintos):
Task: "Servicio contable en backend/app/services/asientos.py"
Task: "Esquemas Pydantic en backend/app/schemas/asientos.py"

# Tras T017/T018, secuencial:
Task: "Router en backend/app/api/asientos.py (depende de T017, T018)"
Task: "Registrar router en backend/app/main.py (depende de T019)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (API de asientos con fixtures)
4. **STOP and VALIDATE**: `python -m pytest backend/tests -q` (cuadre, transición, correlativo, cerrado)
5. Deploy/demo si procede

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. **US1** → test independiente → MVP (núcleo contable)
3. **US2** → test independiente → el e2e de US1 por API público se cierra
4. **US3** → test independiente → plan de cuentas por ejercicio
5. **US4** → interfaz MD3 multipuesto → demo completa
6. **Polish** → quickstart S1–S6 + suites + hardening + gate note (Libro Mayor → Fase 1 slice)

### Parallel Team Strategy

1. Equipo completo hace Setup + Foundational en conjunto
2. Tras Foundational:
   - Dev A: US1 (core contable, MVP)
   - Dev B: US2 (identidad)
   - Dev C: US3 (cuentas) — y luego US4 completada por uno de ellos
3. US4 integra lo que han soltado A/B/C (requiere API estable)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] maps to spec.md user stories (US1=P1, US2/US3=P2, US4=P3)
- Construcción de esquema SIEMPRE vía Alembic (FR-021): cada cambio de modelo → revisión `alembic revision --autogenerate`
- Verificar que los tests fallan antes de implementar
- Commit tras cada tarea o grupo lógico
- Parar en cada checkpoint para validar la story independientemente
- Evitar: tareas vagas, conflictos de mismo archivo, dependencias cruzadas que rompan la independencia
- Suites automáticas en `quickstart.md` Â§Automatización como puerta de salida (R2)

