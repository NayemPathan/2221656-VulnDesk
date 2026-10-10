# **VulnDesk: Technical Design Document (TDD)**

VulnDesk is a three-layer web application: a React \+ TypeScript single-page app called a FastAPI REST API, which enforces JWT authentication, RBAC and permission scopes and stores data in a relational database through SQLAlchemy. Requirement IDs (FR, NFR) refer to the VulnDesk SRS.

## **1\. Architecture**

| Layer | Technology | Responsibility |
| :---: | :---: | :---: |
| Presentation | React, TypeScript, React Router, Axios | Pages, forms, role-aware navigation, calls the API |
| API | FastAPI, Pydantic | Routing, request validation, authentication, scope checks, error responses |
| Business logic | Python service modules | Submission policy, status transitions, deadline calculation, statistics |
| Data access | SQLAlchemy ORM, Alembic migrations | Models, queries, transactions |
| Storage | SQLite in development, PostgreSQL in production | Persistent data |

**Rule of the design:** routers only handle HTTP and security; all business rules live in the service layer, so they can be tested without HTTP and changed in one place (the deadline policy, for example).

## **2\. Project Structure**

VulnDesk/  
  backend/  
    app/  
      main.py            application, CORS, router registration  
      core/              config.py, security.py (hashing, JWT), deps.py (current user, scope check)  
      db/                session.py, base.py  
      models/            user.py, report.py, comment.py, status\_history.py  
      schemas/           Pydantic request and response models  
      routers/           auth.py, users.py, reports.py, comments.py, dashboard.py  
      services/          report\_service.py, policy.py, stats\_service.py  
    alembic/             migrations  
    tests/               pytest: unit and API tests  
  frontend/  
    src/  
      api/               Axios client, one module per resource  
      context/           AuthContext (token, user, scopes)  
      routes/            ProtectedRoute, scope-based guards  
      pages/             Login, Register, Dashboard, Reports, ReportDetail, NewReport, AdminUsers, Profile  
      components/        tables, forms, status badges, comment thread  
      types/             TypeScript types matching API schemas

## 

## **3\. Data Model**

| Entity | Fields | Notes |
| :---: | :---: | :---: |
| User | id, name, email (unique), hashed\_password, role (researcher, analyst, admin), is\_active, created\_at | Soft delete \= is\_active false, so history is kept |
| Report | id, title, description, component, steps\_to\_reproduce, proposed\_severity, final\_severity (nullable), status, reporter\_id, duplicate\_of\_id (nullable), first\_responder\_id (nullable), first\_response\_at (nullable), created\_at, updated\_at | The response deadline is calculated from created\_at and proposed\_severity, not stored |
| Comment | id, report\_id, author\_id, body, is\_internal, created\_at | Internal notes have is\_internal true |
| StatusHistory | id, report\_id, changed\_by, from\_status, to\_status, changed\_at | Append-only: no update or delete code exists |
| DeadlinePolicy | severity, response\_days | Four rows (1, 2, 5, 10 days); changing policy means changing rows, not code |
| AuditLog (Could) | id, user\_id, action, target\_type, target\_id, created\_at | Built only after the core is complete |

**Relationships:** a User has many Reports (as reporter) and many Comments. A Report has many Comments and many StatusHistory entries. A Report may point to another Report as its duplicate.

## 

## **4\. Authentication and Authorization Design**

**Release split.** In the MVP, every protected endpoint already calls one get\_current\_user function, but it returns a seeded demo user chosen by an X-Demo-User header instead of reading a token. Ownership rules (a researcher sees only their own reports) and workflow rules are enforced in the service layer from the start. In the Beta, only the body of get\_current\_user changes: it verifies the JWT and checks scopes, so endpoints, schemas and service code stay the same. The header is accepted only when a DEMO\_MODE setting is on, and it is off in the deployed Beta.

**Authentication (FR-01, FR-02).**

* Passwords are hashed with bcrypt (cost 12 or higher) and never stored or logged in plain text.  
* POST /auth/login accepts the OAuth2 password form and returns a signed JWT access token containing the user id, role and granted scopes, expiring after 30 minutes.  
* The token is verified on every request. Invalid, expired or missing token returns 401\.

