# Data Model — 001-modulo-core-contable (Fase 1)

Fuente: spec.md §Key Entities y §2 (Modelo de Datos & Contexto), con
aclaraciones sesión 2026-10-08; decisiones en research.md. Convenciones:
IDs enteros autoincrementales; timestamps UTC ISO-8601; importes `NUMERIC`
con `Decimal` de 2 decimales ≥ 0 por API.

**Migraciones**: todo el esquema se materializa mediante **Alembic**
(FR-021). Este documento define el esquema conceptual; la revisión inicial de
Alembic debe reflejarlo exactamente (índices, UNIQUE, FK).

## Diagrama de relaciones

```text
[Usuario] ──< [EmpresaUsuario] >── [Empresa]
                                        │
                                        └──< [Ejercicio] (ej. 2026)
                                                ├──< [Cuenta]
                                                └──< [Asiento] ──< [Apunte]
```

## Entidades

### Usuario

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | INTEGER PK | autoincremental |
| username | TEXT | UNIQUE, no nulo, 3–50 chars |
| email | TEXT | UNIQUE, formato válido |
| hashed_password | TEXT | argon2, no nulo (mínimo 8 chars al crear, FR-017) |
| rol | TEXT | `admin` \| `contable` |
| activo | BOOLEAN | default `true` |

Relaciones: N↔N con Empresa vía EmpresaUsuario.

### Empresa

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | INTEGER PK | autoincremental |
| cif | TEXT | 9 chars, UNIQUE |
| razon_social | TEXT | no nulo, ≤ 120 |
| nombre_comercial | TEXT | nullable, ≤ 120 |
| activa | BOOLEAN | default `true` |
| created_at | DATETIME | UTC |

### EmpresaUsuario (tabla intermedia)

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| usuario_id | INTEGER FK → Usuario | PK compuesta, CASCADE |
| empresa_id | INTEGER FK → Empresa | PK compuesta, CASCADE |
| rol_especifico | TEXT | `admin` \| `contable` \| `lectura`, nullable |

### Ejercicio

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | INTEGER PK | autoincremental |
| empresa_id | INTEGER FK → Empresa | RESTRICT, no nulo |
| anio | INTEGER | 2000–2100; UNIQUE(empresa_id, anio) |
| fecha_inicio | DATE | 01-01 del año |
| fecha_fin | DATE | 31-12 del año |
| estado | TEXT | `abierto` \| `cerrado`, default `abierto` |

**Transiciones**:

```text
abierto ──(Fase 2: cierre con validación de cuadre)──> cerrado
cerrado   (sin transición inversa; escrituras → 409)
```

### Cuenta (Plan de Cuentas por Ejercicio, PGC España)

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | INTEGER PK | autoincremental |
| ejercicio_id | INTEGER FK → Ejercicio | CASCADE, no nulo |
| codigo | TEXT | dígitos, 1–10; UNIQUE(ejercicio_id, codigo) |
| nombre | TEXT | no nulo, ≤ 200 |
| nivel | INTEGER | 1–5 |

Reglas: crear cuenta exige ejercicio `abierto` (409 si cerrado) y código
único en el ejercicio (409 si duplicado); el mismo código en otro ejercicio
es válido. Los apuntes solo referencian cuentas del ejercicio activo.

### Asiento (cabecera de diario)

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | INTEGER PK | autoincremental |
| ejercicio_id | INTEGER FK → Ejercicio | RESTRICT, no nulo |
| numero | INTEGER NULL | ≥ 1, UNIQUE(ejercicio_id, numero); **NULL en borrador**, se asigna al asentar |
| fecha | DATE | dentro de fecha_inicio/fecha_fin del ejercicio |
| concepto | TEXT | no nulo, ≤ 300 |
| estado | TEXT | `borrador` \| `asentado` |

**Transiciones (Fase 1, activas)**:

```text
(nuevo) ──POST /api/v1/asientos (estado=borrador)──> borrador
borrador ──PUT /api/v1/asientos/{id}──> borrador        (editar apuntes)
borrador ──POST /api/v1/asientos/{id}/asentar──> asentado  (exige cuadre)
asentado ──(sin PUT/PATCH/DELETE)──> inmutable
```

- `numero = NULL` mientras sea borrador; se asigna al **asentar** (FR-009).
- Guardar/editar borrador admite descuadres y 2..N líneas (FR-007/FR-020).
- `asentar` firma la transición en una sola operación: valida cuadre → asigna
  correlativo → persiste estado.

### Apunte (línea debe/haber)

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| id | INTEGER PK | autoincremental |
| asiento_id | INTEGER FK → Asiento | CASCADE, no nulo |
| cuenta_id | INTEGER FK → Cuenta | RESTRICT, no nulo |
| debe | NUMERIC | ≥ 0, 2dp, default 0 |
| haber | NUMERIC | ≥ 0, 2dp, default 0 |

**Reglas de negocio**:

- **Partida doble al asentar (invariante de conjunto)**: Σ debe − Σ haber =
  0 sobre **todas** las líneas del asiento (FR-007/FR-020). Si Δ ≠ 0 → 422
  sin consumir número ni cambiar estado.
- Por línea: exactamente uno de `debe`/`haber` > 0 (líneas mixtas o en cero
  → 422, tanto en borrador como al asentar).
- Mínimo **2** apuntes por asiento; sin límite superior (N).
- Cada `cuenta_id` DEBE pertenecer al `ejercicio_id` del asiento → 422.
- En borrador el conjunto puede estar descuadrado (se persiste tal cual).

## Reglas de validación cruzada (contexto)

| Regla | Origen | Fallo |
|-------|--------|-------|
| `X-Empresa-Id` requerida en endpoints de negocio | FR-005 | 400 |
| Usuario con acceso a la empresa (EmpresaUsuario) | FR-005 | 403 |
| `X-Ejercicio-Id` existe y pertenece a `X-Empresa-Id` | FR-005 | 400/403 |
| Escrituras exigen ejercicio `abierto` | FR-008 | 409 |
| Empresa inactiva bloquea escrituras | coherencia | 403 |

## Índices recomendados (deben existir en la migración inicial)

- `empresa_usuario (usuario_id)`, `empresa_usuario (empresa_id)`
- `ejercicio (empresa_id)`
- `cuenta (ejercicio_id)`, `cuenta (ejercicio_id, codigo)` UNIQUE
- `asiento (ejercicio_id, numero)` UNIQUE (admite NULL), `asiento (ejercicio_id, fecha)`
- `apunte (asiento_id)`, `apunte (cuenta_id)` (para futuro Libro Mayor)

## Reglas de inmutabilidad (Constitución III)

- `asiento.estado = 'asentado'`: sin PUT/PATCH/DELETE expuestos.
- Ejercicio `cerrado`: ninguna escritura (409) — incluye borradores.
- Correcciones futuras: solo mediante asiento de rectificación/extorno (Fase 2+).