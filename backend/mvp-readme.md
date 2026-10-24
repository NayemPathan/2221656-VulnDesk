# VulnDesk: Vulnerability Intake, Triage & Access-Controlled Tracking System

[](https://fastapi.tiangolo.com)
[](https://sqlmodel.tiangolo.com)
[](https://supabase.com)
[](https://react.dev)
[](https://www.typescriptlang.org)
[](https://vercel.com)

## 1. Project Overview

A mid-sized software company maintaining multiple web and mobile products previously handled vulnerability intake through unstructured emails, chat messages, and shared spreadsheets. This led to lost reports, untracked severity modifications, duplicate submissions, and exploit payloads exposed to unauthorized personnel.

**VulnDesk** replaces this informal workflow with a structured, role-segregated web system featuring:
1. **Researcher Report Intake & Full CRUD:** Submit, list, view, update, and delete reports while in `New` status with automated 5-rule policy validation.
2. **Analyst Triage & Transparent Feedback:** Severity classification, state transitions, duplicate linking, and visible rejection reasons for researchers.
3. **Immutable Audit History:** Every status transition is saved transactionally in an append-only audit log.
4. **Role-Segregated Comments:** Public discussion threads combined with analyst-only internal notes.

---

## 2. System Architecture & Tech Stack

* **Backend:** FastAPI (Python), SQLModel (SQLAlchemy 2.0 ORM + Pydantic validation), Alembic (schema migrations).
* **Database:** Supabase managed PostgreSQL (AWS Connection Pooler on port 6543) + local SQLite fallback for automated tests.
* **Frontend:** Functional React with TypeScript, Vite, React Router, and Tailwind CSS.
* **Hosting & Deployment:** Vercel (FastAPI serverless function via `api/index.py` + static React build).

---

## 3. Local Setup & Verification Guide (Step-by-Step)

Follow these exact steps to set up, configure, migrate, seed, test, and run the backend locally.

### Step 1: Open Terminal in the `backend/` Directory

```bash
cd backend
```

---

### Step 2: Create & Activate the Virtual Environment

#### On Windows (PowerShell):
If PowerShell blocks script execution with `running scripts is disabled on this system`, enable script execution for your user first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then create and activate the virtual environment:
```powershell
python -m venv .venv
.venv\Scripts\activate
```

#### On Windows (Command Prompt `cmd.exe`):
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

#### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

*(When active, `(.venv)` will appear at the beginning of your terminal prompt).*

---

### Step 3: Configure Editor Interpreter (VS Code / Cursor)

To ensure your editor recognizes all third-party libraries (and eliminates warnings like `Cannot resolve imported module 'dotenv'`):
1. Press `Ctrl + Shift + P` (or `F1`).
2. Type **`Python: Select Interpreter`** and press Enter.
3. Choose the virtual environment: `Python 3.x.x ('.venv': venv) .\backend\.venv\Scripts\python.exe`.

---

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 5: Configure Environment Variables (`.env`)

Copy the template file:
```bash
cp .env.example .env
```

Open `backend/.env` and configure your settings:
* **Option A: Connect to your live Supabase database:**
  ```ini
  DATABASE_URL=postgresql+psycopg://postgres.jsshnmcwnahworbiaqlp:YourActualPassword@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
  DEMO_MODE=true
  ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
  ```
* **Option B: Quick offline local SQLite fallback:**
  ```ini
  DATABASE_URL=sqlite:///./vulndesk_local.db
  DEMO_MODE=true
  ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
  ```

---

### Step 6: Run Automated Tests (`pytest`)

Run the automated test suite:
```bash
pytest -v
```

**Expected Result (100% Passed):**
```text
tests\test_phase1_db.py::test_seed_database_is_idempotent PASSED        [ 50%]
tests\test_phase1_db.py::test_health_endpoint_and_openapi_docs PASSED   [100%]
```
* `test_seed_database_is_idempotent`: Validates all 4 tables (`user`, `report`, `comment`, `status_history`), foreign keys, seed relationships, and ensures running the seed script multiple times never duplicates rows.
* `test_health_endpoint_and_openapi_docs`: Validates `GET /api/v1/health` and Swagger UI `/api/docs`.

---

### Step 7: Apply Database Migrations (`Alembic`)

Apply the initial schema migration (`0001_initial_mvp_schema.py`) to create all tables and indexes:
```bash
alembic upgrade head
```

---

### Step 8: Seed Initial Demo Data

Populate the database with the 5 demo users, sample vulnerability reports across workflow states, status history, and comments:
```bash
python -m app.seed
```

**Seeded Demo Accounts for Assessment Demo:**
* `alice@vulndesk.local` — **Researcher** (owns Reports #1, #2, #3; can edit/delete Report #1 while `New`)
* `bob@vulndesk.local` — **Researcher** (owns Report #4; used to demonstrate cross-user 404 isolation)
* `mallory@vulndesk.local` — **Banned Researcher** (used to test Submission Policy Rule iv)
* `charlie@vulndesk.local` — **Security Analyst** (triages reports, sets severity, writes internal notes)
* `admin@vulndesk.local` — **Administrator** (reopens end-state reports, views all data)

---

### Step 9: Start Local Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

---

### Step 10: Verify in Browser & DevTools

1. **Service Health Check:**
   Open: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)  
   **Response:**
   ```json
   {
     "status": "ok",
     "service": "VulnDesk API",
     "version": "0.1.0",
     "database": "connected",
     "demo_mode": true
   }
   ```
2. **Interactive Swagger Documentation:**
   Open: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)  
   * Displays all active endpoints, request/response schemas, and allows interactive execution.
3. **OpenAPI JSON Schema:**
   Open: [http://localhost:8000/api/openapi.json](http://localhost:8000/api/openapi.json)

---

## 4. MVP REST API Endpoint Reference

All routes are prefixed with `/api/v1`:

| Method | Path | Acting Role (`X-Demo-User`) | Description | Status Codes |
|---|---|---|---|---|
| `GET` | `/health` | Any | Checks database connection and server status | `200` |
| `POST` | `/reports` | Researcher | Submits a report (validates 5 policy rules) | `201`, `409`, `422` |
| `GET` | `/reports` | Researcher (own), Analyst/Admin (all) | Lists reports with filters and pagination | `200` |
| `GET` | `/reports/{id}` | Owner Researcher, Analyst, Admin | Fetches single report detail (includes rejection reason) | `200`, `404` |
| `PUT` | `/reports/{id}` | Owner Researcher | Edits report content **only while status is `New`** | `200`, `404`, `409`, `422` |
| `DELETE` | `/reports/{id}` | Owner Researcher | Deletes report **only while status is `New`** (CRUD) | `204`, `404`, `409` |
| `PATCH` | `/reports/{id}/severity` | Analyst | Assigns `final_severity` (`low`, `medium`, `high`, `critical`) | `200`, `404`, `422` |
| `PATCH` | `/reports/{id}/status` | Analyst | Transitions status (requires rejection reason or duplicate ID) | `200`, `404`, `409`, `422` |
| `GET` | `/reports/{id}/history` | Owner Researcher, Analyst, Admin | Lists immutable status audit trail | `200`, `404` |
| `POST` | `/reports/{id}/comments` | Owner Researcher, Analyst | Adds comment or internal note (`is_internal=true`) | `201`, `404`, `422` |
| `GET` | `/reports/{id}/comments` | Owner Researcher, Analyst, Admin | Lists comments oldest-first (hides internal notes from researcher) | `200`, `404` |

---
