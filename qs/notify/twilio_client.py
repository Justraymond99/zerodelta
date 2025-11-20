from __future__ import annotations

from typing import Optional, List
from dataclasses import dataclass

try:
    from twilio.rest import Client
    HAS_TWILIO = True
except ImportError:
    HAS_TWILIO = False
    Client = None

from qs.config import get_settings


@dataclass
class TwilioSettings:
    account_sid: Optional[str]
    auth_token: Optional[str]
    from_number: Optional[str]


def get_twilio_settings() -> TwilioSettings:
    s = get_settings()
    # We keep Twilio credentials in env variables directly (not in pydantic Settings for now)
    import os
    return TwilioSettings(
        account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        from_number=os.getenv("TWILIO_FROM"),
    )


def get_allowed_numbers() -> List[str]:
    """Get list of allowed phone numbers from environment variable."""
    import os
    numbers = os.getenv("TWILIO_ALLOWED_NUMBERS", "")
    return [n.strip() for n in numbers.split(',') if n.strip()]


def send_sms(to_number: str, body: str) -> bool:
    cfg = get_twilio_settings()
    if not (cfg.account_sid and cfg.auth_token and cfg.from_number):
        return False
    try:
        client = Client(cfg.account_sid, cfg.auth_token)
        client.messages.create(to=to_number, from_=cfg.from_number, body=body)
        return True
    except Exception:
        return False


def send_sms_update(body: str) -> int:
    """
    Send SMS update to all allowed numbers.
    Returns the number of successful sends.
    """
    numbers = get_allowed_numbers()
    if not numbers:
        return 0
    success_count = 0
    for number in numbers:
        if send_sms(number, body):
            success_count += 1
    return success_count