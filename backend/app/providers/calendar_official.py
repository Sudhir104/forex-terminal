"""Free economic calendar built from official sources:
   - US release dates from the FRED releases API (dates only, no consensus)
   - central-bank meeting dates from data/central_banks.yaml
"""
from __future__ import annotations

from datetime import date

import yaml

from ..config import BASE_DIR, get_settings
from ..constants import CURRENCIES
from . import http
from .base import CalendarProvider, EventObs

CB_PATH = BASE_DIR / "data" / "central_banks.yaml"

FRED_RELEASES = {
    "Consumer Price Index": ("US CPI", "high"),
    "Employment Situation": ("US Non-Farm Payrolls & Unemployment", "high"),
    "Gross Domestic Product": ("US GDP", "high"),
    "Advance Monthly Sales for Retail and Food Services": ("US Retail Sales", "high"),
    "Personal Income and Outlays": ("US PCE Inflation", "high"),
    "Producer Price Index": ("US PPI", "medium"),
    "Job Openings and Labor Turnover Survey": ("US JOLTS", "medium"),
    "Industrial Production and Capacity Utilization": ("US Industrial Production", "medium"),
    "Unemployment Insurance Weekly Claims Report": ("US Jobless Claims", "medium"),
}


def load_cb_yaml(path=CB_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def meetings_to_events(cfg: dict, start: date, end: date) -> list[EventObs]:
    out: list[EventObs] = []
    for ccy, row in cfg.items():
        if ccy not in CURRENCIES or not isinstance(row, dict):
            continue
        for m in row.get("meetings") or []:
            d = m if isinstance(m, date) else date.fromisoformat(str(m))
            if start <= d <= end:
                out.append(EventObs(currency=ccy, title=f"{row.get('bank', ccy)} rate decision", event_date=d,
                                    source="official", impact="high", kind="central_bank",
                                    source_url=row.get("statement_url")))
    return out


class OfficialCalendar(CalendarProvider):
    name = "official"
    requires_key = False

    def __init__(self) -> None:
        self.fred_key = get_settings().fred_api_key
        self.errors: list[str] = []

    def fetch(self, start: date, end: date) -> list[EventObs]:
        self.errors = []
        events: list[EventObs] = []
        try:
            events += meetings_to_events(load_cb_yaml(), start, end)
        except Exception as e:  # noqa: BLE001
            self.errors.append(f"central_banks.yaml: {e}")
        if self.fred_key:
            try:
                r = http.get("https://api.stlouisfed.org/fred/releases/dates", params={
                    "api_key": self.fred_key, "file_type": "json", "realtime_start": start.isoformat(),
                    "realtime_end": end.isoformat(), "include_release_dates_with_no_data": "true",
                    "order_by": "release_date", "sort_order": "asc", "limit": 1000})
                for row in r.json().get("release_dates", []):
                    title = FRED_RELEASES.get(row.get("release_name"))
                    if not title:
                        continue
                    d = date.fromisoformat(row["date"])
                    if start <= d <= end:
                        events.append(EventObs(currency="USD", title=title[0], event_date=d, source="fred",
                                               impact=title[1], source_url=f"https://fred.stlouisfed.org/releases/calendar"))
            except Exception as e:  # noqa: BLE001
                self.errors.append(f"fred release dates: {e}")
        return events
