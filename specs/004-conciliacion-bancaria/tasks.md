---
description: "Lista de tareas para Conciliación Bancaria con Auto-Matching (Spec 4)"
---

# Tareas: Conciliación Bancaria con Auto-Matching

**Input**: Documentos de diseño de `/specs/004-conciliacion-bancaria/` (plan.md, spec.md)

**Prerrequisitos**: plan.md, spec.md

**Tests**: Incluidos — la constitución (R2) exige tests de parsing, matching y aislamiento multi-tenant antes de liberar; criterios SC-01..SC-19 e "Independent Test" de cada historia validables por tests (pytest + vitest).

**Organización**: Tareas agrupadas por user story, independientemente implementables y testeables. Prioridades del spec: **US1 = P1 (MVP)**, **US2 = P1**, **US3 = P1**, **US4 = P1**, **US5 = P2**. Con migración Alembic (2 tablas nuevas).

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: Ejecutable en paralelo (archivos distintos, sin dependencias)
- **[Story]**: A qué user story pertenece (US1, US2, US3, US4, US5)
- Rutas exactas en cada descripción
- **Estado real** (actualizado al completar el frontend, oct 2026): `[x]` hecho · `[x]*` hecho con divergencias/notas (ver detalle inline) · `[ ]` pendiente

---

## Phase 1: Setup (Infraestructura Compartida)

**Propósito**: Dependencias nuevas y registro del router de banco

- [x] T001 Añadir dependencias `openpyxl>=3.1`, `pandas>=2.2`, `pybank43>=0.1` a `backend/pyproject.toml` e instalar con `..\.venv\Scripts\python.exe -m pip install -e .` (desde `backend/`), verificando que los imports funcionan
  - *Nota*: `openpyxl>=3.1` y `pandas>=2.2` añadidos e instalados con `pip install -e .`; `pybank43` NO se añadió — el parser CSB es propio (rama permitida en T006) y no requiere la dependencia.
- [x] T002 Crear esqueleto de router en `backend/app/api/banco.py` (`APIRouter(prefix="/banco", tags=["banco"])`, sin endpoints aún) y registrarlo en `backend/app/main.py` con `app.include_router(banco_router, prefix="/api/v1")`

---

## Phase 2: Foundational (Prerrequisitos Bloqueantes)

**Propósito**: Migración Alembic, modelos ORM, schemas Pydantic y servicio base de parsing compartidos por US1–US4. NINGUNA user story puede arrancar hasta completar esta fase.

**CRÍTICO**: No puede empezar trabajo de user story hasta completar esta fase

- [x] T003 [P] Definir modelos ORM `MovimientoBanco` y `ReglaBanco` en `backend/app/models/contable.py` con campos exactos de data-model.md (ver spec §Modelo de Datos): `fecha_operacion`, `fecha_valor`, `concepto`, `referencia`, `referencia_2`, `importe` (Decimal 19,2), `saldo`, `divisa` (default EUR), `codigo_banco`, `numero_documento`, `info_adicional`, `procesado` (bool, default False), `asiento_id` (FK nullable), `regla_id` (FK nullable), `hash_unicidad` (str 64, unique), `origen_archivo` (str 20: excel|csv|csb); `ReglaBanco` con `empresa_id`, `nombre`, `patron_regex`, `cuenta_debe`, `cuenta_haber`, `importe_fijo` (nullable), `porcentaje` (nullable), `prioridad` (int default 0), `auto_asentar` (bool default False), `activa` (bool default True)
- [x] T004 Generar migración Alembic: `..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "add movimiento_banco y regla_banco"`; revisar y corregir (`sa.String`, índices `ix_*` a mano), luego `..\.venv\Scripts\python.exe -m alembic upgrade head`
  - *Nota*: migración `6b69941fa552` (`add movimiento_banco, regla_banco, log_procesamiento_banco, asiento origen regla_id`); revisada a mano y aplicada.
