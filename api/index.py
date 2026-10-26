"""
Vercel Serverless Function Entrypoint (api/index.py)
=====================================================================
WHAT THIS FILE DOES:
Exposes the FastAPI `app` object from `backend/app/main.py` at `/api/index.py` so Vercel's
Python Serverless Runtime (`@vercel/python`) can serve all `/api/*` requests (`/api/v1/*`,
`/api/docs`, `/api/openapi.json`) from the same Vercel project that hosts our React SPA.

WHY WE WROTE IT THIS WAY:
Vercel's Python runtime AST scanner requires `app` to be defined or imported at the
top level of `api/index.py` (never nested inside a `try/except` block). All cold-start
and runtime error handling is therefore placed inside `create_app()` in `backend/app/main.py`.
=====================================================================
"""

import sys
from pathlib import Path

# Add `<repo_root>/backend` to Python's module search path so `from app.main import app` works on Vercel
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # ty: ignore[unresolved-import]

__all__ = ["app"]