"""Bank of England Statistical Interactive Database (no key). Official Bank Rate."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta

from . import http
from .base import MacroBundle, MacroProvider, RateObs

URL = "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp"
SERIES = "IUDBEDR"


def parse_iadb_csv(text: str, series: str = SERIES) -> list[tuple[date, float]]:
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            d = datetime.strptime(row["DATE"].strip(), "%d %b %Y").date()
            out.append((d, float(row[series])))
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(out)


class BoeMacro(MacroProvider):
    name = "boe"
    requires_key = False
    covers = ("GBP",)

    def fetch(self, currencies: list[str], scope: str = "all") -> MacroBundle:
        b = MacroBundle()
        if "GBP" not in currencies:
            return b
        start = (date.today() - timedelta(days=800)).strftime("%d/%b/%Y")
        try:
            r = http.get(URL, params={"csv.x": "yes", "Datefrom": start, "Dateto": "now", "SeriesCodes": SERIES,
                                      "CSVF": "TN", "UsingCodes": "Y", "VPD": "Y", "VFD": "N"})
            last = None
            for d, v in parse_iadb_csv(r.text):
                if last is None or abs(v - last) > 1e-9:
                    b.rates.append(RateObs("GBP", "Bank of England", v, d, self.name,
                                           "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp"))
                    last = v
        except Exception as e:  # noqa: BLE001
            b.errors.append(f"boe rate: {e}")
        return b
