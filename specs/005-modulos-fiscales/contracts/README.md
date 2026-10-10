# Contratos HTTP — Módulos Fiscales

Base path: `/api/v1`. Todos los endpoints requieren `Authorization: Bearer` (o
cookie `access_token`) + cabeceras `X-Empresa-Id` y `X-Ejercicio-Id` (ver
`specs/001-modulo-core-contable/contracts/auth.md`). Significado general de
errores: `400` contexto faltante, `403` sin acceso a la empresa, `404` recurso
no encontrado, `409` conflicto de unicidad/estado(cerrado), `422` validación.

| Documento | Cobertura |
|-----------|-----------|
| [`facturas.md`](./facturas.md) | Facturas (CRUD), Libros de IVA, resumen de retenciones 111/115 |
| [`presentaciones.md`](./presentaciones.md) | Vista de presentación AEAT y fichero de posiciones fijas (303/111/115/200) |
| [`is.md`](./is.md) | Liquidación del Impuesto sobre Sociedades |

Los importes monetarios viajan como **string decimal** con 2 decimales (JSON),
p. ej. `"1210.00"`. Los ficheros AEAT se descargan como `text/plain` (UTF-8,
CRLF) con longitudes de campo fijas.