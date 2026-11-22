"""
Application Configuration (backend/app/config.py)
=====================================================================
Reads database, demo-mode, CORS, and Beta JWT/cookie configuration from
environment variables or `.env`.
=====================================================================
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _default_sqlite_url() -> str:
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/vulndesk_local.db"
    return "sqlite:///./vulndesk_local.db"


def _normalize_database_url(raw_url: str | None) -> str:
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
    """Centralized settings object imported across the backend."""

    project_name: str = "VulnDesk API"
    version: str = "0.2.0"
    api_v1_prefix: str = "/api/v1"
    PASSWORD_PEPPER: str = "dev-pepper-change-in-production"

    database_url: str = field(
        default_factory=lambda: _normalize_database_url(os.getenv("DATABASE_URL"))
    )

    demo_mode: bool = field(
        default_factory=lambda: os.getenv("DEMO_MODE", "true").strip().lower()
        in ("true", "1", "yes")
    )

    allowed_origins: list[str] = field(
        default_factory=lambda: _parse_origins(
            os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        )
    )

    # Beta JWT & Lockout Settings (Phases 7-10)
    jwt_secret_key: str = field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET_KEY", "dev-insecure-vulndesk-jwt-secret-change-in-prod"
        )
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    max_failed_login_attempts: int = 5
    lockout_minutes: int = 15
    cookie_secure: bool = field(
        default_factory=lambda: bool(os.getenv("VERCEL"))
        or os.getenv("COOKIE_SECURE", "false").strip().lower() in ("true", "1", "yes")
    )


settings = Settings()
