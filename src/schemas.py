from datetime import datetime
from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    """Data the client sends when signing up a new user."""
    name:  str
    email: EmailStr  # validated — must be a proper email format
    phone: str


class ScheduledMessageOut(BaseModel):
    """A single scheduled message returned in API responses."""
    id:           int
    message_type: str           # welcome | sms_followup | final_tips
    channel:      str           # email | sms
    send_at:      datetime      # when the message is scheduled to be sent
    sent_at:      datetime | None = None  # actual send time (None if not sent yet)
    status:       str           # pending | sent

    # Allow Pydantic to read values directly from SQLAlchemy ORM objects
    model_config = {"from_attributes": True}


class SignupResponse(BaseModel):
    """Response returned after a successful signup."""
    user_id:            int
    name:               str
    email:              str
    scheduled_messages: list[ScheduledMessageOut]  # the 3 messages that were scheduled
