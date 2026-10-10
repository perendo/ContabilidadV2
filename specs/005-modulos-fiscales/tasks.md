---

description: "Task list for feature implementation"
---

# Tasks: Módulos Fiscales (IVA, Retenciones IRPF, IS, Presentación AEAT)

**Input**: Design documents from `specs/005-modulos-fiscales/`

**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/

**Tests**: Incluidos (obligatorios por Constitución: cobertura automática de toda lógica de cálculo y cuadre antes de liberar). Backend `..\.venv\Scripts\python.exe -m pytest -q`; frontend `npm test`.

**Organization**: Tasks grouped by user story (US1-US5 + Presentación AEAT) para implementación y tests independientes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Story]**: User story al que pertenece (US1..US5, US-PRES)
- Incluir rutas exactas

## Path Conventions (2 apps, ver plan.md)

- Backend: `backend/app/...`, `backend/tests/integration/...`
- Frontend: `frontend/src/...`, `frontend/tests/...`
- Migraciones: Alembic (`backend/alembic/versions/...`); ficheros solo via Alembic (gotcha AGENTS.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar el terreno para las tablas y servicios fiscales

- [ ] T001 Crear `backend/app/models/fiscal.py` (módulo vacío con `__all__` a rellenar) y añadir la exportación en `backend/app/models/__init__.py`
- [ ] T002 [P] Añadir `backend/impuestos/` a `.gitignore` (raíz) y crear la carpeta con un `.gitkeep`; documentar en `backend/README.md` que los ficheros AEAT se guardan en `impuestos/{empresa_id}/{anio}/`
- [ ] T003 [P] Revisar `backend/pyproject.toml` (no se prevén dependencias nuevas; confirmar que `Alembic` y `openpyxl`/`pandas` existentes siguen declarados)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelos + migración + helpers compartidos. Sin esto, ninguna user story es implementable.

**CRITICAL**: Ninguna user story puede comenzar hasta completar esta fase.

- [ ] T004 Crear en `backend/app/models/fiscal.py` los enums como `str` (patrón proyecto, persistidos como `String`): `OrigenFactura` = `venta` | `compra`; `TipoRetencion` = `111` | `115`; estados `registrada` | `anulada` (factura) y `borrador` | `cerrada` (IS)
- [ ] T005 [P] Crear clase `Factura` en `backend/app/models/fiscal.py` con campos de `data-model.md`: `ejercicio_id` (FK RESTRICT), `origen` (String(10)), `numero` (String(50), no nulo), `fecha` (date), `fecha_operacion` (date nullable), `tercero_cif` (String(9)), `tercero_razon_social` (String(200)), `solo_identificativo` (bool default false), `tipo_retencion` (String(3) nullable), `estado` (default `registrada`), `notas` (String(1000) nullable), `asiento_id` (FK Asiento RESTRICT nullable), `creado_por_usuario_id` (FK Usuario), `created_at`; `UniqueConstraint(ejercicio_id, tercero_cif, numero)` → `uq_factura_ejercicio_cif_numero`; índices `ix_factura_ejercicio_fecha` y `ix_factura_ejercicio_origen`
- [ ] T006 [P] Crear clase `LineaFacturaIVA` en `backend/app/models/fiscal.py`: `factura_id` (FK CASCADE), `numero_linea` (≥1), `descripcion` (String(300)), `base_imponible` (Numeric(19,2)), `tipo_iva` (Numeric(5,2)), `cuota_iva` (Numeric(19,2)), `tipo_re`/`cuota_re` (nullable), `operacion_exenta` (bool default false), `base_retencion`/`pct_retencion`/`cuota_retencion` (nullable); índice `ix_linea_factura_factura`
- [ ] T007 [P] Crear clase `LiquidacionImpuestoSociedades` en `backend/app/models/fiscal.py`: 1 por ejercicio (`UniqueConstraint(ejercicio_id, name="uq_lis_ejercicio")`), `resultado_contable` (Numeric(19,2)), `ajustes_json` (String(12000)), `tipo_gravamen` (Numeric(5,2) default 25.00), `retenciones_pagos_cuenta` (Numeric(19,2) default 0), `base_imponible`/`cuota_integra`/`cuota_diferencial` (nullable, se congelan al cerrar), `estado` (default `borrador`), `asiento_id` nullable, `creado_por_usuario_id`, `cerrado_por_usuario_id` nullable, `created_at`/`cerrado_at`
- [ ] T008 [P] Crear clase `FicheroPresentacion` en `backend/app/models/fiscal.py`: `ejercicio_id` (FK RESTRICT), `modelo` (String(3): 303|111|115|200), `periodo` (String(8), p.ej. `2026T4`/`2026`), `ruta` (String(255)), `hash_sha256` (String(64)), `generado_por_usuario_id` (FK), `generado_at`; `UniqueConstraint(ejercicio_id, modelo, periodo, name="uq_fichero_ejercicio_modelo_periodo")`
- [ ] T009 Migración Alembic: `..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "módulos fiscales"`; corregir a mano (gotcha): reemplazar `sqlmodel.sql.sqltypes.AutoString` por `sa.String(...)` y añadir los índices `ix_factura_*`, `ix_linea_factura_factura`; comprobar que los enums quedan como `String`; `alembic upgrade head`
- [ ] T010 Schemas Pydantic en `backend/app/schemas/facturas.py`, `presentaciones.py`, `is.py` con `model_config = ConfigDict(from_attributes=True)`: `LineaFacturaIVAIn/Out`, `FacturaIn/Out` (Decimal como string), `AjusteIS {concepto, sentido: aumento|disminucion, importe}`, `LiquidacionISIn/Out`, `PresentacionVista`, `FicheroOut`; validadores `field_validator` con 2 decimales
- [ ] T011 [P] Helpers compartidos en `backend/app/services/fiscales_util.py`: `cuantizar2(d)` (`Decimal.quantize(0.01, ROUND_HALF_UP)`), `validar_cif(cif)` (string 9 dígitos, letra/patrón NIF/CIF), `_utcnow`; constantes de cuentas PGC por defecto `{400, 430, 600, 700, 472, 477, 4751, 473, 631}`
- [ ] T012 [P] Base del generador AEAT en `backend/app/services/aeat.py`: clase/plantilla por modelo (estructura de registros `{nombre, posicion, longitud, tipo, padding}`, encoding y CRLF parametrizables) + método `validar_formato(registros)` que recorra la plantilla y compruebe longitudes/tipos antes de escribir el fichero (decisión R1/R2 research.md)
- [ ] T013 [P] Tests del cimiento en `backend/tests/integration/test_fiscal_base.py`: migración en BD temporal aplica (`alembic upgrade head` vía conftest), unicidad CIF+numero+ejercicio eleva `IntegrityError` al insertar duplicado directo, `validar_cif` y `cuantizar2` (HALF_UP) pasan casos límite (0.005 → 0.01)

**Checkpoint**: Foundation lista — la implementación de user stories puede comenzar

---

## Phase 3: User Story 1 - Registrar factura de venta con IVA repercutido (P1) — MVP

**Goal**: Registrar una factura de venta a crédito (430/700/477) con línea/s de IVA; el sistema genera de forma atómica el asiento cuadrado; duplicados CIF+Nº+ejercicio rechazados con 409.

**Independent Test**: Postear `POST /api/v1/facturas` `{origen:"venta", numero:"FV-001", fecha, tercero_cif, lineas:[{base_imponible:"1000.00", tipo_iva:"21.00", cuota_iva:"210.00"}]}` → 201 con `asiento_id`, el asiento cumple ΣDebe=ΣHaber (430 deb 1210 / 700 hab 1000 / 477 hab 210) y aparece en el Diario; repetir mismo CIF+numero → 409.

### Tests para User Story 1 (obligatorios por Constitución — escribir y verlos FALLAR antes de implementar)

> **NOTE**: Escribir estos tests PRIMERO, asegurar que FALLAN antes de implementar

- [ ] T014 [P] [US1] Integration test `test_factura_venta_asiento_cuadrado` en `backend/tests/integration/test_facturas.py`: venta 1000 @21% → apuntes (430 deb 1210 / 700 hab 1000 / 477 hab 210), ΣDebe=ΣHaber, `asiento_id` poblado, correlativo asignado
- [ ] T015 [P] [US1] Integration test `test_duplicado_cif_numero_ejercicio_409` en `backend/tests/integration/test_facturas.py`: 2º POST mismo CIF+numero → 409 y no crea asiento; mismo numero en otro ejercicio → 201
- [ ] T016 [P] [US1] Integration test `test_multi_tipo_iva_una_linea_por_tipo` en `backend/tests/integration/test_facturas.py`: dos líneas 21% y 10% → dos apuntes en 477 y total cuadra
- [ ] T017 [P] [US1] Integration test `test_factura_sin_contexto_400_sin_acceso_403` en `backend/tests/integration/test_facturas.py` (patrón conftest `contexto`, vincular usuario a la empresa)

### Implementación para User Story 1

- [ ] T018 [US1] Implementar `crear_factura(...)` en `backend/app/services/facturas.py`: validar CIF (`validar_cif`), cuotas vs `base×tipo/100` a 2dp (→422 si difiere), ejercicio abierto (→409), unicidad CIF+numero+ejercicio (→409, backstop BD); calcular asiento con cuentas de `fiscales_util.py`; **misma transacción**: insertar factura + líneas + asiento + apuntes y `session.commit()` único (reusar `services/asientos.py` para el cuadre y correlativo)
- [ ] T019 [US1] Implementar `POST /api/v1/facturas` y `GET /api/v1/facturas` (paginado, filtros `origen`/`desde`/`hasta`/`tercero_cif`, default limit 50 max 200) y `GET /api/v1/facturas/{id}` en `backend/app/api/facturas.py`, registrando el router en `backend/app/main.py`
- [ ] T020 [US1] Frontend: `FormFactura.tsx` en `frontend/src/components/` (líneas dinámicas base/tipo_iva, preview del asiento SOLO como UX — cálculo definitivo en backend) + página `frontend/src/app/facturas/nueva/page.tsx` y listado `frontend/src/app/facturas/page.tsx`
- [ ] T021 [US1] Añadir tipos y métodos `api.facturas.*` (crear/listar/detalle) en `frontend/src/lib/api.ts`; manejar 409 duplicado con mensaje claro

**Checkpoint**: US1 funcional y testeable de forma independiente → **MVP alcanzado**

---

## Phase 4: User Story 2 - Registrar factura de compra con IVA soportado y Recargo de Equivalencia (P1)

**Goal**: Registrar facturas de compra (600/472/400) incluyendo Recargo de Equivalencia (cuota RE deducible en 472); sin retenciones aún (US4).

**Independent Test**: `POST /api/v1/facturas` `{origen:"compra", numero:"FC-001", ...}` con línea base 500 @21% (cuota 105) → 201, asiento 600 deb 500 / 472 deb 105 / 400 hab 605; variante con `tipo_re:"5.20"` añade cuota RE en 472 y el total cuadra.

**Dependency**: T018 (mismo `services/facturas.py`).

### Tests para User Story 2 (obligatorios)

- [ ] T022 [P] [US2] Integration test `test_factura_compra_cuadra` en `backend/tests/integration/test_facturas.py`: compra 500 @21% → 600/472/400 correctos
- [ ] T023 [P] [US2] Integration test `test_recargo_equivalencia_se_registra` en `backend/tests/integration/test_facturas.py`: base con `tipo_re:"5.20"`, `cuota_re:"26.00"` → RE en 472 y ΣDebe=ΣHaber
- [ ] T024 [P] [US2] Integration test `test_operacion_exenta_sin_cuota` en `backend/tests/integration/test_facturas.py`: `operacion_exenta:true`, tipo 0 → sin línea 472, asiento de gasto puro

### Implementación para User Story 2

- [ ] T025 [US2] Extender `crear_factura` en `backend/app/services/facturas.py` para `origen="compra"`: mapeo 600 (debe) / 472 (debe, IVA + RE) / 400 (haber); si `operacion_exenta` → `tipo_iva=0`/`cuota_iva=0` y omitir 472
- [ ] T026 [US2] Frontend: soporte `origen="compra"` + campo RE en `frontend/src/components/FormFactura.tsx` (mismo formulario, campos condicionales)

**Checkpoint**: US1 y US2 funcionan de forma independiente

---

## Phase 5: User Story 3 - Consultar y exportar los Libros Registro de IVA (P1)

**Goal**: Consulta de Libro Repercutido/Soportado por rango de fechas con totales por tipo y exportación CSV.

**Independent Test**: Tras registrar varias facturas (US1/US2), `GET /api/v1/facturas/libros/iva?origen=repercutido&desde=...&hasta=...` devuelve detalle por factura + `totales_por_tipo`/`total_base`/`total_cuota` que coinciden al céntimo con las facturas del periodo; `GET .../libros/iva/exportar` devuelve CSV `;` con BOM.

**Dependency**: T025 (datos de US1/US2).

### Tests para User Story 3 (obligatorios)

- [ ] T027 [P] [US3] Integration test `test_libro_iva_totales_por_tipo` en `backend/tests/integration/test_facturas.py`: varios tipos → agregados correctos, coincidentes con facturas
- [ ] T028 [P] [US3] Integration test `test_libro_iva_exportar_csv` en `backend/tests/integration/test_facturas.py`: cabeceras (fecha, número, CIF, nombre, base, tipo, cuota, total), `;` como separador, BOM UTF-8

### Implementación para User Story 3

- [ ] T029 [US3] Implementar `listar_libro_iva(...)` y `exportar_libro_iva(...)` en `backend/app/services/facturas.py` (agregación por `tipo_iva`, números `Decimal` sensibles)
- [ ] T030 [US3] Endpoints `GET /api/v1/facturas/libros/iva` (con response `{operaciones, totales_por_tipo, total_base, total_cuota}`) y `GET /api/v1/facturas/libros/iva/exportar` en `backend/app/api/facturas.py`
- [ ] T031 [US3] Frontend: `frontend/src/components/LibroIVA.tsx` + página `frontend/src/app/fiscal/libros-iva/page.tsx` (tabs Soportado/Repercutido, filtro fechas, botón exportar CSV con `window.open` al endpoint)

**Checkpoint**: US3 funcional sobre facturas de US1/US2

---

## Phase 6: User Story 4 - Retenciones IRPF y agrupación por perceptor 111/115 (P1)

**Goal**: Facturas de compra a profesionales/alquileres con retención; el asiento registra 4751 (111) o 4751/473 configurado (115) y el resumen agrupado por CIF alimenta los modelos.

**Independent Test**: Compra `tipo_retencion:"111"` con línea base 1000 @21% retención 15% → asiento 600 deb 1000 / 472 deb 210 / 400 hab 1060 / 4751 hab 150; `GET /api/v1/facturas/retenciones?tipo=111&desde&hasta` agrupa por CIF con base/cuota/nº facturas coincidentes al céntimo.

**Dependency**: T025 (campo `tipo_retencion` y retención por línea ya extendidos para compra).

### Tests para User Story 4 (obligatorios)

- [ ] T032 [P] [US4] Integration test `test_factura_compra_con_retencion_cuadra` en `backend/tests/integration/test_facturas.py`: 1000 @21% ret 15% → apuntes exactos (600/472/400/4751), ΣDebe=ΣHaber
- [ ] T033 [P] [US4] Integration test `test_resumen_111_por_cif` en `backend/tests/integration/test_facturas.py`: 3 facturas mismo CIF → agregado por CIF es la Σ exacta
- [ ] T034 [P] [US4] Integration test `test_resumen_115_separa_alquileres` en `backend/tests/integration/test_facturas.py`: alquileres (115) no aparecen en 111 y sí en 115
- [ ] T035 [P] [US4] Integration test `test_perceptor_sin_cif_valido_excluido_y_pct_fuera_rango` en `backend/tests/integration/test_facturas.py`: CIF inválido → 422; `pct_retencion > 100` → 422

### Implementación para User Story 4

- [ ] T036 [US4] Añadir en `crear_factura` (compra) el apunte de pasivo de retención: `base_retencion`/`pct_retencion`/`cuota_retencion` validados (cuota = base×pct/100 a 2dp, pct 0–100 → 422 si no), cuenta `4751` para 111 y cuenta configurable (default `4751`) para 115, en `backend/app/services/facturas.py`
- [ ] T037 [US4] Implementar `resumen_retenciones(...)` en `backend/app/services/facturas.py`: agregado por `tercero_cif` (`base_retencion`, `cuota_retencion`, `numero_facturas`), excluye CIF inválidos (FR-017); endpoint `GET /api/v1/facturas/retenciones` (query `tipo` 111|115, `desde`, `hasta`) en `backend/app/api/facturas.py`
- [ ] T038 [US4] Frontend: `frontend/src/components/ResumenRetenciones.tsx` + página `frontend/src/app/fiscal/retenciones/page.tsx` (selección 111/115, tabla por CIF)

**Checkpoint**: US4 funcional sobre facturas de compra

---

## Phase 7: User Story 5 - Liquidación del Impuesto sobre Sociedades (P2)

**Goal**: CRUD de la liquidación por ejercicio (resultado contable + ajustes + tipo 25% + retenciones/pagos a cuenta), cálculo en backend y cierre que congela los resultados.

**Independent Test**: `POST /api/v1/is` con resultado 100000, aumento 5000, disminución 8000, tipo 25, retenciones 4000 → `GET /api/v1/is` devuelve base 97000 / cuota íntegra 24250 / diferencial 20250; `POST /api/v1/is/cerrar` congela y `PUT` tras cerrar → 409.

**Dependency**: Foundation (T007/T010). Independiente de facturas.

### Tests para User Story 5 (obligatorios)

- [ ] T039 [P] [US5] Integration test `test_is_base_y_cuota` en `backend/tests/integration/test_presentaciones_is.py`: 100000 ± 5000/8000 @25% retenciones 4000 → 97000/24250/20250
- [ ] T040 [P] [US5] Integration test `test_is_a_devolver` en `backend/tests/integration/test_presentaciones_is.py`: retenciones > cuota íntegra → cuota diferencial negativa
- [ ] T041 [P] [US5] Integration test `test_is_una_por_ejercicio_y_cerrada_inmutable` en `backend/tests/integration/test_presentaciones_is.py`: 2º POST → 409; tras cerrar, PUT → 409; ejercicio cerrado → 409

### Implementación para User Story 5

- [ ] T042 [US5] Implementar `services/is.py` en `backend/app/services/`: `calcular(liq)` (fórmula única del contrato is.md: `base = resultado + Σaumentos − Σdisminuciones`; `cuota_integra = base×tipo/100` cuantizado; `diferencial = cuota_integra − retenciones`), validar `ajustes_json` con `AjusteIS`
- [ ] T043 [US5] Endpoints `GET/POST/PUT /api/v1/is` y `POST /api/v1/is/cerrar` en `backend/app/api/is.py` (cerrar solo si ejercicio abierto; congelar campos; registrar `cerrado_por_usuario_id`/`cerrado_at`), router en `backend/app/main.py`
- [ ] T044 [US5] Frontend: `frontend/src/components/LiquidacionIS.tsx` (editor de ajustes aumento/disminución) + página `frontend/src/app/fiscal/is/page.tsx` (resumen calculado por el backend, botón cerrar)

**Checkpoint**: US5 funcional

---

## Phase 8: Presentación AEAT - vista, fichero de posiciones fijas, directorio impuestos y descarga (FR-026…031)

**Goal**: Vista de presentación (resumen por bloques + casillas oficiales) por modelo y botón de descarga del fichero de posiciones fijas (303/111/115/200), persistido en `impuestos/{empresa}/{anio}`; descarga solo con liquidación/periodo cerrados (409 en otro caso); la descarga a petición no impide el guardado.

**Independent Test**: Con IS cerrado, `GET /api/v1/presentaciones/200?periodo=2026` → resumen+casillas con `bloque_descarga.habilitado:true`; `GET /api/v1/presentaciones/200/fichero?periodo=2026` descarga `200_2026.txt` con posiciones fijas válidas y aparece `backend/impuestos/{empresa_id}/2026/200_2026.txt`; con liquidación en borrador → 409 y botón deshabilitado.

**Dependency**: T012 (generador base), US3/US4/US5 (datos), T007 (FicheroPresentacion).

### Tests para User Story Presentación AEAT (obligatorios)

- [ ] T045 [P] [US-PRES] Integration test `test_fichero_303_posiciones_fijas` en `backend/tests/integration/test_presentaciones_is.py`: genera fichero de un trimestre cerrado y valida longitudes/alineación/totales contra la plantilla
- [ ] T046 [P] [US-PRES] Integration test `test_fichero_111_115_por_cif` en `backend/tests/integration/test_presentaciones_is.py`: un registro por perceptor con retenciones correctas
- [ ] T047 [P] [US-PRES] Integration test `test_fichero_200_is` en `backend/tests/integration/test_presentaciones_is.py`: casillas (resultado/base/cuota íntegra/diferencial) coinciden con la liquidación cerrada
- [ ] T048 [P] [US-PRES] Integration test `test_fichero_solo_con_periodo_cerrado_409` en `backend/tests/integration/test_presentaciones_is.py`: borrador → 409; vista en pantalla sí disponible
- [ ] T049 [P] [US-PRES] Integration test `test_directorio_impuestos_y_trazabilidad` en `backend/tests/integration/test_presentaciones_is.py`: ruta `impuestos/{empresa_id}/{anio}/{modelo}_{periodo}.txt`; regenerar sobrescribe (mismo nombre, nuevo hash) con `hash_sha256`/usuario/fecha en `fichero_presentacion`

### Implementación para User Story Presentación AEAT

- [ ] T050 [US-PRES] Extender `services/aeat.py`: plantillas concretas de posiciones fijas para 303 (agregados por tipo), 111/115 (registro por perceptor), 200 (casillas por bloques) con las longitudes de las especificaciones oficiales AEAT (rentrey versión vigente documentada en `research.md` R1); generador que emite cabecera (NIF/razón social/periodo), registros de totales y registro de fin; valida con `validar_formato` antes de escribir
- [ ] T051 [US-PRES] Implementar `persistir_fichero(...)` en `backend/app/services/aeat.py`: mkdir `impuestos/{empresa_id}/{anio}`, escritura idempotente (sobrescribe mismo `{modelo}_{periodo}.txt`), `hash_sha256`, upsert en `fichero_presentacion`
- [ ] T052 [US-PRES] Endpoints en `backend/app/api/presentaciones.py`: `GET /api/v1/presentaciones/{modelo}?periodo=` (vista resumen+casillas, calculada en backend) y `GET /api/v1/presentaciones/{modelo}/fichero?periodo=` (409 si no cerrado; devuelve fichero persistido o regenera+guarda+descarga en la petición); router en `backend/app/main.py`
- [ ] T053 [US-PRES] Frontend: `frontend/src/components/PresentacionAEAT.tsx` (resumen por bloques + detalle por casillas desplegable + botón de descarga) y página `frontend/src/app/presentaciones/page.tsx`; botón **deshabilitado** cuando `bloque_descarga.habilitado=false` mostrando `motivo`
- [ ] T054 [US-PRES] Añadir `api.presentaciones.*` en `frontend/src/lib/api.ts` (vista + descarga; el descarga usa blob de `text/plain`)

**Checkpoint**: todas las user stories y la presentación AEAT funcionales de forma independiente

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Mejoras transversales y cierre de validaciones

- [ ] T055 [P] Verificar `.gitignore` cubre `backend/impuestos/` y que ningún env/secreto se registra (auditoría `git status`)
- [ ] T056 [P] Frontend: test smoke en `frontend/tests/fiscales.test.tsx` (formulario factura renderiza y valida CIF/duplicado; página presentaciones renderiza botón deshabilitado en borrador) — `npx vitest run`
- [ ] T057 Manejo unificado de errores 409/422/400/403 en frontend (`frontend/src/lib/api.ts`) con mensajes comprensibles (patrón Defectos: duplicado, ejercicio cerrado, periodo sin cerrar)
- [ ] T058 Documentar en `specs/001-modulo-core-contable/tasks.md`: actualizar relación de módulos disponibles (Facturas, Libros IVA, Retenciones, IS, Presentaciones)
- [ ] T059 Ejecutar `quickstart.md` extremo a extremo (4 escenarios) y corregir desviaciones detectadas
- [ ] T060 Verificación final en orden: backend `..\.venv\Scripts\python.exe -m ruff check app tests` → `pytest -q`; frontend `npm run lint` → `npx tsc --noEmit` → `npm run build`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias — puede empezar ya
- **Foundational (Phase 2)**: depende de Setup; BLOQUEA todas las user stories
- **User Stories (Phase 3+)**: dependen de Foundational
  - US1 (P1) → US2 → US3 → US4 (dependencia de datos/servicio compartido)
  - US5 (P2) independiente de facturas, puede ejecutarse en paralelo con US1-US4
  - Presentación AEAT: depende de T012 y de datos de US3/US4/US5
- **Polish (final)**: depende de las user stories deseadas

### User Story Dependencies

- **US1**: tras Foundational — sin dependencias de otras stories
- **US2**: depende de US1 (mismo `services/facturas.py`)
- **US3**: depende de US1+US2 (datos)
- **US4**: depende de US2 (retenciones sobre compras)
- **US5**: independiente (solo Foundation)
- **US-PRES**: depende de Foundation (T012) + datos de US3/US4/US5

### Within each user story

- Tests se escriben y FALLAN antes de la implementación
- Modelos/servicios antes que endpoints; endpoints antes que integración
- Story completa antes de pasar a la siguiente prioridad

### Parallel Opportunities

- Todo lo marcado [P] en Setup/Foundational corre en paralelo (T002-T003; T005→T008; T011-T013)
- US5 puede empezar en paralelo a US1 (archivos `services/is.py`, `api/is.py`, `models/fiscal.py` ya creados en Foundation)
- Tests de una misma story marcados [P] corren en paralelo
- Models de una story marcados [P] corren en paralelo

---

## Parallel Example: User Story 1

```
# Tests de US1 en paralelo (FALLAN antes de implementar):
Task: "test_factura_venta_asiento_cuadrado en backend/tests/integration/test_facturas.py"
Task: "test_duplicado_cif_numero_ejercicio_409 en backend/tests/integration/test_facturas.py"
Task: "test_multi_tipo_iva_una_linea_por_tipo en backend/tests/integration/test_facturas.py"
Task: "test_factura_sin_contexto_400_sin_acceso_403 en backend/tests/integration/test_facturas.py"

# Implementación secuencial dentro de US1:
Task: "services/facturas.py crear_factura -> api/facturas.py -> FormFactura.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup (Phase 1) → Foundational (Phase 2) → **US1 (Phase 3)**
2. STOP y VALIDAR: `pytest backend/tests/integration/test_facturas.py`
3. Demo: alta de factura de venta con IVA y asiento cuadrado en Diario

### Incremental Delivery

1. Setup + Foundational → Foundation lista
2. US1 (MVP) → validar → demo
3. US2 (compras/RE) → US3 (libros IVA) → US4 (retenciones 111/115)
4. US5 (IS) puede ir en paralelo desde Foundation
5. Presentación AEAT (vista + fichero + descarga + `impuestos/`) sobre datos cerrados
6. Polish: quickstart + ruff→pytest→lint→tsc→build

### Parallel Team Strategy

- Developer A: US1 → US2 → US3 → US4 (cadena de facturas)
- Developer B: US5 (IS) en paralelo desde Foundation
- Developer C: Presentación AEAT tras T012 (generador base)

---

## Notes

- [P] = archivos distintos, sin dependencias
- [Story] asegura trazabilidad de cada tarea a su user story
- Cada user story debe poder completarse y probarse de forma independiente
- Verificar que los tests fallan antes de implementar (TDD por Constitución)
- Commit tras cada tarea o grupo lógico
- Parar en cualquier checkpoint para validar la story
- Evitar: tareas vagas, conflictos de archivo, dependencias cruzadas que rompan la independencia
- Gotchas AGENTS.md aplicables: Alembic (AutoString→sa.String + índices), enums como String, `Decimal`, slowapi en `app/rate_limit.py`, cuentas solo dígitos