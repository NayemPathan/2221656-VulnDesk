# **VulnDesk: Product Requirements Document (PRD)**

VulnDesk replaces email and spreadsheet handling of vulnerability reports with one role-controlled web application, and version 1.0 is planned for delivery within the semester.


## **1\. Problem and Goals**

A mid-sized software company receives security vulnerability reports from outside researchers and internal testers by email, chat and a shared spreadsheet. Reports get lost or duplicated, researchers rarely hear back, anyone with access to the shared inbox can read sensitive exploit details, and nobody can show who changed a report's severity or status.

| Goal | Target for version 1.0 |
| ----- | ----- |
| G1: One place for every report | New reports will be submitted and tracked in. |
| G2: Timely first response | At least 90% of reports leave the New status within their deadline |
| G3: Confidential by default | Zero successful cross-user report reads in the automated access tests |
| G4: Traceable decisions | Report status changes recorded with who, when, old and new value |
| G5: Deliverable on time | MVP shown at the mid-term demo; all Must features (MVP and Beta) complete and tested by the deadline. |

The targets are project assumptions, to be measured in testing and the final demo.

## **2\. Users**

| Role | Who they are | What they need | Main challenge today |
| ----- | ----- | ----- | ----- |
| Researcher | External bug-bounty hunters and internal testers (about 285\) | Submit a report easily and see what happened to it | No acknowledgement, no status, no way to follow up |
| Analyst | Security team members (about 12\) | See all reports, set severity, move reports through the workflow, discuss with researchers | Reports scattered across email and sheets, duplicates, no deadlines |
| Admin | System administrators (about 3\) | Manage accounts and roles, see how the process performs | No control over who can see what, no overview |

## **3\. Scope**

**In scope (version 1.0):** accounts and login, role-based access with permission scopes, report submission and editing, report list with filters, triage workflow with status history, comments and internal notes, role-based dashboards, admin user and role management.

**Could have, only after the core is complete:** email notification on status change, and an audit log of important actions.

**Out of scope:** automated vulnerability scanning, AI or machine learning features, bounty or payment handling, file uploads, mobile apps.

## **4\. Features by Priority**

MoSCoW overview: must have (non-negotiable features), should have (important but non-critical features), could have (nice-to-have features)

| Feature | Description | Roles | Priority | Release |
| :---: | :---: | :---: | :---: | :---: |
| Demo user selector (temporary) | The acting user is picked from seeded demo users so ownership and workflow rules can be shown before login exists; removed when authentication is built | Developer | Must | MVP |
| Report submission | Title, description, component, steps to reproduce, proposed severity, with submission policy checks | Researcher | Must | MVP |
| My reports | List, view and edit own reports while status is New | Researcher | Must | MVP |
| Report list and search | All reports, filter by status, severity, component, date, keyword | Analyst, Admin | Must | MVP |
| Triage workflow | Assign final severity, move through status workflow, mark duplicates | Analyst | Must | MVP |
| Status history | Append-only record of every status change | Analyst, Admin, Researcher | Must | MVP |
| Comments and internal notes | Public thread per report, plus analyst-only notes | Researcher, Analyst | Must | MVP |
| Registration and login | Email and password, token-based sessions | All | Must | Beta |
| Roles and permission scopes (RBAC) | Scopes enforced on every endpoint; menus and actions shown only if permitted | All | Must | Beta |
| User and role management | Create, deactivate, delete (soft) users, assign roles | Admin | Must | Beta |
| Profile and dashboards | Profile page (view, change name and password) and per-role dashboards | All | Should | Beta |
| Overdue flag | Mark New reports past their response deadline | Analyst, Admin | Should | Beta |
| Reopen end states | Admin reopens Closed, Rejected or Duplicate reports | Admin | Should | Beta |
| Deployment | Hosted on the company virtual machine with HTTPS, seeded accounts and backups | Admin | Must | Beta |
| Email notification | Notify researcher when status changes | Researcher | Could | After Beta |
| Audit log | Admin-viewable log of logins, role changes, deletions | Admin | Could | After Beta |

## **5\. Key User Stories**

