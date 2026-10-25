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
from pathlib import Path

# Add `<repo_root>/backend` to Python's module search path so `from app.main import app` works on Vercel
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # ty: ignore[unresolved-import]

__all__ = ["app"]