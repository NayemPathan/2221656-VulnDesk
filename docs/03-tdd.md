# VulnDesk: Technical Design Document (TDD)

Web Application Development | Solo project | [Your Name] | ID: [Your ID] | Version 1.0 | [Date]

Related documents: [PRD](01-prd.md) | [SRS](02-srs.md) | [README](../README.md)

Requirement IDs (FR, NFR), story IDs (US) and acceptance criteria (AC) refer to the SRS and PRD.

---

## 1. Tech Stack

| Area | Technology | Release |
|---|---|---|
| API framework | FastAPI (Python), Pydantic | MVP |
| ORM and models | SQLModel (SQLAlchemy and Pydantic combined) | MVP |
| Database | Supabase (managed PostgreSQL); SQLite is allowed for quick local tests | MVP |
| Front end | React, TypeScript, Vite, React Router | MVP |
| Hosting | Vercel (front end static build, API as a Python serverless function) | Beta |
| Migrations | Alembic | Beta (the first migration is created in M1) |
| Tokens | PyJWT (HS256) | Beta |
| Password hashing | Argon2id (`argon2-cffi`) | Beta |
| Tests | pytest, FastAPI TestClient, Locust (load) | MVP |

---

## 2. Architecture

### Layers

```mermaid
flowchart TB
    subgraph Client["Browser"]
        UI["React + TypeScript SPA"]
    end
    subgraph Vercel["Vercel"]
        STATIC["Static front-end build"]
        FN["FastAPI app (serverless function)"]
    end
    subgraph App["FastAPI app"]
        RT["Routers (HTTP only)"]
        DEP["Dependencies: current user, scopes"]
        SVC["Services: rules, workflow, stats"]
        ORM["SQLModel data access"]
    end
    DB[("Supabase PostgreSQL")]
    UI -->|HTTPS| STATIC
    UI -->|HTTPS /api/v1| FN
    FN --- RT
    RT --> DEP
    RT --> SVC
    SVC --> ORM
    ORM --> DB
```

**Design rule:** routers only deal with HTTP; every business rule (submission policy, status transitions, ownership, deadlines, statistics) lives in the service layer, so it can be tested without HTTP and changed in one place.

### Request flow (protected endpoint)

```mermaid
sequenceDiagram
    participant C as React app
    participant R as Router
    participant D as get_current_user
    participant S as Service
    participant DB as PostgreSQL
    C->>R: HTTPS request with access token
    R->>D: resolve user and required scopes
    D->>DB: load user by id from token
    alt token invalid, user missing or banned
        D-->>C: 401
    else scope missing
        D-->>C: 403
    else allowed
        D-->>R: user
        R->>S: call service with validated data
        S->>DB: query or change data in a transaction
        alt rule violated
            S-->>C: 409 with reason
        else not owner
            S-->>C: 404
        else success
            S-->>C: 200 or 201 with JSON
        end
    end
```

### Login sequence (Beta)

```mermaid
sequenceDiagram
    actor U as User
    participant FE as React app
    participant API as FastAPI
    participant DB as PostgreSQL
    U->>FE: email and password
    FE->>API: POST /api/v1/auth/login
    API->>DB: load user by email
    alt user missing, banned or locked
        API-->>FE: 401 generic error
    else user found
        API->>API: verify password with Argon2id
        alt wrong password
            API->>DB: failed_login_count + 1 (lock 15 min at 5)
            API-->>FE: 401 generic error
        else correct password
            API->>DB: reset counter, store hashed refresh token
            API-->>FE: 200 access token in body, refresh token in HttpOnly cookie
        end
    end
```

### Refresh sequence (Beta)

```mermaid
sequenceDiagram
    participant FE as React app
    participant API as FastAPI
    participant DB as PostgreSQL
    FE->>API: request with expired access token
    API-->>FE: 401
    FE->>API: POST /api/v1/auth/refresh (refresh cookie)
    API->>DB: find token by hash
    alt valid, not expired, not revoked
        API->>DB: revoke old token, store new token (same family)
        API-->>FE: 200 new access token and new refresh cookie
        FE->>API: retry the original request
    else unknown, expired or already used
        API->>DB: revoke the whole token family
        API-->>FE: 401, user must log in again
    end
```

---

## 3. Project Structure

