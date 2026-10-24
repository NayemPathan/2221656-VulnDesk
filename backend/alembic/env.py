"""
Alembic Migration Environment (backend/alembic/env.py)
=====================================================================
WHAT THIS FILE DOES:
Runs whenever executed an `alembic` command (such as `alembic upgrade head`).
It connects Alembic to our `settings.database_url` (from `.env`) and tells Alembic to compare
the database against `SQLModel.metadata` (our SQLModel table definitions).

WHY WE WROTE IT THIS WAY:
1. Dynamic Database URL: We never hardcode the Supabase password inside `alembic.ini`.
   Instead, `config.set_main_option("sqlalchemy.url", settings.database_url)` injects the URL
   from `app/config.py` at runtime.
2. `poolclass=pool.NullPool`: Migrations run once and exit, so we use `NullPool` to close the
   connection immediately after the migration finishes.
=====================================================================
"""

from logging.config import fileConfig

import app.models  # noqa: F401 - importing registers User, Report, Comment, StatusHistory
from alembic import context

# Import our project settings and all SQLModel models so SQLModel.metadata knows every table
from app.config import settings
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Alembic Config object, which provides access to values within `alembic.ini`
config = context.config

# Override sqlalchemy.url dynamically with the DATABASE_URL from our environment / .env file
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up standard Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic to use SQLModel's metadata for `--autogenerate` schema diffs
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL script without connecting to a live DB)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to Supabase/SQLite and applies DDL changes)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
