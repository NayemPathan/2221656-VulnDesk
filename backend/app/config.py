"""
Application Configuration (backend/app/config.py)
=====================================================================
WHAT THIS FILE DOES:
Reads configuration settings (like the database URL, demo mode flag, and CORS origins)
from environment variables or the local `.env` file.

WHY WE WROTE IT THIS WAY:
1. Security (TDD Section 8): Secrets like database passwords must never be hardcoded in Python files.
2. Driver Compatibility: Supabase gives URLs starting with `postgres://` or `postgresql://`,
   but SQLAlchemy 2.0 + psycopg v3 requires `postgresql+psycopg://`. The helper function
   `_normalize_database_url` automatically fixes the prefix so your app never crashes on Vercel.
3. Local Testing Fallback: If no `DATABASE_URL` is set, it defaults to a local SQLite file
   (`sqlite:///./vulndesk_local.db`) so you or your tutor can run the project in 1 minute even offline.
=====================================================================
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _default_sqlite_url() -> str:
    """Use writable /tmp directory if running on Vercel without DATABASE_URL set."""
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/vulndesk_local.db"
    return "sqlite:///./vulndesk_local.db"


def _normalize_database_url(raw_url: str | None) -> str:
    """
    Convert 'postgres://' or 'postgresql://' into 'postgresql+psycopg://' and strip
    any accidental quotes or 'DATABASE_URL=' prefixes pasted into Vercel.
    """
    if not raw_url or not raw_url.strip():
        return _default_sqlite_url()

    url = raw_url.strip().strip('"').strip("'")
    if url.startswith("DATABASE_URL="):
        url = url.split("DATABASE_URL=", 1)[1].strip().strip('"').strip("'")

    if not url:
        return _default_sqlite_url()

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _parse_origins(raw_origins: str) -> list[str]:
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


@dataclass
class Settings:
    project_name: str = "VulnDesk API"
    version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    database_url: str = field(
        default_factory=lambda: _normalize_database_url(os.getenv("DATABASE_URL"))
    )

    demo_mode: bool = field(
        default_factory=lambda: os.getenv("DEMO_MODE", "true").strip().lower()
        in ("true", "1", "yes")
    )

    allowed_origins: list[str] = field(
        default_factory=lambda: _parse_origins(
            os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,*")
        )
    )


settings = Settings()