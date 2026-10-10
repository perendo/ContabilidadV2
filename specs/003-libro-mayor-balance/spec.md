# Feature Specification: Libro Mayor y Balance de Sumas y Saldos

**Feature Branch**: `003-libro-mayor-balance`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "En la auditoria se ha encontrado esto: Victor Garcia Cobos 30,00 (09/10/2026, Efectivo); Daniel Urrutia Guevara 30,00/30,00 (09/10/2026, Bizum); Carlos Sanchez 50,00 (09/10/2026, Bizum); Mario Sanchez 30,00/50,00 (09/10/2026, Bizum). Añade también una opción para generar el Mayor y el Balance de Sumas y Saldos."

## Clarifications

### Session 2026-10-10

- Q: ¿Cómo se debe poder consultar el Libro Mayor (alcance)? → A: Ambos modos: por cuenta individual **y** listado de todas las cuentas con movimiento.
- Q: ¿En qué formato deben generarse/exportarse los informes? → A: Pantalla + descarga CSV + PDF, con un **botón independiente para cada formato** (uno para CSV y otro para PDF).
- Q: ¿Los informes presentan también los niveles superiores del PGC? → A: Sí, agregación jerárquica: los niveles 1-3 (grupos/subgrupos) aparecen con la suma acumulada de sus subcuentas, además del detalle de las cuentas con apuntes.
- Q: ¿Qué formato debe tener el CSV exportado? → A: Separador de campos `;` y decimal con coma, codificación UTF-8 con BOM (compatible con hoja de cálculo en español).
- Q: ¿El Balance incluye cuentas con movimiento pero saldo cero? → A: Sí, se incluyen todas las cuentas con movimiento aunque su saldo quede a cero (se muestra saldo 0); solo se omiten las cuentas sin ningún movimiento.
- Q: ¿Qué volumen de asientos por ejercicio deben soportar los informes? → A: Hasta 10.000 asientos por ejercicio dentro del objetivo de menos de 3 segundos.
- Q: ¿Cómo presenta el Balance el saldo de cada cuenta? → A: Formato clásico de cuatro columnas: Suma Debe, Suma Haber, Saldo Deudor y Saldo Acreedor.
- Q: ¿Qué usuarios pueden consultar y exportar los informes? → A: Cualquier usuario con acceso a la empresa/ejercicio (roles admin y contable), sin distinción de rol.
- Q: ¿Qué datos identificativos incluyen las exportaciones? → A: Razón social y CIF de la empresa, ejercicio (año), rango de fechas aplicado y fecha/hora de generación.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar el Libro Mayor (Priority: P1)

Un contable abre el Libro Mayor del ejercicio activo en dos modos: (a) el
**mayor de una cuenta concreta**, seleccionada buscando por código o nombre,
con todos sus apuntes **asentados** en orden cronológico (fecha, número de
asiento, concepto, importe en Debe o Haber y **saldo acumulado** tras cada
movimiento); y (b) un **listado global** de todas las cuentas con movimiento,
desde el que puede entrar al detalle de cualquiera de ellas. Puede acotar el
resultado a un rango de fechas (desde/hasta) dentro del ejercicio.

**Why this priority**: el Mayor es la consulta de detalle por cuenta que
fundamenta el análisis y la auditoría contable; la propia constitución lo
sitúa en la Fase 1 del núcleo. Sin él no es posible examinar el origen de un
saldo.

**Independent Test**: con una cuenta con varios apuntes asentados, abrir su
Mayor y comprobar que el saldo acumulado final coincide exactamente con el
saldo de esa cuenta en el Balance de Sumas y Saldos.

**Acceptance Scenarios**:

1. **Given** una cuenta con apuntes asentados, **When** se abre su Libro
   Mayor, **Then** los movimientos aparecen ordenados por fecha y número de
   asiento, cada uno con su importe en Debe o Haber y el saldo acumulado
   resultante.
