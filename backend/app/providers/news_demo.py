from __future__ import annotations

from datetime import timedelta

from ..timeutil import utcnow
from .base import NewsObs, NewsProvider

SAMPLES = [
    ("USD", "Fed official says inflation remains elevated, sees rates staying restrictive"),
    ("EUR", "ECB policymakers signal further easing as euro area growth slows"),
    ("GBP", "Bank of England holds rates, wage growth still strong"),
    ("JPY", "Bank of Japan governor hints at gradual tightening if wages keep rising"),
    ("CHF", "SNB says inflation stays low, ready to act on franc strength"),
    ("AUD", "RBA minutes: board sees downside risks to growth, cooling labour market"),
    ("NZD", "RBNZ signals more rate cuts as economy stays in contraction"),
    ("CAD", "Bank of Canada: inflation slows, unemployment rises, cut still possible"),
]


class DemoNews(NewsProvider):
    name = "demo"
    is_demo = True

    def fetch(self, session=None) -> list[NewsObs]:
        now = utcnow()
        return [NewsObs(headline=f"[DEMO] {text}", published_at=now - timedelta(hours=3 * i + 1), source="demo",
                        source_url=f"https://example.invalid/demo/{ccy.lower()}", currency=ccy,
                        summary="Synthetic headline for DEMO_MODE.") for i, (ccy, text) in enumerate(SAMPLES)]
