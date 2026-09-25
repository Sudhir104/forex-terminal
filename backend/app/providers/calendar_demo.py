from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from ..timeutil import utcnow
from .base import CalendarProvider, EventObs


class DemoCalendar(CalendarProvider):
    name = "demo"
    is_demo = True

    def fetch(self, start: date, end: date) -> list[EventObs]:
        base = utcnow().replace(minute=0, second=0, microsecond=0)
        rows = [("USD", "US CPI (demo)", "high", 3, "3.3%", "3.4%"), ("EUR", "ECB rate decision (demo)", "high", 27, None, "2.25%"),
                ("CAD", "Canada retail sales (demo)", "medium", 30, "0.3%", "0.1%"), ("GBP", "UK employment data (demo)", "medium", 52, None, "4.3%"),
                ("AUD", "RBA minutes (demo)", "medium", 75, None, None), ("USD", "Fed speaker (demo)", "low", 8, None, None)]
        out = []
        for ccy, title, impact, hrs, fc, prev in rows:
            when = base + timedelta(hours=hrs)
            out.append(EventObs(currency=ccy, title=title, event_date=when.date(), event_time=when, impact=impact,
                                forecast=fc, previous=prev, source="demo"))
        return out
