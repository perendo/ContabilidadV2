<!--
Sync Impact Report
==================
- Version change: 1.0.0 → 1.1.0 (MINOR: nueva referencia normativa material)
- Modified principles:
  - I. Incremental Vertical Slices → I. Slices Verticales Incrementales
  - II. Strict Backend-Frontend Separation → II. Separación Estricta Backend-Frontend
  - III. Primary Accounting Integrity → III. Integridad Contable Primaria
  - IV. Robust Typed Architecture → IV. Arquitectura Tipada Robusta
  - V. Multi-Station SQLite Concurrency → V. Concurrencia SQLite MultiPuesto
- Added sections: ninguna nueva; se añade la exigencia de cumplimiento del
  PGC de España en Principios y en Restricciones Técnicas y de Modelo de Datos.
- Removed sections: ninguna
- Follow-up TODOs: ninguno
-->

# Constitución de ContabilidadV2

## Principios Fundamentales

### I. Slices Verticales Incrementales (NO NEGOCIABLE)

Toda funcionalidad se entrega como módulos pequeños, autocontenidos y
funcionales (slices verticales) que compilan, se ejecutan y se validan de
forma independiente. La estabilidad y la validación rápida DEBEN preceder a
la adición de complejidad; ningún slice parcial o defectuoso se integrará en
la línea principal de desarrollo. Justificación: mantiene el sistema
contable auditable y hace que los defectos aparezcan pronto en un dominio
donde los errores silenciosos son costosos.

### II. Separación Estricta Backend-Frontend (NO NEGOCIABLE)

El sistema DEBE mantener una separación clara entre la API backend (FastAPI)
y el cliente web (Next.js). Toda la lógica contable (validaciones, cálculos,
cuadre, reglas de periodos) reside EXCLUSIVAMENTE en el backend; el frontend
solo presenta y orquesta, nunca calcula resultados contables. Justificación:
garantiza un comportamiento contable coherente, testeable y auditable sea
cual sea el cliente que se utilice.

### III. Integridad Contable Primaria (NO NEGOCIABLE)

- Todo asiento o apunte DEBE cumplir estrictamente la partida doble: la suma
  del Debe DEBE ser igual a la suma del Haber en todo momento.
- Los asientos asentados/cerrados son inmutables; las correcciones se
  efectúan mediante asientos de rectificación/extorno, nunca editando ni
  eliminando el asiento original.
- El sistema DEBE ajustarse a la normativa del Plan General Contable (PGC)
  de España en su estructura de cuentas, nomenclatura y reglas de registro.
Justificación: el cuadre y la inmutabilidad son los fundamentos legales y
probatorios de los registros contables, y el cumplimiento del PGC es
obligatorio para la validez contable en España.

### IV. Arquitectura Tipada Robusta

El backend se construye con FastAPI y Python, con tipado estricto mediante
modelos Pydantic en todas las entradas y salidas, rendimiento asíncrono
cuando proceda, y generación automática de OpenAPI como fuente de verdad del
contrato. El frontend se construye con Next.js, usando Server Components por
defecto y Client Components solo cuando la reactividad o la agilidad de la
interfaz lo exijan.

### V. Concurrencia SQLite MultiPuesto

SQLite DEBE configurarse para entorno multipuesto: se habilitará el modo WAL
(Write-Ahead Logging) y pragmas de concurrencia para soportar accesos
simultáneos sin bloqueos de lectura. Las lecturas NO DEBEN quedar bloqueadas
por escrituras en operación normal.

## Restricciones Técnicas y de Modelo de Datos

- Backend: FastAPI (Python), tipado estricto con Pydantic, E/S asíncrona,
  documentación OpenAPI.
- Base de datos: SQLite con modo WAL y pragmas de concurrencia ajustados.
- Frontend: Next.js con división Server/Client Components según la necesidad.
- Normativa aplicable: Plan General Contable (PGC) de España. El modelo de
  datos contable DEBE reflejar la estructura de cuentas del PGC (cuentas y
  subcuentas, grupos y subgrupos) y sus reglas de registro.
- El modelo de datos contable DEBE imponer el cuadre de partida doble
  (Debe = Haber) en el momento de la escritura, como invariante de base de
  datos/API, y no solo en la interfaz.
- Los periodos cerrados y los asientos asentados DEBEN estar bloqueados
  frente a modificaciones en la capa de datos además de en la capa API.

## Estrategia de Iteración y Estándares de Código

1. **Fase 1 (Núcleo Base)**: gestión del Plan General Contable
   (cuentas/subcuentas según el PGC de España); registro e introducción
   simple de asientos diarios (Debe/Haber); consulta sencilla de Diario y
   Libro Mayor.
2. **Fase 2 (Validación y Multipuesto)**: control de concurrencia y
   validaciones de cierre de periodo; listados de Balance de Sumas y Saldos.
3. **Fase 3 (Especialización y Automatización)**: gestión de IVA/impuestos;
   facturación básica integrada y herramientas auxiliares.

Estándares:

- Toda nueva característica DEBE pasar por el flujo de Spec Kit
  (`specify plan`, `specify spec`) antes de iniciar la implementación.
- Se REQUIERE cobertura de pruebas automáticas para toda la lógica de cálculo
  y cuadre contable antes de liberar cada iteración; ninguna versión se
  publica con pruebas de cuadre fallidas o ausentes.
- Las fases son ordenadas e incrementales: no se inicia trabajo de una fase
  posterior hasta que el slice de la fase actual esté validado y estable.

## Gobierno

- Esta constitución prevalece sobre todas las demás prácticas del proyecto
  ContabilidadV2; las convenciones en conflicto DEBEN ceder ante ella.
- Las enmiendas DEBEN documentarse en este archivo, incrementar la versión
  según semver (MAJOR: eliminación o redefinición de principios; MINOR: nueva
  sección o principio añadido o expandido materialmente; PATCH:
  aclaraciones, redacción, correcciones), y registrar la fecha de enmienda.
- Procedimiento de enmienda: proponer el cambio, actualizar este archivo con
  un Sync Impact Report y obtener la aprobación del responsable del proyecto
  antes de fusionar.
- Revisión de cumplimiento: cada PR y cada revisión DEBE verificar el
  cumplimiento de todos los principios; las violaciones DEBEN bloquear el
  merge hasta su resolución.
- Usar la documentación del repositorio (README, docs) para la guía de
  desarrollo en tiempo de ejecución, siempre que no entre en conflicto con
  esta constitución.

**Versión**: 1.1.0 | **Ratificada**: 2026-10-08 | **Última Enmienda**: 2026-10-08
