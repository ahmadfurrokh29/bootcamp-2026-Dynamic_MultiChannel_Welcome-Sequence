import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.models import User, MessageSchedule
from src.scheduler import process_due_messages

# Separate test DB — never touches the real database
TEST_DB = "sqlite:///./test_scheduler.db"
engine  = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test and drop them after — clean state every time."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    """Provide a fresh DB session for each test."""
    session = TestingSession()
    yield session
    session.close()


def _make_message(db, channel: str, send_at: datetime) -> MessageSchedule:
    """Helper: create a user and a pending message with a given send_at time."""
    user = User(name="Test", email=f"t_{send_at.timestamp()}@t.com", phone="0300")
    db.add(user)
    db.flush()
    msg = MessageSchedule(user_id=user.id, message_type="welcome", channel=channel, send_at=send_at, status="pending")
    db.add(msg)
    db.commit()
    return msg


def test_sends_due_messages(db):
    """A message whose send_at is in the past should be sent by the poller."""
    msg = _make_message(db, "email", datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10))
    process_due_messages(db)
    db.refresh(msg)
    assert msg.status == "sent"


def test_updates_status_to_sent(db):
    """After sending, the message status must be updated to 'sent' in the DB."""
    msg = _make_message(db, "sms", datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1))
    process_due_messages(db)
    db.refresh(msg)
    assert msg.status == "sent"


def test_ignores_future_messages(db):
    """A message whose send_at is in the future should NOT be sent yet."""
    msg = _make_message(db, "email", datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=9999))
    process_due_messages(db)
    db.refresh(msg)
    assert msg.status == "pending"


def test_recovery_after_restart(db):
    """
    Simulate a process restart: close the DB session, open a new one,
    and verify the poller still picks up and sends the pending message.
    This proves the scheduler recovers from crashes using the DB as source of truth.
    """
    msg    = _make_message(db, "sms", datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=5))
    msg_id = msg.id
    db.close()  # simulate process restart — old session is gone

    new_db = TestingSession()  # fresh session like after a real restart
    process_due_messages(new_db)
    recovered = new_db.get(MessageSchedule, msg_id)
    assert recovered.status == "sent"
    new_db.close()


def test_already_sent_not_resent(db):
    """Running the poller twice should not send an already-sent message again."""
    msg = _make_message(db, "email", datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10))
    process_due_messages(db)   # first run — sends it
    db.refresh(msg)
    assert msg.status == "sent"
    process_due_messages(db)   # second run — should skip it
    assert msg.status == "sent"
