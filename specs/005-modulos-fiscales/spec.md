# Especificación: Libros Registro de IVA, Retenciones IRPF e Impuesto sobre Sociedades

**Feature**: `005-modulos-fiscales`
**Fecha**: 2026-10-11
**Estado**: Borrador
**Input**: User description: "Spec 1: Libros Registro de IVA, Retenciones IRPF e Impuesto sobre Sociedades" — módulos fiscales sobre la arquitectura multi-tenant (Empresa, Ejercicio, Usuario) existente.

---

## Resumen

Añadir al núcleo contable los **módulos fiscales** necesarios para la operativa diaria de una empresa española:

1. **Libro Registro de IVA (Soportado y Repercutido)**: registro de facturas de compra y venta con desglose de bases, tipos y cuotas de IVA (y Recargo de Equivalencia), generando de forma automática y atómica el asiento contable correspondiente.
2. **Libro Registro de Retenciones e IRPF**: gestión de retenciones soportadas/practicadas en facturas de profesionales y alquileres, con agrupación por perceptor para las liquidaciones de los modelos 111 y 115.
3. **Impuesto sobre Sociedades (IS)**: cálculo del resultado contable ajustado (aumentos/disminuciones extracontables), aplicación del tipo de gravamen, deducción de retenciones y pagos a cuenta, y determinación de la cuota a ingresar o a devolver.

Todo ello respetando los principios del proyecto: la lógica fiscal vive **solo** en el backend, los asientos cumplen partida doble (ΣDebe = ΣHaber) al asentarse, y los asentados/periodos cerrados son inmutables.

---

## Clarifications

### Session 2026-10-11

- Q: ¿Para cuáles de las liquidaciones de este módulo debe generarse el fichero de posiciones fijas de la AEAT? → A: Todos los modelos calculados (303 IVA trimestral, 111/115 retenciones IRPF y 200 IS); el fichero debe seguir estrictamente la plantilla oficial de posiciones fijas definida por la AEAT.
- Q: ¿Cómo debe mostrarse en pantalla la vista de presentación a la AEAT de cada modelo? → A: Ambas: un resumen simplificado por bloques arriba y, desplegable, el detalle por casillas oficiales con su numeración tal como aparecen en el formulario AEAT.
- Q: ¿Cuándo debe poder generarse el fichero de posiciones fijas de cada modelo? → A: Solo con datos cerrados/validados: 111/115 y 200 requieren liquidación cerrada, y 303 requiere periodo cerrado; en otro estado la vista en pantalla funciona pero la descarga se deniega (botón deshabilitado + rechazo del backend).
- Q: ¿La generación del fichero debe cubrir el envío telemático a la AEAT? → A: No, solo generar y descargar el fichero para presentación manual; además, los ficheros se guardan en un directorio `impuestos` organizado por empresa y ejercicio (un único fichero por modelo/periodo) para no complicar las presentaciones.
- Q: ¿El usuario dispone de botón de descarga del fichero generado? → A: Sí, se incluye un botón de descarga del fichero para el usuario que lo solicite; esto NO impide que el fichero se guarde también en el directorio impuestos (ambas operaciones coexisten).

---

## Contexto y Motivación

- **Estado actual**: el núcleo permite crear ejercicios, cuentas (PGC base + subcuentas), asientos manuales, Diario, Mayor y Balance de Sumas y Saldos.
- **Problema**: introducir facturas con IVA y retenciones a mano es propenso a error y no permite obtener los libros registro ni las liquidaciones periódicas exigidas por la AEAT.
- **Oportunidad**: al modelar la factura como documento estructurado, el sistema puede **derivar automáticamente** el asiento y, con él, los Libros de IVA/IRPF y las bases para los modelos 111/115 y el IS.

---

## Historias de Usuario

### US1: Registrar factura de venta (IVA repercutido) (P1)

**Como** contable
**Quiero** dar de alta una factura emitida con una o varias líneas de IVA
**Para** que el sistema genere el asiento de ingreso y alimente el Libro de IVA Repercutido

