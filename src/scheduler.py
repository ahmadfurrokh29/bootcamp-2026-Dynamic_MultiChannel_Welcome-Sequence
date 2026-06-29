import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.config import POLL_INTERVAL
from src.database import SessionLocal
from src.models import MessageSchedule, User
from src.senders import send_email, send_sms
from src.logger import logger


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def process_due_messages(db: Session, simulate_crash_after_id: int | None = None) -> None:
    now = _now()
    due = (
        db.query(MessageSchedule)
        .filter(MessageSchedule.status == "pending", MessageSchedule.send_at <= now)
        .all()
    )

    for msg in due:
        user: User = msg.user
        due_time  = msg.send_at
        sent_time = _now()
        drift     = (sent_time - due_time).total_seconds()

        if msg.channel == "email":
            send_email(user.name, user.email, msg.message_type)
        else:
            send_sms(user.name, user.phone, msg.message_type)

        logger.info(
            f"DRIFT | ID: {msg.id} | Due: {due_time} | Sent: {sent_time} | Drift: {drift:.2f}s"
        )

        # Failure mode 1: crash before marking sent → duplicate on restart
        if simulate_crash_after_id and msg.id == simulate_crash_after_id:
            logger.warning(f"CRASH SIMULATED after msg ID {msg.id} — status NOT updated")
            raise SystemExit("Simulated crash for failure mode demo")

        msg.status  = "sent"
        msg.sent_at = sent_time
        db.commit()


def simulate_crash_message(db: Session, message_id: int) -> str:
    msg = db.get(MessageSchedule, message_id)
    if not msg:
        return "not_found"
    if msg.status == "sent":
        return "already_sent"

    user: User = msg.user
    if msg.channel == "email":
        send_email(user.name, user.email, msg.message_type)
    else:
        send_sms(user.name, user.phone, msg.message_type)

    logger.warning(f"CRASH SIMULATED after msg ID {msg.id} — status NOT updated")
    return "crashed"


def run_poller() -> None:
    logger.info("Scheduler started — recovering pending messages from DB")
    while True:
        db = SessionLocal()
        try:
            process_due_messages(db)
        except Exception as exc:
            logger.error(f"Poller error: {exc}")
        finally:
            db.close()
        time.sleep(POLL_INTERVAL)
