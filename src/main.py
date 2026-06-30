import threading
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from src.config import SMS_DELAY, TIP_DELAY
from src.database import get_db, init_db
from src.models import User, MessageSchedule
from src.schemas import SignupRequest, SignupResponse, ScheduledMessageOut
from src.scheduler import run_poller, process_due_messages, simulate_crash_message, _now
from src.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once when the app starts.
    Creates DB tables and starts the background scheduler thread.
    """
    init_db()
    thread = threading.Thread(target=run_poller, daemon=True)  # daemon=True means it stops when the main process stops
    thread.start()
    logger.info("Background poller thread started")
    yield  # app runs here


app = FastAPI(
    title="Dynamic Multi-Channel Welcome Sequence",
    description="Sends welcome email → SMS → tips on a persisted schedule",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/signup", response_model=SignupResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """Register a new user and schedule 3 messages: welcome email, SMS follow-up, and final tips."""
    # Reject duplicate emails
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create the user record
    user = User(name=payload.name, email=payload.email, phone=payload.phone)
    db.add(user)
    db.flush()  # get the user.id without committing yet

    # Schedule 3 messages with delays based on config
    now = _now()
    schedules = [
        MessageSchedule(user_id=user.id, message_type="welcome",      channel="email", send_at=now),
        MessageSchedule(user_id=user.id, message_type="sms_followup", channel="sms",   send_at=now + timedelta(seconds=SMS_DELAY)),
        MessageSchedule(user_id=user.id, message_type="final_tips",   channel="sms",   send_at=now + timedelta(seconds=SMS_DELAY + TIP_DELAY)),
    ]
    db.add_all(schedules)
    db.commit()
    db.refresh(user)

    logger.info(f"SIGNUP | User: {user.name} | Email: {user.email}")

    return SignupResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        scheduled_messages=[ScheduledMessageOut.model_validate(s) for s in schedules],
    )


@app.get("/users", summary="List all registered users")
def list_users(db: Session = Depends(get_db)):
    """Return all users in the database."""
    return [
        {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "created_at": u.created_at}
        for u in db.query(User).all()
    ]


@app.get("/schedules", summary="List all message schedules")
def list_schedules(db: Session = Depends(get_db)):
    """Return all scheduled messages including sent_at for drift calculation."""
    return [
        {
            "id":           r.id,
            "user_id":      r.user_id,
            "message_type": r.message_type,
            "channel":      r.channel,
            "send_at":      r.send_at,
            "sent_at":      r.sent_at,   # None if not yet sent; used to calculate drift in the UI
            "status":       r.status,
        }
        for r in db.query(MessageSchedule).all()
    ]


@app.delete("/users/{user_id}", status_code=204, summary="Delete user and all their scheduled messages")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user. Their scheduled messages are automatically deleted via cascade."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    logger.info(f"DELETE | User ID: {user_id} | Name: {user.name}")


@app.post("/simulate-crash/{message_id}", summary="Failure Mode 1: crash after send, before status update")
def simulate_crash(message_id: int, db: Session = Depends(get_db)):
    """
    Demo endpoint for the duplicate-send failure mode.
    Sends the message but does NOT update status to 'sent'.
    When the backend restarts, the poller will find it still pending and send it again.
    """
    result = simulate_crash_message(db, message_id)
    if result == "crashed":
        return {"detail": "Simulated crash for failure mode demo"}
    if result == "already_sent":
        return {"detail": "Message already sent — pick a pending one"}
    return {"detail": "Message not found"}
