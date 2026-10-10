here is the Webapp tutor said now to submit: Tasks
1. PRD — `docs/01-prd.md`

* Release plan (MVP → Beta) with a roadmap diagram
Problem statement and goals (tagged MVP / Beta)
Target users: student, group owner, group member, admin
In scope / out of scope per release
Feature list with MoSCoW priority and release
User stories for MVP and Beta
Success metrics per release
Milestones: MVP (docs, data layer, CRUD API, mid demo) and Beta (auth + profile, RBAC + admin dashboard + ban, group tasks, security, final demo)

2. SRS — `docs/02-srs.md`

* Purpose, scope, definitions (CRUD, REST, JWT, RBAC, group task, etc.)
Roles: global (`user`, `admin`) and per-group (`owner`, `member`)
Use case diagrams (MVP and Beta) and task state diagram
Functional requirements with IDs, release and linked user story
Non-functional requirements with IDs (performance, security, maintainability, usability)
Validation rules and status codes
Beta permission matrix (role × action)
Acceptance criteria (Given / When / Then)
Traceability: story → requirement → endpoint

3. TDD — `docs/03-tdd.md`

* Tech stack (FastAPI, SQLModel, Supabase, Vercel; Beta: Alembic, PyJWT, Argon2)
Architecture, request flow and login / refresh sequence diagrams
Project structure
Data model and ERD (MVP `task`; Beta users, refresh tokens, groups, members)
REST API under `/api/v1`: endpoint tables with who can call each one; API docs at `/api/docs`
Auth, RBAC, ban and profile design (tokens, password hashing, login lockout, permission dependencies)
Admin dashboard stats design
Security, configuration (env vars), Supabase setup, migrations, deployment, risks

4. README — `README.md`

* Replace the "FastAPI + React Template" title and class exercise with Smarter Todo
Short project description and the MVP / Beta feature list
Tech stack (FastAPI, SQLModel, Supabase, React + Vite, Vercel)
Links to the PRD, SRS and TDD in `docs/`
Run locally (backend + frontend) and where the API docs are (`/api/docs`)
Environment variables (`DATABASE_URL`, and Beta `JWT_SECRET` etc.) with a note that secrets never go in Git
Deploy to Vercel steps
Contributing: link to `AGENTS.md` for branch, commit and PR conventions

Definition of done

* All three docs and the updated README merged into `main` through a PR
Every functional requirement traces to a user story and an endpoint
Every Beta endpoint lists which role can call it
README no longer mentions the template or the class exercise
Reviewed and approved