- [x] T005 [P] Definir schemas Pydantic de request/response en `backend/app/schemas/banco.py`: `MovimientoBancoIn` (campos de importación), `MovimientoBancoOut` (con `from_attributes=True`), `ReglaBancoIn` (patron_regex, cuenta_debe, cuenta_haber, importe_fijo?, porcentaje?, prioridad?, auto_asentar?), `ReglaBancoOut`, `ImportRequest` (file UploadFile), `ImportResponse` (importados, duplicados, errores, formato_detectado), `ProcesarResponse` (creados, pendientes, fallidos, log), `SimularResponse` (matches[])
  - *Nota*: además `MatchItem`, `LogProcesamientoOut` y `MarcarProcesadoRequest` (US4 manual).
- [x] T006 [P] Implementar parsers base en `backend/app/services/banco.py`: `parse_excel_santander(file_bytes)` (busca fila header "Fecha Operación", salta 7 filas cabecera, mapea 12 columnas, convierte importe float→Decimal, fecha dd/mm/yyyy→date, detecta código_banco), `parse_csv_estandar(file_bytes)` (sep `;`, decimal `,`, encoding detect UTF-8/Latin1, mismas columnas), `parse_csb_cuaderno43(file_bytes)` (registros 01/02/03/99 longitud fija según AEB Norma 43, usar `pybank43` si disponible o parser propio), `detectar_formato(file_bytes, filename)` (por extensión + sniffing primeras líneas: `PK`=xlsx, `;` en línea 1=CSV, empieza `01`=CSB)
- [x] T007 [P] Implementar utilidades compartidas en `backend/app/services/banco.py`: `calcular_hash_unicidad(fecha_valor, importe, referencia)` (SHA256), `validar_cuentas_regla(session, ejercicio_id, cuenta_debe, cuenta_haber)` (existen en ejercicio), `convertir_signo_banco_a_contable(importe, codigo_banco)` (banco: negativo=cargo; contable: regla define debe/haber positivo)

**Checkpoint**: Foundation ready — US1 a US4 pueden implementarse (en paralelo si hay equipo)

---

## Phase 3: User Story 1 - Importar Extracto Bancario (Priority: P1) — MVP

**Goal**: Subir Excel Santander / CSV / CSB → parse → guardar `MovimientoBanco` con `procesado=False`, deduplicar por hash

**Independent Test**: Importar el archivo `Data/1. MovimientosCuenta ene_feb26.xlsx` → 100+ movimientos creados, hash único, `procesado=False`, campos `fecha_operacion`, `fecha_valor`, `codigo_banco`, `referencia_2` poblados; re-importar mismo archivo → 0 duplicados (409 o ignorados)

### Tests for User Story 1 (requeridos por constitución R2)

> **NOTA: Escribir estos tests PRIMERO, asegurar que FALLAN antes de implementar**

- [x]* T008 [US1] Tests de integración importación en `backend/tests/integration/test_banco.py`: Excel Santander (cabecera 7 filas + header fila 8) → parse correcto 100+ filas, importe/fecha/code mapeados; CSV `;`/`,`/UTF-8 → mismo resultado; CSB registros 01/02/03/99 → parse correcto; duplicados (mismo hash) → 409 o ignorados según flag; multi-tenant (empresa ajena) → 403; ejercicio cerrado → 200 (solo lectura)
  - *Parcial*: cubiertos CSV (`test_importar_csv_crea_movimientos_pendientes`) y duplicados por hash (`test_importar_duplicado_no_reinserta`); el parsing Excel/CSB y los casos multi-tenant / ejercicio cerrado no tienen test dedicado (ver T044/T045).

### Implementation for User Story 1

- [x] T009 [US1] Implementar `importar_extractos(session, ejercicio_id, file_bytes, filename, ignorar_duplicados=False)` en `backend/app/services/banco.py`: detectar formato, llamar parser correspondiente, validar filas, calcular hash, upsert por hash (si existe y no ignorar → error), insertar `MovimientoBanco` con `procesado=False`, `origen_archivo`, `ejercicio_id`, devolver `ImportResponse`
- [x] T010 [US1] Implementar endpoint `POST /api/v1/banco/importar` en `backend/app/api/banco.py`: `UploadFile`, `EjercicioDep`+`SessionDep`+`EmpresaDep`, form-data `file` + `ignorar_duplicados?`, validar tamaño máx 10MB, devolver `ImportResponse`; 400 si formato no soportado, 422 si archivo corrupto
- [x] T011 [US1] Añadir en `frontend/src/lib/api.ts` tipos (`ImportResponse`, `MovimientoBanco`) y método `api.banco.importar(file, {ignorar_duplicados})` (FormData, headers contexto, credenciales)
- [x] T012 [US1] Crear componente `BancoImportar` en `frontend/src/components/BancoImportar.tsx`: drag & drop zona, auto-detección formato (icono Excel/CSV/CSB), preview tabla primeras 20 filas (fecha, concepto, importe, código), botón "Importar" con checkbox "Ignorar duplicados", estados carga/éxito/error con MUI v6
- [x] T013 [US1] Crear página `frontend/src/app/banco/importar/page.tsx` (client component con `Suspense`) montando `BancoImportar`
- [x] T014 [US1] Test de frontend importación en `frontend/tests/Banco.test.tsx`: render zona drop, preview tabla con datos mock, botón importa llama `api.banco.importar`