```
VulnDesk/
  README.md
  AGENTS.md                  branch, commit and PR conventions
  vercel.json                routes /api/* to the API function
  docs/
    01-prd.md  02-srs.md  03-tdd.md
  api/
    index.py                 Vercel entry point, imports the FastAPI app
  backend/
    app/
      main.py                app creation, routers, docs at /api/docs
      config.py              settings read from environment variables
      database.py            engine and session dependency
      deps.py                get_current_user, scope checks
      security.py            Argon2 hashing, JWT, refresh tokens
      models/                SQLModel tables: user, report, comment,
                             status_history, refresh_token, deadline_policy
      schemas/               request and response models
      routers/               health, reports, comments, auth, users,
                             dashboard, admin
      services/              report_service, policy, auth_service, stats_service
      seed.py                demo users and sample reports
    alembic/                 migrations
    tests/                   unit and API tests
    requirements.txt
    .env.example
  frontend/
    package.json  vite.config.ts  index.html
    src/
      api/                   API client, one module per resource
      auth/                  AuthContext, ProtectedRoute, RequireScope (Beta)
      pages/                 Reports, ReportDetail, NewReport, Login,
                             Register, Dashboard, AdminUsers, Profile
      components/            tables, forms, status badge, comment thread
      types/                 TypeScript types matching API schemas
```

---

## 4. Data Model

### ERD

```mermaid
erDiagram
    USER ||--o{ REPORT : submits
    USER ||--o{ COMMENT : writes
    USER ||--o{ STATUS_HISTORY : changes
    USER ||--o{ REFRESH_TOKEN : owns
    REPORT ||--o{ COMMENT : has
    REPORT ||--o{ STATUS_HISTORY : logs
    REPORT |o--o| REPORT : "duplicate of"
    USER {
        int id PK
        string name
        string email UK
        string role
        datetime created_at
        string hashed_password "Beta"
        boolean is_banned "Beta"
        boolean is_deleted "Beta"
        int failed_login_count "Beta"
        datetime locked_until "Beta"
    }
    REPORT {
        int id PK
        string title
        string description
        string component
        string steps_to_reproduce
        string proposed_severity
        string final_severity
        string status
        int reporter_id FK
        int duplicate_of_id FK
        int first_responder_id FK
        datetime first_response_at
        datetime created_at
        datetime updated_at
    }
    COMMENT {
        int id PK
        int report_id FK
        int author_id FK
        string body
        boolean is_internal
        datetime created_at
    }
    STATUS_HISTORY {
        int id PK
        int report_id FK
        int changed_by FK
        string from_status
        string to_status
        datetime changed_at
    }
    REFRESH_TOKEN {
        int id PK
        int user_id FK
        string token_hash UK "Beta"
        string family_id "Beta"
        datetime expires_at "Beta"
        datetime revoked_at "Beta"
        datetime created_at "Beta"
    }
    DEADLINE_POLICY {
        string severity PK "Beta"
        int response_days "Beta"
    }
```

### Tables per release

| Table | MVP | Beta |
|---|---|---|
| `user` | `id`, `name`, `email`, `role`, `created_at`; seeded demo users, no password | Adds `hashed_password`, `is_banned`, `is_deleted`, `failed_login_count`, `locked_until`; demo users get passwords or are removed |
| `report` | All columns shown | Unchanged |
| `comment` | All columns shown | Unchanged |
| `status_history` | All columns shown; append-only (no update or delete code) | Unchanged |
| `refresh_token` | Not present | New table |
| `deadline_policy` | Not present | New table with 4 rows: critical 1, high 2, medium 5, low 10 days |

**Notes.**
- The response deadline is calculated from `created_at` and `proposed_severity`, not stored.
- `first_response_at` and `first_responder_id` are set when a report first leaves New, and feed the Beta statistics.
- Deleting a user is a soft delete (`is_deleted`), so reports, comments and history stay intact.
- The MVP already has a `user` table, so foreign keys are correct from the first migration and Beta only adds columns.

---

## 5. REST API

All endpoints are under `/api/v1`. Interactive API docs are at **`/api/docs`** (OpenAPI JSON at `/api/openapi.json`). Errors use `{"detail": "..."}`. Status codes and validation rules are in SRS section 7.

### MVP endpoints

In the MVP the caller is the demo user from the `X-Demo-User` header. Ownership and workflow rules are enforced; scopes are not.

