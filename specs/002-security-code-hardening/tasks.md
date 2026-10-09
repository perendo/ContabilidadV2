---

description: "Lista de tareas para la implementación de la feature"
---

# Tareas: Spec 2 — Hardening de Seguridad y Código

**Entrada**: Documentos de diseño en `specs/002-security-code-hardening/`

**Prerrequisitos**: plan.md (obligatorio), spec.md (obligatorio), research.md, data-model.md, contracts/

**Tests**: SÍ se incluyen. La spec exige explícitamente tests de regresión de seguridad (sección 4 de spec.md) y la Constitución requiere cobertura de la lógica de cuadre antes de liberar.

**Organización**: Las tareas se agrupan por historia de usuario (una por slice de la spec) para permitir implementación y prueba independientes. Prioridades: P1 (Crítica), P2 (Alta/Media), P3 (Baja).

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Story]**: Historia de usuario a la que pertenece (US1…US6)
- Se incluye la ruta exacta de archivo en cada tarea

## Convenciones de rutas

- **Backend**: `backend/app/`, `backend/tests/`, `backend/alembic/versions/`
- **Frontend**: `frontend/src/`, `frontend/tests/`

---

## Fase 1: Setup (Infraestructura compartida)

**Propósito**: Preparar dependencias y baseline antes de tocar código.

- [X] T001 [P] Añadir la dependencia `slowapi` a `[project].dependencies` en `backend/pyproject.toml` e instalar con `..\.venv\Scripts\python.exe -m pip install -e ".[dev]"` (desde `backend/`)
- [X] T002 [P] Registrar el baseline ejecutando `..\.venv\Scripts\python.exe -m ruff check app tests` y `..\.venv\Scripts\python.exe -m pytest -q` desde `backend/`, y anotar el estado inicial

---

## Fase 2: Fundacional (Prerrequisitos bloqueantes)

**Propósito**: Habilitar la suite de tests antes de las historias. Al hacerse obligatorio `jwt_secret` (US1), ninguna prueba puede ni importar la app sin esta base.

**⚠ CRÍTICO**: Ninguna historia puede empezar hasta completar esta fase.

- [X] T003 Definir la variable de entorno `APP_JWT_SECRET` de prueba (≥ 32 caracteres) en `backend/tests/conftest.py` ANTES de importar `app.*`, y llamar a `get_settings.cache_clear()`
- [X] T004 [P] Revisar/ajustar las fixtures compartidas `contexto`, `make_usuario(rol=...)`, `make_cuenta` y `auth_headers` en `backend/tests/conftest.py` para que US2–US5 puedan construir escenarios sin duplicación

**Checkpoint**: Base lista — las historias pueden empezar.

---

## Fase 3: US1 — Hardening de configuración y secretos (Prioridad: P1) 🎯 MVP

**Hallazgos**: SEC-01 (crítica).
**Objetivo**: Eliminar el secreto JWT por defecto y hacerlo obligatorio en todos los entornos, con validación reforzada en producción.
**Prueba independiente**: Con `APP_JWT_SECRET` ausente la construcción de `Settings` falla; en `environment="production"` un secreto débil lanza error. `pytest tests/unit/test_config.py` en verde.

### Tests para US1

- [X] T005 [P] [US1] Crear `backend/tests/unit/test_config.py`: (a) `Settings()` sin `APP_JWT_SECRET` lanza `ValidationError`; (b) con `environment="production"` y secreto de < 32 caracteres o que contenga "change-me" lanza `ValueError`

### Implementación para US1

- [X] T006 [US1] Modificar `backend/app/config.py`: `jwt_secret: str` **sin valor por defecto**; `jwt_expires_seconds: int = 3600` (máximo 1 hora); añadir `environment: str = "development"`; añadir `rate_limit_login: str = "5/minute"`; añadir `@model_validator(mode="after")` que en producción exija `len(jwt_secret) >= 32` y sin "change-me"
- [X] T007 [US1] Actualizar `backend/.env.example`: documentar la generación segura de `APP_JWT_SECRET` (p. ej. `python -c "import secrets; print(secrets.token_urlsafe(48))"`) y quitar cualquier valor tipo `change-me`