**Checkpoint**: US1 funcional y testeable independientemente (importar 3 formatos, deduplicar, multi-tenant)

---

## Phase 4: User Story 2 - Configurar Reglas Auto-Matching (Priority: P1)

**Goal**: CRUD reglas por empresa (regex + 2 cuentas + prioridad + auto_asentar) + simulador

**Independent Test**: Crear regla "UNION FENOSA" → cuenta_debe=410, cuenta_haber=572, prioridad=10 → simular con movimientos reales → devuelve matches correctos; prioridad resuelve conflictos; validación cuentas inexistentes → 422

### Tests for User Story 2 (requeridos por constitución R2)

- [x]* T015 [US2] Tests de integración reglas en `backend/tests/integration/test_banco.py`: CRUD reglas (crear, listar, actualizar, borrar); validación cuentas (deben existir en ejercicio activo); simular regla devuelve movimientos que matchan; prioridad mayor gana; regex case-insensitive; multi-tenant (regla empresa A no visible en B)
  - *Parcial*: el CRUD y la validación de cuentas se ejercitan a través de los tests de `TestProcesar`/pendientes (`_crear_regla` reutilizado); no hay tests de lista separados por empresa (multi-tenant) ni de conflicto de prioridad.

### Implementation for User Story 2

- [x]* T016 [US2] Implementar servicio reglas en `backend/app/services/banco.py`: `crear_regla()`, `listar_reglas(empresa_id)`, `obtener_regla(id)`, `actualizar_regla()`, `borrar_regla()`, `simular_regla(regla_id, ejercicio_id, desde, hasta)` (busca movimientos sin procesar, aplica regex `re.IGNORECASE` sobre `concepto` + `referencia`, devuelve lista matches con cuenta_debe/cuenta_haber calculadas)
  - *Divergencia*: CRUD y simulación implementados directamente en los endpoints de `backend/app/api/banco.py` (no como funciones de `services/banco.py`), apoyándose en `validar_cuentas_regla()` del servicio.
- [x] T017 [US2] Implementar endpoints CRUD `/api/v1/banco/reglas` en `backend/app/api/banco.py`: `GET` lista, `POST` crear (valida cuentas existen en ejercicio activo de la empresa), `PUT` actualizar, `DELETE` borrar, `POST /reglas/{id}/simular` (query `desde`, `hasta`), todos con `EmpresaDep`+`EjercicioDep`+`SessionDep`
- [x] T018 [US2] Añadir en `frontend/src/lib/api.ts` tipos (`ReglaBanco`, `SimularResponse`) y métodos `api.banco.reglas()`, `api.banco.crearRegla()`, `api.banco.actualizarRegla()`, `api.banco.borrarRegla()`, `api.banco.simularRegla()`
- [x] T019 [US2] Crear componente `BancoReglas` en `frontend/src/components/BancoReglas.tsx`: tabla MUI con columnas (Nombre, Patrón, Cuenta Debe, Cuenta Haber, Prioridad, Auto Asentar, Acciones), modal crear/editar (select cuentas del ejercicio, input regex, number prioridad, switch auto_asentar), botón "Simular" abre modal con preview matches (tabla: Fecha, Concepto, Importe, Cuenta D, Cuenta H), botón eliminar con confirmación
- [x] T020 [US2] Crear página `frontend/src/app/banco/reglas/page.tsx` (client component) montando `BancoReglas`
- [x] T021 [US2] Test de frontend reglas en `frontend/tests/Banco.test.tsx`: render tabla, modal crear/editar, simular muestra matches

