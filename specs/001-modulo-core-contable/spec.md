# Feature Specification: Módulo Core Contable Multi-Tenant (Fase 1)

**Feature Branch**: `001-modulo-core-contable`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Plan de Especificación: Módulo Core Contable Multi-Tenant (Fase 1)"

## Clarifications

### Session 2026-10-08

- Q: ¿La interfaz debe seguir el estándar Material Design 3? → A: Sí, MD3 (confirmado por el usuario como requisito de interfaz).
- Q: ¿Cómo aplicar MD3 en el frontend? → A: Librería MUI v6 con tema MD3 (scheme claro/oscuro, tokens configurables).
- Q: ¿El flujo de asientos necesita estado borrador en Fase 1? → A: Sí, borrador guardable en BD; el asiento se puede guardar descuadrado como `borrador` y asentarse después (el `asentado` exige Σ Debe = Σ Haber).
- Q: ¿Qué política de contraseñas aplicar? → A: Longitud mínima 8, hash argon2, sin caducidad ni bloqueo en Fase 1.
- Q: ¿La vista de Diario permite ver apuntes y gestionar borradores? → A: Sí, filas expandibles con apuntes (GET /asientos/{id}) y listado de borradores reutilizables.
- Q: ¿Cómo tratar estados vacíos, de carga y errores en la UI? → A: Snackbar/Alert M3 para errores de red/API, estados vacíos ilustrados y skeletons de carga.
- Q: ¿Puede un asiento tener más de dos líneas de apunte? → A: Sí, los asientos pueden ser múltiples (de 2 a N líneas; mínimo 2, sin límite superior en Fase 1).
- Q: ¿Cómo se gestionan las migraciones de esquema? → A: Alembic desde el principio (el esquema se versiona con migraciones; sin `create_all` en producción).
- Q: ¿Comportamiento de sesión y arranque? → A: Login obligatorio en cada sesión; es la única operación en primer plano ("sobre la marcha"); el resto carga en segundo plano; al entrar se preselecciona la empresa/ejercicio de la sesión anterior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registro de asientos con partida doble (Priority: P1)

Un contable selecciona una Empresa y un Ejercicio activos, abre el
formulario de introducción de asientos, añade líneas de apunte (cuenta,
Debe, Haber), ve el descuadre en tiempo real y guarda el asiento; el
backend valida el cuadre (Σ Debe = Σ Haber) antes de asentarlo y asigna el
número correlativo del ejercicio. El asiento puede guardarse previamente
como `borrador` (incluso descuadrado) y asentarse después.

**Why this priority**: es el núcleo del sistema contable sin el cual no
existe valor; los demás componentes lo soportan.

**Independent Test**: se puede probar end-to-end con la API y el formulario
web: crear empresa/ejercicio/cuentas, registrar un asiento cuadrado y
verificar que aparece en el Diario con su número correlativo.

**Acceptance Scenarios**:

1. **Given** un ejercicio abierto, **When** se intenta asentar un asiento con
   Σ Debe ≠ Σ Haber, **Then** el backend lo rechaza con error de validación
   (pero sí permite guardarlo como `borrador`).
2. **Given** un ejercicio abierto, **When** se asienta un asiento cuadrado,
   **Then** se persiste atómicamente (asiento + apuntes) con número
   correlativo único del ejercicio y estado `asentado`.
3. **Given** un ejercicio cerrado, **When** se intenta guardar o asentar un
   asiento, **Then** el backend lo rechaza.

---

### User Story 2 - Gestión de Usuarios, Empresas y Ejercicios (Priority: P2)

Un usuario se autentica, ve solo las empresas a las que tiene acceso,
crea empresas y abre ejercicios (años contables) dentro de ellas.

**Why this priority**: habilita el aislamiento multipuesto y el contexto
sobre el que opera la US1; puede entregarse de forma independiente.

**Independent Test**: dos usuarios con empresas distintas no ven ni pueden
operar sobre los datos del otro (prueba de pertenencia por cabeceras de
contexto).

**Acceptance Scenarios**:

1. **Given** un usuario sin acceso a una empresa, **When** envía
   `X-Empresa-Id` de esa empresa, **Then** recibe 403.
2. **Given** un usuario autenticado, **When** crea una empresa, **Then** queda
   asociada a él en `EmpresaUsuario`.

---

### User Story 3 - Plan de Cuentas por Ejercicio (Priority: P2)

Un contable consulta, busca y da de alta cuentas/subcuentas del Plan
General Contable dentro del ejercicio activo; el código es único por
ejercicio.

**Why this priority**: es el requisito previo para poder anotar apuntes
contra cuentas.

