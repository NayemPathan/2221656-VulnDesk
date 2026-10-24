"""
Phase 1 Automated Tests (backend/tests/test_phase1_db.py)
=====================================================================
WHAT THIS FILE DOES:
Verifies our Phase 1 deliverables using `pytest` and an isolated in-memory SQLite database:
1. `test_seed_database_is_idempotent`: Confirms all 4 tables are created, `seed_database()`
   inserts the 5 demo users, 4 sample reports, 4 status history rows, and 3 comments, and
   running `seed_database()` a second time does NOT duplicate any rows.
2. `test_health_endpoint_and_openapi_docs`: Uses FastAPI's `TestClient` and dependency override
   to test `GET /api/v1/health` and `GET /api/docs` without touching your real Supabase database.

WHY WE USE `app.dependency_overrides[get_session]`:
In automated tests, we never want tests to wipe or pollute our real cloud Supabase database.
Overriding `get_session` swaps in a temporary in-memory SQLite database (`sqlite://`) just
for the duration of the test!
=====================================================================
"""

from app.database import get_session
from app.main import app
from app.models import Comment, Report, StatusHistory, User
from app.seed import seed_database
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select


def _create_test_engine():
    """
    Create an isolated in-memory SQLite engine for testing.
    `StaticPool` keeps the same in-memory database alive across multiple connections in one test.
    """
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_seed_database_is_idempotent():
    """Verify that seeding populates all 4 tables and is safe to run multiple times."""
    test_engine = _create_test_engine()
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        # First run on an empty database should insert all demo records
        first_run = seed_database(session)
        assert first_run["seeded"] is True
        assert first_run["users"] == 5
        assert first_run["reports"] == 4

        # Second run on an already-seeded database must skip insertion (idempotency)
        second_run = seed_database(session)
        assert second_run["seeded"] is False

        # Query all 4 tables to verify row counts and foreign-key relationships
        users = session.exec(select(User)).all()
        reports = session.exec(select(Report)).all()
        histories = session.exec(select(StatusHistory)).all()
        comments = session.exec(select(Comment)).all()

        assert len(users) == 5
        assert len(reports) == 4
        assert len(histories) == 4
        assert len(comments) == 3

        # Verify that our rejected report includes `rejection_reason` for researcher visibility
        rejected = [r for r in reports if r.status == "rejected"]
        assert len(rejected) == 1
        assert rejected[0].rejection_reason is not None


def test_health_endpoint_and_openapi_docs():
    """Verify GET /api/v1/health returns 200 OK and /api/docs serves the Swagger UI."""
    test_engine = _create_test_engine()
    SQLModel.metadata.create_all(test_engine)

    # Override FastAPI's get_session dependency to use our in-memory test database
    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    # Test GET /api/v1/health
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "connected"

    # Test GET /api/docs (NFR-13 requirement)
    docs_response = client.get("/api/docs")
    assert docs_response.status_code == 200

    # Clean up dependency overrides after the test completes
    app.dependency_overrides.clear()
