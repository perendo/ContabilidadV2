# Backend — ContabilidadV2

Core contable multi-tenant: FastAPI + SQLModel + Alembic (Python 3.12, venv en
la raíz del repo `.venv`).

## Módulo fiscal (spec 005)

Los ficheros AEAT de posiciones fijas (modelos 303/111/115/200) se generan y
persisten en:

```text
backend/impuestos/{empresa_id}/{anio}/{modelo}_{periodo}.txt
```

- Carpeta versionada solo con `.gitkeep` (`.gitignore`: `backend/impuestos/*` + `!backend/impuestos/.gitkeep`); los ficheros generados quedan ignorados.
- Un único fichero por `(ejercicio, modelo, periodo)`; regenerar sobrescribe y refresca la trazabilidad (`generado_at`, usuario y hash).
- Trazabilidad (hash SHA-256, usuario y fecha) en la tabla `fichero_presentacion`.
- La descarga (`GET /api/v1/presentaciones/{modelo}/fichero`) exige el **ejercicio cerrado** (303/111/115) o la **liquidación del IS cerrada** (200); en caso contrario responde `409`.