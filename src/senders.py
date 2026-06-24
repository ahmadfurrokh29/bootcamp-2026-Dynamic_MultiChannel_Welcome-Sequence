from datetime import datetime, timezone
from src.logger import logger


def send_email(user_name: str, email: str, message_type: str) -> None:
    _log("EMAIL", user_name, email, message_type)


def send_sms(user_name: str, phone: str, message_type: str) -> None:
    _log("SMS", user_name, phone, message_type)


def _log(channel: str, user_name: str, contact: str, message_type: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"{channel} SENT | User: {user_name} | To: {contact} | Type: {message_type} | Time: {now}")
