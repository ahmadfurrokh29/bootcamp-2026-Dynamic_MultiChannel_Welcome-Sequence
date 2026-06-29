from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


def _utcnow() -> datetime:
    """Return current UTC time without timezone info (SQLite stores naive datetimes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    """Represents a registered user in the system."""
    __tablename__ = "users"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    name:       Mapped[str]      = mapped_column(String,  nullable=False)
    email:      Mapped[str]      = mapped_column(String,  unique=True, nullable=False)
    phone:      Mapped[str]      = mapped_column(String,  nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    # One user has many scheduled messages; deleting a user deletes all their messages
    schedules: Mapped[list["MessageSchedule"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class MessageSchedule(Base):
    """Represents a single scheduled message (email or SMS) for a user."""
    __tablename__ = "message_schedules"

    id:           Mapped[int]            = mapped_column(Integer, primary_key=True, index=True)
    user_id:      Mapped[int]            = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    message_type: Mapped[str]            = mapped_column(String,  nullable=False)  # welcome | sms_followup | final_tips
    channel:      Mapped[str]            = mapped_column(String,  nullable=False)  # email | sms
    send_at:      Mapped[datetime]       = mapped_column(DateTime, nullable=False)  # when it should be sent
    status:       Mapped[str]            = mapped_column(String,  default="pending")  # pending | sent
    sent_at:      Mapped[datetime | None] = mapped_column(DateTime, nullable=True)   # actual send time (for drift calculation)
    created_at:   Mapped[datetime]       = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="schedules")