**Checkpoint**: US1 funcional y verificable de forma aislada.

---

## Fase 4: US2 — Integridad contable: partida doble, trazabilidad y correlativo (Prioridad: P1) 🎯

**Hallazgos**: CONT-01 (crítica), LEGAL-01 (alta), CONC-01 (alta).
**Objetivo**: Impedir el asentado de asientos vacíos o descuadrados, añadir trazabilidad legal (Ley Antifraude 11/2021) y robustecer el correlativo.
**Prueba independiente**: `test_asentar_asiento_sin_apuntes_retorna_422` y el test de trazabilidad pasan; `alembic upgrade head` y `downgrade -1` funcionan.

### Tests para US2

- [X] T008 [P] [US2] Asegurar en `backend/tests/integration/test_security_hardening.py` el test `test_asentar_asiento_sin_apuntes_retorna_422` (HTTP 422 y `detail` contiene "al menos 2")
- [X] T009 [P] [US2] Añadir test de trazabilidad en `backend/tests/integration/test_security_hardening.py`: al crear un borrador se persiste `creado_por_usuario_id`/`created_at`; al asentar se persisten `asentado_por_usuario_id`/`asentado_at` y `version` incrementa
- [X] T010 [P] [US2] Verificar que `backend/tests/integration/test_concurrency.py` sigue verde tras los cambios de correlativo

### Implementación para US2

- [X] T011 [P] [US2] Añadir a `backend/app/models/contable.py` en `Asiento`: `creado_por_usuario_id` (FK `usuario.id` `ondelete="RESTRICT"`, `nullable=False`), `asentado_por_usuario_id` (FK `usuario.id` RESTRICT, nullable), `created_at` (`DateTime(timezone=True)`, `nullable=False`, default UTC), `asentado_at` (`DateTime(timezone=True)`, nullable), `version: int = 1` (no nulo); e índice `ix_asiento_ejercicio_estado_fecha` sobre `(ejercicio_id, estado, fecha)`
- [X] T012 [US2] Crear la migración Alembic `<rev>_trazabilidad_auditoria_asientos.py` en `backend/alembic/versions/` con `down_revision = "bb1c920e98ab"`: añadir columnas como nullable → backfill a usuario admin/sistema + `created_at=now()` → aplicar `NOT NULL` a `creado_por_usuario_id` y `created_at` → crear `ix_asiento_ejercicio_estado_fecha`; `downgrade()` en orden inverso. Sustituir `AutoString` por `sa.String(...)` y añadir los `ix_*` a mano
- [X] T013 [US2] En `backend/app/services/asientos.py` `asentar(session, asiento, usuario_id)`: cargar los apuntes persistidos; si `len(apuntes_db) < 2` → `ApiError(422, "Un asiento contable requiere al menos 2 líneas de apunte")`; si `Δ ≠ 0` → `ApiError(422, ...)`; al asignar correlativo fijar `estado="asentado"`, `asentado_por_usuario_id=usuario_id`, `asentado_at=datetime.now(UTC)` e incrementar `version`
- [X] T014 [US2] En `backend/app/services/asientos.py` `guardar_borrador(...)` y `editar_borrador(...)`: aceptar `usuario_id`, fijar `creado_por_usuario_id` al crear y actualizar `fecha`/`concepto` incrementando `version` al editar
- [X] T015 [US2] En `backend/app/api/asientos.py`: inyectar `UsuarioDep` en `crear_borrador`, `editar_borrador` y `asentar`, y propagar `usuario.id` a los servicios de US2
- [X] T016 [US2] Exponer los campos de trazabilidad (`numero` ya existe; añadir `created_at`, `asentado_at` si aporta) en `backend/app/schemas/asientos.py` `AsientoOut` de forma opcional y actualizar `_to_out` en `backend/app/api/asientos.py`