| Method and path | Intended caller | Purpose | Requirement |
|---|---|---|---|
| GET /health | anyone | Health check | NFR-03 |
| POST /reports | researcher | Submit report (policy checked) | FR-07, FR-08 |
| GET /reports | researcher (own), analyst, admin (all) | List with filters and paging | FR-09, FR-11 |
| GET /reports/{id} | owner, analyst, admin | Report detail | FR-09 |
| PUT /reports/{id} | owner researcher | Edit own report while New | FR-10 |
| PATCH /reports/{id}/severity | analyst | Set final severity | FR-12 |
| PATCH /reports/{id}/status | analyst | Change status along allowed transitions | FR-13, FR-14, FR-15 |
| GET /reports/{id}/history | owner, analyst, admin | Status history | FR-15 |
| POST /reports/{id}/comments | owner researcher, analyst | Add comment or internal note | FR-18, FR-19 |
| GET /reports/{id}/comments | owner researcher, analyst, admin | List comments (internal notes only for analysts) | FR-20 |

### Beta endpoints: who can call each one

| Method and path | Roles allowed | Scope | Purpose | Requirement |
|---|---|---|---|---|
| POST /auth/register | visitor | public | Register a researcher | FR-01 |
| POST /auth/login | visitor | public | Log in; access token and refresh cookie | FR-02, FR-29 |
| POST /auth/refresh | any holder of a refresh token | refresh cookie | New access token, rotate refresh token | FR-28 |
| POST /auth/logout | any logged-in user | any logged-in user | Revoke refresh token | FR-28 |
| GET /users/me | researcher, analyst, admin | any logged-in user | Own profile and scopes | FR-03, FR-25 |
| PATCH /users/me | researcher, analyst, admin | any logged-in user | Change own name | FR-03 |
| PUT /users/me/password | researcher, analyst, admin | any logged-in user | Change password (current password required) | FR-03 |
| POST /reports | researcher | reports:create | Submit report | FR-07, FR-08 |
| GET /reports | researcher (own), analyst, admin (all) | reports:read_own or reports:read_all | List; includes overdue flag | FR-09, FR-11, FR-17 |
| GET /reports/{id} | owner researcher, analyst, admin | reports:read_own or reports:read_all | Report detail | FR-09 |
| PUT /reports/{id} | owner researcher | reports:update_own | Edit own report while New | FR-10 |
| PATCH /reports/{id}/severity | analyst | reports:triage | Set final severity | FR-12 |
| PATCH /reports/{id}/status | analyst | reports:triage | Change status | FR-13, FR-14 |
| POST /reports/{id}/reopen | admin | reports:reopen | Reopen an end-state report | FR-16 |
| GET /reports/{id}/history | owner researcher, analyst, admin | same as the report | Status history | FR-15 |
| POST /reports/{id}/comments | owner researcher, analyst | comments:create (comments:internal for notes) | Add comment | FR-18, FR-19 |
| GET /reports/{id}/comments | owner researcher, analyst, admin | comments:read (comments:internal for notes) | List comments | FR-20 |
| GET /dashboard | researcher, analyst, admin | any logged-in user | Role-specific dashboard | FR-21, FR-22 |
| GET /admin/stats | admin | stats:read | System statistics | FR-23 |
| GET /users | admin | users:read | List users | FR-04 |
| POST /users | admin | users:manage | Create user with role | FR-04 |
| GET /users/{id} | admin | users:read | View a user | FR-04 |
| PATCH /users/{id}/role | admin | roles:assign | Change role (not own) | FR-06 |
| POST /users/{id}/ban | admin | users:manage | Ban user (not self) | FR-05 |
| POST /users/{id}/unban | admin | users:manage | Unban user | FR-05 |
| DELETE /users/{id} | admin | users:manage | Soft delete (not self) | FR-05 |
| GET /audit-logs (After Beta) | admin | audit:read | Audit log | FR-27 |

---

## 6. Auth, RBAC, Ban and Profile Design

### Tokens

| Token | Form | Lifetime | Storage |
|---|---|---|---|
| Access token | JWT signed with `JWT_SECRET` (HS256, PyJWT). Claims: `sub` (user id), `role`, `iat`, `exp` | 15 minutes | Sent in the `Authorization: Bearer` header; kept in memory in the browser, never in `localStorage` |
| Refresh token | Random 256-bit value | 7 days | Sent as an HttpOnly, Secure, SameSite=Strict cookie limited to `/api/v1/auth`; only its SHA-256 hash is stored in `refresh_token` |

**Rotation.** Every refresh revokes the used token and issues a new one in the same `family_id`. If an already-used or revoked token appears again, the whole family is revoked and the user must log in again.

### Password hashing

Passwords are hashed with Argon2id using the library defaults and are never stored or logged in plain text. The password rule is 8 to 128 characters with at least one letter and one digit.

### Login lockout

`user.failed_login_count` increases on each wrong password and resets on success. At 5, `locked_until` is set to 15 minutes ahead. A locked, banned or unknown account returns the same generic 401 as a wrong password, so the response does not reveal which accounts exist. The counter is kept in the database because serverless functions keep no memory between requests.

