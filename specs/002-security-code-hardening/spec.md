# Feature Specification: Spec 2 - Security & Code Hardening

**Feature Branch**: `002-security-code-hardening`  
**Status**: Ready for Implementation  
**Created**: Octubre 2026  
**Input**: Informe de Auditoría de Código y Seguridad sobre `001-modulo-core-contable`  
**Target Platform**: Linux/Windows multipuesto (FastAPI + SQLModel + Next.js 15)  

---

## 1. Resumen de Hallazgos y Matriz de Amenazas

La auditoría de la Fase 1 reveló 14 vectores de riesgo categorizados por severidad y superficie de ataque:

| ID | Severidad | Categoría | Archivo / Componente | Vector / Vulnerabilidad | Impacto |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | 🔴 **Crítica** | Autenticación | `backend/app/config.py` | Fallback de `jwt_secret` estático en código fuente. | Falsificación de tokens JWT con rol admin sin autenticación. |
| **CONT-01** | 🔴 **Crítica** | Lógica Contable | `backend/app/services/asientos.py` | Bypass de partida doble: Asentado de asientos con 0 líneas. | Corrupción legal de libros diarios; violación del Código de Comercio y PGC. |
| **SEC-02** | 🟠 **Alta** | Web Security | `backend/app/api/deps.py` & `auth.py` | Autenticación por cookie sin protección contra CSRF ni cabecera anti-forgery. | Peticiones cross-origin no autorizadas para crear asientos o empresas. |
| **PERF-01** | 🟠 **Alta** | Disponibilidad (DoS) | `backend/app/api/asientos.py` & `cuentas.py` | Vuelco total de tablas en memoria RAM (`len(session.exec().all())`). | Agotamiento de memoria RAM (OOM Crash) del proceso uvicorn bajo carga real. |
| **SEC-03** | 🟠 **Alta** | Aislamiento Multi-Tenant | `backend/app/api/deps.py` | Omisión de validación de `Empresa.activa` en `get_empresa_context`. | Acceso e inserción de datos en tenants formalmente dados de baja o suspendidos. |
| **CONC-01** | 🟠 **Alta** | Concurrencia | `backend/app/services/asientos.py` | TOCTOU y colisión en asignación de correlativos con `range(5)`. | Fallos 409 por contención y riesgo de asientos desbalanceados por edición paralela. |
| **SEC-05** | 🟠 **Alta** | Disponibilidad (DoS) | `backend/app/api/auth.py` | Ausencia de Rate Limiting en endpoint de Login con función pesada Argon2. | Saturación del 100% de CPU en workers ante ataques de fuerza bruta. |
| **LEGAL-01**| 🟠 **Alta** | Cumplimiento Legal | `backend/app/models/contable.py` | Carencia de pistas de auditoría (quién creó, quién asentó, timestamp). | Incumplimiento grave de la Ley Antifraude 11/2021 y normativa tributaria. |
| **PERF-02** | 🟡 **Media** | Rendimiento DB | `backend/app/services/asientos.py` | Problema N+1 masivo en `obtener_apuntes` y `_totales`. | Latencia inaceptable (>2s) en páginas del Diario con cientos de apuntes. |
| **SEC-04** | 🟡 **Media** | Control de Acceso (RBAC)| `backend/app/api/empresas.py` | Creación de ejercicios sin validar rol administrativo. | Escalada de privilegios de usuario contable raso. |
| **FRONT-01**| 🟡 **Media** | Precisión Numérica | `frontend/src/components/FormAsiento.tsx`| Uso de aritmética flotante (`Number` IEEE 754) en cálculo de delta contable. | Falsos descuadres en cliente y discrepancias con el servidor. |
| **SEC-06** | 🔵 **Baja** | Reconocimiento | `backend/app/main.py` | Exposición de pragmas de SQLite en `/health`. | Fuga de información sobre motor e infraestructura. |
| **FRONT-02**| 🔵 **Baja** | UI / A11y | `frontend/src/components/FormAsiento.tsx`| Incumplimiento del estándar Material Design 3 (MUI v6). | Inconsistencia visual y de experiencia de usuario. |
| **OPS-01**  | 🔵 **Baja** | Portabilidad | `start_servers.py` | Dependencia rígida de utilidades CLI de Windows (`cmd /k`, `taskkill`). | Fallo de despliegue en Linux, Docker y entornos CI/CD. |

---

## Clarifications

### Session 2026-10-09

