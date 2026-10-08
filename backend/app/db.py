from collections.abc import Generator

from sqlalchemy import Engine, event
from sqlmodel import Session, create_engine

from app.config import get_settings

_settings = get_settings()

_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}


def _apply_sqlite_pragmas(dbapi_conn, _connection_record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


engine: Engine = create_engine(_settings.database_url, connect_args=_connect_args)

if _settings.database_url.startswith("sqlite"):
    event.listens_for(engine, "connect")(_apply_sqlite_pragmas)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def sqlite_pragmas_state() -> dict[str, str]:
    from sqlalchemy import text

    with engine.connect() as conn:
        journal = conn.execute(text("PRAGMA journal_mode;")).scalar()
        busy = conn.execute(text("PRAGMA busy_timeout;")).scalar()
        fk = conn.execute(text("PRAGMA foreign_keys;")).scalar()
    return {"journal_mode": journal, "busy_timeout": str(busy), "foreign_keys": str(fk)}
