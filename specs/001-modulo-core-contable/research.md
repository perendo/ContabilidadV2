# Research — 001-modulo-core-contable (Fase 1)

Fase 0 del plan (revisión 2026-10-08, tras aclaraciones). Resuelve los
NEEDS CLARIFICATION y decisiones tecnológicas. Se re-emite porque las
aclaraciones de la sesión 2026-10-08 cambian decisiones previas: **borrador
editable** (sustituye a D6), **asientos múltiples** y **Alembic**.

## D1. Modelo multi-tenant: BD única con aislamiento lógico

**Decision**: una única base SQLite compartida; aislamiento lógico por
`empresa_id`/`ejercicio_id` en todas las entidades, reforzado por
dependencias FastAPI que validan pertenencia (usuario → empresa vía
`EmpresaUsuario`; ejercicio → empresa). **(sin cambios)**

**Rationale**: el entorno es multipuesto sobre una única instancia en LAN;
además Alembic, WAL y backups se gestionan una sola vez.

**Alternativas consideradas**: DB por tenant (rechazada: complejidad
operativa, dificulta consolidados futuros); schemas por tenant (no soportado
por SQLite).

## D2. Autenticación: JWT + cookie httpOnly, argon2

**Decision**: `POST /api/v1/auth/login` emite JWT (PyJWT) con expiración por
defecto 12 h, almacenado en cookie httpOnly + SameSite=Lax. Recuperación del
usuario por cookie. Hash de contraseña con **argon2-cffi**. Política de
contraseñas: longitud mínima **8**, sin caducidad ni bloqueo (FR-017). **(parcialmente actualizado: argon2 y política)**

**Rationale**: "autenticación básica" para LAN; cookie httpOnly mitiga XSS;
argon2 sobre bcrypt por defectos de algoritmo; política mínima suficiente
para usuarios internos.

**Alternativas consideradas**: Bearer en localStorage (rechazado: XSS);
sesión con tabla propia (innecesaria en Fase 1); OAuth/SSO (fuera de
alcance).

## D3. ORM + migraciones: SQLModel + Alembic

**Decision**: modelos SQLModel sobre SQLAlchemy 2.x; **Alembic** gestiona
todas las migraciones desde el arranque (FR-021). El `env.py` apunta a la
metadata de los modelos (declarative base); se incluye `alembic init` +
revisión inicial en el slice 1. Prohibido `create_all` en producción.

**Rationale**: Alembic da evolución del esquema auditable (crucial para un
sistema contable cuyo esquema cambiará en Fase 2: cierres, IVA, facturación)
y permite migrar BD existentes en despliegues multipuesto; `create_all` solo
para tests aislados si conviene, aunque la norma es migrar siempre.

**Alternativas consideradas**: `create_all` + diffs manuales (rechazado:
sin historial ni rollback); SQLAlchemy `MetaData.create_all` (mismo problema);
herramientas NoSQL-style (n/a).

## D4. Correlativo de asiento: MAX+1 transaccional al asentar

**Decision**: el número se asigna en el momento de **asentar** (no al
guardar borrador), dentro de la misma transacción:
`SELECT COALESCE(MAX(numero),0)+1 FROM asiento WHERE ejercicio_id = ?`,
respaldado por `UNIQUE(ejercicio_id, numero)` y un reintento ante carrera.

**Rationale**: WAL ⇒ un único escritor ⇒ MAX+1 correcto; UNIQUE como red de
seguridad. Los borradores no consumen número (coherente con FR-009).

**Alternativas consideradas**: tabla `counters`; UUID como número visible
(rompe correlativo contable) — ambas rechazadas.

## D5. Importes: Decimal de Python 2dp, columnas NUMERIC

**Decision**: la API acepta/devuelve importes como cadena decimal (`Decimal`,
2 decimales exactos, `ge=0`). Columnas SQLite `NUMERIC`. Cualquier suma de
cuadre se computa en `Decimal` de Python (nunca float ni agregación SQL sin
revisar). Se revisará la estrategia en Fase 2 si aparecen agregados SQL
(Balance de Sumas y Saldos) → posible movimiento a céntimos INTEGER.

**Rationale**: invariante de cuadre en la capa de servicio, sin drift a esta
escala.

## D6. Flujo de asientos: BORRADOR EDITABLE → ASENTADO (ACTUALIZADO)

**Decision (reemplaza a la anterior)**: el asiento tiene ciclo de vida activo
en Fase 1:

```text
(nuevo) ──POST /asientos (estado='borrador')──> borrador
borrador ──PUT /asientos/{id} (dentro de borrador)──> borrador (editable)
borrador ──POST /asientos/{id}/asentar──> asentado (exige ΣDebe = ΣHaber)
asentado ──(sin transiciones)──> inmutable
```

