from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; treat them as UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def seconds_left_today(now: datetime | None = None) -> float:
    now = now or utcnow()
    end = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(60.0, (end - now).total_seconds())


def today_utc() -> date:
    return utcnow().date()


def age_days(d: date | datetime | None, now: datetime | None = None) -> float | None:
    if d is None:
        return None
    now = now or utcnow()
    if isinstance(d, datetime):
        return (now - as_utc(d)).total_seconds() / 86400
    return (now.date() - d).days