**Why this priority**: es el flujo de facturación más habitual y sin él no hay Libro de IVA Repercutido ni liquidación trimestral.

**Independent Test**: crear una factura de venta a crédito (430/700/477) con una línea al 21% y verificar que el asiento resultante cuadra y aparece en el Libro de IVA Repercutido.

**Acceptance Scenarios**:

1. **Given** un ejercicio abierto con PGC base sembrado y una subcuenta de cliente, **When** registro una factura de venta con base 1.000 € al 21% (cuota 210 €), **Then** el sistema crea un asiento con Debe 1.210 € en 430 y Haber 1.000 € en 700 + 210 € en 477, y la factura queda vinculada a ese asiento.
2. **Given** una factura de venta ya registrada con CIF de cliente y número de factura, **When** intento registrar otra con el mismo CIF y número en el mismo ejercicio, **Then** el sistema rechaza la operación por duplicado.
3. **Given** una factura con varias líneas a tipos distintos (21% y 10%), **When** la registro, **Then** el asiento desglosa una cuota en 477 por cada tipo y ΣDebe = ΣHaber.

---

### US2: Registrar factura de compra (IVA soportado) (P1)

**Como** contable
**Quiero** dar de alta una factura recibida de un proveedor con su IVA
**Para** generar el asiento de gasto y alimentar el Libro de IVA Soportado

**Why this priority**: el IVA soportado deducible es imprescindible para la liquidación trimestral (modelo 303) y el cierre del IS.

**Independent Test**: crear una factura de compra (600/472/400) con base 500 € al 21% y comprobar el cuadre y su presencia en el Libro de IVA Soportado.

**Acceptance Scenarios**:

1. **Given** un proveedor con subcuenta en el ejercicio, **When** registro una factura de compra con base 500 € al 21% (cuota 105 €), **Then** se crea un asiento con Debe 500 € en 600 + 105 € en 472 y Haber 605 € en 400.
2. **Given** una factura de compra sujeta a Recargo de Equivalencia (21% IVA + 5,2% RE), **When** la registro, **Then** el asiento incluye la cuota de IVA en 472 y el recargo en la cuenta de recargo correspondiente, cuadrando el total.

---

### US3: Consultar y exportar los Libros Registro de IVA (P1)

**Como** contable
**Quiero** consultar el Libro Registro de IVA Repercutido y Soportado por periodo
**Para** revisar las operaciones y preparar la liquidación trimestral

**Why this priority**: el libro registro es una obligación formal y la base de los modelos periódicos.

**Independent Test**: tras registrar varias facturas, consultar el libro por rango de fechas y verificar que las totales de bases y cuotas por tipo coinciden con las facturas del periodo.

**Acceptance Scenarios**:

1. **Given** facturas de venta y compra registradas en un trimestre, **When** consulto el Libro de IVA Repercutido filtrado por ese trimestre, **Then** obtengo el detalle por factura y los totales de base y cuota por tipo de IVA.
2. **Given** un libro consultado, **When** lo exporto, **Then** obtengo un fichero tabular con las columnas legales esperadas (fecha, número, CIF, base, tipo, cuota, total).

---

### US4: Gestionar retenciones IRPF y agrupar por perceptor (P1)

**Como** contable
**Quiero** que las facturas de profesionales y alquileres recojan la retención practicada/soportada
**Para** obtener los totales por perceptor que alimentan los modelos 111 y 115

**Why this priority**: sin retenciones no se puede presentar 111 (trabajo/profesionales) ni 115 (alquileres), obligación periódica habitual.

**Independent Test**: registrar una factura de profesional con retención del 15% y verificar que el resumen por CIF devuelve la base, la retención y el número de facturas.

**Acceptance Scenarios**:

