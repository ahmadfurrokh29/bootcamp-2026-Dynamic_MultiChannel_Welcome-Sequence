import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.models import User, MessageSchedule
from src.scheduler import process_due_messages

TEST_DB = "sqlite:///./test_scheduler.db"
engine  = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestingSession()
    yield session
    session.close()


def _make_message(db, channel: str, send_at: datetime) -> MessageSchedule:
    user = User(name="Test", email=f"t_{send_at.timestamp()}@t.com", phone="0300")
    db.add(user)
    db.flush()
    msg = MessageSchedule(user_id=user.id, message_type="welcome", channel=channel, send_at=send_at, status="pending")
    db.add(msg)
    db.commit()
    return msg


def test_sends_due_messages(db):
    msg = _make_message(db, "email", datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10))
    process_due_messages(db)
    db.refresh(msg)
    assert msg.status == "sent"


def test_updates_status_to_sent(db):
    msg = _make_message(db, "sms", datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1))
    process_due_messages(db)
    db.refresh(msg)
    assert msg.status == "sent"


def test_ignores_future_messages(db):
    msg = _make_message(db, "email", datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=9999))
    process_due_messages(db)
    db.refresh(msg)
    assert msg.status == "pending"


def test_recovery_after_restart(db):
    msg    = _make_message(db, "sms", datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=5))
    msg_id = msg.id
    db.close()
    new_db = TestingSession()
    process_due_messages(new_db)
    recovered = new_db.get(MessageSchedule, msg_id)
    assert recovered.status == "sent"
    new_db.close()


def test_already_sent_not_resent(db):
    msg = _make_message(db, "email", datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10))
    process_due_messages(db)
    db.refresh(msg)
    assert msg.status == "sent"
    process_due_messages(db)
    assert msg.status == "sent"
