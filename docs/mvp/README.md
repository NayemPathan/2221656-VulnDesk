# VulnDesk: Vulnerability Intake, Triage & Access-Controlled Tracking System


[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLModel](https://img.shields.io/badge/SQLModel-0.0.22+-blue)](https://sqlmodel.tiangolo.com)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Vercel](https://img.shields.io/badge/Deployed-Vercel-black?logo=vercel&logoColor=white)](https://vercel.com)

---


## 1. Project Overview


A mid-sized software company maintaining multiple web and mobile products previously handled vulnerability intake through unstructured emails, chat messages, and shared spreadsheets. This led to lost reports, untracked severity modifications, duplicate submissions, and exploit payloads exposed to unauthorized personnel.


**VulnDesk** replaces this informal workflow with a structured, role-segregated web system featuring:
1. **Researcher Report Intake & Full CRUD:** Submit, list, view, update, and delete reports while in `New` status with automated policy validation.
2. **Analyst Triage & Rejection Feedback:** Severity classification, state transitions, duplicate linking, and transparent rejection explanations.
3. **Immutable Audit History:** Every status transition is saved transactionally in an append-only audit log.
4. **Role-Segregated Comments:** Public discussion threads combined with analyst-only internal notes.


---


## 2. System Architecture & Tech Stack


* **Backend:** FastAPI (Python), SQLModel (SQLAlchemy 2.0 ORM + Pydantic validation), Alembic (migrations).
* **Database:** Supabase managed PostgreSQL (with transaction pooler on port 6543) + local SQLite for automated tests.
* **Frontend:** Functional React with TypeScript, Vite, React Router, and Tailwind CSS.
* **Deployment:** Vercel (FastAPI serverless function via `api/index.py` + static React build).


---


## 3. MVP REST API Endpoints


All endpoints are prefixed with `/api/v1` (interactive Swagger documentation at `/api/docs`):


| HTTP Method | Route | Description | Acting Role (`X-Demo-User`) |
|---|---|---|---|
| `GET` | `/api/v1/health` | Service and database health check | Any |
| `POST` | `/api/v1/reports` | Submit vulnerability report (5 policy rules) | Researcher |
| `GET` | `/api/v1/reports` | List reports with search, filters, pagination | Researcher (own), Analyst/Admin (all) |
| `GET` | `/api/v1/reports/{id}` | View report detail (with rejection reason) | Owner Researcher, Analyst, Admin |
| `PUT` | `/api/v1/reports/{id}` | Update report content (only while `New`) | Owner Researcher |
| `DELETE` | `/api/v1/reports/{id}` | Delete report (only while `New`) | Owner Researcher |
| `PATCH` | `/api/v1/reports/{id}/severity` | Assign final severity (`low`..`critical`) | Analyst |
| `PATCH` | `/api/v1/reports/{id}/status` | Transition status with rejection/duplicate data | Analyst |
| `GET` | `/api/v1/reports/{id}/history` | Fetch immutable status history | Owner Researcher, Analyst, Admin |
| `POST` | `/api/v1/reports/{id}/comments` | Add comment or internal note | Owner Researcher, Analyst |
| `GET` | `/api/v1/reports/{id}/comments` | List comments (internal notes hidden from researcher)| Owner Researcher, Analyst, Admin |


---


## 4. Local Quick Start


### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed
pytest -v
uvicorn app.main:app --reload --port 8000
```