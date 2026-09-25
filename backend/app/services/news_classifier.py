"""Transparent, rule-based news tagging. Free, deterministic, explainable. (An LLM can refine it later.)"""
from __future__ import annotations

import re

HAWKISH = [
    "rate hike", "raise rates", "raises rates", "raised rates", "hike", "tighten", "tightening", "hawkish",
    "restrictive", "higher for longer", "inflation remains elevated", "inflation above", "upside risks to inflation",
    "inflation accelerat", "strong jobs", "strong labour", "strong labor", "beat expectations", "stronger than expected",
    "wage growth", "price pressures", "quantitative tightening", "further increases",
]
DOVISH = [
    "rate cut", "cuts rates", "cut rates", "lowered rates", "lower rates", "easing", "ease policy", "dovish",
    "accommodative", "downside risks", "inflation falls", "inflation eased", "inflation slows", "slowdown",
    "recession", "weaker than expected", "contraction", "job losses", "unemployment rises", "unemployment rose",
    "missed expectations", "stimulus", "pause", "softening", "cooling",
]
CATEGORIES = {
    "central_bank": ["central bank", "monetary policy", "interest rate", "rate decision", "fomc", "governing council",
                     "mpc", "policy rate", "minutes", "press conference", "governor", "chair"],
    "inflation": ["inflation", "cpi", "consumer price", "ppi", "pce", "price index", "deflator"],
    "employment": ["employment", "unemployment", "payroll", "jobs", "labour market", "labor market", "wage"],
    "growth": ["gdp", "growth", "pmi", "retail sales", "industrial production", "manufacturing", "consumer confidence"],
    "geopolitics": ["war", "sanction", "tariff", "election", "geopolit", "conflict", "trade dispute", "embargo"],
}
HIGH_IMPACT = ["rate decision", "monetary policy statement", "fomc", "press conference", "minutes", "cpi",
               "consumer price", "non-farm", "nonfarm", "employment situation", "gdp", "emergency", "intervention"]
MEDIUM_IMPACT = ["speech", "testimony", "retail sales", "pmi", "unemployment", "inflation", "projections", "report"]

CURRENCY_PATTERNS = {
    "USD": r"\b(federal reserve|the fed\b|fomc|powell|u\.s\.|treasury yields?|us dollar|wall street)\b",
    "EUR": r"\b(ecb|lagarde|eurozone|euro area|bund|euro\b)\b",
    "GBP": r"\b(bank of england|boe\b|bailey|sterling|gilts?|u\.k\.|uk economy|british pound)\b",
    "JPY": r"\b(bank of japan|boj\b|ueda|yen\b|japan)\b",
    "CHF": r"\b(snb\b|swiss national bank|swiss franc|switzerland)\b",
    "AUD": r"\b(rba\b|reserve bank of australia|australia|aussie)\b",
    "NZD": r"\b(rbnz|reserve bank of new zealand|new zealand|kiwi)\b",
    "CAD": r"\b(bank of canada|boc\b|macklem|canadian dollar|loonie|canada)\b",
}


def _hits(text: str, words: list[str]) -> int:
    return sum(1 for w in words if w in text)


def classify(headline: str, summary: str | None = None) -> dict:
    text = f"{headline} {summary or ''}".lower()
    hawk, dove = _hits(text, HAWKISH), _hits(text, DOVISH)
    tone = 0.0 if hawk + dove == 0 else (hawk - dove) / (hawk + dove)

    category, best = "other", 0
    for cat, words in CATEGORIES.items():
        n = _hits(text, words)
        if n > best:
            category, best = cat, n

    head = headline.lower()
    if _hits(head, HIGH_IMPACT):
        impact = "high"
    elif _hits(text, MEDIUM_IMPACT) or category == "central_bank":
        impact = "medium"
    else:
        impact = "low"
    return {"category": category, "tone": round(tone, 2), "impact": impact}


def tag_currencies(headline: str, summary: str | None = None) -> list[str]:
    text = f"{headline} {summary or ''}".lower()
    return [c for c, pat in CURRENCY_PATTERNS.items() if re.search(pat, text)]