**Checkpoint**: US2 funcional y verificable de forma aislada (incluida la migración reversible).

---

## Fase 5: US3 — Aislamiento multi-tenant y RBAC (Prioridad: P2)

**Hallazgos**: SEC-03 (alta), SEC-04 (media).
**Objetivo**: Bloquear el acceso a empresas inactivas/no vinculadas y restringir la creación de ejercicios al rol admin.
**Prueba independiente**: `test_empresa_inactiva_retorna_403` y `test_usuario_contable_no_puede_crear_ejercicio_403` pasan.

### Tests para US3

- [X] T017 [P] [US3] Test `test_empresa_inactiva_retorna_403` en `backend/tests/integration/test_security_hardening.py` (403 y `detail` contiene "inactiva")
- [X] T018 [P] [US3] Test `test_usuario_contable_no_puede_crear_ejercicio_403` en `backend/tests/integration/test_security_hardening.py` (403 y `detail` contiene "admin")

### Implementación para US3

- [X] T019 [US3] En `backend/app/api/deps.py` `get_empresa_context`: `400` si falta/vacía/no numérica la cabecera; `404 "Empresa no encontrada"` si no existe; `403` con "inactiva" si `Empresa.activa is False`; `403 "Sin acceso a la empresa"` si no hay vínculo en `empresa_usuario`
- [X] T020 [US3] En `backend/app/api/empresas.py`: importar `ApiError` desde `app.api.errors` (corrige el `NameError` actual) y en `crear_ejercicio` exigir `usuario.rol == "admin"` → `ApiError(403, "Solo el rol admin puede crear ejercicios")`

**Checkpoint**: US3 independientemente funcional usando solo `contexto` y `make_usuario`.

---

## Fase 6: US4 — Rendimiento de BD y mitigación de DoS (Prioridad: P2)

**Hallazgos**: PERF-01 (alta), PERF-02 (media).
**Objetivo**: Eliminar el volcado de tablas (`len(...all())`) y el N+1 de apuntes.
**Prueba independiente**: `test_paginacion_utiliza_count_y_limita_items` pasa; el detalle de asiento usa una sola consulta JOIN.

### Tests para US4

- [X] T021 [P] [US4] Test `test_paginacion_utiliza_count_y_limita_items` en `backend/tests/integration/test_security_hardening.py` (200, `total` presente, `len(items) <= limit`)

### Implementación para US4

- [X] T022 [US4] En `backend/app/api/asientos.py`: calcular `total` con `select(func.count(Asiento.id))` con los mismos filtros que la consulta de datos, en `diario` y `borradores` (sin `len(...all())`)
- [X] T023 [US4] En `backend/app/api/cuentas.py`: calcular `total` con `select(func.count(Cuenta.id))` con los mismos filtros (query/nivel) en `listar_cuentas`
- [X] T024 [US4] En `backend/app/services/asientos.py`: mantener `obtener_apuntes()` como consulta única con `JOIN` a `Cuenta` (sin N+1) y `_totales()` con `func.sum`

**Checkpoint**: US4 funcional; latencia independiente del número de apuntes.

---

## Fase 7: US5 — Autenticación: CSRF, rate limit y health (Prioridad: P2)

**Hallazgos**: SEC-02 (alta), SEC-05 (alta), SEC-06 (baja).
**Objetivo**: Añadir defensa anti-CSRF en cookie-auth, limitar el login a 5/min por IP y sanear `/health`.
**Prueba independiente**: mutación con cookie sin cabecera → 403 "CSRF"; 6.ª petición a login en < 1 min → 429; `/health` == `{"status":"ok"}`.

### Tests para US5

- [X] T025 [P] [US5] Test `test_mutacion_con_cookie_sin_cabecera_csrf_rechazada` en `backend/tests/integration/test_security_hardening.py` (403 y `detail` contiene "csrf")
- [X] T026 [P] [US5] Test `test_health_no_expone_detalles_internos` en `backend/tests/integration/test_security_hardening.py` (200, sin `journal_mode`/`busy_timeout`, `body["status"] == "ok"`)
- [X] T027 [P] [US5] Test de rate limit en `backend/tests/integration/test_security_hardening.py`: 6 llamadas seguidas a `POST /api/v1/auth/login` desde la misma IP → la 6.ª devuelve 429

