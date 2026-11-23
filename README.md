# VulnDesk

**Vulnerability Report Intake, Triage & Access-Controlled Tracking System**

VulnDesk is a full-stack security operations and vulnerability tracking platform built with React, TypeScript, FastAPI, SQLModel, and PostgreSQL. It supports structured vulnerability submission, severity-based SLA tracking, fine-grained role-based access control (RBAC), collaborative team groups, and an administrative governance and audit console.

## Live Deployment

- **Web Application:** [https\://2221656-vulndesk.vercel.app](https://2221656-vulndesk.vercel.app)  
- **API Base URL:** `https://2221656-vulndesk.vercel.app/api/v1`  
- **Interactive API Docs (Swagger):** [https\://2221656-vulndesk.vercel.app/api/v1/docs](https://2221656-vulndesk.vercel.app/api/v1/docs)  
- **Repository:** [https\://github.com/NayemPathan/2221656-VulnDesk](https://github.com/NayemPathan/2221656-VulnDesk)

---

## Key Features

### Authentication & Session Security

- **Argon2id \+ Pepper Hashing:** Passwords are hashed using `pwdlib[argon2]` combined with an HMAC-SHA256 `PASSWORD_PEPPER`.  
- **In-Memory JWT Access Tokens:** 15-minute HS256-signed JWT access tokens (`sub`, `role`, `iat`, `exp`) are kept strictly in JavaScript memory (never `localStorage`).  
- **HttpOnly Refresh Cookies:** 7-day opaque refresh tokens (`vulndesk_refresh_token`, `SameSite=Lax`, `Path=/api/v1/auth`) are SHA-256 hashed in PostgreSQL with token rotation, revocation, and silent `401` refresh retry in `client.ts`.  
- **Brute-Force Lockout & Session Management:** Accounts lock for 15 minutes after 5 consecutive failed logins. Users can view active sessions, revoke individual sessions, update profiles, and change passwords.

### Role-Based Access Control (RBAC) & Collaborative Groups

- **Centralized Server-Side Guards:** Every protected route passes through `get_current_user`, active/not-banned verification, `require_scopes`, and `check_group_permission` in `backend/app/deps.py`.  
- **Role Hierarchy:** Supports `researcher`, `analyst`, and `admin` roles (plus unauthenticated `Visitor` access where applicable). Researchers have strict query-level isolation over their own `New` reports.  
- **Shared Groups:** Teams can collaborate through groups with per-member `can_create`, `can_edit`, and `can_assign` permissions. Group renaming, deletion, and membership management are restricted to group owners.

### Vulnerability Intake & SLA Tracking

- **5-Rule Intake Validation:** Enforces submission policy checks (returning `409 Conflict` on violations).  
- **Severity-Based SLAs:** Automatically calculates `sla_due_at` deadlines and `is_overdue` flags based on severity:  
  - **Critical:** 1 day  
  - **High:** 2 days  
  - **Medium:** 5 days  
  - **Low:** 10 days

### Admin Console & Security Auditing

- **Overview KPIs:** Tracks `total_users`, `banned_users`, `total_reports`, `total_groups`, `new_users_7d`, and `new_reports_7d`.  
- **User Governance:** Search, role/status filtering, pagination, role updates, single and bulk ban/unban (with reason and automatic skip for self/other admins), soft-delete, user detail modal, session revocation, and CSV export.  
- **Safety Guardrails:** Admins cannot change their own role (`409`), ban or delete themselves (`400`/`409`), or ban another admin (`403`). Banned users are rejected on their very next API request (`403`).  
- **Content Moderation & Audit Logs:** Filter and bulk-delete reports, delete groups, inspect chronological `AuditLog` entries (with `target_label`, `ip_address`, `user_agent`, and action filters), monitor top `failed_login` attempts by IP and email, and export CSVs.

### Frontend Experience

- Built with React 18, TypeScript 5, and Vite 5 (`v2.0.0`) with Inter and JetBrains Mono typography.  
- Supports light/dark themes and keyboard shortcuts (`/`, `Alt+D`, `Alt+R`, `Alt+N`, `Alt+T`, `?`).

---

## Tech Stack

| Layer | Technologies |
| :---- | :---- |
| **Frontend** | React 18, TypeScript 5, Vite 5, `react-router-dom` v6 |
| **Backend** | FastAPI 0.115+, Pydantic, SQLModel 0.0.22+, Alembic (`0001_init`, `0002_beta_auth`) |
| **Security** | `pwdlib[argon2]`, HMAC-SHA256 Pepper, PyJWT 2.9+ (HS256), HttpOnly Refresh Cookies |
| **Database** | Supabase PostgreSQL 15+ (pooler port `:6543`) |
| **Middleware & API** | `X-Process-Time` AOP latency middleware, paginated responses (`page_size <= 100`) |
| **Testing** | `pytest` 8+, FastAPI `TestClient` |
| **Deployment** | Vercel (static React SPA `dist/` \+ serverless FastAPI ASGI `backend/api/index.py`) |

---

## Project Structure

```
2221656-VulnDesk/
├── backend/
│   ├── alembic/
│   │   └── versions/          # Database migrations (0001_init, 0002_beta_auth)
│   ├── api/
│   │   └── index.py           # Vercel serverless ASGI entry point
│   ├── app/
│   │   ├── main.py            # FastAPI app & middleware setup
│   │   ├── config.py          # Environment & settings configuration
│   │   ├── database.py        # SQLModel engine & session management
│   │   ├── security.py        # Argon2id + pepper, JWT & refresh token helpers
│   │   ├── deps.py            # RBAC & group permission dependencies
│   │   ├── seed.py            # Demo database seeder (6 accounts, sample data)
│   │   ├── models/            # SQLModel entities (user, refresh_token, group, group_member, report, comment, status_history, audit_log)
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/          # Business logic & SLA/audit services
│   │   └── routers/           # API v1 route handlers
│   ├── tests/                 # Pytest test suites (Phases 1, 6, 7, 8, 9, 11)
│   ├── .env.example
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── package.json           # v2.0.0
    ├── vite.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css
        ├── types.ts
        ├── api/
        │   └── client.ts      # Fetch wrapper with silent 401 refresh retry
        ├── context/           # Auth & theme providers
        ├── components/        # Reusable UI components & modals
        └── pages/             # Route views (including AdminUsersPage.tsx)
```

---

## API Endpoints (`/api/v1`)

| Domain | Endpoints |
| :---- | :---- |
| **Auth (`/auth`)** | `POST /register`, `POST /login`, `POST /refresh`, `POST /logout`, `GET /me`, `PATCH /me`, `GET /sessions`, `DELETE /sessions/{id}`, `POST /change-password`, `POST /forgot-password`, `POST /reset-password` |
| **Reports (`/reports`)** | `GET /`, `POST /`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`, `PATCH /{id}/triage`, `POST /{id}/comments` |
| **Groups (`/groups`)** | `GET /`, `POST /`, `GET /users-directory`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`, `POST /{id}/members`, `DELETE /{id}/members/{uid}` |
| **Dashboard (`/dashboard`)** | `GET /summary` |
| **Admin (`/admin`)** | `GET /overview`, `GET /users`, `GET /users/paginated`, `GET /users/{id}`, `POST /users`, `PATCH /users/{id}/role`, `PATCH /users/{id}/ban`, `DELETE /users/{id}/sessions`, `DELETE /users/{id}`, `POST /users/bulk-ban`, `POST /users/bulk-unban`, `GET /reports`, `POST /reports/bulk-delete`, `GET /groups`, `DELETE /groups/{id}`, `GET /audit-logs`, `GET /security`, `GET /export/users`, `GET /export/reports`, `GET /export/audit-logs` |

---

## Environment Variables

Configure `backend/.env` (based on `backend/.env.example`) and your frontend environment as needed:

| Variable | Description | Default / Production Value |
| :---- | :---- | :---- |
| `DATABASE_URL` | PostgreSQL connection string (Supabase pooler `:6543` in prod) | Local SQLite/PostgreSQL URL |
| `JWT_SECRET_KEY` | Secret key used to sign HS256 JWT access tokens | Required |
| `PASSWORD_PEPPER` | Server-side secret key for HMAC-SHA256 password peppering | Required |
| `FRONTEND_URL` | Allowed CORS origin for the React frontend | `http://localhost:5173` (local) |
| `DEMO_MODE` | Enables demo/seed conveniences when active | `false` in production |
| `COOKIE_SECURE` | Sets `Secure` flag on the `vulndesk_refresh_token` cookie | `true` in prod, `false` locally |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of JWT access tokens in minutes | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Lifetime of opaque refresh cookies in days | `7` |
| `VITE_API_BASE_URL` | Frontend API base path | `/api/v1` |

---

## Local Development Setup

### Prerequisites

- Python 3.11+  
- Node.js 18+  
- PostgreSQL (or SQLite for local test runs)

### 1\. Backend Setup

```sh
cd backend
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

Create `backend/.env` from `backend/.env.example`, populate your environment variables, seed the initial dataset (2 admins, 3 researchers, 1 analyst, plus sample reports and groups), and start the server:

```sh
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

### 2\. Frontend Setup

```sh
cd frontend
npm install
npm run dev
```

---

## Running Tests

The backend test suite uses `pytest` 8+ and FastAPI's `TestClient`:

```sh
cd backend
pytest -q
```

All **25 / 25** tests pass across:

- `test_phase1_db.py`  
- `test_phase6_auth_db.py`  
- `test_phase7_auth.py`  
- `test_phase8_rbac_admin.py`  
- `test_phase9_sla_dashboard.py`  
- `test_phase11_groups_audit.py`

---

## Known Limitations & Future Work

- **Password Reset Delivery:** `POST /auth/forgot-password` currently returns a signed 15-minute reset token directly in the API response rather than dispatching an email via an external SMTP provider.  
- **Serverless Cold Starts:** Initial requests after inactivity on Vercel serverless functions may experience a \~1–2 second cold-start delay.  
- **Planned Enhancements:**  
  - Transactional email integration (e.g., Resend or SendGrid) for password resets and notifications.  
  - File and screenshot proof-of-concept (PoC) attachments on vulnerability reports.  
  - Automated Slack/Discord webhook alerts for approaching or breached SLA deadlines.