"""Synthetic macro data for DEMO_MODE. All numbers are made up so the UI can be explored without API keys."""
from __future__ import annotations

from datetime import date, timedelta

from ..constants import CURRENCY_META
from ..timeutil import utcnow
from .base import IndicatorObs, MacroBundle, MacroProvider, RateObs, YieldObs

# rate_now, rate_before (~120d ago), cpi, cpi_prev, core, gdp, gdp_prev, unemp, unemp_prev, y2, y10
DEMO = {
    "USD": (4.50, 4.75, 3.1, 3.3, 3.4, 2.4, 2.2, 4.0, 4.1, 4.20, 4.35),
    "EUR": (2.25, 2.75, 2.2, 2.4, 2.7, 0.9, 0.8, 6.3, 6.3, 2.10, 2.55),
    "GBP": (4.25, 4.50, 3.4, 3.2, 3.8, 1.2, 1.0, 4.4, 4.3, 3.95, 4.60),
    "JPY": (0.50, 0.25, 2.8, 2.6, 2.5, 0.8, 0.6, 2.5, 2.5, 0.85, 1.35),
    "CHF": (0.25, 0.50, 0.3, 0.4, 0.5, 1.4, 1.3, 2.7, 2.6, 0.25, 0.55),
    "AUD": (4.10, 4.35, 3.0, 3.1, 3.3, 1.8, 1.6, 4.1, 4.0, 3.70, 4.25),
    "NZD": (3.50, 4.25, 2.5, 2.7, 2.9, 0.4, 0.2, 5.1, 5.0, 3.30, 4.35),
    "CAD": (2.75, 3.25, 2.3, 2.1, 2.6, 1.5, 1.4, 6.6, 6.7, 2.85, 3.20),
}


class DemoMacro(MacroProvider):
    name = "demo"
    is_demo = True
    covers = tuple(DEMO.keys())

    def fetch(self, currencies: list[str], scope: str = "all") -> MacroBundle:
        b = MacroBundle()
        today = utcnow().date()
        first_of_month = today.replace(day=1)
        for ccy in currencies:
            row = DEMO.get(ccy)
            if not row:
                continue
            rate, rate_before, cpi, cpi_p, core, gdp, gdp_p, un, un_p, y2, y10 = row
            bank = CURRENCY_META[ccy]["bank"]
            b.rates.append(RateObs(ccy, bank, rate_before, today - timedelta(days=300), self.name))
            b.rates.append(RateObs(ccy, bank, rate, today - timedelta(days=90), self.name))
            b.yields.append(YieldObs(ccy, "2Y", y2, today, self.name))
            b.yields.append(YieldObs(ccy, "10Y", y10, today, self.name))
            if scope != "all":
                continue
            b.indicators += [
                IndicatorObs(ccy, "cpi_yoy", first_of_month - timedelta(days=30), cpi, self.name, previous=cpi_p,
                             forecast=round(cpi - 0.1, 2) if ccy in ("USD", "EUR", "GBP") else None,
                             release_time=utcnow() - timedelta(days=5)),
                IndicatorObs(ccy, "core_cpi_yoy", first_of_month - timedelta(days=30), core, self.name,
                             previous=core + 0.1),
                IndicatorObs(ccy, "gdp_yoy", first_of_month - timedelta(days=60), gdp, self.name, previous=gdp_p,
                             forecast=round(gdp + 0.1, 2) if ccy in ("USD", "GBP") else None,
                             release_time=utcnow() - timedelta(days=12)),
                IndicatorObs(ccy, "unemployment", first_of_month - timedelta(days=30), un, self.name, previous=un_p,
                             release_time=utcnow() - timedelta(days=8)),
            ]
        if "USD" in currencies:
            for i in range(8):
                b.indicators.append(IndicatorObs("GLOBAL", "vix", today - timedelta(days=i), 17.5 + 0.4 * (i % 3),
                                                 self.name, previous=17.5 + 0.4 * ((i + 1) % 3), unit="pts"))
        return b