### Implementación para US5

- [X] T028 [US5] En `backend/app/main.py`: crear `Limiter(key_func=get_remote_address)`, asignarlo a `app.state.limiter`, registrar `SlowAPIMiddleware` y el handler de `RateLimitExceeded`; el límite se lee de `Settings.rate_limit_login`
- [X] T029 [US5] En `backend/app/api/auth.py`: decorar `login` con `@limiter.limit(_settings.rate_limit_login)` y añadir el parámetro `request: Request`
- [X] T030 [US5] En `backend/app/api/deps.py`: añadir dependencia/guard que exija, cuando la autenticación provenga de la cookie `access_token`, la cabecera `X-Requested-With: XMLHttpRequest` en `POST`/`PUT`/`DELETE`, devolviendo `ApiError(403, "... CSRF ...")` en caso contrario; `Authorization: Bearer` queda exento
- [X] T031 [US5] Sanear `GET /api/v1/health` en `backend/app/main.py` para devolver únicamente `{"status": "ok"}` (eliminar `db`, `busy_timeout`, `foreign_keys`, `migrations`); dejar `sqlite_pragmas_state()` en `backend/app/db.py` solo para los logs de arranque (`lifespan`)
- [X] T032 [US5] En `frontend/src/lib/api.ts`: añadir la cabecera `X-Requested-With: XMLHttpRequest` a toda petición `POST`/`PUT`/`DELETE` en el helper `request`, y crear el test `frontend/tests/api.test.ts` que verifique su envío

**Checkpoint**: US5 funcional; la app completa (frontend incluido) sigue operando tras activar el guard CSRF.

---

## Fase 8: US6 — Precisión aritmética y UI frontend (Prioridad: P3)

**Hallazgos**: FRONT-01 (media), FRONT-02 (baja).
**Objetivo**: Δ en céntimos enteros y controles de `FormAsiento` migrados a MUI v6.
**Prueba independiente**: `npm test` (incluye `FormAsiento.test.tsx`) y `npm run build` en verde.

### Tests para US6

- [X] T033 [P] [US6] Afianzar en `frontend/tests/FormAsiento.test.tsx` el cálculo de Δ en céntimos enteros (p. ej. `0.1 + 0.2` no produce descuadre falso)

### Implementación para US6

- [X] T034 [US6] En `frontend/src/components/FormAsiento.tsx`: confirmar `calcularDelta` sobre céntimos (`Math.round(x*100)`) y normalizar `filaEstaCuadrada` a céntimos para coherencia
- [X] T035 [US6] En `frontend/src/components/FormAsiento.tsx`: migrar **solo** los controles interactivos (`TextField`, `Select`, `Button` de MUI v6) conservando todos los `data-testid` (`fecha`, `concepto`, `fila-N`, `delta`, `guardar-borrador`, `asentar`); no rehacer el layout

**Checkpoint**: US6 funcional de forma aislada.

---

## Fase 9: Polish y aspectos transversales

**Propósito**: Mejoras que afectan a varias historias y limpieza.

- [X] T036 [P] OPS-01: hacer portable `start_servers.py` (detectar SO y evitar `cmd /k`/`taskkill`; usar `subprocess` y terminación de procesos compatible con Linux)
- [X] T037 [P] Reconciliar el duplicado `specs/02-security-hardening.md` con `specs/002-security-code-hardening/spec.md` (actualizar o eliminar el duplicado)
- [X] T038 [P] Ejecutar la validación de `specs/002-security-code-hardening/quickstart.md` (flujo de curl, migración up/down y tests)
- [X] T039 Ejecutar verificación final completa: backend `ruff check app tests` → `pytest -q`; frontend `npm run lint` → `npx tsc --noEmit` → `npm run build`
- [X] T040 Marcar `[X]` las casillas completadas en este `specs/002-security-code-hardening/tasks.md`

