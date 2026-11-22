"""
FastAPI Application Entry Point (backend/app/main.py)
=====================================================================
WHAT THIS FILE DOES:
Creates and configures the main FastAPI `app` object, attaches CORS middleware so the React
frontend can talk to the API, configures the interactive Swagger docs at `/api/docs` (NFR-13),
and registers all API routers (`health`, `auth`, `reports`, `triage`, `comments`) under `/api/v1`.
=====================================================================
"""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings

logger = logging.getLogger("vulndesk.http")



def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    app = FastAPI(
        title="VulnDesk",
        version="2.0.0",
        description=(
            "VulnDesk: A Vulnerability Report Intake, Triage and Access-Controlled Tracking System."
        ),
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # Configure Cross-Origin Resource Sharing (CORS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def catch_unhandled_exceptions_middleware(request: Request, call_next):
        """
        Catch any unhandled database/connection errors (including inside FastAPI dependencies
        like `get_session` and `get_current_user`) and return a readable JSON 500 response
        instead of crashing the Vercel serverless container with FUNCTION_INVOCATION_FAILED.
        """
        try:
            return await call_next(request)
        except SQLAlchemyError as exc:
            logger.exception("Database error while handling %s", request.url.path)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": (
                        f"Server error ({exc.__class__.__name__}): {exc}. "
                        "Verify DATABASE_URL in Vercel Settings -> Environment Variables."
                    )
                },
            )
    @app.middleware("http")
    async def log_requests_middleware(request: Request, call_next):
        """
        Cross-Cutting Logging & Performance Timing Aspect (AOP):
        Logs every HTTP request and attaches `X-Process-Time` without
        duplicating timing/logging code inside any router or service.
        """
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Process-Time"] = f"{elapsed_ms}ms"
        logger.info(
            "%s %s -> %s (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


    try:
        from app.database import ensure_sqlite_initialized
        from app.routers import (
            admin,
            auth,
            comments,
            dashboard,
            health,
            groups,
            reports,
            triage,
        )

        ensure_sqlite_initialized()

        # Mount all routers under /api/v1
        app.include_router(health.router, prefix=settings.api_v1_prefix)
        app.include_router(auth.router, prefix=settings.api_v1_prefix)
        app.include_router(admin.router, prefix=settings.api_v1_prefix)
        app.include_router(reports.router, prefix=settings.api_v1_prefix)
        app.include_router(triage.router, prefix=settings.api_v1_prefix)
        app.include_router(comments.router, prefix=settings.api_v1_prefix)
        app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
        app.include_router(groups.router, prefix=settings.api_v1_prefix)

        # Also mount under /v1 (hidden from OpenAPI docs) in case a serverless proxy strips /api
        app.include_router(health.router, prefix="/v1", include_in_schema=False)
        app.include_router(auth.router, prefix="/v1", include_in_schema=False)
        app.include_router(admin.router, prefix="/v1", include_in_schema=False)
        app.include_router(reports.router, prefix="/v1", include_in_schema=False)
        app.include_router(triage.router, prefix="/v1", include_in_schema=False)
        app.include_router(comments.router, prefix="/v1", include_in_schema=False)
        app.include_router(dashboard.router, prefix="/v1", include_in_schema=False)
        app.include_router(groups.router, prefix="/v1", include_in_schema=False)

    except (ImportError, SQLAlchemyError) as startup_exc:
        logger.exception("Backend startup failed")
        error_summary = f"{startup_exc.__class__.__name__}: {startup_exc}"

        @app.api_route(
            "/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
        )
        async def startup_error_handler(_request: Request, path: str) -> JSONResponse:
            return JSONResponse(
                status_code=500,
                content={
                    "detail": (
                        f"Backend startup error on /{path} ({error_summary}). "
                        "Check DATABASE_URL in Vercel Settings -> Environment Variables."
                    )
                },
            )

    return app


# Expose `app` at module level for `uvicorn app.main:app --reload` and Vercel's `api/index.py`
app = create_app()