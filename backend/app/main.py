from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.asientos import router as asientos_router
from app.api.auth import router as auth_router
from app.api.cuentas import router as cuentas_router
from app.api.empresas import router as empresas_router
from app.api.errors import register_error_handlers
from app.config import get_settings
from app.db import sqlite_pragmas_state

logger = getLogger("contabilidadv2")

_settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("ContabilidadV2 backend arrancando (pragmas: %s)", sqlite_pragmas_state())
    yield
    logger.info("ContabilidadV2 backend detenido")


app = FastAPI(title="ContabilidadV2 API", version="0.1.0", lifespan=lifespan)

register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(asientos_router, prefix="/api/v1")
app.include_router(cuentas_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(empresas_router)


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    """Estado del servicio: base de datos en modo WAL y migraciones disponibles."""
    pragmas = sqlite_pragmas_state()
    return {
        "status": "ok",
        "db": pragmas["journal_mode"].lower(),
        "busy_timeout": pragmas["busy_timeout"],
        "foreign_keys": pragmas["foreign_keys"],
        "migrations": "current",
    }