### Permission dependencies (RBAC and scopes)

Scopes are fixed per role in one dictionary. The server recomputes a user's scopes from the database on every request, so a role change or ban takes effect immediately, even for a token that is still valid.

| Role | Scopes |
|---|---|
| researcher | `reports:create`, `reports:read_own`, `reports:update_own`, `comments:create`, `comments:read` |
| analyst | `reports:read_all`, `reports:triage`, `comments:create`, `comments:read`, `comments:internal` |
| admin | `reports:read_all`, `reports:reopen`, `comments:read`, `users:read`, `users:manage`, `roles:assign`, `stats:read` (and `audit:read` after Beta) |

```python
# deps.py (Beta)
async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    payload = decode_access_token(token)               # 401 if invalid or expired
    user = session.get(User, int(payload["sub"]))
    if user is None or user.is_banned or user.is_deleted:
        raise HTTPException(status_code=401, detail="Not authenticated")
    granted = SCOPES_BY_ROLE[user.role]
    for scope in security_scopes.scopes:
        if scope not in granted:
            raise HTTPException(status_code=403, detail="Missing permission")
    return user

# usage in a router
@router.patch("/reports/{report_id}/status")
def change_status(report_id: int, body: StatusChange,
                  user: User = Security(get_current_user, scopes=["reports:triage"])):
    ...
```

**MVP seam.** In the MVP, `get_current_user` has the same signature but reads the `X-Demo-User` header (only when `DEMO_MODE=true`) and does not check scopes. In the Beta only the body of this function changes, so routers, schemas and services stay the same. `DEMO_MODE` is off in the deployed Beta, and the header is then ignored.

**Ownership rules** live in the service layer: a researcher asking for another researcher's report gets 404. These apply in both releases.

### Ban

`POST /users/{id}/ban` sets `is_banned`, revokes all of the user's refresh tokens, and takes effect on the next request, because `get_current_user` checks `is_banned` on every call. An admin cannot ban, delete or change the role of their own account (409).

### Profile

`GET /users/me` returns name, email, role and scopes (the interface uses them to show or hide actions). `PATCH /users/me` changes the name. `PUT /users/me/password` needs the current password, applies the password rule, and revokes all refresh tokens.

---

## 7. Admin Dashboard Statistics Design

`GET /admin/stats` (scope `stats:read`) is computed by `stats_service` from `report` and `status_history`, so the measures can change without schema changes.

| Measure | How it is computed |
|---|---|
| Reports by status and severity | `GROUP BY status, final_severity` (proposed severity if no final one yet) |
| Average time to first response | Average of `first_response_at - created_at` over reports where `first_response_at` is set |
| On-time rate per analyst | For reports with `first_responder_id` = analyst: share where `first_response_at` is within `created_at` plus `response_days` from `deadline_policy` |
| Reports per researcher per month | `GROUP BY reporter_id, month of created_at` |
| Overdue count | New reports where now is later than `created_at` plus `response_days` |

```json
{
  "by_status": {"new": 12, "under_review": 5, "confirmed": 3, "fixed": 2, "closed": 20, "rejected": 4, "duplicate": 2},
  "by_severity": {"low": 9, "medium": 18, "high": 14, "critical": 7},
  "avg_first_response_hours": 20.5,
  "on_time_rate_by_analyst": [{"analyst_id": 3, "name": "Analyst One", "rate": 0.93}],
  "reports_per_researcher_per_month": [{"researcher_id": 7, "month": "2026-11", "count": 4}],
  "overdue_count": 2
}
```

`GET /dashboard` returns a smaller, role-specific result: a researcher gets counts of their own reports by status; an analyst gets the triage queue (status New) and the overdue reports; an admin gets the same summary as `/admin/stats`.

---

## 8. Security

- All input is validated by Pydantic schemas and service rules; the database is reached only through SQLModel, so queries are parameterised (injection).
- React escapes output and no user text is inserted as raw HTML (XSS). Responses carry basic security headers.
- Access control is checked on the server for every protected endpoint; the interface only hides actions (broken access control).
- Argon2id for passwords, short-lived access tokens, rotating refresh tokens, login lockout, ban checked on every request.
- Generic login errors; no stack traces or internals in error responses.
- Secrets come from environment variables and never from Git; `.env` is in `.gitignore`.
- CORS is limited to the front end's own origin (the front end and API share one domain on Vercel).
- Dependencies are pinned and checked for known vulnerabilities before release.

---

## 9. Configuration (Environment Variables)

