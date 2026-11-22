# FastAPI + React Template

FastAPI backend + Vite/React/TypeScript frontend, deployed to Vercel as one project.

```
backend/    FastAPI app (routes under /api)
frontend/   Vite + React + TypeScript
vercel.json Vercel setup: /api/* goes to backend, everything else to frontend
```

## Requirements

- [Python](https://www.python.org/downloads/) 3.10+
- [Node.js](https://nodejs.org/) 22+

> On macOS/Linux, use `python3` instead of `python`.

## Run locally

**Backend** (terminal 1):

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
fastapi dev main.py
```

**Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and click **Say hello**. Vite forwards `/api` requests to the backend on port 8000.

To run it the way Vercel does instead, from the project root:

```bash
npm install -g vercel
vercel dev -L
```

> Add new Python packages to `backend/requirements.txt`.

## Class exercise

Send an ID, name and email from React to FastAPI and show the reply.

1. In `backend/main.py`, uncomment the `EXERCISE (part 1)` block. Try `POST /api/user` at http://localhost:8000/docs.
2. In `frontend/src/App.tsx`, uncomment `<UserForm />` and the `UserForm` function (`EXERCISE (part 2)`).
3. Fill in the form at http://localhost:5173 and click **Send**.

Try an invalid email (send it from `/docs`, since the browser blocks it in the form): FastAPI returns `422` without any extra code.

## Deploy to Vercel

1. Push the repo to GitHub.
2. Go to https://vercel.com/new, import the repo and click **Deploy**. Keep **Root Directory** as `./`.

Every push to `main` redeploys automatically. Or deploy from your machine with `vercel --prod`.

## Troubleshooting

- **"Running scripts is disabled" in PowerShell:** run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **`fastapi` not found:** activate the virtual environment first.
- **`Request failed: 500` in the app:** the backend isn't running.
- **App at localhost:8000 shows an old version:** delete `frontend/dist`.
- **Vercel build fails:** check **Build Logs** in the Vercel dashboard, and make sure `npm run build` works in `frontend/`.

## Live Deployment & Demo Accounts (CSE 309 Final)

- **Frontend (Vercel):** https://2221656-vulndesk.vercel.app
- **Backend API Base:** https://2221656-vulndesk.vercel.app/api/v1
- **Swagger / OpenAPI Docs:** https://2221656-vulndesk.vercel.app/api/v1/docs

### Seeded Test Accounts (Passwords in PDF Appendix & Submission Form)
| Account Email | Role | Status / Purpose |
| :--- | :--- | :--- |
| `admin@vulndesk.local` | `admin` | Primary Administrator (full governance, audit log, security view) |
| `tutor@vulndesk.local` | `admin` | Secondary Admin / Instructor Evaluator account |
| `alice@vulndesk.local` | `researcher` | Standard User — Owner of shared group *Web Security Triage Team* |
| `bob@vulndesk.local` | `researcher` | Standard User — Group member (`can_create=true` only) |
| `charlie@vulndesk.local` | `analyst` | Triage Analyst — Group member (`can_edit=true`, `can_assign=true`) |
| `mallory@vulndesk.local` | `researcher` | Banned User (for testing immediate `403` rejection) |

### Seeded Shared Group (Mixed Permissions)
- **Group Name:** `Web Security Triage Team`
- **Owner:** `alice@vulndesk.local` (can rename, delete, and manage members)
- **Members:**
  - `bob@vulndesk.local` → `Create: Yes`, `Edit: No`, `Assign: No`
  - `charlie@vulndesk.local` → `Create: No`, `Edit: Yes`, `Assign: Yes`