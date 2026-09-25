from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import EventOut
from ..services.auth import current_user
from ..services.repo import upcoming_events
from ..timeutil import utcnow

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("", response_model=list[EventOut])
def list_events(currency: str | None = Query(default=None), days_back: int = Query(default=2, le=30),
                days_forward: int = Query(default=21, le=90), session: Session = Depends(get_db),
                _=Depends(current_user)):
    today = utcnow().date()
    rows = upcoming_events(session, today - timedelta(days=days_back), today + timedelta(days=days_forward),
                           currency.upper() if currency else None)
    return [EventOut(id=e.id, currency=e.currency, title=e.title, event_date=e.event_date, event_time=e.event_time,
                     impact=e.impact, kind=e.kind, actual=e.actual, forecast=e.forecast, previous=e.previous,
                     source=e.source, source_url=e.source_url) for e in rows]
