# Modelo de Datos (Fase 1): Spec 2 — Hardening de Seguridad y Código

**Feature**: `002-security-code-hardening`
**Fecha**: 2026-10-09

Este documento describe únicamente las entidades y cambios de esquema afectados por Spec 2. El esquema base proviene de la migración `bb1c920e98ab` (Fase 1). Todos los cambios de esquema se aplican **solo** vía Alembic.

---

## 1. Diagrama de relaciones (afectado)

```text
Usuario (usuario)
  └─< empresa_usuario >─ Empresa (empresa)
                            └─< Ejercicio (ejercicio)
                                  └─< Asiento (asiento)  [auditoría: usuario]
                                        └─< Apunte (apunte) >─ Cuenta (cuenta)
```

- `Asiento.creado_por_usuario_id`, `Asiento.asentado_por_usuario_id` → FK a `Usuario.id` (`ON DELETE RESTRICT`).
- `Asiento.ejercicio_id` → FK a `Ejercicio.id` (`ON DELETE RESTRICT`).
- `Apunte.asiento_id` → FK a `Asiento.id` (`ON DELETE CASCADE`).
- `Apunte.cuenta_id` → FK a `Cuenta.id` (`ON DELETE RESTRICT`).

---

## 2. Entidad `Asiento` (modificada — LEGAL-01, CONC-01)

Tabla `asiento`. Restricciones existentes: `UNIQUE(ejercicio_id, numero)` (`uq_asiento_ejercicio_numero`).

| Campo | Tipo | Nulable | Default | Origen | Notas |
|-------|------|---------|---------|--------|-------|
| `id` | int PK | no | auto | existente | |
| `ejercicio_id` | int FK → `ejercicio.id` (RESTRICT) | no | — | existente | |
| `numero` | int | sí | — | existente | Correlativo del ejercicio; `NULL` en borrador |
| `fecha` | date | no | — | existente | Debe estar dentro del periodo del ejercicio |
| `concepto` | str(300) | no | — | existente | |
| `estado` | str(20) | no | `borrador` | existente | `borrador` \| `asentado` |
| `creado_por_usuario_id` | int FK → `usuario.id` (RESTRICT) | **no** | — | **NUEVO** | Trazabilidad de creación |
| `asentado_por_usuario_id` | int FK → `usuario.id` (RESTRICT) | sí | — | **NUEVO** | `NULL` hasta asentar |
| `created_at` | datetime (tz) | **no** | `datetime.now(UTC)` | **NUEVO** | UTC |
| `asentado_at` | datetime (tz) | sí | — | **NUEVO** | `NULL` hasta asentar; `UTC` |
| `version` | int | no | `1` | **NUEVO** | Reservado para concurrencia optimista (Fase 2); se incrementa en servidor |

**Índice nuevo**: `ix_asiento_ejercicio_estado_fecha` sobre `(ejercicio_id, estado, fecha)`.

**Reglas de validación / negocio**:
- Al **asentar**: `estado == "borrador"`, ejercicio `abierto`, nº de apuntes ≥ 2, Δ = 0, fecha dentro del periodo. Al asentar se fijan `numero`, `estado="asentado"`, `asentado_por_usuario_id`, `asentado_at`.
- Un asiento `asentado` es **inmutable** (no editable ni borrable); correcciones vía asiento de rectificación.
- `numero` es `NULL` en `borrador` y único por ejercicio al asentar.
- `version` no se expone al cliente en Spec 2.

**Transiciones de estado**:

```text
(no existe) --crear borrador--> borrador --asentar--> asentado (final, inmutable)
                                   ^   |
                                   |   +--editar--> borrador (mismos invariantes)
                                   +---reintento correlativo (IntegrityError)---+
```

---

## 3. Entidad `Apunte` (sin cambios de columnas; índice relevante)

Tabla `apunte`. Sin cambios de columnas en Spec 2.

| Campo | Tipo | Nulable | Notas |
|-------|------|---------|-------|
| `id` | int PK | no | |
| `asiento_id` | int FK → `asiento.id` (CASCADE) | no | Índice `ix_apunte_asiento_id` (existente) |
| `cuenta_id` | int FK → `cuenta.id` (RESTRICT) | no | Índice `ix_apunte_cuenta_id` (existente) |
| `debe` | Numeric(19,2) | no | ≥ 0; ≤ 2 decimales |
| `haber` | Numeric(19,2) | no | ≥ 0; ≤ 2 decimales |

**Regla de negocio**: cada línea debe tener exactamente una cara (`debe` XOR `haber`) con valor > 0.

---

## 4. Entidades de contexto (sin cambios de esquema)

- **`Usuario`** (`usuario`): `id`, `username` (unique), `email` (unique), `hashed_password`, `rol` (`admin` \| `contable`), `activo`. Origen de las FK de auditoría.
- **`Empresa`** (`empresa`): `id`, `cif` (unique), `razon_social`, `nombre_comercial`, `activa` (bool), `created_at`. `activa=False` bloquea todo acceso (SEC-03).
- **`Ejercicio`** (`ejercicio`): `id`, `empresa_id` (FK), `anio`, `fecha_inicio`, `fecha_fin`, `estado` (`abierto` \| `cerrado`). `UNIQUE(empresa_id, anio)`.
- **`Cuenta`** (`cuenta`): `id`, `ejercicio_id` (FK), `codigo` (≤10, solo dígitos), `nombre`, `nivel` (1-5). `UNIQUE(ejercicio_id, codigo)`.
- **`empresa_usuario`** (Table): `usuario_id`, `empresa_id`, `rol_especifico`. Determina la pertenencia al tenant.

---

## 5. Migración Alembic (NUEVA)

- **Nombre**: `<rev>_trazabilidad_auditoria_asientos.py`
- **`down_revision`**: `bb1c920e98ab`
- **`upgrade()`** (orden obligatorio):
  1. `op.add_column("asiento", ...)` de `creado_por_usuario_id`, `asentado_por_usuario_id`, `created_at`, `asentado_at`, `version` como **nullable** (o con `server_default` provisional).
  2. **Backfill**: actualizar filas existentes asignando `creado_por_usuario_id` a un usuario admin/sistema y `created_at = now()` (no-op si no hay asientos). En la BD de desarrollo actual no hay asientos ni PGC.
  3. `op.alter_column(..., nullable=False)` para `creado_por_usuario_id` y `created_at`. (SQLite: usar `batch_alter_table` si es necesario.)
  4. Crear índice `ix_asiento_ejercicio_estado_fecha` sobre `(ejercicio_id, estado, fecha)`.
- **`downgrade()`**: `drop_index` y `drop_column` en orden inverso.
- **Gotcha**: no confiar en `--autogenerate` para las FK/índices; sustituir `AutoString` por `sa.String(...)` y añadir `ix_*` a mano, luego `alembic upgrade head`.

---

## 6. Invariantes de datos (verificación)

1. Σ`debe` = Σ`haber` en todo `Asiento.estado == "asentado"`.
2. Todo `Asiento` tiene ≥ 2 `Apunte`.
3. `Asiento.numero` es único por `ejercicio_id` y no nulo cuando `estado == "asentado"`.
4. `Asiento.creado_por_usuario_id` y `created_at` siempre presentes.
5. `Asiento` de un ejercicio cerrado no puede crearse, editarse ni asentarse.
6. Ningún acceso a datos de una `Empresa` con `activa = False`.
