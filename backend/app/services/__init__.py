"""
Business Logic Services Package (backend/app/services/__init__.py)
=====================================================================
WHY THIS PACKAGE EXISTS (TDD Section 2 Design Rule):
"Routers only deal with HTTP; every business rule (submission policy, status transitions,
ownership, deadlines, statistics) lives in the service layer, so it can be tested without
HTTP and changed in one place."
=====================================================================
"""