- Q: Cuando una petición se autentica mediante la cookie `access_token`, ¿qué cabecera anti-CSRF debe enviar una petición mutacional (`POST`/`PUT`/`DELETE`) para que el backend la acepte? → A: Exigir únicamente la presencia de `X-Requested-With: XMLHttpRequest` (no se emite ni valida `X-CSRF-Token`).
- Q: El límite de 5/minuto sobre `/auth/login` ¿qué peticiones cuenta y con qué clave? → A: Todas las peticiones (éxito o fallo), con clave = IP remota.
- Q: Al quedar `jwt_secret` sin valor por defecto, ¿cómo debe comportarse la aplicación en desarrollo y tests cuando no se define `APP_JWT_SECRET`? → A: Obligatorio en todos los entornos; la app no arranca sin `APP_JWT_SECRET`, y `conftest.py` y `.env.example` deben definirlo (sin ningún fallback embebido).
- Q: La exigencia anti-CSRF rompería las mutaciones del cliente autenticado por cookie; ¿debe el frontend enviar `X-Requested-With: XMLHttpRequest` y en qué peticiones? → A: Sí; `src/lib/api.ts` añade la cabecera en toda petición `POST`/`PUT`/`DELETE` (nuevo slice + test).
- Q: `creado_por_usuario_id` y `created_at` son `NOT NULL`; ¿qué debe hacer la migración Alembic con los asientos ya existentes? → A: Estrategia nullable → backfill a un usuario admin/sistema → `NOT NULL`. Nota: la BD de desarrollo actual no contiene asientos ni PGC, por lo que el backfill no afecta a ninguna fila y es aceptable recrear la BD de desarrollo; la migración se escribe igualmente de forma defensiva.
- Q: El campo `version` que se añade a `Asiento` ¿cómo debe usarse realmente en Spec 2? → A: Solo servidor: se añade el campo y se incrementa en cada modificación, sin validarlo contra el cliente (control de concurrencia optimista queda para Fase 2).
- Q: Tras quitar los pragmas, ¿qué debe devolver exactamente `GET /api/v1/health`? → A: Únicamente `{"status": "ok"}` (liveness mínimo, sin versión ni detalles de infraestructura).
- Q: ¿Qué alcance debe tener la migración a MUI v6 en `FormAsiento.tsx` (FRONT-02)? → A: Solo los controles interactivos del formulario (`TextField`, `Select`, `Button` de MUI v6) con etiquetas y `data-testid`, sin rehacer el layout.

---

## 2. Cambios Requeridos en Arquitectura y Código

### 2.1. Ajustes en Modelos SQLModel y Esquemas Pydantic

#### A. Trazabilidad Contable e Inalterabilidad (Ley Antifraude 11/2021)
Modificar `backend/app/models/contable.py` para incluir auditoría estricta de usuarios y marcas temporales:

```python
# backend/app/models/contable.py
from datetime import UTC, datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Index
from sqlmodel import Field, SQLModel

def _utcnow() -> datetime:
    return datetime.now(UTC)

class Asiento(SQLModel, table=True):
    __tablename__ = "asiento"
    __table_args__ = (
        UniqueConstraint("ejercicio_id", "numero", name="uq_asiento_ejercicio_numero"),
        Index("ix_asiento_ejercicio_estado_fecha", "ejercicio_id", "estado", "fecha"),
    )
    id: int | None = Field(default=None, primary_key=True)
    ejercicio_id: int = Field(
        sa_column=Column("ejercicio_id", ForeignKey("ejercicio.id", ondelete="RESTRICT"), nullable=False)
    )
    numero: int | None = Field(default=None)
    fecha: date = Field(nullable=False)
    concepto: str = Field(nullable=False, max_length=300)
    estado: str = Field(default="borrador", max_length=20)
    
    # Nuevos campos de trazabilidad requeridos:
    creado_por_usuario_id: int = Field(
        sa_column=Column("creado_por_usuario_id", ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    )
    asentado_por_usuario_id: int | None = Field(
        default=None,
        sa_column=Column("asentado_por_usuario_id", ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=True)
    )
    created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    asentado_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    version: int = Field(default=1, nullable=False)  # Reservado para control de concurrencia optimista (Fase 2)
```

#### B. Endurecimiento de Configuración y Clave JWT
Eliminar la asignación de claves inseguras por defecto en `backend/app/config.py`:

```python
# backend/app/config.py
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")
    database_url: str = "sqlite:///./contabilidadv2.db"
    jwt_secret: str  # Obligatorio: la app no arranca si falta
    jwt_algorithm: str = "HS256"
    jwt_expires_seconds: int = 3600  # Máximo 1 hora
    environment: str = "development"
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]
    rate_limit_login: str = "5/minute"

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        if self.environment == "production":
            if len(self.jwt_secret) < 32 or "change-me" in self.jwt_secret.lower():
                raise ValueError("APP_JWT_SECRET no cumple los requisitos mínimos de seguridad en producción (mínimo 32 caracteres seguros)")
        return self
```

> **Nota (todos los entornos):** `APP_JWT_SECRET` es obligatorio también en desarrollo y tests; no existe ningún secreto por defecto embebido. `backend/tests/conftest.py` debe definir un `APP_JWT_SECRET` de prueba y `.env.example` debe documentar cómo generar uno seguro.

---

### 2.2. Aislamiento Multi-Tenant Estricto (Prevención de IDOR)

Refactorizar `backend/app/api/deps.py` para garantizar aislamiento por tenant y validar estados de empresa:

```python
# backend/app/api/deps.py
def get_empresa_context(
    usuario: Annotated[Usuario, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    x_empresa_id: Annotated[str | None, Header(alias="X-Empresa-Id")] = None,
) -> int:
    if x_empresa_id is None or not x_empresa_id.strip():
        raise ApiError(400, "Cabecera X-Empresa-Id requerida")
    if not x_empresa_id.isdigit():
        raise ApiError(400, "Cabecera X-Empresa-Id inválida")

    empresa_id = int(x_empresa_id)

    # 1. Validar existencia y estado de la empresa
    empresa = session.get(Empresa, empresa_id)
    if empresa is None:
        raise ApiError(404, "Empresa no encontrada")
    if not empresa.activa:
        raise ApiError(403, "La empresa seleccionada está inactiva")

    # 2. Validar pertenencia del usuario al tenant
    vinculo = session.exec(
        select(empresa_usuario).where(
            empresa_usuario.c.usuario_id == usuario.id,
            empresa_usuario.c.empresa_id == empresa_id,
        )
    ).first()
    if vinculo is None:
        raise ApiError(403, "Acceso no autorizado a la empresa")

    return empresa_id
```

---

### 2.3. Blindaje de la Lógica Contable y Prevención de Consultas N+1

Reescribir `backend/app/services/asientos.py` para asegurar las siguientes reglas de negocio:
1. **Regla de Partida Doble Obligatoria:** Un asiento solo puede asentarse si contiene $\ge 2$ líneas de apunte y $\Delta = 0$.
2. **Eliminación de N+1 SQL:** Uso de agregaciones y JOINs explícitos.
3. **Paginación en Base de Datos:** Cálculo del `total` mediante `func.count()`.

```python
# backend/app/services/asientos.py
def asentar(session: Session, asiento: Asiento, usuario_id: int) -> Asiento:
    if asiento.estado != "borrador":
        raise ApiError(409, "El asiento ya se encuentra asentado")

    _ejercicio_abierto(session, asiento.ejercicio_id)

    apuntes_db = session.exec(select(Apunte).where(Apunte.asiento_id == asiento.id)).all()

    # REGLA CONTABLE FUNDAMENTAL: Partida doble
    if len(apuntes_db) < 2:
        raise ApiError(422, "Un asiento contable requiere al menos 2 líneas de apunte")

    # Validar coherencia contable (importes positivos y una cara por apunte)
    validar_lineas([{"debe": a.debe, "haber": a.haber} for a in apuntes_db])

    delta = calcular_delta([{"debe": a.debe, "haber": a.haber} for a in apuntes_db])
    if delta != Decimal("0"):
        raise ApiError(422, f"El asiento no cuadra: descuadre Δ = {delta}")

    # Serialización y asignación del correlativo oficial
    max_num = session.exec(
        select(func.coalesce(func.max(Asiento.numero), 0)).where(
            Asiento.ejercicio_id == asiento.ejercicio_id
        )
    ).one()

    asiento.numero = max_num + 1
    asiento.estado = "asentado"
    asiento.asentado_por_usuario_id = usuario_id
    asiento.asentado_at = datetime.now(UTC)

    session.commit()
    session.refresh(asiento)
    return asiento

def obtener_apuntes(session: Session, asiento_id: int) -> list[dict]:
    # Consulta única con JOIN: cero consultas N+1
    stmt = (
        select(Apunte, Cuenta.codigo)
        .join(Cuenta, Apunte.cuenta_id == Cuenta.id)
        .where(Apunte.asiento_id == asiento_id)
    )
    filas = session.exec(stmt).all()
    return [
        {
            "cuenta_id": ap.cuenta_id,
            "cuenta_codigo": codigo,
            "debe": str(ap.debe),
            "haber": str(ap.haber),
        }
        for ap, codigo in filas
    ]
```

