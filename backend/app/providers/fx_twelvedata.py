from __future__ import annotations

from ..config import get_settings
from ..timeutil import utcnow
from . import http
from .base import FxProvider, PriceQuote


class TwelveDataFx(FxProvider):
    """Free plan: ~800 credits/day, 8/minute, 1 credit per symbol. Paid plans: same code, raise TWELVEDATA_DAILY_CREDITS."""

    name = "twelvedata"
    requires_key = True
    supports_live = True
    cost_per_call_per_pair = 1
    URL = "https://api.twelvedata.com/price"

    def __init__(self) -> None:
        s = get_settings()
        self.key = s.twelvedata_api_key
        self.daily_credit_limit = s.twelvedata_daily_credits

    def is_configured(self) -> bool:
        return bool(self.key)

    def fetch_quotes(self, pairs: list[str]) -> list[PriceQuote]:
        r = http.get(self.URL, params={"symbol": ",".join(pairs), "apikey": self.key})
        data = r.json()
        if isinstance(data, dict) and data.get("status") == "error":
            raise RuntimeError(f"Twelve Data error {data.get('code')}: {data.get('message')}")
        if len(pairs) == 1 and "price" in data:
            data = {pairs[0]: data}
        now = utcnow()
        out: list[PriceQuote] = []
        for pair in pairs:
            row = data.get(pair)
            if not isinstance(row, dict) or "price" not in row:
                continue
            try:
                out.append(PriceQuote(pair=pair, mid=float(row["price"]), ts=now, source=self.name))
            except (TypeError, ValueError):
                continue
        if not out:
            raise RuntimeError("Twelve Data returned no usable prices")
        return out
