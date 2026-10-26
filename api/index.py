"""
Vercel Serverless Function Entrypoint (api/index.py)
=====================================================================
WHAT THIS FILE DOES:
Exposes the FastAPI `app` object from `backend/app/main.py` at `/api/index.py` so Vercel's
Python Serverless Runtime (`@vercel/python`) can serve all `/api/*` requests (`/api/v1/*`,
`/api/docs`, `/api/openapi.json`) from the same Vercel project that hosts our React SPA!

WHY WE WROTE IT THIS WAY (TDD Section 1 & 12):
- Vercel looks for Python serverless functions inside the root `api/` folder.
- Since our backend package lives inside `backend/app/`, we insert `backend/` at the front
  of `sys.path` at runtime before importing `from app.main import app`.
- `__all__ = ["app"]` tells linters (like Ruff) that `app` is intentionally re-exported.
=====================================================================
"""

import sys
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.main import app as backend_app  # ty: ignore[unresolved-import]

    app: FastAPI = backend_app
except Exception as startup_exc:  # noqa: BLE001 - report any backend startup failure
    error_trace = traceback.format_exc()
    startup_error_detail = (
        f"Backend startup error ({startup_exc.__class__.__name__}: {startup_exc}). "
    )
    app = FastAPI(title="VulnDesk Startup Diagnostic")

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def startup_error_handler(_request: Request, path: str) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "detail": (
                    f"{startup_error_detail}on /api/{path} "
                    "Check DATABASE_URL in Vercel Settings -> Environment Variables."
                ),
                "traceback": error_trace,
            },
        )


__all__ = ["app"]