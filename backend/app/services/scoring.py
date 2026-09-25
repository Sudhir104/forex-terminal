"""Currency Strength Engine.

Pure, deterministic and explainable: every factor score is 0-10, traced back to the raw
observations that produced it (see FactorResult.evidence). FACT (raw numbers) and
CALCULATION (this file) are kept separate from INTERPRETATION (services/explain.py).

Design choices that matter for a *free-tier-first* build:
 - `forecast` is usually missing on the free tier, so `surprise` degrades gracefully:
   vs-forecast when we have consensus (paid calendar), else vs-previous, else omitted.
 - A factor with no data is left as None and excluded from the weighted average
   (weights are renormalised over whatever *is* available) rather than defaulting to
   a fake "neutral" 5 - a currency with only 3 populated factors gets a lower `coverage`
   score, which the UI/API should show so nobody mistakes a thin score for a rich one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from ..constants import (CURRENCIES, DEFAULT_WEIGHTS, FACTORS, INVERTED_INDICATORS, RISK_BETA,
                          STALE_DAYS, SURPRISE_SCALE)
from ..timeutil import age_days, utcnow
from . import repo


def clip(x: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, x))


def scale_zscore_like(delta: float, span: float) -> float:
    """Map a signed delta to a 0-10 score around a neutral midpoint of 5, saturating at +-2*span."""
    return clip(5 + 5 * clip(delta / span, -1, 1))


@dataclass
class FactorResult:
    score: Optional[float]
    notes: str
    inputs: dict = field(default_factory=dict)
    stale: bool = False


@dataclass
class ScoreResult:
    currency: str
    total: Optional[float]
    coverage: float
    confidence: str
    surprise_method: str
    factors: dict[str, Optional[float]]
    evidence: dict[str, dict]
    weights: dict[str, float]


def _stale(kind: str, d) -> bool:
    limit = STALE_DAYS.get(kind)
    if limit is None or d is None:
        return False
    a = age_days(d)
    return a is not None and a > limit


# ---------------------------------------------------------------- factors --

def factor_monetary(session: Session, ccy: str) -> FactorResult:
    latest, older = repo.rate_change_since(session, ccy, days=180)
    if latest is None:
        return FactorResult(None, "No policy-rate data yet.")
    delta = latest.rate - older.rate if older else 0.0
    score = scale_zscore_like(delta, span=1.0)  # +-1.00pp over 6mo saturates the score
    stale = _stale("rate", latest.effective_date)
    notes = f"Policy rate {latest.rate:.2f}% ({'+' if delta >= 0 else ''}{delta:.2f}pp vs ~6mo ago)."
    return FactorResult(score, notes, {"rate": latest.rate, "delta_6m": round(delta, 3),
                                       "effective_date": str(latest.effective_date), "source": latest.source}, stale)


def factor_yields(session: Session, ccy: str, usd_10y: Optional[float]) -> FactorResult:
    y10 = repo.latest_yield(session, ccy, "10Y")
    if y10 is None:
        return FactorResult(None, "No 10Y yield data yet.")
    if ccy == "USD" or usd_10y is None:
        # Absolute level fallback (USD itself, or no USD benchmark available yet).
        score = scale_zscore_like(y10.value - 3.0, span=3.0)
        notes = f"10Y yield {y10.value:.2f}%."
    else:
        spread = y10.value - usd_10y
        score = scale_zscore_like(spread, span=2.0)
        notes = f"10Y yield {y10.value:.2f}% vs US {usd_10y:.2f}% (spread {spread:+.2f}pp)."
    stale = _stale("yield", y10.obs_date)
    return FactorResult(score, notes, {"10Y": y10.value, "us_10Y": usd_10y, "obs_date": str(y10.obs_date),
                                       "source": y10.source}, stale)


def _indicator_factor(session: Session, ccy: str, key: str, span: float, label: str, invert: bool = False) -> FactorResult:
    row = repo.latest_indicator(session, ccy, key)
    if row is None:
        return FactorResult(None, f"No {label.lower()} data yet.")
    prior = row.previous if row.previous is not None else None
    if prior is None:
        p = repo.prior_indicator(session, ccy, key, row.obs_date)
        prior = p.actual if p else None
    delta = 0.0 if prior is None else row.actual - prior
    if invert:
        delta = -delta
    score = scale_zscore_like(delta, span=span)
    stale = _stale(key, row.obs_date)
    trend = f"({'+' if delta >= 0 else ''}{delta:.2f} vs prior)" if prior is not None else "(no prior on file)"
    notes = f"{label} {row.actual:.2f}{row.unit} {trend}."
    return FactorResult(score, notes, {"actual": row.actual, "previous": prior, "obs_date": str(row.obs_date),
                                       "source": row.source, "source_url": row.source_url}, stale)


def factor_inflation(session: Session, ccy: str) -> FactorResult:
    return _indicator_factor(session, ccy, "cpi_yoy", span=1.0, label="CPI y/y")


def factor_growth(session: Session, ccy: str) -> FactorResult:
    return _indicator_factor(session, ccy, "gdp_yoy", span=1.5, label="GDP y/y")


def factor_employment(session: Session, ccy: str) -> FactorResult:
    return _indicator_factor(session, ccy, "unemployment", span=0.8, label="Unemployment rate", invert=True)


def factor_surprise(session: Session, ccy: str) -> tuple[FactorResult, str]:
    """Averages the surprise (actual vs forecast, else vs previous) across whatever indicators we have."""
    scores, notes_parts, method = [], [], "none"
    for key in ("cpi_yoy", "gdp_yoy", "unemployment", "retail_sales_yoy"):
        row = repo.latest_indicator(session, ccy, key)
        if row is None:
            continue
        scale = SURPRISE_SCALE.get(key, 0.5)
        if row.forecast is not None:
            raw = row.actual - row.forecast
            method = "vs_forecast"
        elif row.previous is not None:
            raw = row.actual - row.previous
            method = "vs_previous" if method != "vs_forecast" else method
        else:
            continue
        if key in INVERTED_INDICATORS:
            raw = -raw
        scores.append(scale_zscore_like(raw, span=scale))
        notes_parts.append(f"{key} {'beat' if raw >= 0 else 'missed'} by {abs(raw):.2f}")
    if not scores:
        return FactorResult(None, "No comparable data yet."), "none"
    avg = sum(scores) / len(scores)
    return FactorResult(avg, "; ".join(notes_parts) + ".", {"n": len(scores)}), method


def factor_risk(session: Session, ccy: str) -> FactorResult:
    vix = repo.latest_indicator(session, "GLOBAL", "vix")
    if vix is None:
        return FactorResult(None, "No VIX data yet.")
    beta = RISK_BETA.get(ccy, 0.0)
    # VIX 15 -> calm/neutral, VIX 30 -> stressed. beta>0 (safe haven) gains when vol rises.
    stress = clip((vix.actual - 15) / 15, -1, 1)
    score = clip(5 + 5 * beta * stress)
    notes = f"VIX {vix.actual:.1f} ({'risk-off' if stress > 0.15 else 'risk-on' if stress < -0.15 else 'calm'})."
    return FactorResult(score, notes, {"vix": vix.actual, "beta": beta}, _stale("vix", vix.obs_date))


def factor_news(session: Session, ccy: str) -> FactorResult:
    items = repo.recent_news(session, ccy, hours=72, limit=50)
    if not items:
        return FactorResult(None, "No recent tagged news.")
    weight = {"high": 3, "medium": 2, "low": 1}
    num = sum(it.tone * weight.get(it.impact, 1) for it in items)
    den = sum(weight.get(it.impact, 1) for it in items)
    tone = num / den if den else 0.0
    score = clip(5 + 5 * tone)
    notes = f"{len(items)} tagged headlines, avg tone {tone:+.2f} (72h)."
    return FactorResult(score, notes, {"n": len(items), "avg_tone": round(tone, 3)})


# ------------------------------------------------------------- aggregate --

def score_currency(session: Session, ccy: str, weights: Optional[dict[str, float]] = None,
                   usd_10y: Optional[float] = None) -> ScoreResult:
    w = weights or DEFAULT_WEIGHTS
    surprise, method = factor_surprise(session, ccy)
    results: dict[str, FactorResult] = {
        "monetary": factor_monetary(session, ccy),
        "inflation": factor_inflation(session, ccy),
        "growth": factor_growth(session, ccy),
        "employment": factor_employment(session, ccy),
        "yields": factor_yields(session, ccy, usd_10y),
        "surprise": surprise,
        "risk": factor_risk(session, ccy),
        "news": factor_news(session, ccy),
    }
    available = {k: r for k, r in results.items() if r.score is not None}
    if not available:
        total, confidence = None, "none"
    else:
        wsum = sum(w[k] for k in available)
        total = round(sum(r.score * w[k] for k, r in available.items()) / wsum, 2) if wsum else None
        confidence = "high" if len(available) >= 6 else "medium" if len(available) >= 3 else "low"
    coverage = round(len(available) / len(FACTORS), 2)
    return ScoreResult(
        currency=ccy, total=total, coverage=coverage, confidence=confidence, surprise_method=method,
        factors={k: (r.score if r.score is None else round(r.score, 2)) for k, r in results.items()},
        evidence={k: {"notes": r.notes, "inputs": r.inputs, "stale": r.stale} for k, r in results.items()},
        weights=w,
    )


def score_all(session: Session, currencies: list[str] = CURRENCIES,
             weights: Optional[dict[str, float]] = None) -> dict[str, ScoreResult]:
    usd_10y_row = repo.latest_yield(session, "USD", "10Y")
    usd_10y = usd_10y_row.value if usd_10y_row else None
    return {c: score_currency(session, c, weights, usd_10y) for c in currencies}


def pair_differential(scores: dict[str, ScoreResult], base: str, quote: str) -> Optional[float]:
    b, q = scores.get(base), scores.get(quote)
    if not b or not q or b.total is None or q.total is None:
        return None
    return round(b.total - q.total, 2)
