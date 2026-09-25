"""Static market definitions: currencies, pairs, factors and model assumptions."""
from __future__ import annotations

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"]

CURRENCY_META = {
    "USD": {"name": "US Dollar", "country": "United States", "bank": "Federal Reserve"},
    "EUR": {"name": "Euro", "country": "Euro Area", "bank": "European Central Bank"},
    "GBP": {"name": "British Pound", "country": "United Kingdom", "bank": "Bank of England"},
    "JPY": {"name": "Japanese Yen", "country": "Japan", "bank": "Bank of Japan"},
    "CHF": {"name": "Swiss Franc", "country": "Switzerland", "bank": "Swiss National Bank"},
    "AUD": {"name": "Australian Dollar", "country": "Australia", "bank": "Reserve Bank of Australia"},
    "NZD": {"name": "New Zealand Dollar", "country": "New Zealand", "bank": "Reserve Bank of New Zealand"},
    "CAD": {"name": "Canadian Dollar", "country": "Canada", "bank": "Bank of Canada"},
}

# Pairs we actually fetch from a provider (7 credits per refresh). Everything else is a cross.
FETCH_PAIRS = ["EUR/USD", "GBP/USD", "AUD/USD", "NZD/USD", "USD/JPY", "USD/CHF", "USD/CAD"]

MAJOR_PAIRS = list(FETCH_PAIRS)
CROSS_PAIRS = [
    "EUR/GBP", "EUR/JPY", "EUR/CHF", "EUR/AUD", "EUR/NZD", "EUR/CAD",
    "GBP/JPY", "GBP/CHF", "GBP/AUD", "GBP/NZD", "GBP/CAD",
    "AUD/JPY", "AUD/NZD", "AUD/CAD", "AUD/CHF",
    "NZD/JPY", "NZD/CAD", "NZD/CHF",
    "CAD/JPY", "CAD/CHF", "CHF/JPY",
]
ALL_PAIRS = MAJOR_PAIRS + CROSS_PAIRS  # 28 pairs

FACTORS = ["monetary", "inflation", "growth", "employment", "yields", "surprise", "risk", "news"]

FACTOR_LABELS = {
    "monetary": "Monetary policy",
    "inflation": "Inflation",
    "growth": "Growth",
    "employment": "Employment",
    "yields": "Bond yields",
    "surprise": "Data surprises",
    "risk": "Risk sentiment",
    "news": "News tone",
}

# Model assumptions - NOT objective truth. Editable at runtime through the settings table.
DEFAULT_WEIGHTS = {
    "monetary": 0.25,
    "inflation": 0.15,
    "growth": 0.15,
    "employment": 0.10,
    "yields": 0.15,
    "surprise": 0.10,
    "risk": 0.05,
    "news": 0.05,
}

# Sensitivity of each currency to risk-off (+1 = strong safe haven, -1 = strong risk-on currency).
RISK_BETA = {
    "JPY": 1.0, "CHF": 0.8, "USD": 0.5, "EUR": 0.1,
    "GBP": -0.3, "CAD": -0.5, "AUD": -1.0, "NZD": -1.0,
}

# Days after which an observation is considered stale, per indicator.
STALE_DAYS = {
    "cpi_yoy": 75, "core_cpi_yoy": 75, "unemployment": 75, "gdp_yoy": 150,
    "retail_sales_yoy": 75, "nfp_change": 75, "vix": 7, "yield": 45, "rate": 10,
}

# Scale used to turn a raw surprise (actual - benchmark) into a normalised number.
SURPRISE_SCALE = {
    "cpi_yoy": 0.2, "core_cpi_yoy": 0.2, "unemployment": 0.2,
    "gdp_yoy": 0.4, "retail_sales_yoy": 0.8, "nfp_change": 75.0,
}
# Indicators where a higher number is BAD for the currency.
INVERTED_INDICATORS = {"unemployment"}

INDICATOR_LABELS = {
    "cpi_yoy": "CPI (y/y)", "core_cpi_yoy": "Core CPI (y/y)", "unemployment": "Unemployment rate",
    "gdp_yoy": "GDP (y/y)", "retail_sales_yoy": "Retail sales (y/y)", "nfp_change": "Payroll change (k)",
    "vix": "VIX",
}


def split_pair(pair: str) -> tuple[str, str]:
    p = pair.replace("-", "/").replace("_", "").upper()
    if "/" not in p and len(p) == 6:
        p = p[:3] + "/" + p[3:]
    base, quote = p.split("/")
    return base, quote


def normalize_pair(pair: str) -> str:
    base, quote = split_pair(pair)
    return f"{base}/{quote}"
