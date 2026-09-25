"""Upsert helpers: write normalised provider records into the DB, storing source+timestamp on every row."""
from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import normalize_pair
from ..models import BondYield, CalendarEvent, FxPrice, Indicator, NewsItem, PolicyRate
from ..providers.base import EventObs, IndicatorObs, MacroBundle, NewsObs, PriceQuote, RateObs, YieldObs
from ..timeutil import utcnow


def save_quotes(session: Session, quotes: Iterable[PriceQuote]) -> int:
    n = 0
    for q in quotes:
        session.add(FxPrice(pair=normalize_pair(q.pair), bid=q.bid, ask=q.ask, mid=q.mid, ts=q.ts,
                            source=q.source, is_reference=q.is_reference))
        n += 1
    session.flush()
    return n


def latest_prices(session: Session, pairs: list[str] | None = None) -> dict[str, FxPrice]:
    q = select(FxPrice)
    if pairs:
        q = q.where(FxPrice.pair.in_([normalize_pair(p) for p in pairs]))
    rows = session.execute(q.order_by(FxPrice.pair, FxPrice.ts.desc())).scalars().all()
    out: dict[str, FxPrice] = {}
    for r in rows:
        if r.pair not in out:
            out[r.pair] = r
    return out


def save_indicator(session: Session, obs: IndicatorObs) -> bool:
    existing = session.execute(select(Indicator).where(
        Indicator.currency == obs.currency, Indicator.indicator == obs.indicator,
        Indicator.obs_date == obs.obs_date, Indicator.source == obs.source)).scalar_one_or_none()
    if existing:
        changed = existing.actual != obs.actual or existing.forecast != obs.forecast
        existing.actual, existing.previous, existing.forecast = obs.actual, obs.previous, obs.forecast
        existing.source_url, existing.release_time = obs.source_url, obs.release_time
        existing.retrieved_at = utcnow()
        return changed
    session.add(Indicator(currency=obs.currency, indicator=obs.indicator, obs_date=obs.obs_date, actual=obs.actual,
                          previous=obs.previous, forecast=obs.forecast, unit=obs.unit, release_time=obs.release_time,
                          source=obs.source, source_url=obs.source_url))
    return True


def save_rate(session: Session, obs: RateObs) -> bool:
    existing = session.execute(select(PolicyRate).where(
        PolicyRate.currency == obs.currency, PolicyRate.effective_date == obs.effective_date,
        PolicyRate.source == obs.source)).scalar_one_or_none()
    if existing:
        return False
    session.add(PolicyRate(currency=obs.currency, bank=obs.bank, rate=obs.rate, effective_date=obs.effective_date,
                           source=obs.source, source_url=obs.source_url))
    return True


def save_yield(session: Session, obs: YieldObs) -> bool:
    existing = session.execute(select(BondYield).where(
        BondYield.currency == obs.currency, BondYield.maturity == obs.maturity, BondYield.obs_date == obs.obs_date,
        BondYield.source == obs.source)).scalar_one_or_none()
    if existing:
        existing.value = obs.value
        return False
    session.add(BondYield(currency=obs.currency, maturity=obs.maturity, value=obs.value, obs_date=obs.obs_date,
                          source=obs.source, source_url=obs.source_url))
    return True


def save_macro_bundle(session: Session, bundle: MacroBundle) -> dict[str, int]:
    counts = {"indicators": 0, "rates": 0, "yields": 0}
    for obs in bundle.indicators:
        if save_indicator(session, obs):
            counts["indicators"] += 1
    for obs in bundle.rates:
        if save_rate(session, obs):
            counts["rates"] += 1
    for obs in bundle.yields:
        if save_yield(session, obs):
            counts["yields"] += 1
    session.flush()
    return counts


def latest_indicator(session: Session, currency: str, indicator: str) -> Indicator | None:
    return session.execute(select(Indicator).where(Indicator.currency == currency, Indicator.indicator == indicator)
                           .order_by(Indicator.obs_date.desc())).scalars().first()