2. **Given** varias cuentas con movimiento en el ejercicio, **When** se abre el
   listado global del Mayor, **Then** se muestran todas las cuentas con
   movimiento y es posible abrir el detalle de cada una.
3. **Given** un rango de fechas (desde/hasta), **When** se consulta el Mayor,
   **Then** solo se muestran los movimientos del rango y el primer movimiento
   parte del saldo acumulado anterior al rango (saldo de apertura del periodo).
4. **Given** una cuenta sin apuntes asentados, **When** se abre su Mayor,
   **Then** se muestra un estado vacío informativo (sin error).

---

### User Story 2 - Generar el Balance de Sumas y Saldos (Priority: P1)

Un contable genera el Balance de Sumas y Saldos del ejercicio activo. Por cada
cuenta con movimientos se muestran la **suma del Debe**, la **suma del Haber**
y el **saldo** resultante (deudor o acreedor), junto con los **totales
generales** de Debe y Haber del informe.

**Why this priority**: es el informe de control que permite comprobar el
cuadre global de la contabilidad y sustentar una auditoría; es el objetivo
explícito de la petición y una consulta obligada del PGC.

**Independent Test**: registrar varios asientos asentados en distintas cuentas
y verificar que las sumas por cuenta, los saldos y los totales generales
coinciden con lo esperado de forma auditable.

**Acceptance Scenarios**:

1. **Given** apuntes asentados distribuidos en varias cuentas, **When** se
   genera el Balance de Sumas y Saldos, **Then** cada cuenta muestra su suma
   de Debe, su suma de Haber y su saldo (deudor/acreedor) clasificado
   correctamente.
2. **Given** todos los asientos incluidos están en estado `asentado`, **When**
   se genera el Balance, **Then** la suma total del Debe coincide con la suma
   total del Haber (cuadre global) y, si no coincide, el sistema lo resalta de
   forma visible.
3. **Given** los movimientos hallados en la auditoría (Victor 30,00 / Daniel
   30,00 y 30,00 / Carlos 50,00 / Mario 30,00 y 50,00, todos de 09/10/2026),
   una vez registrados como asientos, **When** se generan el Mayor y el
   Balance, **Then** cada titular aparece con sus importes en Debe/Haber,
   su saldo y la fecha correspondiente, permitiendo reconstruir la pista de
   auditoría.

---

### User Story 3 - Filtrar por periodo y exportar los informes (Priority: P2)

El contable acota el Mayor y el Balance a un rango de fechas del ejercicio y
exporta el informe resultante para adjuntarlo a la auditoría o conservarlo
como documento de trabajo.

**Why this priority**: los informes son utilizables en pantalla sin
exportación, pero su entrega formal (auditoría/archivo) exige un documento
descargable; por eso es valor incremental sobre US1/US2.

**Independent Test**: generar un informe con un rango de fechas, exportarlo y
comprobar que el contenido exportado coincide con lo mostrado en pantalla.

**Acceptance Scenarios**:

1. **Given** un rango de fechas seleccionado, **When** se generan los informes,
   **Then** solo se incluyen los movimientos del periodo y los saldos se
   calculan en consecuencia.
2. **Given** un informe generado, **When** el usuario pulsa el botón de
   exportar **CSV**, **Then** se descarga un CSV que reproduce fielmente los
   datos mostrados; **When** pulsa el botón **PDF**, **Then** se descarga un
   PDF con el mismo contenido.

---

### Edge Cases

- Cuenta con movimientos anteriores al rango consultado: el Mayor debe arrancar
  del saldo acumulado previo (saldo de apertura del periodo).
- Cuenta sin ningún movimiento en el ejercicio: aparece como estado vacío en el
  Mayor y se excluye del Balance.
- Cuenta con movimientos que se compensan y dejan saldo cero: se incluye en el
  Balance con saldo 0 y se distingue de una cuenta sin movimiento (que se
  omite).