---

## Dependencias y orden de ejecución

### Dependencias entre fases

- **Setup (Fase 1)**: sin dependencias
- **Fundacional (Fase 2)**: depende de Setup — BLOQUEA las historias
- **Historias (Fases 3–8)**: dependen del Fundacional
  - Pueden ejecutarse en paralelo (si hay capacidad)
  - O secuencialmente por prioridad: P1 → P2 → P3
- **Polish (Fase 9)**: depende de las historias deseadas

### Dependencias entre historias

- **US1 (P1)**: independiente (introduce la obligatoriedad de `jwt_secret`)
- **US2 (P1)**: independiente; toca `models/contable.py`, migración, `services/asientos.py`, `api/asientos.py`, `schemas/asientos.py`
- **US3 (P2)**: independiente; toca `api/deps.py`, `api/empresas.py` (T019 comparte `api/deps.py` con US5/T030 → coordinar)
- **US4 (P2)**: independiente; toca `api/asientos.py`, `api/cuentas.py`, `services/asientos.py` (comparte `services/asientos.py` con US2)
- **US5 (P2)**: independiente; toca `main.py`, `api/auth.py`, `api/deps.py`, `frontend/src/lib/api.ts`
- **US6 (P3)**: independiente; toca solo `frontend/src/components/FormAsiento.tsx` y sus tests

> **Archivos compartidos a coordinar**: `backend/app/api/deps.py` (US3, US5), `backend/app/services/asientos.py` (US2, US4), `backend/app/api/asientos.py` (US2, US4).

### Dentro de cada historia

- Los tests se escriben y FALLAN antes de la implementación
- Modelos antes que servicios; servicios antes que endpoints
- Implementación antes de la integración

### Oportunidades de paralelización

- Setup: T001, T002 en paralelo
- Fundacional: T004 puede ir en paralelo con T003
- Tests de cada historia marcados [P] en paralelo
- Tras el Fundacional, US1–US6 pueden abordarse por distintos desarrolladores (respetando los archivos compartidos)

---

## Ejemplo paralelo: US2

```bash
# Lanzar los tests de US2 en paralelo:
Task: "Test asentar sin apuntes en backend/tests/integration/test_security_hardening.py"
Task: "Test de trazabilidad en backend/tests/integration/test_security_hardening.py"

# Modelo y migración (archivos distintos):
Task: "Campos de auditoría en backend/app/models/contable.py"
Task: "Migración de trazabilidad en backend/alembic/versions/"
```

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1: Setup
2. Completar Fase 2: Fundacional (CRÍTICO)
3. Completar Fase 3: US1
4. **PARAR Y VALIDAR**: probar US1 de forma independiente
5. Desplegar/demostrar si procede

> Nota: CONT-01 (US2) es igualmente crítica desde el punto de vista legal; se recomienda tratar US1 + US2 como MVP mínimo de seguridad contable.

### Entrega incremental

1. Setup + Fundacional → base lista
2. US1 → probar → (MVP de secretos)
3. US2 → probar → (integridad contable + trazabilidad)
4. US3 → US4 → US5 → US6 → cada una añade valor sin romper las anteriores
5. Polish → verificación transversal

### Estrategia de equipo en paralelo

1. El equipo completa Setup + Fundacional
2. Después:
   - Dev A: US1 y US2 (P1)
   - Dev B: US3 y US4 (P2)
   - Dev C: US5 y US6 (P3)
3. Coordinar los archivos compartidos indicados arriba

---

## Notas

- [P] = archivos distintos, sin dependencias
- [Story] asocia la tarea a su historia para trazabilidad
- Cada historia debe ser completable y testeable de forma independiente
- Verificar que los tests fallan antes de implementar
- Commit tras cada tarea o grupo lógico (solo si se solicita)
- Evitar: tareas vagas, conflictos de archivo y dependencias entre historias
