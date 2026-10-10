 # **VulnDesk: Software Requirements Specification (SRS)**

This SRS defines 27 functional and 12 non-functional requirements for VulnDesk version 1.0, each with an identifier, priority and a way to verify it.


## **1\. Introduction**

**Purpose.** This document specifies what VulnDesk must do, so that design, implementation and testing can be checked against it. It refines the VulnDesk PRD.

**Scope.** VulnDesk is a web application where security researchers submit vulnerability reports, security analysts triage them through a status workflow, and administrators manage users and roles. It does not scan systems for vulnerabilities and does not process payments.

**Definitions.**

| Term | Meaning |
| :---: | :---: |
| Report | A vulnerability report submitted by a researcher |
| Scope | A named permission (for example reports:triage) checked on every protected API call |
| RBAC | Role-based access control: each role is granted a set of scopes |
| Internal note | A comment visible only to analysts |
| End state | Closed, Rejected or Duplicate |
| MoSCoW | Priority: M \= Must, S \= Should, C \= Could |

## **2\. Overall Description**

**Product perspective.** VulnDesk is a standalone system made of a React \+ TypeScript single-page application, a FastAPI REST back end, and a relational database. It has no dependency on other company systems. An external email service is an optional (Could) secondary actor.

**User classes.** Researcher (about 285 users), Analyst (about 12\) and Admin (about 3). Each user holds exactly one role.

**Operating environment.** Current versions of Chrome, Firefox and Edge on desktop and mobile; server on one Linux virtual machine (2 vCPU, 4 GB RAM).

**Design and implementation constraints.** React with TypeScript, FastAPI with Python, REST APIs, token-based authentication, RBAC with permission scopes, free or open-source tools only, one developer, 14 weeks.

**Assumptions.** About 150 new reports a month and up to 60 concurrent users at peak. Management is still revising the response-deadline policy and dashboard measures, so these are treated as changeable.

**Releases.** Every requirement is marked MVP or Beta. The MVP (mid-term demo, running locally) delivers the core report, workflow and comment features through the REST API; the acting user is chosen from seeded demo users and no login is needed. The Beta (final demo) adds authentication, roles, permission scopes, user administration, profile and dashboards, and deployment. Requirements marked Optional are built only after the Beta is complete.

## **3\. Roles and Permission Scopes**

Scopes are defined from the start but enforced on every endpoint from the Beta release (FR-24). In the MVP the same ownership and workflow rules are applied using the seeded demo user.

| Scope | Researcher | Analyst | Admin | Allows |
| :---: | :---: | :---: | :---: | :---: |
| reports:create | Yes | \- | \- | Submit a report |
| reports:read\_own | Yes | \- | \- | Read own reports |
| reports:update\_own | Yes | \- | \- | Edit own report while status is New |
| reports:read\_all | \- | Yes | Yes | Read every report |
| reports:triage | \- | Yes | \- | Set severity and change status |
| reports:reopen | \- | \- | Yes | Reopen an end-state report |
| comments:create | Yes | Yes | \- | Add a comment |
| comments:read | Yes | Yes | Yes | Read non-internal comments |
| comments:internal | \- | Yes | \- | Create and read internal notes |
| users:read | \- | \- | Yes | List and view users |
| users:manage | \- | \- | Yes | Create, deactivate, delete users |
| roles:assign | \- | \- | Yes | Change a user's role |
| stats:read | \- | \- | Yes | View system-wide statistics |
| audit:read | \- | \- | Yes (Could) | View the audit log |

## **4\. Functional Requirements**

