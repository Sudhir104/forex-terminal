"""'Why?' explanations. Two tiers:
  1. Template (always available, free, instant) - built straight from the scoring evidence.
  2. LLM (optional) - asked only to phrase the SAME facts in a sentence or two; it is
     never given room to invent a number, and its output is cached so we don't re-spend
     tokens on an unchanged score.

Architecture from the plan: Official data -> DB -> calculations -> structured facts -> AI ->
human-readable text. The AI explains, it does not source.
"""
from __future__ import annotations

import hashlib
import json
from typing import Optional

from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..constants import FACTOR_LABELS
from ..models import ExplanationCache
from .scoring import ScoreResult

SYSTEM_PROMPT = (
    "You explain a rules-based currency strength score to a retail trader. "
    "You will be given JSON with a total score and per-factor scores/notes, each backed by a "
    "real data point. Write 2-4 short sentences naming the 2-3 factors that moved the score most "
    "and why, in plain language. STRICT RULES: use ONLY the numbers given to you; never invent a "
    "statistic, date, or event that is not in the JSON; do not predict future price direction; "
    "do not give trading advice. If the data is thin, say so plainly instead of padding."
)


def _facts_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def top_drivers(result: ScoreResult, n: int = 3) -> list[tuple[str, float, str]]:
    scored = [(k, v, result.evidence[k]["notes"]) for k, v in result.factors.items() if v is not None]
    scored.sort(key=lambda t: abs(t[1] - 5), reverse=True)
    return scored[:n]


def template_explanation(result: ScoreResult) -> str:
    if result.total is None:
        return f"Not enough data yet to score {result.currency} ({result.coverage:.0%} factor coverage)."
    drivers = top_drivers(result)
    if not drivers:
        return f"{result.currency} strength is {result.total}/10, but no individual factor stands out yet."
    parts = [f"{FACTOR_LABELS[k]} ({result.evidence[k]['notes'].rstrip('.')})" for k, _, _ in drivers]
    lead = "supported by" if result.total >= 5 else "weighed down by"
    text = f"{result.currency} strength is {result.total}/10, {lead} " + "; ".join(parts) + "."
    if result.coverage < 0.6:
        text += f" Note: only {result.coverage:.0%} of factors have data right now, so treat this as partial."
    return text


def _facts_payload(result: ScoreResult) -> dict:
    return {
        "currency": result.currency, "total": result.total, "coverage": result.coverage,
        "confidence": result.confidence, "surprise_method": result.surprise_method,
        "factors": [{"factor": k, "label": FACTOR_LABELS[k], "score": v, "notes": result.evidence[k]["notes"]}
                    for k, v in result.factors.items() if v is not None],
    }


def _call_llm(settings: Settings, payload: dict) -> Optional[str]:
    from ..providers import http
    prompt = json.dumps(payload)
    try:
        if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            r = http.post_json("https://api.anthropic.com/v1/messages", {
                "model": settings.anthropic_model, "max_tokens": 300,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            }, headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01",
                       "content-type": "application/json"})
            blocks = r.json().get("content", [])
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
            return text or None
        if settings.llm_provider == "groq" and settings.groq_api_key:
            r = http.post_json("https://api.groq.com/openai/v1/chat/completions", {
                "model": settings.groq_model, "max_tokens": 300, "temperature": 0.3,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            }, headers={"Authorization": f"Bearer {settings.groq_api_key}", "content-type": "application/json"})
            return r.json()["choices"][0]["message"]["content"].strip() or None
    except Exception:  # noqa: BLE001 - explanation is a nice-to-have, template always covers us
        return None
    return None


def explain(session: Session, result: ScoreResult, settings: Optional[Settings] = None) -> dict:
    settings = settings or get_settings()
    template = template_explanation(result)
    if settings.llm_provider == "none" or result.total is None:
        return {"text": template, "origin": "template", "drivers": [k for k, _, _ in top_drivers(result)]}

    payload = _facts_payload(result)
    fhash = _facts_hash(payload)
    key = f"score:{result.currency}"
    cached = session.get(ExplanationCache, key)
    if cached and cached.facts_hash == fhash:
        return {"text": cached.text, "origin": cached.origin, "drivers": [k for k, _, _ in top_drivers(result)]}

    text = _call_llm(settings, payload)
    origin = "llm" if text else "template"
    text = text or template
    if cached is None:
        cached = ExplanationCache(key=key, facts_hash=fhash, text=text, origin=origin)
        session.add(cached)
    else:
        cached.facts_hash, cached.text, cached.origin = fhash, text, origin
    session.commit()
    return {"text": text, "origin": origin, "drivers": [k for k, _, _ in top_drivers(result)]}


def explain_pair(session: Session, base_result: ScoreResult, quote_result: ScoreResult,
                 settings: Optional[Settings] = None) -> dict:
    settings = settings or get_settings()
    diff = None if base_result.total is None or quote_result.total is None else round(base_result.total - quote_result.total, 2)
    if diff is None:
        return {"text": "Not enough data yet to compare these two currencies.", "origin": "template", "differential": None}
    b_drivers, q_drivers = top_drivers(base_result, 2), top_drivers(quote_result, 2)
    leader, other = (base_result, quote_result) if diff >= 0 else (quote_result, base_result)
    lead_drivers = b_drivers if leader is base_result else q_drivers
    reason = "; ".join(f"{FACTOR_LABELS[k]} ({leader.evidence[k]['notes'].rstrip('.')})" for k, _, _ in lead_drivers) or "no single standout factor"
    template = (f"{base_result.currency}/{quote_result.currency} fundamental differential: "
               f"{base_result.currency} {base_result.total} vs {quote_result.currency} {quote_result.total} "
               f"({diff:+.2f}). {leader.currency} is ahead, mainly on {reason}.")
    if settings.llm_provider == "none":
        return {"text": template, "origin": "template", "differential": diff}
    payload = {"base": _facts_payload(base_result), "quote": _facts_payload(quote_result), "differential": diff}
    fhash = _facts_hash(payload)
    key = f"pair:{base_result.currency}{quote_result.currency}"
    cached = session.get(ExplanationCache, key)
    if cached and cached.facts_hash == fhash:
        return {"text": cached.text, "origin": cached.origin, "differential": diff}
    text = _call_llm(settings, payload)
    origin = "llm" if text else "template"
    text = text or template
    if cached is None:
        session.add(ExplanationCache(key=key, facts_hash=fhash, text=text, origin=origin))
    else:
        cached.facts_hash, cached.text, cached.origin = fhash, text, origin
    session.commit()
    return {"text": text, "origin": origin, "differential": diff}
