"""
FastAPI Application Entry Point (backend/app/main.py)
=====================================================================
WHAT THIS FILE DOES:
Creates and configures the main FastAPI `app` object, attaches CORS middleware so the React
frontend can talk to the API, configures the interactive Swagger docs at `/api/docs` (NFR-13),
and registers all API routers (`health`, `reports`, `triage`, `comments`) under `/api/v1`.
=====================================================================
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import ensure_sqlite_initialized
from app.routers import comments, health, reports, triage


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    ensure_sqlite_initialized()

    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        description=(
            "VulnDesk: A Vulnerability Report Intake, Triage and Access-Controlled Tracking System."
        ),
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def catch_unhandled_exceptions_middleware(request: Request, call_next):
        """Return a readable JSON 500 error instead of FUNCTION_INVOCATION_FAILED."""
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001 - this middleware intentionally converts uncaught request errors to JSON 500s.
            return JSONResponse(
                status_code=500,
                content={
                    "detail": (
                        f"Server error ({exc.__class__.__name__}): {exc}. "
                        "Verify DATABASE_URL in Vercel Settings -> Environment Variables."
                    )
                },
            )

    app.include_router(health.router, prefix=settings.api_v1_prefix)
    app.include_router(reports.router, prefix=settings.api_v1_prefix)
    app.include_router(triage.router, prefix=settings.api_v1_prefix)
    app.include_router(comments.router, prefix=settings.api_v1_prefix)

    return app


app = create_app()