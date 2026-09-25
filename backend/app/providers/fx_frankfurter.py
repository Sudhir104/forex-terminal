from __future__ import annotations

from datetime import date, datetime, time, timezone

from . import http
from .base import FxProvider, PriceQuote

ECB_CCY = ["EUR", "GBP", "AUD", "NZD", "JPY", "CHF", "CAD"]


class FrankfurterFx(FxProvider):
    """ECB reference rates (once per working day). Free, no key. A fallback / history source, NOT a live feed."""

    name = "frankfurter"
    requires_key = False
    supports_live = False
    BASE = "https://api.frankfurter.dev/v1"

    def _to_quotes(self, day: str, rates: dict[str, float], wanted: list[str]) -> list[PriceQuote]:
        d = date.fromisoformat(day)
        ts = datetime.combine(d, time(15, 0), tzinfo=timezone.utc)  # ECB publishes around 16:00 CET
        out: list[PriceQuote] = []
        for pair in wanted:
            base, quote = pair.split("/")
            if base == "USD" and quote in rates:
                mid = float(rates[quote])
            elif quote == "USD" and base in rates and float(rates[base]) != 0:
                mid = 1.0 / float(rates[base])
            else:
                continue
            out.append(PriceQuote(pair=pair, mid=mid, ts=ts, source=self.name, is_reference=True))
        return out

    def fetch_quotes(self, pairs: list[str]) -> list[PriceQuote]:
        r = http.get(f"{self.BASE}/latest", params={"base": "USD", "symbols": ",".join(ECB_CCY)})
        data = r.json()
        quotes = self._to_quotes(data["date"], data["rates"], pairs)
        if not quotes:
            raise RuntimeError("Frankfurter returned no usable rates")
        return quotes

    def fetch_history(self, start: date, end: date, pairs: list[str]) -> list[PriceQuote]:
        r = http.get(f"{self.BASE}/{start.isoformat()}..{end.isoformat()}",
                     params={"base": "USD", "symbols": ",".join(ECB_CCY)})
        data = r.json()
        out: list[PriceQuote] = []
        for day, rates in sorted(data.get("rates", {}).items()):
            out += self._to_quotes(day, rates, pairs)
        return out
