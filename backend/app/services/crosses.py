"""Cross-rate maths: we fetch 7 USD pairs and derive the other 21 locally (4x fewer API credits)."""
from __future__ import annotations

from ..constants import ALL_PAIRS, CURRENCIES, split_pair


def usd_values(quotes: dict[str, float]) -> dict[str, float]:
    """USD value of one unit of each currency, from the fetched USD pairs."""
    v = {"USD": 1.0}
    for pair, price in quotes.items():
        if price <= 0:
            continue
        base, quote = split_pair(pair)
        if quote == "USD":
            v[base] = price
        elif base == "USD":
            v[quote] = 1.0 / price
    return v


def derive_pairs(quotes: dict[str, float], pairs: list[str] | None = None) -> dict[str, float]:
    v = usd_values(quotes)
    out: dict[str, float] = {}
    for pair in pairs or ALL_PAIRS:
        base, quote = split_pair(pair)
        if base in v and quote in v and v[quote] != 0:
            out[pair] = v[base] / v[quote]
    return out


def missing_currencies(quotes: dict[str, float]) -> list[str]:
    v = usd_values(quotes)
    return [c for c in CURRENCIES if c not in v]
