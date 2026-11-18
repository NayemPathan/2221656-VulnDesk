"""
Phase 6 Automated Tests: Argon2id Hashing, RefreshToken & Tutor Seed
=====================================================================
Verifies:
1. Argon2id password hashing and verification (`hash_password`, `verify_password`).
2. `seed_database` creates 6 users (including `tutor@vulndesk.local`) with valid Argon2id hashes.
3. Backfill path safely populates `password_hash` and `tutor@vulndesk.local` on an existing MVP DB.
4. `RefreshToken` rows cascade-delete when their parent `User` is deleted.
=====================================================================
"""

from datetime import UTC, datetime, timedelta

from app.models import RefreshToken, User, UserRole
from app.security import (
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.seed import DEFAULT_DEMO_PASSWORD, TUTOR_DEFAULT_PASSWORD, seed_database
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select


def _create_fk_sqlite_engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


def test_argon2id_password_and_token_hashing():
    """Verify Argon2id hashing + verification and SHA-256 token hashing."""
    hashed = hash_password("MySecurePass123!")
    assert hashed.startswith("$argon2id$")
    assert verify_password("MySecurePass123!", hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("Anything", None) is False

    raw = generate_refresh_token()
    digest = hash_token(raw)
    assert len(digest) == 64
    assert digest == hash_token(raw)


def test_seed_creates_tutor_and_backfills_existing_mvp_users():
    """Verify both fresh seeding and idempotent backfill of existing MVP users."""
    eng = _create_fk_sqlite_engine()
    SQLModel.metadata.create_all(eng)

    # 1. Fresh DB seed
    with Session(eng) as session:
        res1 = seed_database(session)
        assert res1["seeded"] is True
        assert res1["users"] == 6

        tutor = session.exec(select(User).where(User.email == "tutor@vulndesk.local")).first()
        alice = session.exec(select(User).where(User.email == "alice@vulndesk.local")).first()
        assert tutor is not None and tutor.role == UserRole.ADMIN.value
        assert verify_password(TUTOR_DEFAULT_PASSWORD, tutor.password_hash) is True
        assert alice is not None
        assert verify_password(DEFAULT_DEMO_PASSWORD, alice.password_hash) is True

    # 2. Simulate an existing MVP database where password_hash is NULL and tutor doesn't exist
    eng2 = _create_fk_sqlite_engine()
    SQLModel.metadata.create_all(eng2)
    with Session(eng2) as session:
        legacy_alice = User(
            name="Alice Rahman (Researcher)",
            email="alice@vulndesk.local",
            role=UserRole.RESEARCHER.value,
            password_hash=None,
        )
        session.add(legacy_alice)
        session.commit()

        backfill = seed_database(session)
        assert backfill["seeded"] is False
        assert backfill["passwords_backfilled"] == 1
        assert backfill["tutor_created"] is True

        refreshed_alice = session.exec(
            select(User).where(User.email == "alice@vulndesk.local")
        ).first()
        assert refreshed_alice is not None
        assert verify_password(DEFAULT_DEMO_PASSWORD, refreshed_alice.password_hash) is True


def test_refresh_token_cascade_delete():
    """Verify RefreshToken rows are deleted when the owning User is deleted."""
    eng = _create_fk_sqlite_engine()
    SQLModel.metadata.create_all(eng)

    with Session(eng) as session:
        user = User(
            name="Temp User",
            email="temp@vulndesk.local",
            role=UserRole.RESEARCHER.value,
            password_hash=hash_password("TempPass123!"),
        )
        session.add(user)
        session.flush()
        assert user.id is not None

        rt = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(generate_refresh_token()),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session.add(rt)
        session.commit()

        assert len(session.exec(select(RefreshToken)).all()) == 1
        session.delete(user)
        session.commit()
        assert len(session.exec(select(RefreshToken)).all()) == 0