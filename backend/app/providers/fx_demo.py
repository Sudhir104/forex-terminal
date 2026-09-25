from __future__ import annotations

import math

from ..timeutil import utcnow
from .base import FxProvider, PriceQuote

# Synthetic levels for DEMO_MODE only - not real market prices.
BASE = {"EUR/USD": 1.085, "GBP/USD": 1.27, "AUD/USD": 0.66, "NZD/USD": 0.61,
        "USD/JPY": 150.0, "USD/CHF": 0.88, "USD/CAD": 1.36}


class DemoFx(FxProvider):
    name = "demo"
    is_demo = True

    def fetch_quotes(self, pairs: list[str]) -> list[PriceQuote]:
        now = utcnow()
        minutes = now.timestamp() / 60
        out = []
        for i, pair in enumerate(pairs):
            base = BASE.get(pair)
            if base is None:
                continue
            wobble = 1 + 0.004 * math.sin(minutes / 37 + i) + 0.0015 * math.sin(minutes / 5 + i * 2)
            mid = base * wobble
            spread = mid * 0.00008
            out.append(PriceQuote(pair=pair, mid=mid, bid=mid - spread, ask=mid + spread, ts=now, source=self.name))
        return out