1. **Given** una factura de un profesional con base 1.000 €, IVA 21% y retención 15%, **When** la registro, **Then** el asiento incluye el gasto, el IVA soportado y el pasivo de retención (4751/473) de forma cuadrada, y la retención queda asociada al perceptor.
2. **Given** varias facturas con retención del mismo perceptor en un trimestre, **When** solicito el resumen por perceptor, **Then** obtengo los totales agregados por CIF para el modelo correspondiente (111/115).
3. **Given** una factura de alquiler con retención, **When** consulto el Libro de Retenciones de ese trimestre, **Then** aparece clasificada como tipo alquiler (115) y separada de las de profesionales (111).

---

### US5: Liquidación del Impuesto sobre Sociedades (P2)

**Como** responsable fiscal
**Quiero** calcular la liquidación del IS a partir del resultado contable del ejercicio
**Para** conocer la cuota a ingresar o a devolver antes de presentar el modelo

**Why this priority**: cierra el ciclo fiscal anual; depende de que el ejercicio esté completo y cuadrado, por lo que es de prioridad posterior a la facturación.

**Independent Test**: partiendo de un resultado contable conocido, registrar ajustes extracontables, aplicar el 25%, restar retenciones/pagos a cuenta y verificar la cuota resultante.

**Acceptance Scenarios**:

1. **Given** un ejercicio con resultado contable de 100.000 € y ajustes (aumentos 5.000 €, disminuciones 8.000 €), **When** genero la liquidación al 25%, **Then** la base imponible es 97.000 € y la cuota íntegra es 24.250 €.
2. **Given** una cuota íntegra de 24.250 € y retenciones/pagos a cuenta por 4.000 €, **When** cierro la liquidación, **Then** la cuota diferencial a ingresar es 20.250 € y queda almacenada en el modelo de liquidación.
3. **Given** una liquidación guardada, **When** la reabro/cambio de ejercicio, **Then** el resultado se recalcula de forma reproducible a partir del resultado contable y los ajustes.

---

### Edge Cases

- **Factura con base imponible 0** (p. ej. operación exenta o no sujeta): el asiento no genera línea de IVA; debe permitirse y registrarse el motivo.
- **Redondeo monetario**: importes con más de 2 decimales en bases o tipos deben normalizarse a 2 decimales sin romper el cuadre (ajuste por diferencia de redondeo).
- **Duplicado exacto por CIF + Nº factura** dentro del mismo ejercicio: rechazo; el mismo Nº en ejercicios distintos es válido.
- **Retención ≥ base** o porcentajes fuera de rango (>100%): rechazo con validación.
- **Tipo de IVA no soportado** (p. ej. 0%, 4%, 10%, 21% y RE): debe poder registrarse cualquier tipo válido y reflejarse el tipo exacto en el libro.
- **Ejercicio cerrado**: no deben poder añadirse facturas ni modificarse liquidaciones de un ejercicio cerrado.
- **Perceptor sin CIF válido**: no debe poder agregarse en el resumen de modelos oficiales.
- **Liquidación IS sin retenciones**: cuota diferencial = cuota íntegra (sin error).
- **Regenerar un fichero ya generado** (mismo modelo/periodo): reemplaza el fichero existente en `impuestos/{empresa}/{ejercicio}` (idempotente, nunca duplica copias) y actualiza la trazabilidad de generación.

---

## Requirements *(mandatory)*

### Functional Requirements

**Facturación y asiento automático**

- **FR-001**: El sistema DEBE permitir registrar facturas de venta (repercutido) y de compra (soportado) con, al menos, fecha, número, CIF y razón social del tercero, tipo de operación y líneas de detalle.
- **FR-002**: Cada línea de factura DEBE almacenar base imponible, tipo de IVA, cuota de IVA y, cuando proceda, tipo y cuota de Recargo de Equivalencia.
- **FR-003**: El sistema DEBE calcular la cuota de IVA como base × tipo, redondeada a 2 decimales, sin delegar el cálculo en el cliente.
- **FR-004**: Al registrar una factura, el sistema DEBE generar de forma **atómica** el asiento contable correspondiente usando las cuentas PGC: 400/430 (terceros), 600/700 (gasto/ingreso) y 472/477 (IVA soportado/repercutido).
- **FR-005**: El asiento generado DEBE cumplir ΣDebe = ΣHaber; si no cuadra, la factura NO DEBE persistirse.
- **FR-006**: El sistema DEBE impedir facturas duplicadas por la combinación **CIF + Número de factura + Ejercicio** (repercutido y soportado).
- **FR-007**: El sistema DEBE vincular cada factura con el asiento que ha generado (trazabilidad bidireccional).
- **FR-008**: El sistema NO DEBE permitir registrar o modificar facturas en ejercicios cerrados.

