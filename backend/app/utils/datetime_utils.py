from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def to_naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)






