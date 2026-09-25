"""ECB Data Portal (SDMX REST, no key). Euro-area inflation, deposit facility rate, yield curve, unemployment."""
from __future__ import annotations

import csv
import io
from datetime import date
from typing import Optional

from . import http
from .base import IndicatorObs, MacroBundle, MacroProvider, RateObs, YieldObs

BASE = "https://data-api.ecb.europa.eu/service/data"
SERIES = {
    "cpi_yoy": "ICP/M.U2.N.000000.4.ANR",
    "core_cpi_yoy": "ICP/M.U2.N.XEF000.4.ANR",
    "unemployment": "LFSI/M.I9.S.UNEHRT.TOTAL0.15_74.T",
}
RATE = "FM/B.U2.EUR.4F.KR.DFR.LEV"
YIELDS = {"2Y": "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y", "10Y": "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y"}


def parse_period(p: str) -> date:
    p = p.strip()
    if len(p) == 10:
        return date.fromisoformat(p)
    if len(p) == 7 and p[4] == "-" and p[5] != "Q":
        return date(int(p[:4]), int(p[5:7]), 1)
    if "Q" in p:
        y, q = p.split("-Q") if "-Q" in p else (p[:4], p[-1])
        return date(int(y), int(q) * 3, 1)
    if len(p) == 4:
        return date(int(p), 12, 31)
    raise ValueError(f"unrecognised period {p}")


def parse_csv(text: str) -> list[tuple[date, float]]:
    """ECB csvdata -> ascending [(date, value)]."""
    out: list[tuple[date, float]] = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            out.append((parse_period(row["TIME_PERIOD"]), float(row["OBS_VALUE"])))
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(out)


class EcbMacro(MacroProvider):
    name = "ecb"
    requires_key = False
    covers = ("EUR",)

    def _get(self, path: str, last_n: int) -> list[tuple[date, float]]:
        r = http.get(f"{BASE}/{path}", params={"lastNObservations": last_n, "format": "csvdata"})
        return parse_csv(r.text)

    @staticmethod
    def _url(path: str) -> str:
        return f"https://data.ecb.europa.eu/data/datasets/{path.split('/')[0]}"

    def fetch(self, currencies: list[str], scope: str = "all") -> MacroBundle:
        b = MacroBundle()
        if "EUR" not in currencies:
            return b
        try:
            rows = self._get(RATE, 400)
            last: Optional[float] = None
            for d, v in rows:
                if last is None or abs(v - last) > 1e-9:
                    b.rates.append(RateObs("EUR", "European Central Bank", v, d, self.name, self._url(RATE)))
                    last = v
        except Exception as e:  # noqa: BLE001
            b.errors.append(f"ecb rate: {e}")
        for mat, path in YIELDS.items():
            try:
                rows = self._get(path, 5)
                if rows:
                    d, v = rows[-1]
                    b.yields.append(YieldObs("EUR", mat, v, d, self.name, self._url(path)))
            except Exception as e:  # noqa: BLE001
                b.errors.append(f"ecb yield {mat}: {e}")
        if scope == "all":
            for key, path in SERIES.items():
                try:
                    rows = self._get(path, 3)
                    if rows:
                        d, v = rows[-1]
                        prev = rows[-2][1] if len(rows) > 1 else None
                        b.indicators.append(IndicatorObs("EUR", key, d, v, self.name, self._url(path), previous=prev))
                except Exception as e:  # noqa: BLE001
                    b.errors.append(f"ecb {key}: {e}")
        return b
