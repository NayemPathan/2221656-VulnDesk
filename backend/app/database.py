"""
Database Engine & Session Management (backend/app/database.py)
=====================================================================
WHAT THIS FILE DOES:
1. Creates the SQLAlchemy/SQLModel `engine` (the connection bridge to Supabase PostgreSQL or SQLite).
2. Defines `get_session()`, a FastAPI Dependency Injection generator that opens a database session
   at the start of an HTTP request and automatically closes it when the request finishes.

WHY WE WROTE IT THIS WAY:
- Why differentiate SQLite vs PostgreSQL?
  SQLite is used for fast unit tests (`pytest`) and offline runs, but SQLite disables Foreign Key
  checks by default! We attach a `PRAGMA foreign_keys=ON` listener so SQLite enforces foreign keys
  just like PostgreSQL does.
- Why `pool_size=5, max_overflow=0, pool_pre_ping=True` for PostgreSQL?
  In TDD Section 12 & 14, our backend runs as a serverless function on Vercel connected to
  Supabase's connection pooler. Serverless functions spin up many short-lived instances; using a
  small pool + `pool_pre_ping=True` prevents exhausting Supabase's connection limit and automatically
  reconnects if an idle connection was dropped.
=====================================================================
"""

import logging
from collections.abc import Generator

from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

logger = logging.getLogger(__name__)


def _build_engine():
    """Build and return the appropriate database engine based on settings.database_url."""
    if settings.database_url.startswith("sqlite"):
        eng = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

        @event.listens_for(eng, "connect")
        def _enable_sqlite_fk(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return eng

    # Supabase PostgreSQL (:6543 pooler): disable psycopg v3 prepared statements
    return create_engine(
        settings.database_url,
        connect_args={"prepare_threshold": None},
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
        echo=False,
    )


engine = _build_engine()


def create_db_and_tables() -> None:
    """Create all SQLModel tables directly if they don't exist yet."""
    SQLModel.metadata.create_all(engine)


def ensure_sqlite_initialized() -> None:
    """Auto-initialize and seed /tmp SQLite fallback if DATABASE_URL was not set on Vercel."""
    if not settings.database_url.startswith("sqlite"):
        return
    try:
        import app.models  # noqa: F401
        from app.seed import seed_database

        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            seed_database(session)
    except (ImportError, SQLAlchemyError):
        logger.exception("Failed to initialize or seed the SQLite database")


def get_session() -> Generator[Session, None, None]:
    """FastAPI Dependency that opens and closes a database session per request."""
    with Session(engine) as session:
        yield session