- Ejercicio `cerrado`: los informes siguen siendo consultables en solo lectura
  (no se modifica ningún dato).
- Ejercicio sin asientos asentados: ambos informes muestran estados vacíos
  informativos y totales a cero.
- Importes: se respeta la precisión de dos decimales del modelo contable; no se
  produce pérdida de céntimos en las sumas.
- Aislamiento multi-tenant: solicitudes con contexto de empresa/ejercicio no
  accesible se rechazan (400/403) y nunca mezclan datos de otro ejercicio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST ofrecer una vista de **Libro Mayor** que, para una
  cuenta del ejercicio activo, liste sus apuntes asentados en orden
  cronológico mostrando fecha, número de asiento, concepto, importe en Debe o
  Haber y el **saldo acumulado** tras cada movimiento.
- **FR-002**: El Libro Mayor MUST ofrecer **ambos modos**: (a) mayor de una
  cuenta concreta seleccionable por código o nombre, y (b) listado global de
  todas las cuentas con movimiento del ejercicio, navegable y con acceso al
  detalle por cuenta. El Mayor MUST poder solicitarse para cualquier nivel de
  cuenta: en cuentas de grupo (niveles 1-3) agrega los movimientos de sus
  subcuentas; en cuentas hoja muestra sus propios apuntes.
- **FR-003**: El sistema MUST calcular el saldo acumulado y clasificarlo como
  deudor o acreedor; este cálculo MUST realizarse exclusivamente en el backend.
- **FR-004**: El sistema MUST ofrecer una vista de **Balance de Sumas y Saldos**
  del ejercicio activo que, por cada cuenta, muestre la suma del Debe, la suma
  del Haber y el saldo resultante, además de los totales generales. El Balance
  MUST presentar **agregación jerárquica**: los niveles 1-3 (grupos/subgrupos)
  muestran las sumas y saldos acumulados de sus subcuentas, seguidas de las
  cuentas de detalle que reciben apuntes, ordenadas por código. MUST incluir
  toda cuenta con movimiento, **aunque su saldo neto sea cero**; solo se omiten
  las cuentas sin ningún movimiento. Cada fila MUST presentar el **formato
  clásico de cuatro columnas**: Suma Debe, Suma Haber, Saldo Deudor y Saldo
  Acreedor (el saldo de cada cuenta se clasifica en una sola de las dos
  columnas de saldo).
- **FR-005**: El Balance MUST totalizar las sumas del Debe y del Haber y MUST
  evidenciar de forma visible cualquier diferencia entre ambos totales.
- **FR-006**: Ambos informes MUST considerar únicamente asientos en estado
  `asentado` del ejercicio activo; los asientos en estado `borrador` MUST
  quedar excluidos.
- **FR-007**: Ambos informes MUST permitir filtrar por rango de fechas
  (desde/hasta) dentro del ejercicio activo; el Mayor MUST partir del saldo
  acumulado anterior al inicio del rango.
- **FR-008**: El acceso a los informes MUST respetar el contexto
  empresa/ejercicio (`X-Empresa-Id` + `X-Ejercicio-Id`) y el aislamiento
  multi-tenant, rechazando (400/403) accesos a contextos no válidos o no
  vinculados.
- **FR-009**: Toda validación, agregación y cálculo de saldos de los informes
  MUST residir en el backend; el frontend únicamente presenta los resultados.
- **FR-010**: El sistema MUST permitir exportar cada informe en pantalla y en
  **dos formatos descargables**: CSV y PDF, con un **botón independiente para
  cada formato** (uno para CSV y otro para PDF) tanto en el Libro Mayor como en
  el Balance de Sumas y Saldos. El CSV MUST usar `;` como separador de campos y
  la coma como separador decimal, con codificación UTF-8 con BOM (compatible con
  la hoja de cálculo en español).