---

### 2.4. Protección Anti-CSRF y Mitigación de DoS en Login

1. **Defensa en Profundidad Anti-CSRF:**  
   Cuando la autenticación provenga de la cookie `access_token`, el backend exigirá la presencia de la cabecera `X-Requested-With: XMLHttpRequest`. Las peticiones mutacionales (`POST`, `PUT`, `DELETE`) que no incluyan dicha cabecera con ese valor serán denegadas con HTTP 403 y un `detail` que contenga la cadena "CSRF". No se emite ni valida ningún `X-CSRF-Token`. El frontend (`src/lib/api.ts`) envía esta cabecera en toda petición mutacional (`POST`/`PUT`/`DELETE`).
2. **Rate Limiting con SlowAPI:**  
   Integrar un limitador de tasa sobre `/api/v1/auth/login` por **IP remota**, contabilizando **todas las peticiones (aciertos y fallos)**: máximo 5 peticiones por minuto; la sexta y siguientes devuelven HTTP 429. No se usa el nombre de usuario como clave. Objetivo: proteger el coste computacional de Argon2.

---

## 3. Plan de Remediación Paso a Paso (Vertical Slices)

### Slice 1: Hardening de Configuración y Secretos
* Tarea 1.1: Modificar `Settings` en `app/config.py` eliminando el secreto por defecto.
* Tarea 1.2: Añadir comprobación de entropía y longitud mínima en modo producción.
* Tarea 1.3: Documentar la generación segura de claves en `.env.example`.

### Slice 2: Integridad Contable y Partida Doble
* Tarea 2.1: Implementar comprobación `len(apuntes_db) >= 2` en `asentar()`.
* Tarea 2.2: Añadir migración Alembic `002_trazabilidad_auditoria_asientos.py` para incorporar `creado_por_usuario_id`, `asentado_por_usuario_id`, `created_at` y `asentado_at`. La estrategia de upgrade será: añadir columnas como nullable → backfill de las filas existentes a un usuario admin/sistema (no-op si no hay asientos) → aplicar `NOT NULL` a `creado_por_usuario_id` y `created_at`.
* Tarea 2.3: Actualizar los endpoints de borrador y asentado para propagar el `usuario.id`.
* Tarea 2.4: Incrementar `Asiento.version` en el servidor en cada modificación (sin validación contra el cliente; el control de concurrencia optimista se activa en Fase 2).

### Slice 3: Blindaje de Aislamiento Multi-Tenant y RBAC
* Tarea 3.1: Incorporar validación `Empresa.activa == True` en `get_empresa_context()`.
* Tarea 3.2: Requerir rol `admin` para la creación de nuevos ejercicios en `POST /api/v1/ejercicios`.

### Slice 4: Rendimiento de Base de Datos y Prevención DoS
* Tarea 4.1: Sustituir `len(session.exec().all())` por `func.count()` en endpoints de paginación de asientos y cuentas.
* Tarea 4.2: Sustituir bucle N+1 en `obtener_apuntes()` por consulta con JOIN sobre `Cuenta`.
* Tarea 4.3: Incorporar índices compuestos en el modelo `Asiento` y `Apunte`.

### Slice 5: Protección de Autenticación, Rate Limit y CSRF
* Tarea 5.1: Configurar `slowapi` en FastAPI para restringir intentos de login a 5 req/min.
* Tarea 5.2: En `deps.py`, validar cabecera `X-Requested-With` cuando se use autenticación basada en cookie.
* Tarea 5.3: Sanitizar endpoint `/health` para devolver únicamente `{"status": "ok"}`, eliminando pragmas y cualquier detalle interno de SQLite.

### Slice 6: Precisión Aritmética y UI en Frontend
* Tarea 6.1: Refactorizar `calcularDelta()` en `FormAsiento.tsx` para operar sobre céntimos enteros (`Math.round(x * 100)`).
* Tarea 6.2: Migrar solo los controles interactivos de `FormAsiento.tsx` (`TextField`, `Select`, `Button`) a componentes Material Design 3 de MUI v6, conservando selectores `data-testid`; no se rehace el layout del componente.
* Tarea 6.3: Añadir en `src/lib/api.ts` la cabecera `X-Requested-With: XMLHttpRequest` a toda petición `POST`/`PUT`/`DELETE`, y cubrirlo con un test de vitest.

