"""PAID-TIER EXAMPLE (Finnhub has a limited free tier too - check redistribution terms before showing data to friends).
Enable with NEWS_PROVIDERS=finnhub,rss and FINNHUB_API_KEY=..."""
from __future__ import annotations

from datetime import datetime, timezone

from ..config import get_settings
from . import http
from .base import NewsObs, NewsProvider


class FinnhubNews(NewsProvider):
    name = "finnhub"
    requires_key = True
    URL = "https://finnhub.io/api/v1/news"

    def __init__(self) -> None:
        self.key = get_settings().finnhub_api_key

    def is_configured(self) -> bool:
        return bool(self.key)

    def fetch(self, session=None) -> list[NewsObs]:
        r = http.get(self.URL, params={"category": "forex", "token": self.key})
        out = []
        for a in r.json():
            try:
                out.append(NewsObs(headline=a["headline"], summary=a.get("summary") or None, source=a.get("source") or "finnhub",
                                   source_url=a["url"], currency=None,
                                   published_at=datetime.fromtimestamp(a["datetime"], tz=timezone.utc)))
            except (KeyError, TypeError, ValueError):
                continue
        return out