- **FR-011**: La interfaz de los informes MUST seguir Material Design 3 (MUI v6)
  y tratar los estados de carga, vacío y error con componentes M3 coherentes con
  el resto de la aplicación.
- **FR-012**: Los informes MUST respetar la precisión decimal (dos decimales)
  del modelo contable sin degradar la suma de céntimos.
- **FR-013**: Tanto la consulta como la exportación de los informes MUST estar
  permitidas a cualquier usuario vinculado a la empresa/ejercicio (roles `admin`
  y `contable`), sin distinción de rol; la autorización se basa en el contexto
  empresa/ejercicio (FR-008).
- **FR-014**: Los documentos exportados (CSV y PDF) MUST incluir un encabezado
  identificativo con la razón social y el CIF de la empresa, el ejercicio (año),
  el rango de fechas aplicado y la fecha/hora de generación, además del título
  del informe.

### Key Entities *(include if feature involves data)*

- **Cuenta (mayorizada)**: cuenta del PGC dentro del ejercicio; agrega sus
  apuntes y su saldo. Atributos relevantes: código, nombre, nivel.
- **Cuenta de grupo/subgrupo (nivel 1-3)**: cuenta sin apuntes directos cuyo
  movimiento, sumas y saldo se calculan como acumulado de sus subcuentas
  (cuentas cuyo código empieza por su código).
- **Apunte**: línea Debe/Haber de un asiento asentado vinculada a una cuenta;
  unidad de detalle del Libro Mayor.
- **Asiento asentado**: cabecera de diario en estado `asentado` (fecha,
  número, concepto); única fuente incluida en los informes.
- **Línea de informe (Mayor)**: fila de movimiento con fecha, referencia de
  asiento, concepto, importe y saldo acumulado.
- **Línea de informe (Balance)**: fila por cuenta con las cuatro columnas
  clásicas: Suma Debe, Suma Haber, Saldo Deudor y Saldo Acreedor.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El saldo acumulado de cada cuenta en el Libro Mayor coincide
  exactamente con el saldo de esa cuenta en el Balance de Sumas y Saldos
  (0 discrepancias).
- **SC-002**: Para los asientos asentados de un ejercicio, la suma total del
  Debe del Balance es igual a la suma total del Haber (cuadre global) en el
  100% de las consultas.
- **SC-003**: El 100% de los asientos en estado `borrador` queda excluido de
  ambos informes.
- **SC-004**: Un contable puede generar en pantalla cualquiera de los dos
  informes de un ejercicio con hasta **10.000 asientos** en menos de 3 segundos.
- **SC-005**: El contenido exportado reproduce fielmente lo mostrado en
  pantalla (0 diferencias de importes o filas).
- **SC-006**: Los informes no mezclan datos entre empresas/ejercicios:
  0 accesos cruzados entre contextos distintos.

## Assumptions

- El modelo y las reglas de partida doble ya existen (asientos con apuntes
  Debe/Haber, estados `borrador`/`asentado`, inmutabilidad de lo asentado); esta
  funcionalidad es de consulta y agregación, no de registro.
- El Libro Mayor y el Balance de Sumas y Saldos operan siempre sobre el
  **ejercicio activo** seleccionado en la interfaz; no requieren comparación
  entre ejercicios en esta fase.
- Los informes incluyen toda cuenta **con movimientos** (aunque su saldo neto
  sea cero); las cuentas sin ningún movimiento se muestran vacías en el Mayor y
  se omiten del Balance.
- La exportación se ofrece en CSV y PDF, cada una con su propio botón, tanto en
  el Libro Mayor como en el Balance de Sumas y Saldos (confirmado en
  clarificación).
- El coste del informe se asume aceptable con SQLite en modo WAL y los
  volúmenes de un ejercicio anual típico; no se requiere motor de informes
  externo.
- Se mantiene el estilo y los componentes M3 ya empleados en las vistas de
  Diario y Plan de Cuentas.