**Libros Registro de IVA**

- **FR-009**: El sistema DEBE ofrecer consulta del **Libro Registro de IVA Repercutido** y del **Libro Registro de IVA Soportado** filtrable por rango de fechas.
- **FR-010**: El libro DEBE mostrar por factura: fecha, número, CIF y nombre del tercero, base imponible, tipo de IVA, cuota de IVA y total.
- **FR-011**: El libro DEBE totalizar bases y cuotas agrupadas por tipo de IVA del periodo consultado.
- **FR-012**: El sistema DEBE permitir exportar los libros de IVA en un formato tabular.

**Retenciones e IRPF**

- **FR-013**: El sistema DEBE permitir asociar a una factura una o varias retenciones, indicando base de retención, porcentaje y cuota.
- **FR-014**: El sistema DEBE distinguir la naturaleza de la retención (trabajo/profesionales → modelo 111; alquileres → modelo 115).
- **FR-015**: El asiento de una factura con retención DEBE registrar el pasivo de retención en las cuentas 4751 (Hacienda acreedora por retenciones) o 473 (Hacienda retenciones practicadas/soportadas), según naturaleza, cuadrando el total.
- **FR-016**: El sistema DEBE proporcionar un resumen de retenciones **agrupado por CIF de perceptor** para el periodo, con base, cuota y número de facturas, apto para las liquidaciones 111/115.
- **FR-017**: El sistema NO DEBE incluir en los resúmenes a perceptores sin CIF válido.

**Impuesto sobre Sociedades**

- **FR-018**: El sistema DEBE permitir crear una `LiquidacionImpuestoSociedades` por ejercicio con el resultado contable, una lista de ajustes extracontables (aumentos/disminuciones) y el tipo de gravamen (por defecto 25%).
- **FR-019**: El sistema DEBE calcular la base imponible = resultado contable + aumentos − disminuciones, y la cuota íntegra = base × tipo.
- **FR-020**: El sistema DEBE restar de la cuota íntegra las retenciones y pagos a cuenta para obtener la cuota diferencial (a ingresar si positiva, a devolver si negativa).
- **FR-021**: El sistema DEBE permitir registrar pagos a cuenta y retenciones imputados al IS y conservarlos para el cálculo.

**Presentación a la AEAT y fichero oficial**

- **FR-026**: El sistema DEBE mostrar en pantalla, para cada liquidación (303 IVA trimestral, 111/115 retenciones y 200 IS), la vista de presentación con: (a) un **resumen simplificado por bloques** (bases, cuotas, retenciones, pagos a cuenta y cuota resultante) y (b) el **detalle por casillas oficiales** del modelo, con su numeración tal como aparecen en el formulario AEAT y desplegable.
- **FR-027**: El sistema DEBE ofrecer para cada modelo (303, 111, 115, 200) una acción de generación del fichero de texto de **posiciones fijas** que siga estrictamente la plantilla oficial definida por la AEAT, así como un **botón de descarga** del fichero para el usuario que lo solicite. La descarga es independiente del guardado: el fichero DEBE quedar además persistido en el directorio `impuestos`.
- **FR-028**: El sistema DEBE validar el fichero generado contra las reglas de la plantilla oficial (longitudes de campo, tipos, alineación y totales) antes de entregárselo al usuario; un fichero no conforme NO DEBE ofrecerse.
- **FR-029**: El sistema DEBE restringir la descarga del fichero a estados cerrados/validados: el botón de generación se habilita solo cuando la liquidación de 111/115/200 está cerrada o el periodo del 303 está cerrado; en borrador la vista en pantalla funciona pero la descarga se deniega (backend) y el botón se muestra deshabilitado con aviso.
- **FR-030**: El sistema DEBE persistir cada fichero generado en una estructura organizada por **empresa y ejercicio** (directorio `impuestos/{empresa}/{ejercicio}`), con un único fichero por modelo y periodo; regenerar el mismo modelo/periodo reemplaza el fichero existente en lugar de duplicar copias.
- **FR-031**: El sistema DEBE registrar la trazabilidad de cada fichero generado (modelo, periodo, ruta, usuario y fecha de generación) para saber qué fichero corresponde a cada presentación.