**Checkpoint**: US2 funcional — reglas persistentes, simulador valida antes de procesar

---

## Phase 5: User Story 3 - Procesar Auto-Matching y Generar Asientos (Priority: P1)

**Goal**: Batch recorre pendientes, aplica reglas por prioridad, crea asientos (borrador/asentado), marca procesados

**Independent Test**: Con 5 reglas y 50 movimientos pendientes → `POST /procesar` crea 40 asientos (80% match), 10 quedan pendientes, 0 asientos descuadrados, idempotente (re-ejecutar no duplica)

### Tests for User Story 3 (requeridos por constitución R2)

- [x]* T022 [US3] Tests de integración procesado en `backend/tests/integration/test_banco.py`: batch crea asientos correctos (debe/haber según regla, importe del movimiento o fijo/%), `procesado=True`, `asiento_id` link, `regla_id` link; `auto_asentar=True` → estado `asentado`, `False` → `borrador`; idempotente (2ª ejecución 0 nuevos); multi-tenant aislamiento; 0 asientos descuadrados (ΣDebe=ΣHaber)
  - *Parcial*: `TestProcesar` cubre auto-asentar con correlativo (ΣDebe=ΣHaber), borrador, sin reglas → pendientes, cuenta inexistente → fallo logueado; la idempotencia (2ª ejecución) y el aislamiento multi-tenant del batch no tienen test explícito.

### Implementation for User Story 3

- [x]* T023 [US3] Implementar `procesar_pendientes(session, ejercicio_id, desde?, hasta?)` en `backend/app/services/banco.py`: obtiene movimientos `procesado=False` en rango, ordena reglas por prioridad DESC, para cada movimiento busca 1ª regla que matcha (`re.search(patron, concepto) or re.search(patron, referencia)`), si match: calcula importe (fijo/porcentaje o movimiento), llama `crear_asiento_desde_regla(session, regla, movimiento)`, marca movimiento `procesado=True`, `asiento_id`, `regla_id`; devuelve `ProcesarResponse` (creados, pendientes, fallidos[], log[])
  - *Divergencia*: implementado inline en el endpoint `POST /procesar` de `backend/app/api/banco.py` (mismo orden por prioridad DESC, regex `re.IGNORECASE`, importe fijo/porcentaje, llamada a `guardar_borrador`/`asentar` del servicio contable, log al finalizar) en vez de en `services/banco.py`.
- [x]* T024 [US3] Implementar `crear_asiento_desde_regla(session, regla, movimiento)` en `backend/app/services/banco.py`: construye `Asiento` (fecha=movimiento.fecha_valor, concepto=movimiento.concepto, estado=borrador/asentado según regla.auto_asentar, apuntes: línea 1 cuenta_debe importe_absoluto, línea 2 cuenta_haber importe_absoluto), valida ΣDebe=ΣHaber, guarda, retorna asiento
  - *Divergencia*: la creación del asiento se hace inline en `api/banco.py` reutilizando `svc_asientos.guardar_borrador` (+ `asentar` si `auto_asentar`), con signo contable convertido por `convertir_signo_banco_a_contable`.
- [x] T025 [US3] Implementar endpoint `POST /api/v1/banco/procesar` en `backend/app/api/banco.py`: `EjercicioDep`+`SessionDep`+`EmpresaDep`, query `desde`, `hasta`, devuelve `ProcesarResponse`
- [x] T026 [US3] Añadir en `frontend/src/lib/api.ts` método `api.banco.procesar({desde, hasta})` y tipo `ProcesarResponse`
- [x] T027 [US3] (Opcional) Botón "Procesar automático" en `BancoPendientes` o página separada `frontend/src/app/banco/procesar/page.tsx` con resumen resultado (creados/pendientes/fallidos)
  - *Decisión*: botón "Procesar automático" dentro de `BancoPendientes` con resumen en alerta (creados/pendientes/fallidos); no se creó página separada.

**Checkpoint**: US3 funcional — batch idempotente, asientos cuadran, trazabilidad completa

---

## Phase 6: User Story 4 - Gestionar Pendientes Manualmente (Priority: P1)