**Independent Test**: crear cuentas en dos ejercicios distintos con el mismo
código y verificar que ambas existen sin colisión.

**Acceptance Scenarios**:

1. **Given** el ejercicio activo, **When** se crea una cuenta con código ya
   existente en ese ejercicio, **Then** el backend rechaza con conflicto.
2. **Given** dos ejercicios, **When** se listan cuentas, **Then** cada lista
   está estrictamente filtrada por su `ejercicio_id`.

---

### User Story 4 - Interfaz Multipuesto con Selector de Contexto (Priority: P3)

El acceso comienza con una pantalla de **login obligatorio en cada sesión**;
el login es la única operación en primer plano ("sobre la marcha") y el
resto de cargas ocurre en segundo plano. Tras autenticarse, la interfaz
(siguiendo el estándar **Material Design 3**) preselecciona la Empresa y el
Ejercicio de la sesión anterior y muestra una barra superior con desplegables
para cambiar de contexto, persistido en cookies, operando sobre Plan de
Cuentas, Introducción de Asientos y Diario de forma transparente.

**Why this priority**: multiplica la usabilidad del entorno multipuesto, pero
las APIs ya son utilizables sin ella.

**Independent Test**: cambiar el selector de ejercicio recarga los datos del
Plan de Cuentas y Diario correspondientes al nuevo contexto.

**Acceptance Scenarios**:

1. **Given** dos pestañas con empresas/ejercicios distintos, **When** operan
   en paralelo, **Then** no se interfieren entre sí.
2. **Given** un asiento descuadrado, **When** se intenta enviar, **Then** el
   botón de envío está bloqueado en cliente y el backend también rechaza.

---

### Edge Cases

- Concurrencia: accesos simultáneos de lectura/escritura no deben producir
  "database is locked" (WAL + busy_timeout).
- Ejercicio cerrado: cualquier intento de registro/modificación se rechaza
  en servidor.
- Relación Ejercicio-Empresa inválida en cabeceras de contexto → 400/403.
- Número correlativo: debe ser independiente por ejercicio (y, por
  extensión, por empresa).
- Asientos en estado `borrador` (guardables descuadrados, editables) vs
  `asentado` (inmutables, con número correlativo); solo los `asentado`
  forman parte del Diario contable definitivo.
- Asientos múltiples: un asiento con N líneas debe cuadrar en el conjunto
  (Σ Debe = Σ Haber sobre todas sus líneas), no por pares.
- Edición concurrente del mismo borrador: se aplica last-write-wins sin
  versión/optimismo en Fase 1 (decisión documentada; no hay endpoint de
  cierre ni de destrucción).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST usar SQLite en modo WAL con
  `busy_timeout=5000` y claves foráneas activadas.
- **FR-002**: El sistema MUST soportar múltiples Empresas y Ejercicios
  (multi-tenant lógico) con aislamiento por contexto.
- **FR-003**: El sistema MUST gestionar Usuarios con autenticación básica
  (username/password con hash) y roles (`admin`, `contable`).
- **FR-003b**: El rol `admin` MUST poder crear empresas y gestionar el
  acceso de usuarios; el rol `contable` MUST poder operar sobre empresas a
  las que tenga acceso (crear ejercicios, cuentas y asientos) pero NO crear
  empresas ni vínculos `EmpresaUsuario`; ningún rol debe poder destruir
  registros contables asentados.
- **FR-004**: El sistema MUST asociar usuarios a empresas vía tabla
  intermedia `EmpresaUsuario` con rol específico.
- **FR-005**: El backend MUST extraer el contexto de las cabeceras
  `X-Empresa-Id` y `X-Ejercicio-Id` y validar pertenencia (ejercicio →
  empresa, usuario → empresa).
- **FR-006**: El Plan de Cuentas MUST estar aislado por Ejercicio, con
  `codigo` único dentro de cada `ejercicio_id`.
- **FR-007**: El asentamiento de un asiento (pass a estado `asentado`) MUST
  validar en servidor Σ Debe − Σ Haber = 0 antes de persistir; el guardado
  como `borrador` SÍ permite descuadres.
- **FR-008**: El registro/asentamiento de asientos y el guardado de borradores
  MUST rechazar operaciones en ejercicios con estado `cerrado`.
- **FR-009**: El número de asiento MUST ser correlativo y único dentro del
  ejercicio, generado automáticamente en el momento de asentar (los
  `borrador` aún no tienen número).
- **FR-010**: El guardado del asiento y sus apuntes MUST ser una transacción
  atómica en SQLite.
