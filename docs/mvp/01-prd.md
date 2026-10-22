# VulnDesk: Product Requirements Document (PRD)

VulnDesk is a web application where security researchers submit vulnerability reports, security analysts triage them through an auditable status workflow, and administrators manage users and access. It is delivered in two milestones: an **MVP** for the mid-term evaluation (supporting full CRUD, live Vercel deployment, and demo role switching) and a **Beta** for the final demo (with JWT authentication, Argon2id hashing, and fine-grained RBAC scopes).


Related documents: [SRS](02-srs.md) | [TDD](03-tdd.md) | [README](../README.md) | [AGENTS](../AGENTS.md)


---


## 1. Release Plan (MVP → Beta)


| Release Dimension | MVP (Mid-Term Assessment) | Beta (Final Evaluation) |
|---|---|---|
| **Demo Target** | Mid-term viva (November 4, 2026) | Final evaluation (Week 14) |
| **Scope Demonstrated** | Complete Report CRUD (Create, Read Single, Read List, Update while New, Delete while New), 5-rule submission policy, triage workflow, visible rejection reasons, append-only status history, public & internal comments, and demo user switcher (`X-Demo-User`). | User registration, login, logout, token refresh rotation, login lockout, profile management, fine-grained RBAC scopes on all endpoints, admin user management and ban, admin dashboard statistics, role dashboards, and overdue SLA flags. |
| **Environment & Deployment** | Hosted on **Vercel** connected to **Supabase PostgreSQL** over HTTPS (mandatory for CSE 309), plus local run instructions. | Deployed on Vercel with Supabase PostgreSQL over HTTPS; security-hardened. |
| **Identity & Authentication** | Acting user chosen from seeded demo users via the `X-Demo-User` header (`DEMO_MODE=true`). | Real user accounts, Argon2id passwords, 15-minute JWT access tokens, and 7-day rotating refresh tokens. |


---


## 2. Problem Statement and Goals


A mid-sized software company receives security vulnerability reports from external bug-bounty researchers and internal quality testers via email, chat messages, and a shared spreadsheet. Reports frequently get lost or duplicated, researchers rarely receive feedback, anyone with shared inbox access can read sensitive exploit payloads, and nobody can verify who modified a report's severity or status.


| ID | Goal | Release | Target Metric |
|---|---|---|---|
| **G1** | Unified Intake & Full CRUD | MVP | 100% of vulnerability reports are submitted, listed, viewed, updated, and deleted (while New) through VulnDesk. |
| **G2** | Traceable & Immutable Decisions | MVP | 100% of status transitions logged in append-only history with who, when, old status, and new status in the same database transaction. |
| **G3** | Confidentiality by Default | MVP & Beta | Zero cross-user report reads or unauthorized internal note leaks in automated access tests. |
| **G4** | Transparent Researcher Feedback | MVP | 100% of rejected reports provide an analyst rejection reason viewable by the researcher. |
| **G5** | High Availability & Performance | MVP & Beta | 99.5% service availability and 95% of API requests responding within 2 seconds under peak load. |


---


## 3. Target Users & Roles


| Role | Target Persona | Core Needs in VulnDesk | Release Availability |
|---|---|---|---|
| **Researcher** | External bug-bounty hunters and internal testers (~285 users) | Submit vulnerability reports with reproduction steps, track status, edit or delete submissions while `New`, view rejection reasons, and comment. | MVP (`X-Demo-User`), Beta (Full Auth) |
| **Analyst** | Security operations team members (~12 users) | View all reports, filter/search by severity/status/component, set final severity, transition statuses (with rejection reason or duplicate link), and write internal notes. | MVP (`X-Demo-User`), Beta (Full Auth) |
| **Admin** | System administrators (~3 users) | Oversee user accounts, soft-delete or ban accounts, reopen end-state reports, and view system statistics. | MVP (Read-only / demo), Beta (Full Management) |
| **Visitor** | Unauthenticated users | Register as a researcher or log into an existing account. | Beta |


---


## 4. MVP vs. Beta Feature Scope


| Feature ID | Feature Name | Description | Role(s) | MoSCoW | Release |
|---|---|---|---|---|---|
| **F-01** | Demo Role Switcher | Switch between demo Researcher, Analyst, and Admin using the `X-Demo-User` header (`DEMO_MODE=true`). | Developer, Tutor | Must | MVP |
| **F-02** | Report Submission (Create) | Submit report with title, description, component, steps, proposed severity, validated against 5 submission rules. | Researcher | Must | MVP |
| **F-03** | My Reports & Detail (Read) | List and view own reports with pagination, keyword search, status, and severity filters. | Researcher | Must | MVP |
| **F-04** | Report Edit (Update) | Edit title, description, component, steps, or proposed severity **only while status is `New`**. | Researcher | Must | MVP |
| **F-05** | Report Withdrawal (Delete) | Delete own report **only while status is `New`** (completes full CRUD requirement for CSE 309). | Researcher | Must | MVP |
| **F-06** | Report Triage & Severity | View all reports, assign `final_severity`, and transition workflow status along allowed state transitions. | Analyst | Must | MVP |
| **F-07** | Rejection Reason Tracking | Capture and display analyst's rejection explanation when moving status to `Rejected`. | Analyst, Researcher | Must | MVP |
| **F-08** | Append-Only Status History | Transactionally record who changed status, from what, to what, and when. | All (Read-only) | Must | MVP |
| **F-09** | Comments & Internal Notes | Discussion thread per report; analysts can post private internal notes hidden from researchers. | Researcher, Analyst | Must | MVP |
| **F-10** | Vercel & Supabase Deployment | Deployed live over HTTPS connecting to Supabase PostgreSQL pooler. | All | Must | MVP |
| **F-11** | User Auth & Profile | User registration, login, rotating refresh tokens, profile edit, password change. | All | Must | Beta |
| **F-12** | Fine-Grained RBAC Scopes | Server-enforced permission scopes on every protected endpoint. | All | Must | Beta |
| **F-13** | Admin User Management & Ban | Admin creates users, changes roles, bans/unbans accounts, soft-deletes users. | Admin | Must | Beta |
| **F-14** | Dashboards & Overdue Flags | Role dashboards, SLA first-response deadline tracking, overdue report flags. | Analyst, Admin | Should | Beta |


---


## 5. Success Metrics for MVP (Mid-Term Demo)


* **Full CRUD Operational:** Create (`POST /reports`), Read List (`GET /reports`), Read Single (`GET /reports/{id}`), Update (`PUT /reports/{id}`), and Delete (`DELETE /reports/{id}`) work in both React UI and Postman.
* **5 of 5 Submission Policy Rules Passing:** Automated unit/API tests verify title length (5-120), description length (50-5000), <5 open reports limit, active account check, and <3 invalid rejections in the current month.
* **Triage & Status History Integrity:** Every status transition writes a corresponding `StatusHistory` record in the same database transaction.
* **Live Deployment:** Accessible on a public Vercel URL over HTTPS connected to Supabase PostgreSQL.
* **GitHub Presentation:** 6 merged pull requests with descriptive branch names, issue links, and conventional commits.
