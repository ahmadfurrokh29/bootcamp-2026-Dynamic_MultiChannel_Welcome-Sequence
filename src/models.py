from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class User(Base):
    __tablename__ = "users"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    name:       Mapped[str]      = mapped_column(String,  nullable=False)
    email:      Mapped[str]      = mapped_column(String,  unique=True, nullable=False)
    phone:      Mapped[str]      = mapped_column(String,  nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    schedules: Mapped[list["MessageSchedule"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class MessageSchedule(Base):
    __tablename__ = "message_schedules"

    id:           Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    user_id:      Mapped[int]      = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    message_type: Mapped[str]      = mapped_column(String,  nullable=False)  # welcome / sms_followup / final_tips
    channel:      Mapped[str]      = mapped_column(String,  nullable=False)  # email / sms
    send_at:      Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status:       Mapped[str]              = mapped_column(String,  default="pending")  # pending / sent
    sent_at:      Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at:   Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="schedules")