**Goal**: UI para ver movimientos sin match y completarlos creando asiento manual

**Independent Test**: Lista pendientes muestra 10 movimientos → click "Crear asiento" en fila → modal selector cuentas (busca por código/nombre) + líneas debe/haber → guardar → movimiento marcado `procesado=True`, link a asiento creado

### Tests for User Story 4 (requeridos por constitución R2)

- [x]* T028 [US4] Tests de integración pendientes en `backend/tests/integration/test_banco.py`: `GET /pendientes` paginado + filtros (`desde`, `hasta`, `codigo_banco`); crear asiento manual vía endpoint existente `/asientos` + marcar movimiento procesado; filtro "solo pendientes" en Diario
  - *Parcial*: `GET /pendientes` cubierto; el flujo manual completo quedó cubierto por `TestPendientesManuales` (crear asiento manual con `origen="manual"` + `POST /banco/movimientos/{id}/procesado`); el "filtro en Diario" se resolvió en el frontend con acceso directo a pendientes (ver T033), sin endpoint nuevo.

### Implementation for User Story 4

- [x]* T029 [US4] Implementar endpoint `GET /api/v1/banco/pendientes` en `backend/app/api/banco.py`: `EjercicioDep`+`SessionDep`+`EmpresaDep`, query `desde`, `hasta`, `codigo_banco`, `offset`, `limit`, devuelve `Paginado[MovimientoBancoOut]` filtrado `procesado=False`
  - *Divergencia*: devuelve `list[MovimientoBancoOut]` plano (sin envoltorio `Paginado`) respetando `offset`/`limit`; simplificación acordada con el cliente.
- [x]* T030 [US4] Añadir en `frontend/src/lib/api.ts` método `api.banco.pendientes(params)` y tipo `Paginado<MovimientoBanco>`
  - *Divergencia*: el método devuelve `MovimientoBanco[]` (alineado con la respuesta plana de T029).
- [x] T031 [US4] Crear componente `BancoPendientes` en `frontend/src/components/BancoPendientes.tsx`: tabla MUI paginada (Fecha, Concepto, Importe, Saldo, Código, Referencias, Acciones), filtros arriba (fecha desde/hasta, código), botón "Crear asiento" por fila abre modal (reusa selector cuentas de `FormAsiento`: busca por código/nombre, 2 líneas debe/haber con importe pre-llenado del movimiento, botón "Guardar y procesar")
  - *Nota*: paginación en cliente con "Cargar más" (offset/limit); el selector de cuentas es un `NativeSelect` con el plan de cuentas del ejercicio; importes pre-llenados con el signo convertido a debe/haber.
- [x] T032 [US4] Crear página `frontend/src/app/banco/pendientes/page.tsx` (client component) montando `BancoPendientes`
- [x]* T033 [US4] Añadir filtro "Origen: Pendientes" en Diario (`/diario`) y página `/banco` tab 3
  - *Decisión*: en `/diario` un botón "Pendientes de conciliar" que enlaza a `/banco/pendientes` (tab 3 de `/banco`); no se añadió un filtro campo en el listado del Diario.

**Checkpoint**: US4 funcional — pendientes listados, completables manualmente, integrado en Diario

---

## Phase 7: User Story 5 - Trazabilidad y Auditoría (Priority: P2)

**Goal**: Campo `origen` en asiento, `regla_id` link, log de procesamiento

**Independent Test**: Asiento generado por auto-matching → `origen="auto"`, `regla_id` poblado; asiento manual → `origen="manual"`; `POST /procesar` loggea timestamp, reglas aplicadas, N creados/pendientes/fallidos

### Tests for User Story 5 (requeridos por constitución R2)

- [x]* T034 [US5] Tests de integración trazabilidad en `backend/tests/integration/test_banco.py`: `AsientoOut` incluye `origen` (auto|manual|importado) y `regla_id` si auto; log de procesamiento persistido (tabla nueva o JSON en campo); auditoría: usuario que lanzó procesado, timestamp
  - *Parcial*: `test_procesar_auto_marca_origen_y_regla` y `test_crear_asiento_manual_y_marcar_procesado` cubren `origen`/`regla_id` y la serialización en `AsientoOut`; el log persistido se ejercita en `test_procesar_cuenta_inexistente_registra_fallo` (fallidos); no hay test específico del contenido completo del log.