**Authorization (FR-24).**

* Each role maps to a fixed set of scopes (SRS section 3). The scopes are put into the token at login.  
* Every protected route declares the scope it needs using FastAPI's security scopes (Security(get\_current\_user, scopes=\["reports:triage"\])). A valid token without that scope returns 403\.  
* Scope checks answer "may this kind of user do this kind of action". Ownership checks answer "may this user touch this record", and live in the service layer: a researcher requesting a report they do not own gets 404 (so the existence of other reports is not revealed).  
* Deactivated users are rejected at login and on every request.

**Frontend (FR-25).** The user's scopes are read from the token and stored in AuthContext. Guards hide pages and buttons the user may not use. This is only a convenience; the API remains the authority.

## **5\. REST API Design**

All endpoints are under /api/v1. Responses are JSON. Errors use a common shape with a detailed message.

| Method and path | Scope needed (enforced from Beta) | Purpose | Requirement | Release |
| :---: | :---: | :---: | :---: | :---: |
| POST /reports | reports:create | Submit report (policy checked) | FR-07, FR-08 | MVP |
| GET /reports | reports:read\_own or reports:read\_all | List with filters and paging; researchers see only their own | FR-09, FR-11 | MVP |
| GET /reports/{id} | reports:read\_own or reports:read\_all | Report detail | FR-09 | MVP |
| PUT /reports/{id} | reports:update\_own | Edit own report while New | FR-10 | MVP |
| PATCH /reports/{id}/severity | reports:triage | Set final severity | FR-12 | MVP |
| PATCH /reports/{id}/status | reports:triage | Change status along allowed transitions | FR-13, FR-14 | MVP |
| GET /reports/{id}/history | same read rules as the report | Status history | FR-15 | MVP |
| POST /reports/{id}/comments | comments:create | Add comment; internal needs comments:internal | FR-18, FR-19 | MVP |
| GET /reports/{id}/comments | comments:read | List comments; internal ones only with comments:internal | FR-20 | MVP |
| POST /auth/register | none (public) | Register a researcher | FR-01 | Beta |
| POST /auth/login | none (public) | Log in, receive token | FR-02 | Beta |
| GET /auth/me | any logged-in user | Own profile and scopes | FR-03 | Beta |
| PATCH /auth/me | any logged-in user | Change own name or password | FR-03 | Beta |
| GET /users | users:read | List users | FR-04 | Beta |
| POST /users | users:manage | Create user with role | FR-04 | Beta |
| PATCH /users/{id} | users:manage | Edit name, activate or deactivate | FR-05 | Beta |
| DELETE /users/{id} | users:manage | Soft delete | FR-05 | Beta |
| PATCH /users/{id}/role | roles:assign | Change role | FR-06 | Beta |
| PATCH /reports/{id}/status (reopen) | reports:reopen | Reopen an end-state report | FR-16 | Beta |
| GET /dashboard/summary | any logged-in user | Role-specific summary; admin statistics need stats:read | FR-21 to FR-23 | Beta |
| GET /audit-logs | audit:read | Audit log (Could) | FR-27 | After Beta |

**Status codes.** 200/201 success; 401 not authenticated; 403 missing scope; 404 not found or not yours; 409 business rules violated (submission policy, invalid status transition) with a specific reason; 422 invalid field format.

## **6\. Business Logic Design**

**Submission policy (FR-08).** policy.check\_submission(user, data) runs the five checks in order and raises a rule-violation error naming the first failed rule. Field length checks (title, description) are also in the Pedantic schema.

**Status transitions (FR-13, FR-14, FR-16).** A transition table in report\_service lists allowed pairs and the role allowed to make them. Before saving it also checks: Confirmed needs a final severity; Duplicate needs a valid duplicate\_of\_id; end states can only be left by a user with reports:reopen.

**Atomic status change (NFR-08).** Updating the status, writing the StatusHistory row and (on the first change from New) setting first\_response\_at and first\_responder\_id happen in one database transaction.

**Overdue flag (FR-17).** A report is overdue when its status is New and the current time is later than created\_at plus the days in DeadlinePolicy for its proposed severity. It is calculated when reports are read.