- **FR-011**: El frontend MUST ofrecer selector global de Empresa y Ejercicio
  activos, persistido en cookies/estado de sesión; al entrar MUST preseleccionar
  la empresa/ejercicio de la última sesión (y solo pedir selección si no hay
  contexto previo).
- **FR-011b**: El login MUST ser la única operación de arranque en primer
  plano ("sobre la marcha"): es la única pantalla bloqueante de la sesión; el
  resto de cargas (empresas, ejercicios y datos de negocio) MUST producirse
  en segundo plano de forma asíncrona, sin bloquear la interfaz.
- **FR-012**: El formulario de asientos MUST calcular el descuadre en tiempo
  real: permite guardar como `borrador` con Δ ≠ 0, pero bloquea la acción de
  **asentar** si Δ ≠ 0 o el ejercicio está cerrado.
- **FR-013**: La vista Diario MUST listar los asientos del ejercicio activo,
  paginable y filtrable.
- **FR-014**: El sistema MUST ajustarse a la normativa del PGC de España en
  la estructura de cuentas (código, nombre, nivel).
- **FR-015**: La interfaz web MUST seguir el estándar Material Design 3
  (tokens de color, tipografía, elevación y componentes M3).
- **FR-016**: La vía de implementación de la FR-015 es MUI v6 con un tema
  MD3 de tokens configurables (scheme claro/oscuro).
- **FR-017**: La autenticación MUST exigir contraseñas de longitud mínima 8,
  almacenadas con hash argon2, sin caducidad ni bloqueo en Fase 1.
- **FR-018**: La vista Diario MUST permitir expandir cada asiento para ver
  sus apuntes (detalle vía `GET /api/v1/asientos/{id}`) y MUST listar los
  asientos `borrador` del ejercicio para poder reabrirlos y continuar su
  edición antes de asentarlos.
- **FR-019**: La interfaz MUST tratar con componentes M3 los estados de UI:
  Snackbar/Alert para errores de red/API, estados vacíos (sin cuentas,
  sin asientos, sin borradores) y skeletons durante la carga de datos.
- **FR-020**: Un asiento MUST admitir de 2 a N líneas de apunte (asientos
  múltiples); mínimo 2, sin límite superior en Fase 1.
- **FR-021**: El esquema de base de datos MUST gestionarse con migraciones
  Alembic desde el inicio del proyecto (nada de `create_all` en
  producción); cada cambio de esquema pasa por una revisión Alembic.

### Key Entities

- **Usuario**: credenciales, rol global, estado activo.
- **Empresa**: identidad fiscal (CIF), razón social, estado.
- **EmpresaUsuario**: acceso usuario↔empresa con rol específico.
- **Ejercicio**: año contable de una empresa, con fechas y estado
  (abierto/cerrado).
- **Cuenta**: cuenta/subcuenta PGC dentro de un ejercicio.
- **Asiento**: cabecera de diario (número correlativo, fecha, concepto,
  estado borrador/asentado).
- **Apunte**: línea debe/haber de un asiento, vinculada a una cuenta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Múltiples usuarios/pestañas en empresas o ejercicios distintos
  operan sin interferir en las consultas de los demás.
- **SC-002**: 0 asientos **asentados** con Σ Debe ≠ Σ Haber (validación en
  servidor al asentar; los borradores pueden quedar descuadrados).
- **SC-003**: 0 asientos registrados o modificados en ejercicios cerrados.
- **SC-004**: Los números de asiento son independientes entre ejercicios y
  empresas (sin colisiones).
- **SC-005**: SQLite responde sin "database is locked" ante accesos
  concurrentes de lectura/escritura (modo WAL).

## Assumptions

- Despliegue en LAN/local (entorno multipuesto) con una instancia única de
  FastAPI y base de datos SQLite compartida (aislamiento lógico, no por BD).
- Autenticación "básica": JWT en cookie httpOnly (SameSite=Lax) con hash
  argon2 de contraseña (mínimo 8 caracteres, sin caducidad ni bloqueo), sin
  SSO/OAuth en Fase 1.
- El catálogo de cuentas del PGC se da de alta manualmente por ejercicio en
  Fase 1 (sin carga masiva inicial obligatoria).
- En Fase 1 los usuarios se crean mediante el script seed administrado
  (`backend/app/seed.py`); no hay registro público ni endpoint de alta.
- Solo Windows como plataforma de desarrollo/despliegue inicial (el repo se
  desarrolla en Windows), sin requisitos de móvil.
- Libro Mayor sencillo (saldo por cuenta del ejercicio activo) queda
  pendiente de cierre de Fase 1 según constitución; Balance de Sumas y
  Saldos queda para Fase 2.
