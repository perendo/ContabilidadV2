# Contratos de API — 001-modulo-core-contable (Fase 1)

Convención del proyecto: la API es la única autoridad contable (Principio II
de la constitución). Fuente de verdad en runtime: esquema OpenAPI generado
por FastAPI (`/openapi.json`). Estos ficheros documentan el contrato de
cara a la implementación y a los tests de contrato.

- [Contexto y autenticación](auth.md): auth + cabeceras `X-Empresa-Id` /
  `X-Ejercicio-Id` + pertenencia + política de contraseñas.
- [Empresas y Ejercicios](identidad.md): entidades organizativas.
- [Plan de Cuentas y Asientos](contable.md): núcleo contable (planes,
  borradores, asentado y Diario).

Superficie de asientos (resumen):

| Método | Ruta | Acción |
|--------|------|--------|
| POST | `/api/v1/asientos` | Guardar borrador (admite descuadre, 2..N líneas) |
| PUT | `/api/v1/asientos/{id}` | Editar borrador |
| POST | `/api/v1/asientos/{id}/asentar` | Borrador → asentado (exige ΣDebe = ΣHaber) |
| GET | `/api/v1/asientos` | Diario (asentados), paginado/filtrable |
| GET | `/api/v1/asientos/borradores` | Lista de borradores del ejercicio |
| GET | `/api/v1/asientos/{id}` | Detalle con apuntes (asentado o borrador) |

Convenciones comunes:

- Base path: `/api/v1`.
- Cuerpos JSON; fechas `YYYY-MM-DD`; importes como cadena decimal 2dp.
- Errores: `{ "detail": "<mensaje>" }`.
- Códigos: `400` contexto/firma inválida, `401` no autenticado, `403` sin
  acceso a la empresa/ejercicio, `404` recurso inexistente, `409` conflicto
  de estado (ejercicio cerrado, asiento asentado) o unicidad, `422`
  validación/descuadre.
- Esquema BD bajo control de Alembic (FR-021): los endpoints no cambian el
  esquema; las migraciones viven en `backend/alembic/`.