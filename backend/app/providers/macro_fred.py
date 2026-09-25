"""FRED (St. Louis Fed). Free API key: https://fred.stlouisfed.org/docs/api/api_key.html

US series are first-class. Other currencies use OECD-derived FRED series, which can lag by months
(or be discontinued) - `python -m app.cli doctor` reports staleness so you know what to replace.
Series ids live in FRED_MAP so fixing one is a one-line change.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from ..config import get_settings
from ..constants import CURRENCY_META
from . import http
from .base import IndicatorObs, MacroBundle, MacroProvider, RateObs, YieldObs

# (series_id, transform, lag) - transform: level | yoy | diff
FRED_MAP: dict[str, dict] = {
    "USD": {
        "indicators": {
            "cpi_yoy": ("CPIAUCSL", "yoy", 12),
            "core_cpi_yoy": ("CPILFESL", "yoy", 12),
            "unemployment": ("UNRATE", "level", 1),
            "gdp_yoy": ("GDPC1", "yoy", 4),
            "retail_sales_yoy": ("RSAFS", "yoy", 12),
            "nfp_change": ("PAYEMS", "diff", 1),
        },
        "rate": "DFEDTARU",
        "yields": {"2Y": "DGS2", "10Y": "DGS10"},
    },
    "EUR": {
        "indicators": {
            "cpi_yoy": ("CP0000EZ19M086NEST", "yoy", 12),
            "unemployment": ("LRHUTTTTEZM156S", "level", 1),
            "gdp_yoy": ("CLVMNACSCAB1GQEA19", "yoy", 4),
        },
        "rate": "ECBDFR",
        "yields": {"10Y": "IRLTLT01DEM156N"},
    },
    "GBP": {
        "indicators": {
            "cpi_yoy": ("GBRCPIALLMINMEI", "yoy", 12),
            "unemployment": ("LRHUTTTTGBM156S", "level", 1),
            "gdp_yoy": ("CLVMNACSCAB1GQUK", "yoy", 4),
        },
        "yields": {"10Y": "IRLTLT01GBM156N"},
    },
    "JPY": {
        "indicators": {
            "cpi_yoy": ("JPNCPIALLMINMEI", "yoy", 12),
            "unemployment": ("LRHUTTTTJPM156S", "level", 1),
            "gdp_yoy": ("JPNRGDPEXP", "yoy", 4),
        },
        "rate": "IRSTCB01JPM156N",
        "yields": {"10Y": "IRLTLT01JPM156N"},
    },
    "CHF": {
        "indicators": {
            "cpi_yoy": ("CHECPIALLMINMEI", "yoy", 12),
            "unemployment": ("LRHUTTTTCHM156S", "level", 1),
            "gdp_yoy": ("CLVMNACSCAB1GQCH", "yoy", 4),
        },
        "rate": "IRSTCB01CHM156N",
        "yields": {"10Y": "IRLTLT01CHM156N"},
    },
    "AUD": {
        "indicators": {
            "cpi_yoy": ("AUSCPIALLQINMEI", "yoy", 4),
            "unemployment": ("LRHUTTTTAUM156S", "level", 1),
            "gdp_yoy": ("AUSGDPRQPSMEI", "yoy", 4),
        },
        "rate": "IRSTCB01AUM156N",
        "yields": {"10Y": "IRLTLT01AUM156N"},
    },
    "NZD": {
        "indicators": {
            "cpi_yoy": ("NZLCPIALLQINMEI", "yoy", 4),
            "unemployment": ("LRHUTTTTNZQ156S", "level", 1),
            "gdp_yoy": ("NAEXKP01NZQ189S", "yoy", 4),
        },
        "rate": "IRSTCB01NZM156N",
        "yields": {"10Y": "IRLTLT01NZM156N"},
    },
    "CAD": {
        "indicators": {
            "cpi_yoy": ("CANCPIALLMINMEI", "yoy", 12),
            "unemployment": ("LRHUTTTTCAM156S", "level", 1),
            "gdp_yoy": ("NAEXKP01CAQ189S", "yoy", 4),
        },
        "rate": "IRSTCB01CAM156N",
        "yields": {"10Y": "IRLTLT01CAM156N"},
    },
}
VIX_SERIES = "VIXCLS"


def transform(values: list[float], kind: str, lag: int) -> tuple[Optional[float], Optional[float]]:
    """values are newest-first. Returns (actual, previous)."""
    if kind == "level":
        return (values[0], values[1] if len(values) > 1 else None)
    if kind == "diff":
        if len(values) < 2:
            return (None, None)
        prev = values[1] - values[2] if len(values) > 2 else None
        return (values[0] - values[1], prev)
    if kind == "yoy":
        if len(values) <= lag or values[lag] == 0:
            return (None, None)
        actual = (values[0] / values[lag] - 1) * 100
        prev = None
        if len(values) > lag + 1 and values[lag + 1] != 0:
            prev = (values[1] / values[lag + 1] - 1) * 100
        return (actual, prev)
    raise ValueError(f"unknown transform {kind}")


def change_points(obs_asc: list[tuple[date, float]]) -> list[tuple[date, float]]:
    """Collapse a level series to the dates where the value changed (plus the very first point)."""
    pts: list[tuple[date, float]] = []
    last: Optional[float] = None
    for d, v in obs_asc:
        if last is None or abs(v - last) > 1e-9:
            pts.append((d, v))
            last = v
    return pts


class FredMacro(MacroProvider):
    name = "fred"
    requires_key = True
    covers = tuple(FRED_MAP.keys())
    URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self) -> None:
        self.key = get_settings().fred_api_key

    def is_configured(self) -> bool:
        return bool(self.key)

    def _series(self, series_id: str, limit: int) -> list[tuple[date, float]]:
        """Newest-first list of (date, value), skipping FRED's '.' placeholders."""
        r = http.get(self.URL, params={"series_id": series_id, "api_key": self.key, "file_type": "json",
                                       "sort_order": "desc", "limit": limit})
        out: list[tuple[date, float]] = []
        for o in r.json().get("observations", []):
            try:
                out.append((date.fromisoformat(o["date"]), float(o["value"])))
            except (ValueError, TypeError, KeyError):
                continue
        return out

    @staticmethod
    def _url(series_id: str) -> str:
        return f"https://fred.stlouisfed.org/series/{series_id}"

    def fetch(self, currencies: list[str], scope: str = "all") -> MacroBundle:
        b = MacroBundle()
        for ccy in currencies:
            cfg = FRED_MAP.get(ccy)
            if not cfg:
                continue
            bank = CURRENCY_META[ccy]["bank"]
            if cfg.get("rate"):
                sid = cfg["rate"]
                try:
                    rows = self._series(sid, 420)
                    for d, v in change_points(sorted(rows)):
                        b.rates.append(RateObs(ccy, bank, v, d, self.name, self._url(sid)))
                except Exception as e:  # noqa: BLE001
                    b.errors.append(f"fred {ccy} rate {sid}: {e}")
            for mat, sid in cfg.get("yields", {}).items():
                try:
                    rows = self._series(sid, 6)
                    if rows:
                        d, v = rows[0]
                        b.yields.append(YieldObs(ccy, mat, v, d, self.name, self._url(sid)))
                except Exception as e:  # noqa: BLE001
                    b.errors.append(f"fred {ccy} yield {sid}: {e}")
            if scope != "all":
                continue
            for key, (sid, kind, lag) in cfg.get("indicators", {}).items():
                try:
                    rows = self._series(sid, lag + 8)
                    if len(rows) < 2:
                        continue
                    values = [v for _, v in rows]
                    actual, prev = transform(values, kind, lag)
                    if actual is None:
                        continue
                    unit = "k" if key == "nfp_change" else "%"
                    b.indicators.append(IndicatorObs(ccy, key, rows[0][0], round(actual, 3), self.name,
                                                     self._url(sid), previous=None if prev is None else round(prev, 3),
                                                     unit=unit))
                except Exception as e:  # noqa: BLE001
                    b.errors.append(f"fred {ccy} {key} {sid}: {e}")
        # global risk gauge
        if "USD" in currencies or scope == "fast":
            try:
                rows = self._series(VIX_SERIES, 12)
                for i, (d, v) in enumerate(rows[:10]):
                    prev = rows[i + 1][1] if i + 1 < len(rows) else None
                    b.indicators.append(IndicatorObs("GLOBAL", "vix", d, v, self.name, self._url(VIX_SERIES),
                                                     previous=prev, unit="pts"))
            except Exception as e:  # noqa: BLE001
                b.errors.append(f"fred VIX: {e}")
        return b
