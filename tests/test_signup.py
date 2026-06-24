import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, get_db
from src.main import app

TEST_DB = "sqlite:///./test_welcome.db"
engine  = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_signup_creates_user():
    r = client.post("/signup", json={"name": "Ahmad", "email": "ahmad@test.com", "phone": "03001234567"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Ahmad"
    assert data["email"] == "ahmad@test.com"
    assert "user_id" in data


def test_signup_creates_3_scheduled_messages():
    r = client.post("/signup", json={"name": "Ali", "email": "ali@test.com", "phone": "03009999999"})
    assert r.status_code == 201
    messages = r.json()["scheduled_messages"]
    assert len(messages) == 3
    assert {m["message_type"] for m in messages} == {"welcome", "sms_followup", "final_tips"}


def test_duplicate_email_returns_409():
    payload = {"name": "Sara", "email": "sara@test.com", "phone": "03001111111"}
    client.post("/signup", json=payload)
    r = client.post("/signup", json=payload)
    assert r.status_code == 409


def test_messages_are_pending_on_signup():
    r = client.post("/signup", json={"name": "Zara", "email": "zara@test.com", "phone": "03002222222"})
    for msg in r.json()["scheduled_messages"]:
        assert msg["status"] == "pending"


def test_multiple_users_have_independent_schedules():
    client.post("/signup", json={"name": "U1", "email": "u1@test.com", "phone": "0300111"})
    client.post("/signup", json={"name": "U2", "email": "u2@test.com", "phone": "0300222"})
    schedules = client.get("/schedules").json()
    assert len(schedules) == 6
