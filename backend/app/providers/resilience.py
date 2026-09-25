"""Quota tracking, circuit breaker and guarded provider calls (this is what keeps the free tier alive)."""
from __future__ import annotations

from datetime import timedelta
from typing import Callable, TypeVar

from sqlalchemy.orm import Session

from ..models import ProviderHealth, QuotaUsage
from ..timeutil import as_utc, seconds_left_today, today_utc, utcnow

T = TypeVar("T")

FAILURE_THRESHOLD = 3
MAX_OPEN_SECONDS = 3600
QUOTA_SAFETY = 0.92  # never plan to spend more than 92% of a metered daily allowance


class ProviderUnavailable(Exception):
    pass


class QuotaExceeded(Exception):
    pass


def _health(session: Session, name: str) -> ProviderHealth:
    h = session.get(ProviderHealth, name)
    if h is None:
        h = ProviderHealth(provider=name, failures=0)
        session.add(h)
        session.flush()
    return h


def breaker_open(session: Session, name: str) -> bool:
    h = session.get(ProviderHealth, name)
    if h is None or h.open_until is None:
        return False
    return as_utc(h.open_until) > utcnow()


def record_success(session: Session, name: str) -> None:
    h = _health(session, name)
    h.failures = 0
    h.open_until = None
    h.last_success = utcnow()
    session.commit()


def record_failure(session: Session, name: str, err: Exception) -> None:
    h = _health(session, name)
    h.failures = (h.failures or 0) + 1
    h.last_error = f"{type(err).__name__}: {err}"[:300]
    h.last_error_at = utcnow()
    if h.failures >= FAILURE_THRESHOLD:
        wait = min(60 * (2 ** (h.failures - FAILURE_THRESHOLD)), MAX_OPEN_SECONDS)
        h.open_until = utcnow() + timedelta(seconds=wait)
    session.commit()


def quota_used(session: Session, name: str) -> int:
    row = session.get(QuotaUsage, (name, today_utc()))
    return row.used if row else 0


def add_usage(session: Session, name: str, cost: int) -> None:
    day = today_utc()
    row = session.get(QuotaUsage, (name, day))
    if row is None:
        row = QuotaUsage(provider=name, day=day, used=0)
        session.add(row)
    row.used = (row.used or 0) + cost
    session.commit()


def quota_remaining(session: Session, name: str, limit: int | None) -> int | None:
    if limit is None:
        return None
    return max(0, int(limit * QUOTA_SAFETY) - quota_used(session, name))


def quota_aware_interval(session: Session, name: str, limit: int | None, cost_per_call: int, desired: float) -> float:
    """Smallest polling interval that still lets the remaining credits last until midnight UTC."""
    remaining = quota_remaining(session, name, limit)
    if remaining is None:
        return desired
    if remaining < cost_per_call:
        return seconds_left_today()
    needed = cost_per_call * seconds_left_today() / remaining
    return max(desired, needed)


def guarded_call(session: Session, provider, fn: Callable[[], T], cost: int = 0) -> T:
    name = provider.name
    if breaker_open(session, name):
        raise ProviderUnavailable(f"{name}: circuit open after repeated failures")
    remaining = quota_remaining(session, name, getattr(provider, "daily_credit_limit", None))
    if remaining is not None and cost > remaining:
        raise QuotaExceeded(f"{name}: daily credit budget used up ({cost} needed, {remaining} left)")
    if cost:
        add_usage(session, name, cost)
    try:
        result = fn()
    except Exception as e:  # noqa: BLE001 - we record and re-raise
        record_failure(session, name, e)
        raise
    record_success(session, name)
    return result
