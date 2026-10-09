# Investigación (Fase 0): Spec 2 — Hardening de Seguridad y Código

**Feature**: `002-security-code-hardening`
**Fecha**: 2026-10-09
**Entrada**: [spec.md](./spec.md) + hallazgos de auditoría (SEC-01…OPS-01) + [Clarifications](./spec.md#clarifications)

Todas las incógnitas del Contexto Técnico quedan resueltas. No queda ningún `NEEDS CLARIFICATION`.

---

## 1. Anti-CSRF en autenticación por cookie

- **Decisión**: Exigir la presencia de la cabecera `X-Requested-With: XMLHttpRequest` en toda petición mutacional (`POST`/`PUT`/`DELETE`) cuando la autenticación provenga de la cookie `access_token`. No se emite ni valida `X-CSRF-Token`. Respuesta denegada: HTTP 403 con `detail` que contenga "CSRF".
- **Rationale**: Defensa de "cabecera personalizada" estándar, sin coste de emisión/rotación de tokens. Una página cross-origin no puede fijar cabeceras personalizadas sin pasar por CORS, por lo que el navegador bloquea el envío. Encaja con slices verticales y con el objetivo de mínimo cambio.
- **Alternativas consideradas**:
  - `X-CSRF-Token` emitido por servidor (double-submit): más robusto pero añade endpoint de emisión, rotación y estado → fuera de alcance de Spec 2.
  - Token de sincronización en sesión: requiere almacenamiento de sesión que la app no tiene (JWT stateless).

## 2. Rate limiting del login

- **Decisión**: `slowapi` con `Limiter` aplicado a `/api/v1/auth/login`, clave = IP remota, contabilizando todas las peticiones (aciertos y fallos), límite `5/minute`. La sexta petición y siguientes devuelven HTTP 429.
- **Rationale**: `slowapi` es el limitador estándar para FastAPI/Starlette, clave por IP por defecto, y protege el coste de CPU de Argon2. Contar todas las peticiones evita que un atacante consuma el cupo solo con fallos mientras los aciertos quedan exentos.
- **Alternativas consideradas**:
  - Clave IP+username: permite rotar usuarios para eludir el límite; se descartó.
  - Limitar solo intentos fallidos: exige lógica de post-proceso en el handler y complica el test; se descartó.
  - Limitador propio con SQLite: reinventa la rueda y añade escrituras en la ruta caliente.
- **Impacto**: nueva dependencia `slowapi` en `pyproject.toml` (actualmente **no instalada**).

## 3. Secreto JWT obligatorio en todos los entornos

- **Decisión**: `jwt_secret` sin valor por defecto (obligatorio). Eliminar el fallback `"dev-only-secret-…-change-me"` de `app/config.py`. `backend/tests/conftest.py` define `APP_JWT_SECRET` de prueba y `.env.example` documenta la generación segura. En `environment == "production"` se valida longitud ≥ 32 y ausencia de `change-me`.
- **Rationale**: Cierra SEC-01 (falsificación de tokens con rol admin). Falla de forma temprana y explícita en lugar de arrancar con un secreto conocido.
- **Alternativas consideradas**:
  - Fallback solo en dev: reintroduce la vulnerabilidad en el entorno más probable de robo/olvido; se descartó (ver Clarifications).
  - Secreto aleatorio efímero por arranque: invalida tokens en cada reinicio y complica pruebas; se descartó.

## 4. Migración de auditoría (LEGAL-01)

- **Decisión**: Migración Alembic encadenada tras `bb1c920e98ab` que añade a `asiento`: `creado_por_usuario_id` (FK `usuario.id`, `ON DELETE RESTRICT`), `asentado_por_usuario_id` (FK nullable), `created_at` (`DateTime(timezone=True)`), `asentado_at` (nullable) y `version` (int, default 1). Estrategia de upgrade: añadir columnas como **nullable** → backfill a un usuario admin/sistema → aplicar `NOT NULL` a `creado_por_usuario_id` y `created_at`. Índice compuesto `ix_asiento_ejercicio_estado_fecha`.
- **Rationale**: La única forma auditable de introducir columnas `NOT NULL` (requisito de trazabilidad legal) sin romper el upgrade. En la BD de desarrollo actual no hay asientos ni PGC, por lo que el backfill es un no-op; la migración se escribe igualmente defensiva.
- **Alternativas consideradas**:
  - `server_default` sin backfill: deja datos históricos sin trazabilidad real; insuficiente para Ley Antifraude.
  - Recrear la BD: válido solo en dev; no sirve como migración reproducible en entornos con datos.
- **Autogenerate**: `alembic revision --autogenerate` emite `AutoString` sin import y omite índices FK; las revisiones se corrigen a mano (`sa.String(...)`, `ix_*`) antes de `upgrade head` (gotcha de AGENTS.md).

## 5. Partida doble en `asentar` (CONT-01)

- **Decisión**: `services/asientos.asentar()` debe cargar los apuntes persistidos y verificar `len(apuntes_db) >= 2` **y** Δ = 0 antes de asignar correlativo y cambiar a `asentado`. Mensaje que contenga "al menos 2".
- **Rationale**: Aunque `AsientoRequest` exige `min_length=2` al crear el borrador, un asiento puede quedar sin apuntes por vía directa/BD o por ediciones; el asiento legal (inmutable) no debe poder quedar vacío. El chequeo en el punto de asentar es el último punto de control.
- **Alternativas consideradas**:
  - Confiar solo en la validación Pydantic de entrada: no cubre inserciones directas ni corrupción previa.
  - CHECK constraint de BD: SQLite no permite subconsulta sobre otra tabla en CHECK; se descartó.

## 6. Correlativo y concurrencia (CONC-01)

- **Decisión**: Mantener el patrón actual `range(5)` + `func.max(numero)+1` + captura de `IntegrityError` apoyado en la restricción `uq_asiento_ejercicio_numero`. El campo `version` se incrementa en servidor pero **no** se valida contra el cliente en Spec 2 (concurrencia optimista → Fase 2).
- **Rationale**: SQLite en modo WAL serializa las escrituras; la restricción única garantiza que dos correlativos colisionen y que el reintento resuelva. Evita el 409 espurio y el riesgo de asientos desbalanceados sin introducir todavía el protocolo optimista completo.
- **Alternativas consideradas**:
  - Secuencia dedicada por ejercicio: requiere tabla de contadores y bloqueo; complejidad para Fase 1.
  - `BEGIN IMMEDIATE` a nivel de aplicación: mejora el determinismo pero acopla la capa de servicio al motor.

## 7. Paginación sin volcado de tablas (PERF-01)

- **Decisión**: Calcular `total` con `select(func.count(...)).where(...)` usando los mismos filtros que la consulta de datos, tanto en `api/asientos.py` (`diario`, `borradores`) como en `api/cuentas.py` (`listar_cuentas`). Mantener `offset`/`limit` con `Query(ge=…)`/`le=200`.
- **Rationale**: Evita materializar toda la tabla en RAM (OOM). El contrato de respuesta se mantiene `{ total, offset, limit, items }` (`Paginado[T]`).
- **Alternativas consideradas**: Ventanas SQL (`COUNT(*) OVER()`): SQLite soportada, pero `func.count` es más simple y ya está parcialmente implementada.

## 8. Eliminación de N+1 en apuntes (PERF-02)

- **Decisión**: `services/asientos.obtener_apuntes()` usa una única consulta con `JOIN` a `Cuenta` para traer `cuenta_codigo`. `api/asientos._totales()` usa agregación `func.sum`. Nombre público único `obtener_apuntes` (sin variantes `_optimizados`).
- **Rationale**: Una consulta por asiento en lugar de N; imprescindible para la página del Diario con muchos apuntes.
- **Alternativas consideradas**: `selectinload`/relaciones ORM: SQLModel aquí no define relaciones; el JOIN explícito es más directo.

## 9. Aislamiento multi-tenant y RBAC (SEC-03, SEC-04)

- **Decisión**:
  - `get_empresa_context` valida 400 si falta/está vacía/ no numérica la cabecera `X-Empresa-Id`; 404 si la empresa no existe; 403 con "inactiva" si `Empresa.activa == False`; 403 si el usuario no está vinculado (`empresa_usuario`).
  - `POST /api/v1/ejercicios` exige `usuario.rol == "admin"` (403 con "admin" en el mensaje).
- **Rationale**: Cierra IDOR sobre tenants suspendidos y la escalada de privilegios del rol contable.
- **Defecto detectado a corregir**: `api/empresas.py` referencia `ApiError` **sin importarlo** en `crear_ejercicio` → `NameError` en ejecución. El slice 3 debe añadir el import (`from app.api.errors import ApiError`).

## 10. `/health` sin reconocimiento (SEC-06)

- **Decisión**: `/api/v1/health` devuelve únicamente `{"status": "ok"}`. Se eliminan `db`, `busy_timeout`, `foreign_keys` y `migrations`. El estado de pragmas queda solo en logs de arranque (`lifespan`).
- **Rationale**: Elimina el vector de reconocimiento de infraestructura sin perder el liveness.
- **Alternativas consideradas**: readiness con `{"database":"ok"}`: se valoró; se descartó para el mínimo alcance de Spec 2 (ver Clarifications).

## 11. Rate limiting — configuración

- **Decisión**: Añadir `app.state.limiter = Limiter(key_func=get_remote_address)` y el `SlowAPIMiddleware`/exception handler en `main.py`; decorar `login` con `@limiter.limit("5/minute")` (o el valor de `settings.rate_limit_login`).
- **Rationale**: Integración estándar de `slowapi`; el límite se hace configurable vía `Settings.rate_limit_login`.
- **Nota de test**: `TestClient` comparte la misma IP (`testclient`); los tests de rate limit deben usar un `Limiter` con almacenamiento reseteable o comprobar el 429 tras 6 llamadas en el mismo test.

## 12. Frontend: CSRF, aritmética y MUI (FRONT-01, FRONT-02, Slice 6)

- **Decisión**:
  - `src/lib/api.ts`: añadir `X-Requested-With: XMLHttpRequest` a toda petición con método distinto de GET en el helper `request`.
  - `calcularDelta` ya opera en céntimos enteros (`Math.round(x*100)`); se confirma y se cubre con test. `filaEstaCuadrada` puede normalizarse a céntimos para coherencia.
  - `FormAsiento.tsx`: migrar **solo** los controles interactivos (`TextField`, `Select`, `Button` de MUI v6) conservando `data-testid`; no se rehace el layout.
- **Rationale**: Cumple FRONT-01/FRONT-02 y evita romper la app al activar el guard CSRF, con el mínimo cambio de UI.
- **Alternativas consideradas**: Rehacer el layout completo con Grid (fuera de alcance); detectar cookie en cliente para la cabecera (más frágil que añadirla siempre en mutaciones).

## 13. Resolución de incógnitas del Contexto Técnico

| Incógnita | Resolución |
|-----------|------------|
| Dependencia de rate limiting | `slowapi` (nueva) |
| Compatibilidad CSRF con cookie | Cabecera `X-Requested-With` en todas las mutaciones (backend + frontend) |
| Estrategia de migración `NOT NULL` | nullable → backfill → `NOT NULL` |
| Uso de `version` | Solo servidor; validación diferida a Fase 2 |
| Contrato `/health` | `{"status": "ok"}` |
| Alcance MUI | Solo controles interactivos |

**Salida**: todas las incógnitas resueltas; listo para el diseño de Fase 1.