**Transversales**

- **FR-022**: Todos los importes monetarios DEBEN tratarse con precisión decimal exacta (nunca coma flotante binaria).
- **FR-023**: Todas las operaciones DEBEN estar aisladas por empresa y ejercicio (multi-tenant) con las cabeceras `X-Empresa-Id` y `X-Ejercicio-Id`.
- **FR-024**: El cálculo de cuotas, retenciones, bases y ajustes DEBE residir exclusivamente en el backend.
- **FR-025**: El sistema DEBE registrar la trazabilidad de quién crea/cierra una liquidación y cuándo.

### Key Entities *(include if feature involves data)*

- **Factura**: documento fiscal (venta o compra) con fecha, número, tercero, tipo de operación, estado, ejercicio y vínculo al asiento generado. Clave de unicidad: CIF + número + ejercicio.
- **LineaFacturaIVA**: línea de detalle de una factura con base imponible, tipo de IVA, cuota de IVA y, opcionalmente, tipo y cuota de Recargo de Equivalencia.
- **Tercero / Perceptor**: contraparte de la factura identificada por CIF y razón social; puede ser proveedor, cliente o perceptor sujeto a retención.
- **Retencion**: retención asociada a una factura, con base, porcentaje, cuota, naturaleza y perceptor; agregable por CIF para modelos 111/115.
- **LiquidacionImpuestoSociedades**: liquidación anual con resultado contable, ajustes extracontables (aumentos/disminuciones), tipo de gravamen, retenciones y pagos a cuenta, base imponible y cuota diferencial.
- **Presentación AEAT (fichero)**: artefacto de salida derivado de los libros/liquidaciones que reproduce la plantilla oficial de **posiciones fijas** de un modelo (303/111/115/200); se genera desde datos validados del backend, se muestra en pantalla antes de su descarga y se guarda en un directorio de `impuestos` organizado por empresa y ejercicio.

*(El detalle de tipos, constraints y relaciones se concreta en el documento técnico `.specify/plans/01-modulos-fiscales.md`.)*

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un contable puede registrar una factura con IVA y obtener el asiento cuadrado en menos de 30 segundos, sin introducir manualmente las líneas del asiento.
- **SC-002**: El 100% de los asientos generados automáticamente desde facturas cumplen ΣDebe = ΣHaber (0 asientos descuadrados).
- **SC-003**: El 100% de los intentos de registrar una factura duplicada (mismo CIF + número + ejercicio) son rechazados.
- **SC-004**: El Libro de IVA de un trimestre con hasta 500 facturas se obtiene y totaliza por tipo en menos de 3 segundos.
- **SC-005**: El resumen de retenciones por perceptor para un trimestre coincide exactamente (al céntimo) con la suma de las retenciones de las facturas del periodo.
- **SC-006**: La cuota diferencial del IS calculada por el sistema coincide con el cálculo manual verificado para el 100% de los casos de prueba.
- **SC-007**: 0 facturas o liquidaciones pueden crearse o modificarse en un ejercicio cerrado.
- **SC-008**: El sistema soporta al menos los tipos de IVA general (21%), reducido (10%), superreducido (4%), exento/no sujeto (0%) y Recargo de Equivalencia (5,2%) sin romper el cuadre.
- **SC-009**: El 100% de los ficheros de posiciones fijas generados para 303/111/115/200 pasan un validador de formato contra la plantilla oficial de la AEAT (longitudes y tipos de campo, alineación y totales).
- **SC-010**: El usuario ve en pantalla los datos de presentación de un modelo antes de poder descargar el fichero, y esa vista se carga en menos de 3 segundos con hasta 500 operaciones/periodo.

