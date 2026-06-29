import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.config import POLL_INTERVAL
from src.database import SessionLocal
from src.models import MessageSchedule, User
from src.senders import send_email, send_sms
from src.logger import logger


def _now() -> datetime:
    """Return current UTC time without timezone info (matches how SQLite stores datetimes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def process_due_messages(db: Session) -> None:
    """Find all pending messages that are due and send them."""
    now = _now()

    # Query only messages that are still pending AND whose scheduled time has passed
    due = (
        db.query(MessageSchedule)
        .filter(MessageSchedule.status == "pending", MessageSchedule.send_at <= now)
        .all()
    )

    for msg in due:
        user: User = msg.user
        due_time  = msg.send_at
        sent_time = _now()

        # Send via the appropriate channel
        if msg.channel == "email":
            send_email(user.name, user.email, msg.message_type)
        else:
            send_sms(user.name, user.phone, msg.message_type)

        # Drift = how many seconds late the message was sent vs its scheduled time
        drift = (sent_time - due_time).total_seconds()
        logger.info(f"DRIFT | ID: {msg.id} | Due: {due_time} | Sent: {sent_time} | Drift: {drift:.2f}s")

        # Mark the message as sent and record the actual send time
        msg.status  = "sent"
        msg.sent_at = sent_time
        db.commit()


def simulate_crash_message(db: Session, message_id: int) -> str:
    """
    Failure Mode Demo: send a message but skip marking it as sent.
    This simulates a process crash between the send and the DB update.
    On the next restart, the poller will find it still pending and send it again (duplicate).
    """
    msg = db.get(MessageSchedule, message_id)
    if not msg:
        return "not_found"
    if msg.status == "sent":
        return "already_sent"

    user: User = msg.user

    # Send the message (this would be the real SMS/email in production)
    if msg.channel == "email":
        send_email(user.name, user.email, msg.message_type)
    else:
        send_sms(user.name, user.phone, msg.message_type)

    # Intentionally skip: msg.status = "sent"
    # This leaves the message as "pending" in the DB — simulating a crash
    logger.warning(f"CRASH SIMULATED after msg ID {msg.id} — status NOT updated")
    return "crashed"


def run_poller() -> None:
    """
    Background thread that runs forever.
    Every POLL_INTERVAL seconds it checks the DB for due messages and sends them.
    On startup it automatically picks up any messages that were pending before a restart.
    """
    logger.info("Scheduler started — recovering pending messages from DB")
    while True:
        db = SessionLocal()
        try:
            process_due_messages(db)
        except Exception as exc:
            # Log the error but keep the poller running — do not crash the app
            logger.error(f"Poller error: {exc}")
        finally:
            db.close()
        time.sleep(POLL_INTERVAL)