---

## 4. Casos de Prueba / Regression Security Tests (Pytest + HTTPX)

```python
# backend/tests/integration/test_security_hardening.py
from datetime import date
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlmodel import Session, select
from app.models import Asiento, Apunte, Empresa, Usuario
from app.services.seguridad import create_access_token


def test_asentar_asiento_sin_apuntes_retorna_422(contexto, client, session: Session):
    """Verifica que un asiento con 0 apuntes no pueda ser asentado."""
    ctx = contexto()
    asiento = Asiento(
        ejercicio_id=ctx["ejercicio"].id,
        fecha=date(2026, 5, 10),
        concepto="Asiento vacío fraudulento",
        estado="borrador",
        creado_por_usuario_id=ctx["usuario"].id,
    )
    session.add(asiento)
    session.commit()
    session.refresh(asiento)

    headers = {**ctx["headers"], "X-Empresa-Id": str(ctx["empresa"].id), "X-Ejercicio-Id": str(ctx["ejercicio"].id)}
    
    resp = client.post(f"/api/v1/asientos/{asiento.id}/asentar", headers=headers)
    assert resp.status_code == 422
    assert "al menos 2" in resp.json()["detail"].lower()


def test_empresa_inactiva_retorna_403(contexto, client, session: Session):
    """Un usuario vinculado no puede operar en una empresa desactivada."""
    ctx = contexto()
    empresa = session.get(Empresa, ctx["empresa"].id)
    empresa.activa = False
    session.add(empresa)
    session.commit()

    headers = {**ctx["headers"], "X-Empresa-Id": str(empresa.id)}
    
    resp = client.get("/api/v1/ejercicios", headers=headers)
    assert resp.status_code == 403
    assert "inactiva" in resp.json()["detail"].lower()


def test_usuario_contable_no_puede_crear_ejercicio(contexto, client, make_usuario):
    """Solo el administrador puede abrir nuevos ejercicios fiscales."""
    ctx = contexto()
    contable = make_usuario("contable_user", rol="contable")
    token = create_access_token(contable.username)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Empresa-Id": str(ctx["empresa"].id),
    }

    payload = {
        "anio": 2028,
        "fecha_inicio": "2028-01-01",
        "fecha_fin": "2028-12-31",
    }
    resp = client.post("/api/v1/ejercicios", headers=headers, json=payload)
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"].lower()


def test_paginacion_utiliza_count_y_limita_items(contexto, client, session: Session):
    """El total debe calcularse con count() y el resultado debe respetar el limit."""
    ctx = contexto()
    headers = {
        **ctx["headers"],
        "X-Empresa-Id": str(ctx["empresa"].id),
        "X-Ejercicio-Id": str(ctx["ejercicio"].id),
    }

    resp = client.get("/api/v1/asientos?offset=0&limit=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert len(data["items"]) <= 5


def test_mutacion_con_cookie_sin_cabecera_csrf_rechazada(contexto, client):
    """Peticiones autenticadas solo con cookie deben rechazar POST sin cabecera CSRF."""
    ctx = contexto()
    client.cookies.set("access_token", ctx["token"])

    resp = client.post(
        "/api/v1/cuentas",
        headers={"X-Ejercicio-Id": str(ctx["ejercicio"].id), "X-Empresa-Id": str(ctx["empresa"].id)},
        json={"codigo": "572001", "nombre": "Banco Prueba", "nivel": 4},
    )
    assert resp.status_code == 403
    assert "csrf" in resp.json()["detail"].lower()


def test_health_no_expone_detalles_internos(client):
    """El endpoint /health no debe exponer pragmas ni motores de base de datos."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "journal_mode" not in body
    assert "busy_timeout" not in body
    assert body.get("status") == "ok"
```

---

## 5. Criterios de Aceptación y Validación

* **Criterio 1 (Partida Doble):** Toda llamada a `/asientos/{id}/asentar` sobre un asiento con menos de 2 líneas devuelve HTTP 422.
* **Criterio 2 (Trazabilidad):** El asiento asentado persiste obligatoriamente `asentado_por_usuario_id` y `asentado_at`.
* **Criterio 3 (Multi-tenant Inactivo):** Toda petición con cabecera de empresa con `activa = False` es rechazada con HTTP 403.
* **Criterio 4 (Anti-Brute Force):** La sexta petición a `/auth/login` desde la misma IP en menos de 1 minuto devuelve HTTP 429, con independencia de si acierta o falla la credencial.
