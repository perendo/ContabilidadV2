# Quickstart / Validación — 005-modulos-fiscales

Guía de validación end-to-end tras la implementación. Detalles de esquema y
contratos en [`data-model.md`](./data-model.md) y [`contracts/`](./contracts/).
No sustituye a la suite de tests (`tasks.md`/implementación).

## Prerrequisitos

- Backend levantado y migrado (BD SQLite WAL `backend/contabilidadv2.db`):
  - `..\.venv\Scripts\python.exe -m alembic upgrade head` (desde `backend/`)
  - `..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000` (desde `backend/`)
- Usuarios de desarrollo del seed (`admin/admin-2026`, `contable/contable-2026`).
- Empresa + ejercicio abierto con PGC base sembrado y subcuentas de
  clientes/proveedores (400/430/600/700/472/477 y 4751/473 si se usan
  retenciones).
- Contexto: cabeceras `X-Empresa-Id` y `X-Ejercicio-Id` + `Authorization: Bearer`.

## Escenario 1 — Factura de venta con IVA y asiento automático

1. `POST /api/v1/facturas` con `origen:"venta"`, una línea base `1000.00`,
   `tipo_iva:"21.00"`, `cuota_iva:"210.00"`.
2. Esperado: `201` con `asiento_id` asignado; el asiento cuadra (ΣDebe=ΣHaber) y
   aparece en Diario con apuntes 430/700/477.
3. Repetir el mismo `tercero_cif`+`numero` → `409` (duplicado).

## Escenario 2 — Factura de compra con retención y Libros/Retenciones

1. `POST /api/v1/facturas` `origen:"compra"`, `tipo_retencion:"111"`, línea con
   base `1000.00`, IVA `21.00`, retención `15.00`.
2. Esperado: `201`; asiento con 600 deb 1000 / 472 deb 210 / 400 hab 1060 /
   4751 hab 150.
3. `POST` 2ª factura del mismo CIF (distinto número) con retención.
4. `GET /api/v1/facturas/retenciones?tipo=111&desde=YYYY-01-01&hasta=YYYY-12-31`
   → agrupado por CIF con base y cuota retención totales.
5. `GET /api/v1/facturas/libros/iva?origen=soportado&desde&hasta` → fila por
   factura + totales por tipo.

## Escenario 3 — Liquidación IS y vista de presentación

1. `POST /api/v1/is` con `resultado_contable:"100000.00"`, un ajuste aumento
   `5000.00` y uno disminución `8000.00`, `tipo_gravamen:"25.00"`,
   `retenciones_pagos_cuenta:"4000.00"`.
2. `GET /api/v1/is` → base `97000.00`, cuota íntegra `24250.00`, diferencial
   `20250.00` (a ingresar).
3. `GET /api/v1/presentaciones/200?periodo=YYYY` → `resumen` con esos importes,
   `casillas` con numeración oficial y `bloque_descarga.habilitado: false`.
4. `GET /api/v1/presentaciones/200/fichero?periodo=YYYY` → **409** (borrador).

## Escenario 4 — Cierre y fichero de posiciones fijas

1. `POST /api/v1/is/cerrar` → `200`, `estado:"cerrada"`, resultados congelados;
   `PUT /api/v1/is` → `409` (inmutable).
2. `GET /api/v1/presentaciones/200?periodo=YYYY` →
   `bloque_descarga.habilitado: true`.
3. `GET /api/v1/presentaciones/200/fichero?periodo=YYYY` → descarga
   `200_YYYY.txt` (UTF-8/CRLF, longitudes fijas, cabecera NIF/razón social,
   registros de totales y de fin).
4. Verificar que existe `backend/impuestos/{empresa_id}/{YYYY}/200_YYYY.txt`
   (guardado en el directorio `impuestos`, FR-030) y que la descarga repite la
   misma ruta sin regenerar.
5. Regenerar (borrar el fichero y repetir la descarga) → nuevo `200_YYYY.txt` con
   mismo nombre; `fichero_presentacion` registra hash, usuario y fecha actualizados.

## Comandos de verificación (orden obligatorio)

```text
backend:  ruff check app tests  →  pytest -q
frontend: npm run lint  →  npx tsc --noEmit  →  npm run build
```

## Resultado esperado

- 0 asientos descuadrados generados desde facturas.
- Todos los duplicados CIF+Nº+ejercicio rechazados (409).
- Libro de IVA y resumen de retenciones coinciden al céntimo con las facturas.
- 100% de los ficheros generados pasan el validador de posiciones fijas de la
  plantilla AEAT del modelo.