def prior_indicator(session: Session, currency: str, indicator: str, before: date) -> Indicator | None:
    return session.execute(select(Indicator).where(Indicator.currency == currency, Indicator.indicator == indicator,
                                                    Indicator.obs_date < before)
                           .order_by(Indicator.obs_date.desc())).scalars().first()


def latest_rate(session: Session, currency: str) -> PolicyRate | None:
    return session.execute(select(PolicyRate).where(PolicyRate.currency == currency)
                           .order_by(PolicyRate.effective_date.desc())).scalars().first()


def rate_change_since(session: Session, currency: str, days: int) -> tuple[PolicyRate | None, PolicyRate | None]:
    from datetime import timedelta
    cutoff = utcnow().date() - timedelta(days=days)
    rows = session.execute(select(PolicyRate).where(PolicyRate.currency == currency)
                           .order_by(PolicyRate.effective_date.desc())).scalars().all()
    if not rows:
        return None, None
    latest = rows[0]
    older = next((r for r in rows if r.effective_date <= cutoff), rows[-1])
    return latest, older


def latest_yield(session: Session, currency: str, maturity: str) -> BondYield | None:
    return session.execute(select(BondYield).where(BondYield.currency == currency, BondYield.maturity == maturity)
                           .order_by(BondYield.obs_date.desc())).scalars().first()


def save_news(session: Session, items: Iterable[NewsObs]) -> int:
    n = 0
    for it in items:
        currency = it.currency or "MULTI"
        existing = session.execute(select(NewsItem).where(NewsItem.source_url == it.source_url,
                                                           NewsItem.currency == currency)).scalar_one_or_none()
        if existing:
            continue
        from .news_classifier import classify, tag_currencies
        tags = [it.currency] if it.currency else (tag_currencies(it.headline, it.summary) or ["MULTI"])
        info = classify(it.headline, it.summary)
        for ccy in tags:
            if session.execute(select(NewsItem.id).where(NewsItem.source_url == it.source_url,
                                                          NewsItem.currency == ccy)).first():
                continue
            session.add(NewsItem(currency=ccy, headline=it.headline, summary=it.summary, published_at=it.published_at,
                                 source=it.source, source_url=it.source_url, category=info["category"],
                                 tone=info["tone"], impact=info["impact"]))
            n += 1
    session.flush()
    return n


def recent_news(session: Session, currency: str | None = None, hours: int = 72, limit: int = 100) -> list[NewsItem]:
    from datetime import timedelta
    cutoff = utcnow() - timedelta(hours=hours)
    q = select(NewsItem).where(NewsItem.published_at >= cutoff)
    if currency:
        q = q.where(NewsItem.currency == currency)
    return list(session.execute(q.order_by(NewsItem.published_at.desc()).limit(limit)).scalars().all())


def save_events(session: Session, events: Iterable[EventObs]) -> int:
    n = 0
    for e in events:
        existing = session.execute(select(CalendarEvent).where(
            CalendarEvent.currency == e.currency, CalendarEvent.title == e.title,
            CalendarEvent.event_date == e.event_date)).scalar_one_or_none()
        if existing:
            existing.actual, existing.forecast, existing.previous = e.actual, e.forecast, e.previous
            existing.impact, existing.event_time = e.impact, e.event_time
            continue
        session.add(CalendarEvent(currency=e.currency, title=e.title, event_date=e.event_date, event_time=e.event_time,
                                  impact=e.impact, kind=e.kind, actual=e.actual, forecast=e.forecast,
                                  previous=e.previous, source=e.source, source_url=e.source_url))
        n += 1
    session.flush()
    return n


def upcoming_events(session: Session, start: date, end: date, currency: str | None = None) -> list[CalendarEvent]:
    q = select(CalendarEvent).where(CalendarEvent.event_date >= start, CalendarEvent.event_date <= end)
    if currency:
        q = q.where(CalendarEvent.currency == currency)
    return list(session.execute(q.order_by(CalendarEvent.event_date, CalendarEvent.impact.desc())).scalars().all())