### Implementation for User Story 5

- [x] T035 [US5] Añadir campos `origen` (str: `auto`|`manual`|`importado`) y `regla_id` (FK nullable) a modelo `Asiento` en `backend/app/models/contable.py` + migración Alembic (incluida en `6b69941fa552`)
- [x] T036 [US5] Actualizar `AsientoOut` schema en `backend/app/schemas/asientos.py` para incluir `origen` y `regla_id` (serializados en `_to_out` de `api/asientos.py`)
- [x]* T037 [US5] Modificar `crear_asiento_desde_regla()` en `banco.py` para setear `origen="auto"` y `regla_id`
  - *Divergencia*: `guardar_borrador()` (servicio de asientos) acepta ahora un parámetro `origen`; el auto-matching (inline en `api/banco.py`) pasa `origen="auto"` y setea `asiento.regla_id = regla.id` tras la creación.
- [x] T038 [US5] Crear tabla `LogProcesamientoBanco` (id, ejercicio_id, usuario_id, timestamp, reglas_aplicadas_json, creados, pendientes, fallidos_json) + migración; `procesar_pendientes()` inserta log al finalizar (en el endpoint `POST /procesar`)
- [x] T039 [US5] Endpoint `GET /api/v1/banco/logs` (paginado, filtros fecha) en `backend/app/api/banco.py`
- [x] T040 [US5] Componente `BancoProcesados` en `frontend/src/components/BancoProcesados.tsx`: tabla historial (Fecha, Usuario, Reglas, Creados, Pendientes, Fallidos, Ver log), página `frontend/src/app/banco/procesados/page.tsx`

**Checkpoint**: US5 funcional — trazabilidad completa, auditoría disponible

---

## Phase 8: Polish & Cross-Cutting Concerns

**Propósito**: Verificación end-to-end, rendimiento, edge cases, documentación

- [ ] T041 [P] Recorrer y validar `specs/004-conciliacion-bancaria/quickstart.md` (REST + UI) y marcar casillas criterios aceptación
  - *Pendiente*: `quickstart.md` no existe en la carpeta de la spec 004.
- [x] T042 Ejecutar backend desde `backend/`: `..\.venv\Scripts\python.exe -m ruff check app tests` y `..\.venv\Scripts\python.exe -m pytest -q`; corregir hasta verde — ✅ ruff limpio, **77 tests passed**
- [x] T043 Ejecutar frontend desde `frontend/`: `npm run lint`, `npx tsc --noEmit`, `npm run build`; corregir sin errores — ✅ lint, tsc, **24 tests vitest** y build en verde
- [ ] T044 [P] Verificar AC-01 (importar 1000 movs < 5s), AC-02 (procesar 1000 movs 20 reglas < 3s), AC-03 (0 asientos descuadrados), AC-04 (re-importar 0 duplicados), AC-05 (sin reglas → pendientes), AC-06 (multi-tenant 0 cruce)
  - *Parcial*: AC-03/AC-04/AC-05 cubiertos por tests de integración; AC-01/AC-02 (rendimiento) y AC-06 (cruce multi-tenant del batch) no medidos/testeados.
- [x]* T045 [P] Verificar edge cases: ejercicio `cerrado` importable/consultable solo lectura, archivo corrupto → 422 con detalle, regex inválida → 422, cuenta inexistente en regla → 422, importe 0 → saltar, divisa distinta EUR → warning
  - *Parcial*: cuenta inexistente en regla → fallo controlado en `test_procesar_cuenta_inexistente_registra_fallo`; duplicados → 409/ignorados testeados; el resto (ejercicio cerrado, archivo corrupto, regex inválida, importe 0, divisa) sin verificación explícita.
- [x] T046 Añadir tarjeta "Conciliación Bancaria" (href `/banco`) al panel en `frontend/src/app/page.tsx`
- [x] T047 Actualizar `README.md` o docs con guía de uso conciliación (formatos, reglas, flujo) — sección "Conciliación bancaria (guide)" en `README.md`

---

## Dependencias & Orden de Ejecución

### Dependencias de Fase

