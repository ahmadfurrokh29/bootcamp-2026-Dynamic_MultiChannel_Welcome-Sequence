from datetime import datetime
from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    name:  str
    email: EmailStr
    phone: str


class ScheduledMessageOut(BaseModel):
    id:           int
    message_type: str
    channel:      str
    send_at:      datetime
    status:       str

    model_config = {"from_attributes": True}


class SignupResponse(BaseModel):
    user_id:            int
    name:               str
    email:              str
    scheduled_messages: list[ScheduledMessageOut]
