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

from collections.abc import Generator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings


def _build_engine():
    """Build and return the appropriate database engine based on settings.database_url."""

    # Case 1: Local SQLite database (used in pytest or quick local offline runs)
    if settings.database_url.startswith("sqlite"):
        # `check_same_thread=False` is required by FastAPI because FastAPI can handle
        # a single request across multiple worker threads.
        eng = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

        # SQLite ignores Foreign Key constraints unless we explicitly run `PRAGMA foreign_keys=ON`
        # on every new connection. This ensures invalid user_id or report_id values are rejected.
        @event.listens_for(eng, "connect")
        def _enable_sqlite_fk(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return eng

    # Case 2: Supabase PostgreSQL connection (MVP & Beta cloud database)
    # - pool_pre_ping=True: checks if the DB connection is still alive before running a query
    # - pool_size=5, max_overflow=0: keeps connection usage small for Vercel serverless functions
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
        echo=False,
    )


# Instantiate the global engine once when the module loads
engine = _build_engine()


def create_db_and_tables() -> None:
    """
    Create all SQLModel tables directly if they don't exist yet.
    Note: In production we use `alembic upgrade head`, but this helper is handy
    when running `python -m app.seed` against a fresh local SQLite database.
    """
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """
    FastAPI Dependency (`Depends(get_session)`).
    Opens a new database `Session` for the incoming HTTP request, yields it to the router/service,
    and guarantees the session is closed cleanly in the `with` block even if an exception occurs.
    """
    with Session(engine) as session:
        yield session