---

## Assumptions

- **Reutilización del núcleo**: se reutilizan `Empresa`, `Ejercicio`, `Cuenta`, `Asiento` y `Apunte`; el PGC base ya está sembrado por ejercicio y el usuario crea las subcuentas necesarias.
- **Ámbito PGC**: las cuentas 400/430, 600/700, 472/477, 4751/473, y las de recargo de equivalencia (p. ej. 631/632 dentro del grupo de gastos) forman parte del PGC base o se crean como subcuentas según la operativa.
- **Alcance de modelos AEAT**: se generan los **datos** necesarios para los modelos 303 (IVA), 111/115 (retenciones por perceptor) y 200 (IS) y, además, el **fichero de posiciones fijas** de cada modelo siguiendo estrictamente la plantilla oficial de la AEAT. La **presentación telemática** (envío con firma electrónica al portal AEAT) queda fuera de alcance: el fichero se entrega al usuario para su presentación manual.
- **Almacenamiento de ficheros AEAT**: los ficheros de presentación se guardan en el backend en un directorio de `impuestos` organizado por empresa y ejercicio, con un único fichero por modelo/periodo; la presentación la realiza el usuario descargándolo y subiéndolo manualmente al portal de la AEAT (sin envío telemático automatizado).
- **Tipo de gravamen IS**: 25% por defecto, configurable por ejercicio; no se modelan regímenes especiales ni tipos reducidos de empresas de nueva creación en esta fase.
- **IS simplificado**: los ajustes extracontables se registran como lista de aumentos/disminuciones con importe y descripción; la conciliación detallada con el resultado contable estándar (modelo oficial) se abordará en una iteración posterior.
- **Moneda**: operaciones en EUR; la multipropósito/extranjera queda fuera de alcance de esta spec.
- **Facturas rectificativas**: se contemplan como facturas con signo o tipo de operación propio; el detalle de la rectificación se refinará en el plan.
- **Concurrencia**: se mantiene el modo WAL de SQLite y las validaciones de cuadre en la capa de servicio/DB ya existentes.

---

## Fuera de Alcance (Out of Scope)

- Presentación telemática (envío con firma electrónica a la AEAT): el fichero de posiciones fijas se genera y entrega al usuario para su presentación manual en el portal.
- Facturación electrónica (FACe / FacturaE) y firma digital.
- Gestión de nóminas completas y modelos 190 (resúmenes anuales).
- Contabilidad analítica o centros de coste.
- Multidivisa y conversión de tipos de cambio.
- Regímenes fiscales especiales (módulos, agricultura, entidades sin ánimo de lucro).

---

## Dependencias

- Núcleo contable (`specs/001-modulo-core-contable`): asientos, cuentas, cuadre e inmutabilidad.
- Auth y contexto multi-tenant (cabeceras `X-Empresa-Id` / `X-Ejercicio-Id`).
- Servicio de identidad (`crear_ejercicio` → `sembrar_pgc`) para disponer de las cuentas PGC necesarias.
- Documento técnico de apoyo: `.specify/plans/01-modulos-fiscales.md` (modelo SQLModel, endpoints, slices, tests).

---

## Próximos Pasos

1. `/speckit.clarify` (opcional) para resolver dudas de alcance.
2. `/speckit.plan` → plan técnico detallado (puede apoyarse en `.specify/plans/01-modulos-fiscales.md`).
3. `/speckit.tasks` → desglose en tareas por slice.
4. Implementar Slice 1 (modelos + migración) → Slice 2 (API) → Slice 3 (UI).