- Guardar/actualizar `borrador`: permite descuadres (FR-007/FR-012) y
  `apuntes` con líneas 2..N (FR-020).
- `asentar`: valida en servidor Σ debe − Σ haber = 0 sobre **todas** las
  líneas, genera correlativo, y persiste el cambio en la misma transacción.
- Un borrador nunca aparece como asiento definitivo del Diario contable con
  numeración; el Diario puede listarlo en su pestaña "Borradores"
  (FR-018).

**Rationale**: decisión de producto explícita (sesión 2026-10-08): se
quiere poder guardar parcialmente antes de cuadrar; la separación
borrador/asentado es la práctica contable estándar (borrador = no
numerado, asentado = numerado y definitivo).

**Alternativas consideradas**: solo asentado directo (rechazada por el
usuario); borrador solo en cliente (rechazada: se pidió persistencia).

## D7. Ejercicio cerrado: bloqueo en capa de servicio (409)

**Decision**: cualquier escritura (crear cuenta, guardar/actualizar/asentar
asiento) valida `ejercicio.estado = 'abierto'`; si `cerrado` → 409. No hay
endpoint de cierre en Fase 1 (el cierre con validaciones se habilita en
Fase 2). **(sin cambios significativos)**

## D8. Asientos múltiples (2..N líneas) (NUEVO)

**Decision**: un asiento admite de 2 a N apuntes sin límite superior en
Fase 1 (FR-020). La validación de cuadre se aplica al **conjunto** (Σ sobre
todas las líneas), no por pares. Por línea: exactamente uno de `debe`/`haber`
> 0 (mixtas o en ceros → 422).

**Rationale**: la práctica contable real usa asientos con varios Debe y
varios Haber (p. ej. pagos con retención, IVA, descuentos); el invariante
es del conjunto.

## D9. Frontend MD3 con MUI v6 (NUEVO)

**Decision**: MUI v6 con tema **Material Design 3** (FR-015/FR-016): tokens
de color/tipografía/elevación configurables, scheme claro/oscuro, use
Next.js App Router con Server Components por defecto y Client Components en
los formularios reactivos. Estados de UI con componentes M3 (FR-019):
Snackbar/Alert para errores, empty states y skeletons.

**Rationale**: MUI v6 es la vía robusta y accesible para MD3 en React;
theming por tokens evita reimplementar componentes.

**Alternativas consideradas**: `@material/web` (componentes web Lit, chocan
con el modelo React), NextUI (tema MD3 aproximado), tokens CSS a mano
(esfuerzo y a11y) — rechazadas.

## D10. Persistencia de contexto activo: cookies

**Decision**: el selector global escribe `empresa_id`/`ejercicio_id` en
cookies (no httpOnly, `SameSite=Lax`); las llamadas API incluyen
`X-Empresa-Id`/`X-Ejercicio-Id` desde esas cookies; el contexto React refleja
las cookies. **(sin cambios)**

## D11. Diario expandible + gestión de borradores (NUEVO)

**Decision**: la vista Diario lista asientos asentados (paginada/filtrable,
FR-013) y una pestaña de borradores (FR-018). Cada fila se expande para ver
apuntes vía `GET /api/v1/asientos/{id}`. Los borradores listados se pueden
abrir en el formulario para continuarlos y asentarlos.

**Rationale**: sin detalle no se audita el asiento; sin listado de
borradores el flujo borrador sería un callejón sin salida.

**Alternativas consideradas**: página de detalle dedicada (rechazada:
expansión en tabla es más ágil para revisión contable).

## D12. Estrategia de testing

**Decision**: pytest + `httpx.AsyncClient(ASGITransport)` sobre BD temporal
creada con `alembic upgrade head` (garantiza que las migraciones funcionan).
Tests prioritarios (mapean SC): cuadre N-líneas válido/inválido, transición
borrador→asentado (descuadrado → 422), ejercicio cerrado (409), unicidad de
código de cuenta y de número, independencia de correlativo por ejercicio,
pertenencia de contexto (403), concurrencia WAL. Frontend: vitest para Δ y
bloqueo de asentar.

**Rationale**: la constitución exige pruebas de cálculo/cuadre antes de
liberar; usar Alembic en los tests valida las migraciones a la vez.

## D13. Estructura de cuentas PGC

**Decision**: `Cuenta` con `codigo` (dígitos, 1–10 chars), `nombre`,
`nivel` (1–5); única por `(ejercicio_id, codigo)`. Alta manual por
ejercicio en Fase 1. **(sin cambios)**