| Variable | Release | Purpose | Example |
|---|---|---|---|
| `DATABASE_URL` | MVP | PostgreSQL connection string (Supabase) | `postgresql+psycopg://user:pass@host:6543/postgres` |
| `DEMO_MODE` | MVP | Accept the `X-Demo-User` header; must be `false` in the deployed Beta | `true` |
| `JWT_SECRET` | Beta | Key that signs access tokens; long random value | (never commit) |
| `JWT_ALGORITHM` | Beta | Signing algorithm | `HS256` |
| `ACCESS_TOKEN_MINUTES` | Beta | Access token lifetime | `15` |
| `REFRESH_TOKEN_DAYS` | Beta | Refresh token lifetime | `7` |
| `LOGIN_MAX_ATTEMPTS` | Beta | Failed logins before lockout | `5` |
| `LOGIN_LOCK_MINUTES` | Beta | Lockout duration | `15` |
| `COOKIE_SECURE` | Beta | Send the refresh cookie only over HTTPS | `true` |
| `ALLOWED_ORIGINS` | Beta | Allowed CORS origins when front end and API are on different domains | `http://localhost:5173` |

An `.env.example` file lists the names without real values. Secrets are set in Vercel project settings for the deployed site.

---

## 10. Supabase Setup

1. Create a Supabase project and choose a strong database password.
2. In the project's database settings, copy the PostgreSQL connection string for the connection pooler (needed for serverless functions) and use it as `DATABASE_URL`.
3. Keep the database password out of Git; put the string in `.env` locally and in Vercel settings when deployed.
4. Run the migrations against it (section 11), then run the seed script for demo users.
5. Do not use Supabase's own auth or client libraries: VulnDesk's authentication is its own, as designed in section 6.

---

## 11. Migrations

- Alembic manages the schema. `alembic revision --autogenerate -m "message"` creates a migration from the SQLModel models, which is then read and checked by hand.
- **M1 (MVP):** initial migration creates `user`, `report`, `comment` and `status_history`.
- **M4 (Beta):** adds the credential columns to `user` and creates `refresh_token`.
- **M5 or M6 (Beta):** creates `deadline_policy` with its four rows.
- Every migration must run cleanly on an empty database and on the previous version. Migrations are applied before each deployment: `alembic upgrade head`.

---

## 12. Deployment (Beta)

- The repository is connected to a Vercel project. The React app is built with Vite and served as static files.
- The FastAPI app runs as a Python serverless function through `api/index.py`, and `vercel.json` routes `/api/*` to it. Front end and API share one domain, so cookies are first-party and CORS is not needed.
- Environment variables (`DATABASE_URL`, `JWT_SECRET`, and the rest of section 9) are set in the Vercel project settings, with `DEMO_MODE=false`.
- The database engine uses a small connection pool (or none) and Supabase's pooler, because serverless functions open many short-lived connections.
- After each deployment: open `/api/v1/health` and `/api/docs`, then run the smoke test (log in, list reports).
- HTTPS is provided by Vercel (NFR-06). Uptime is watched with a free monitor (NFR-03).

---

## 13. Testing

| Level | Tool | What is tested | Release |
|---|---|---|---|
| Unit | pytest | Submission policy, transition table, deadline calculation, statistics | MVP |
| API | pytest with TestClient | Every endpoint: success, wrong owner (404), rule violation (409), invalid input (422) | MVP |
| Auth and access | pytest, parametrised | Login, lockout, refresh rotation, ban, every role against every endpoint compared with the SRS permission matrix | Beta |
| Load | Locust | NFR-01 and NFR-02 at 60 concurrent users | Beta |
| Front end | Manual checklist | Forms, error messages, role-based menus, cross-browser check | MVP and Beta |

Each acceptance criterion (AC-01 to AC-21) maps to at least one automated test.

---

## 14. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Authentication and RBAC are built late (weeks 9-12) | Final demo at risk | The `get_current_user` seam exists from the MVP; the design is fixed here in advance; Should features are dropped first |
| Serverless connections exhaust the database | Intermittent errors | Use Supabase's pooler and a small pool; test early in M6 |
| Refresh cookie does not work across origins | Users logged out unexpectedly | Keep front end and API on one Vercel domain |
| Unsettled deadline and dashboard rules | Rework | Deadlines in `deadline_policy`; statistics computed from stored data |
| One developer, 280 hours | Scope overrun | MoSCoW order; After Beta items never started before the core is done |
| Secrets leaked to Git | Severe | `.env` ignored, `.env.example` only, repository scan before the final demo |
