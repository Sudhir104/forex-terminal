"""PAID-TIER EXAMPLE: Trading Economics calendar with consensus forecasts (this is what unlocks true 'surprise' scoring).
Enable with CALENDAR_PROVIDERS=tradingeconomics,official and TRADINGECONOMICS_API_KEY=..."""
from __future__ import annotations

from datetime import date, datetime, timezone

from ..config import get_settings
from ..constants import CURRENCIES
from . import http
from .base import CalendarProvider, EventObs

IMPACT = {1: "low", 2: "medium", 3: "high"}


class TradingEconomicsCalendar(CalendarProvider):
    name = "tradingeconomics"
    requires_key = True

    def __init__(self) -> None:
        self.key = get_settings().tradingeconomics_api_key

    def is_configured(self) -> bool:
        return bool(self.key)

    def fetch(self, start: date, end: date) -> list[EventObs]:
        url = f"https://api.tradingeconomics.com/calendar/country/all/{start.isoformat()}/{end.isoformat()}"
        r = http.get(url, params={"c": self.key, "f": "json"})
        out: list[EventObs] = []
        for row in r.json():
            ccy = (row.get("Currency") or "").upper()
            if ccy not in CURRENCIES:
                continue
            try:
                when = datetime.fromisoformat(row["Date"]).replace(tzinfo=timezone.utc)
            except (KeyError, ValueError):
                continue
            out.append(EventObs(currency=ccy, title=row.get("Event") or row.get("Category") or "Event",
                                event_date=when.date(), event_time=when, impact=IMPACT.get(row.get("Importance"), "medium"),
                                actual=(row.get("Actual") or None), forecast=(row.get("Forecast") or row.get("TEForecast") or None),
                                previous=(row.get("Previous") or None), source=self.name,
                                source_url=row.get("SourceURL") or None))
        return out