- **Setup (Fase 1)**: Sin deps — inicio inmediato
- **Foundational (Fase 2)**: Depende Setup — BLOQUEA todas las user stories
- **User Stories (Fase 3–7)**: Dependen Foundational
  - US1 (P1, MVP) y US2 (P1) en paralelo (equipos distintos), comparten `services/banco.py`
  - US3 (P1) depende US1+US2 (necesita movimientos + reglas)
  - US4 (P1) depende US1 (necesita pendientes) + endpoint asientos existente
  - US5 (P2) depende US3 (necesita asientos generados)
- **Polish (Fase 8)**: Depende completar historias deseadas

### Dependencias User Story

- **US1 (P1, MVP)**: Arranca tras Foundational; sin deps otras historias
- **US2 (P1)**: Arranca tras Foundational; independiente de US1
- **US3 (P1)**: Arranca tras Foundational; **requiere US1 (movimientos) + US2 (reglas)**
- **US4 (P1)**: Arranca tras Foundational; **requiere US1 (pendientes)**
- **US5 (P2)**: Arranca tras Foundational; **requiere US3 (asientos generados)**

### Dentro de Cada User Story

- Tests (T008, T015, T022, T028, T034) se escriben y FALLAN antes de implementar
- Modelos/Servicios antes que endpoints; endpoints antes que UI
- UI antes que test frontend correspondiente

### Oportunidades Paralelas

- T003 y T005 (Fase 2) en paralelo (archivos distintos)
- T006 y T007 (Fase 2) en paralelo
- US1 y US2 pueden desarrollarse en paralelo tras Fase 2 (ojo: T009/T016 editan mismo `services/banco.py` → coordinación/merge secuencial)
- Tests backend de distintas historias comparten `test_banco.py`: no paralelizar escritura mismo archivo
- T041, T044, T045 en paralelo en fase Polish

---

## Ejemplo Paralelo: User Story 1

```bash
# Foundational en paralelo (archivos distintos):
Task: "Definir modelos ORM MovimientoBanco/ReglaBanco en backend/app/models/contable.py"
Task: "Definir schemas Pydantic en backend/app/schemas/banco.py"
Task: "Implementar parsers base en backend/app/services/banco.py"

# US1 — UI en paralelo con página (tras existir componente):
Task: "Crear componente BancoImportar en frontend/src/components/BancoImportar.tsx"
Task: "Crear página frontend/src/app/banco/importar/page.tsx"
```

---

## Estrategia de Implementación

### MVP Primero (User Story 1)

1. Completar Fase 1 (Setup)
2. Completar Fase 2 (Foundational) — **CRÍTICO**
3. Completar Fase 3 (US1 — Importar)
4. **PARAR y VALIDAR**: probar US1 independientemente (importar 3 formatos, deduplicar, multi-tenant)
5. Demo/desplegar si listo

### Entrega Incremental

1. Setup + Foundational → base lista
2. US1 → validar → demo (MVP: importar extractos)
3. US2 → validar reglas + simulador → demo
4. US3 → validar batch + asientos → demo
5. US4 → validar pendientes manuales → demo
6. US5 → validar trazabilidad → demo
7. Polish → rendimiento, edge cases, verificación end-to-end

### Estrategia Equipo Paralelo

Con varios desarrolladores: completar Setup + Foundational en equipo y luego repartir US1 (Importar) y US2 (Reglas); US3 en cuanto US1/US2 estén listos (procesamiento); US4/US5 en paralelo con US3 si hay capacidad.

---

## Notas

- **[P]** = archivos distintos y sin dependencias
- **[Story]** mapea la tarea a su user story para trazabilidad
- **Con migración Alembic**: 2 tablas nuevas (`movimiento_banco`, `regla_banco`) + 1 tabla log (`log_procesamiento_banco`) + campos en `Asiento` (`origen`, `regla_id`)
- Toda la lógica de parsing, matching y generación asientos permanece en **backend** (Constitución II)
- Verificar que tests fallan antes de implementar
- Hacer commit tras cada tarea o grupo lógico
- **Estado real (oct 2026)**: 004 completada (backend + frontend). Pendientes explícitos: T041 (quickstart inexistente), T044 (rendimiento AC-01/AC-02/AC-06 sin medir) y las coberturas parciales marcadas con `[x]*`.