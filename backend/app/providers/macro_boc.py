"""Bank of Canada Valet API (no key). Policy rate, 2Y/10Y yields, CPI (index -> y/y)."""
from __future__ import annotations

from datetime import date

from . import http
from .base import IndicatorObs, MacroBundle, MacroProvider, RateObs, YieldObs

BASE = "https://www.bankofcanada.ca/valet/observations"
RATE = "V39079"
YIELDS = {"2Y": "BD.CDN.2YR.DQ.YLD", "10Y": "BD.CDN.10YR.DQ.YLD"}
CPI_INDEX = "V41690973"


def parse_valet(data: dict, series: str) -> list[tuple[date, float]]:
    out = []
    for o in data.get("observations", []):
        try:
            out.append((date.fromisoformat(o["d"]), float(o[series]["v"])))
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(out)


class BocMacro(MacroProvider):
    name = "boc"
    requires_key = False
    covers = ("CAD",)

    def _get(self, series: str, recent: int) -> list[tuple[date, float]]:
        r = http.get(f"{BASE}/{series}/json", params={"recent": recent})
        return parse_valet(r.json(), series)

    @staticmethod
    def _url(series: str) -> str:
        return f"https://www.bankofcanada.ca/valet/observations/{series}/json"

    def fetch(self, currencies: list[str], scope: str = "all") -> MacroBundle:
        b = MacroBundle()
        if "CAD" not in currencies:
            return b
        try:
            last = None
            for d, v in self._get(RATE, 500):
                if last is None or abs(v - last) > 1e-9:
                    b.rates.append(RateObs("CAD", "Bank of Canada", v, d, self.name, self._url(RATE)))
                    last = v
        except Exception as e:  # noqa: BLE001
            b.errors.append(f"boc rate: {e}")
        for mat, s in YIELDS.items():
            try:
                rows = self._get(s, 5)
                if rows:
                    d, v = rows[-1]
                    b.yields.append(YieldObs("CAD", mat, v, d, self.name, self._url(s)))
            except Exception as e:  # noqa: BLE001
                b.errors.append(f"boc yield {mat}: {e}")
        if scope == "all":
            try:
                rows = self._get(CPI_INDEX, 15)
                if len(rows) >= 13:
                    vals = [v for _, v in reversed(rows)]  # newest first
                    yoy = (vals[0] / vals[12] - 1) * 100
                    prev = (vals[1] / vals[13] - 1) * 100 if len(vals) > 13 else None
                    b.indicators.append(IndicatorObs("CAD", "cpi_yoy", rows[-1][0], round(yoy, 3), self.name,
                                                     self._url(CPI_INDEX),
                                                     previous=None if prev is None else round(prev, 3)))
            except Exception as e:  # noqa: BLE001
                b.errors.append(f"boc cpi: {e}")
        return b
