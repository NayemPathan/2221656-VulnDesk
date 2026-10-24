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

# Load key-value pairs from the local `.env` file into `os.environ` if `.env` exists.
# On Vercel production, environment variables come from the Vercel dashboard instead.
load_dotenv()


def _normalize_database_url(raw_url: str) -> str:
    """
    Convert standard 'postgres://' or 'postgresql://' connection strings into
    'postgresql+psycopg://' so SQLAlchemy 2 uses the installed psycopg v3 driver.
    Leaves 'sqlite://...' URLs untouched for local testing.
    """
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _parse_origins(raw_origins: str) -> list[str]:
    """
    Split a comma-separated string of URLs (e.g. 'http://localhost:5173,https://vulndesk.vercel.app')
    into a clean Python list for FastAPI's CORSMiddleware.
    """
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


@dataclass
class Settings:
    """Centralized settings object imported across the backend."""

    # Metadata shown in the automatic Swagger documentation at /api/docs
    project_name: str = "VulnDesk API"
    version: str = "0.1.0"

    # Every REST endpoint in our SRS/TDD starts with /api/v1 (TDD Section 5)
    api_v1_prefix: str = "/api/v1"

    # Database connection string: reads DATABASE_URL from .env, or falls back to local SQLite
    database_url: str = field(
        default_factory=lambda: _normalize_database_url(
            os.getenv("DATABASE_URL", "sqlite:///./vulndesk_local.db")
        )
    )

    # FR-30: When DEMO_MODE is True (MVP), get_current_user reads the `X-Demo-User` HTTP header
    demo_mode: bool = field(
        default_factory=lambda: os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")
    )

    # Browser origins allowed to make cross-origin requests during local React development
    allowed_origins: list[str] = field(
        default_factory=lambda: _parse_origins(
            os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        )
    )


# Create a single shared instance of Settings to import anywhere in the app
settings = Settings()