| ID | Requirement | Priority | Release |
| :---: | :---: | :---: | :---: |
| **Accounts and access** |  |  |  |
| FR-01 | A visitor can register as a Researcher with name, email and password. The email must be unique and the password at least 8 characters. | M | Beta |
| FR-02 | A user can log in with email and password and receive an access token that expires after 30 minutes. A failed login returns 401 without saying whether the email or the password was wrong. | M | Beta |
| FR-03 | A user can view their own profile and change their name and password. | S | Beta |
| FR-04 | An admin can create a user account with any role. | M | Beta |
| FR-05 | An admin can deactivate, reactivate and delete (soft delete) accounts. A deactivated user cannot log in, and their reports and comments remain. | M | Beta |
| FR-06 | An admin can change a user's role, but cannot change, deactivate or delete their own account. | M | Beta |
| **Reports** |  |  |  |
| FR-07 | A researcher can submit a report with title, description, affected component, steps to reproduce and proposed severity. The new report has status New. | M | MVP |
| FR-08 | The system accepts a submission only if the submission policy holds: title 5 to 120 characters, description 50 to 5,000 characters, fewer than 5 open reports, active account, fewer than 3 reports rejected as invalid this calendar month. Otherwise it rejects the submission and states the reason. | M | MVP |
| FR-09 | A researcher can list and view their own reports and nobody else's. | M | MVP |
| FR-10 | A researcher can edit their own report only while its status is New. | M | MVP |
| FR-11 | An analyst or admin can list all reports, filter by status, severity, component, date range and title keyword, with paging. | M | MVP |
| FR-12 | An analyst can assign a final severity (Low, Medium, High, Critical). | M | MVP |
| FR-13 | An analyst can change a report's status only along the allowed workflow transitions; any other transition is rejected. | M | MVP |
| FR-14 | A report cannot be set to Confirmed without a final severity. A report set to Duplicate must reference an existing report. | M | MVP |
| FR-15 | Every status change is stored with who made it, when, the old status and the new status. This history can be read but never edited or deleted by any role. | M | MVP |
| FR-16 | An admin can reopen a report in an end state; it returns to Under Review. | S | Beta |
| FR-17 | A report in status New past its response deadline (1, 2, 5 or 10 days for Critical, High, Medium or Low) is marked overdue. | S | Beta |
| **Comments** |  |  |  |
| FR-18 | A researcher can comment on their own reports and an analyst on any report. | M | MVP |
| FR-19 | An analyst can add an internal note that only analysts can see. | M | MVP |
| FR-20 | Comments are listed oldest first. A researcher sees only non-internal comments on their own reports. | M | MVP |
| **Dashboards** |  |  |  |
| FR-21 | A researcher's dashboard shows the count of their own reports by status. | S | Beta |
| FR-22 | An analyst's dashboard shows reports awaiting triage and overdue reports. | S | Beta |
| FR-23 | An admin's dashboard shows report counts by status and severity, average time to first response, on-time rate per analyst, and reports per researcher per month. | S | Beta |
| **Access control** |  |  |  |
| FR-24 | Every protected endpoint checks the caller's scopes on the server. A missing or invalid token returns 401, and a valid token without the needed scope returns 403\. | M | Beta |
| FR-25 | The interface shows only the menus and actions the user's scopes allow. (This is a convenience; the server remains the authority.) | M | Beta |
| **Optional** |  |  |  |
| FR-26 | The system emails the researcher when the status of their report changes. | C | After Beta |
| FR-27 | The system records an audit log of logins, role changes and deletions, viewable by admins. | C | After Beta |

## **5\. Allowed Status Transitions**

| From | To | Who |
| :---: | :---: | :---: |
| New | Under Review, Rejected, Duplicate | Analyst |
| Under Review | Confirmed, Rejected, Duplicate | Analyst |
| Confirmed | Fixed | Analyst |
| Fixed | Closed | Analyst |
| Closed, Rejected, Duplicate | Under Review (reopen) | Admin |

## **6\. External Interface Requirements**

* **User interface:** a responsive web interface working from 360 px wide screens upward, with pages for login, registration, dashboard, report list, report detail, new report, user administration and profile.  
* **Software interface:** a JSON REST API under a common prefix, secured by bearer tokens, documented automatically as OpenAPI (Swagger).  
* **Data interface:** a relational database accessed only through the back end.  
* **Communications:** all traffic over HTTPS. An SMTP email service is used only if FR-26 is built.

## **7\. Non-Functional Requirements**

| ID | Category | Requirement and target | How it is verified | Release |
| :---: | :---: | :---: | :---: | :---: |
| NFR-01 | Performance | 95% of API requests complete within 2 seconds with 60 concurrent users | Load test with a free tool such as Locust | Beta |
| NFR-02 | Performance | A report submission is confirmed within 3 seconds at 60 concurrent users | Load test, submission scenario | Beta |
| NFR-03 | Availability | At least 99.5% per month, which allows at most 216 minutes of downtime in a 30-day month | Uptime monitor log | Beta |
| NFR-04 | Security | Passwords are stored only as bcrypt hashes with cost factor 12 or higher | Code review and database inspection | Beta |
| NFR-05 | Security | Every protected endpoint has at least one automated negative access test, and none lets a user read another user's report | Automated test suite result | Beta |
| NFR-06 | Security | All traffic uses HTTPS with TLS 1.2 or higher | TLS scan of the deployed server | Beta |
| NFR-07 | Security | All input is validated on the server; the OWASP Top 10 checklist shows no open high-risk item | Manual checklist review and test cases for injection and script input | MVP |
| NFR-08 | Data integrity | Status changes and their history entries are saved in one transaction, and no API can update or delete a history entry | Automated test and API review | MVP |
| NFR-09 | Usability | At least 4 of 5 test users submit a first report within 5 minutes without help | Usability test with 5 volunteers | Beta |
| NFR-10 | Compatibility | Works on the latest two versions of Chrome, Firefox and Edge, from 360 px screen width | Manual cross-browser check | Beta |
| NFR-11 | Maintainability | Back-end code passes the linter with zero errors, and automated tests cover at least 70% of the service layer | Linter and coverage report | MVP |
| NFR-12 | Documentation | 100% of API endpoints appear in the generated OpenAPI documentation with request and response examples | Review of the documentation page | MVP |

## **8\. Traceability to Verification**

Each functional requirement is covered by at least one automated API test, and Must requirements also by at least one negative test (wrong role, wrong owner, invalid input). The requirement IDs above are used in the test plan and in the technical design, so every test and every endpoint can be traced back to a requirement.