**Statistics (FR-23).** Average time to first response, on-time rate per analyst and reports per researcher per month are computed from Report and StatusHistory data by stats\_service, so the measures can change without schema changes.

## **7\. Frontend Design**

| Route | Page | Visible to | Release |
| :---: | :---: | :---: | :---: |
| (page header) | Demo user switcher, temporary, removed when login is built | Developer | MVP |
| /reports | Report list (own for researchers, all for analysts and admins) with filters | All users | MVP |
| /reports/new | Submit report | Researcher | MVP |
| /reports/:id | Detail, comments, history; triage panel for analysts | Owner, analyst, admin | MVP |
| /login, /register | Login, registration | Public | Beta |
| /dashboard | Role-specific dashboard | All logged-in users | Beta |
| /admin/users | User and role management | Admin | Beta |
| /profile | Own profile and password change | All logged-in users | Beta |

**State and data:** AuthContext keeps the token and user in memory with a copy in sessionStorage, and an Axios interceptor adds the Authorization header and redirects to login on a 401\. Server data is fetched per page, with simple loading and error states.

**Role-aware UI:** a ProtectedRoute component checks login, and a RequireScope component checks a scope before rendering a page or button. React escapes output by default, and no user text is inserted as raw HTML.

## **8\. Security Design (NFR-04 to NFR-07)**

* Server-side validation of every input with Pydantic; database access only through the ORM, so queries are parameterised.  
* CORS is limited to the front end's own origin; HTTPS only in production.  
* No stack traces or internal details in error responses.  
* Login errors do not reveal whether the email exists.  
* Secrets (signing key, database URL) come from environment variables, never from the repository.  
* Dependencies pinned in requirement files and checked for known vulnerabilities before release.

## 

## **9\. Testing Strategy**

| Level | Tool | What is tested |
| :---: | :---: | :---: |
| Unit | pytest | Submission policy, transition table, deadline calculation, statistics |
| API | pytest with FastAPI TestClient | Every endpoint: success case, wrong role (403), wrong owner (404), invalid input (422), rule violation (409) |
| Access matrix | pytest, parametrised | Each role against each endpoint, compared with the scope table in the SRS |
| Load | Locust | NFR-01 and NFR-02 at 60 concurrent users |
| Frontend | Manual checklist, optional component tests | Role-based menus, forms, error messages, cross-browser check |

## **10\. Deployment (MVP local, Beta hosted)**

**MVP:** runs locally with Uvicorn for the API and the React development server, using SQLite, seeded demo users and sample reports, started by a short documented set of commands.

In the Beta, one Linux virtual machine runs Nginx as a reverse proxy with an HTTPS certificate, serves the built React files, and forwards /api to Uvicorn running the FastAPI app. PostgreSQL runs on the same machine, with nightly database backups. Configuration is by environment variables. Alembic migrations run at each deployment.

## **11\. Implementation Plan**

| Weeks | Release | Backend | Frontend |
| :---: | :---: | :---: | :---: |
| 3-4 | MVP | Project setup, models, migrations, report create, read and update endpoints, demo-user dependency, seed data | Project setup, report form, report list and detail, demo user switcher |
| 5-6 | MVP | Submission policy, status workflow and history, comments and internal notes, filters and paging | Triage panel, status history, comment thread, filters |
| 7-8 | MVP | Unit and API tests, bug fixes, local run instructions | Polish, error handling; mid-term demo |
| 9-10 | Beta | Registration, login, JWT, role-to-scope mapping, scope checks on every endpoint, user endpoints | Login, registration, AuthContext, protected routes, scope guards |
| 11-12 | Beta | Admin endpoints, dashboard and statistics, access-matrix and security tests, load test, deployment with HTTPS | Admin user page, dashboards, profile page, cross-browser check |
| 13-14 | Beta | Documentation, final fixes | Final fixes; final demo |

## **12\. Open Design Decisions**

* Whether researchers may see the analyst's reason for rejecting a report (awaiting the customer representative); if yes, a note field is added to StatusHistory.  
* Whether a refresh token is needed. Version 1.0 uses a 30-minute access token and a new login; a refresh token can be added later without changing the API shape.