1. As a researcher, I want to submit a vulnerability report so that the security team can investigate it.  
2. As a researcher, I want to see the current status of my reports so that I know whether anyone is acting on them.  
3. As a researcher, I want to edit my report while it is still NEW, so that I can correct mistakes.  
4. As a researcher, I want to add comments to my report so that I can answer the analyst's questions.  
5. As an analyst, I want to filter all reports by status and severity so that I can work on the most urgent first.  
6. As an analyst, I want to set the final severity and move a report through the workflow so that its state is always accurate.  
7. As an analyst, I want to add internal notes so that the team can discuss a report without the researcher seeing them.  
8. As an analyst, I want to see which reports are close to or past their deadline so that I can respond in time.  
9. As an admin, I want to create accounts and assign roles so that every person has only the access they need.  
10. As an admin, I want to see report counts and response times so that I can judge how well the process works.

## **6\. Business Rules**

**Submission policy.** A report is accepted only if (i) the title has 5 to 120 characters, (ii) the description has 50 to 5,000 characters, (iii) the researcher has fewer than 5 open reports (New or Under Review), (iv) the researcher's account is active, and (v) the researcher has fewer than 3 reports rejected as invalid in the current calendar month. A rejected submission returns the specific reason.

**First-response deadline.** A report must leave the New status within 1 day (Critical), 2 days (High), 5 days (Medium) or 10 days (Low), counted from submission using the proposed severity.

**Status workflow.** New, Under Review, Confirmed, Fixed, Closed, with Rejected and Duplicate as alternative end states. Only analysts change status or severity. Confirmed requires a final severity, and Duplicate must reference an existing report. Only an admin can reopen an end state.

**Access.** A researcher sees only their own reports. Internal notes are visible only to analysts. An admin cannot demote, deactivate or delete their own account.

## **7\. Constraints and Assumptions**

* One student developer, about 20 hours a week for 14 weeks (280 hours).  
* Frontend: React with TypeScript. Backend: FastAPI (Python) with a REST API, token-based authentication, role-based access control and permission scopes.  
* Expected load: about 300 users, 150 new reports a month, up to 60 concurrent users at peak.  
* Hosting on one virtual machine (2 vCPU, 4 GB RAM) with free or open-source tools only.  
* The customer representative (the course instructor) is available once a week.

## **8\. Release Plan**

**MVP (mid-term demo, assumed end of week 8):** the core report, workflow and comment features through REST APIs, running locally with seeded demo users and no login. **Beta (final demo, week 14):** authentication, roles and permission scopes on every endpoint, profile and dashboards, admin management and deployment. Adjust the weeks to the real demo dates.

| Weeks | Release | Milestone |
| :---: | :---: | :---: |
| 1-2 | Planning | Requirements baseline (PRD, SRS) and design baseline (TDD) |
| 3-4 | MVP | Increment 1: database models, report create, read and update API, minimal React pages, local run with seeded data |
| 5-6 | MVP | Increment 2: submission policy, status workflow and history, comments and internal notes, filters |
| 7-8 | MVP | MVP hardening: API tests, bug fixes, demo preparation; mid-term demo |
| 9-10 | Beta | Increment 3: registration, login, JWT, roles and scopes on every endpoint, role-aware interface |
| 11-12 | Beta | Increment 4: admin user and role management, profile and dashboards, access and security tests, deployment with HTTPS, load test |
| 13-14 | Beta | Release 1.0: polish, documentation, final demo |

## **9\. Risks and Open Questions**

| Risk or question | Handling |
| :---: | :---: |
| Time shortage for one developer | Features are ordered by priority and release; After Beta items are dropped first, then Should items |
| Authentication and access control arrive late (weeks 9-10) | Ownership rules and a single current-user function exist from the MVP, so the Beta swaps in tokens and scopes without changing endpoints; scope design is fixed in the TDD in advance; weeks 13-14 act as buffer |
| Access-control mistakes leak reports | Negative tests for wrong role and wrong owner on every endpoint, run before deployment |
| Response-deadline policy is still being revised | Deadlines live in one configuration table, not in scattered code |
| Dashboard measures are not final | Dashboards are built last and read from stored data, so measures can change |
| Should researchers see the analyst's reason for rejection? (open) | Decision needed from the customer representative before the comments increment (week 5\) |

