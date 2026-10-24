"""
FastAPI Application Entry Point (backend/app/main.py)
=====================================================================
WHAT THIS FILE DOES:
Creates and configures the main FastAPI `app` object, attaches CORS middleware so the React
frontend can talk to the API, configures the interactive Swagger docs at `/api/docs` (NFR-13),
and registers all API routers (`health`, `reports`) under `/api/v1`.
=====================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, reports


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        description=(
            "VulnDesk: A Vulnerability Report Intake, Triage and Access-Controlled Tracking System."
        ),
        # SRS NFR-13 & TDD Section 5 require interactive Swagger UI at /api/docs
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # Configure Cross-Origin Resource Sharing (CORS) so our Vite React frontend
    # (http://localhost:5173) can send requests (including the X-Demo-User header) to FastAPI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers under /api/v1
    app.include_router(health.router, prefix=settings.api_v1_prefix)
    app.include_router(reports.router, prefix=settings.api_v1_prefix)

    return app


# Expose `app` at module level for `uvicorn app.main:app --reload` and Vercel's `api/index.py`
app = create_app()