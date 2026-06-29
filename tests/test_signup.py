import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, get_db
from src.main import app

# Use a separate test database so real data is never affected
TEST_DB = "sqlite:///./test_welcome.db"
engine  = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Replace the real DB session with a test DB session during tests."""
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test and drop them after — ensures a clean slate."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# Tell FastAPI to use the test DB instead of the real one
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_signup_creates_user():
    """A valid signup should return 201 with correct user data."""
    r = client.post("/signup", json={"name": "Ahmad", "email": "ahmad@test.com", "phone": "03001234567"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Ahmad"
    assert data["email"] == "ahmad@test.com"
    assert "user_id" in data


def test_signup_creates_3_scheduled_messages():
    """Signup should always create exactly 3 messages: welcome, sms_followup, final_tips."""
    r = client.post("/signup", json={"name": "Ali", "email": "ali@test.com", "phone": "03009999999"})
    assert r.status_code == 201
    messages = r.json()["scheduled_messages"]
    assert len(messages) == 3
    assert {m["message_type"] for m in messages} == {"welcome", "sms_followup", "final_tips"}


def test_duplicate_email_returns_409():
    """Signing up with an already-registered email should be rejected with 409 Conflict."""
    payload = {"name": "Sara", "email": "sara@test.com", "phone": "03001111111"}
    client.post("/signup", json=payload)       # first signup — OK
    r = client.post("/signup", json=payload)   # duplicate — should fail
    assert r.status_code == 409


def test_messages_are_pending_on_signup():
    """All 3 messages should be in 'pending' status right after signup (none sent yet)."""
    r = client.post("/signup", json={"name": "Zara", "email": "zara@test.com", "phone": "03002222222"})
    for msg in r.json()["scheduled_messages"]:
        assert msg["status"] == "pending"


def test_multiple_users_have_independent_schedules():
    """Each user gets their own 3 messages — 2 users = 6 total schedules."""
    client.post("/signup", json={"name": "U1", "email": "u1@test.com", "phone": "0300111"})
    client.post("/signup", json={"name": "U2", "email": "u2@test.com", "phone": "0300222"})
    schedules = client.get("/schedules").json()
    assert len(schedules) == 6


def test_delete_user_removes_user_and_schedules():
    """Deleting a user should also delete all their scheduled messages (cascade delete)."""
    r = client.post("/signup", json={"name": "ToDelete", "email": "delete@test.com", "phone": "03005555555"})
    user_id = r.json()["user_id"]

    # confirm user and 3 schedules exist
    assert len(client.get("/schedules").json()) == 3
    assert len(client.get("/users").json()) == 1

    # delete the user
    d = client.delete(f"/users/{user_id}")
    assert d.status_code == 204

    # both user and their schedules should be gone
    assert len(client.get("/users").json()) == 0
    assert len(client.get("/schedules").json()) == 0


def test_delete_nonexistent_user_returns_404():
    """Deleting a user ID that does not exist should return 404 Not Found."""
    r = client.delete("/users/99999")
    assert r.status_code == 404
