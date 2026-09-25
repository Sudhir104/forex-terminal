from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FxPrice(Base):
    __tablename__ = "fx_prices"
    id: Mapped[int] = mapped_column(primary_key=True)
    pair: Mapped[str] = mapped_column(String(7), index=True)
    bid: Mapped[Optional[float]] = mapped_column(Float)
    ask: Mapped[Optional[float]] = mapped_column(Float)
    mid: Mapped[float] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(40))
    is_reference: Mapped[bool] = mapped_column(Boolean, default=False)  # daily reference rate, not live
    __table_args__ = (Index("ix_fx_pair_ts", "pair", "ts"),)


class Indicator(Base):
    """One observation of an economic indicator. currency='GLOBAL' is used for VIX etc."""
    __tablename__ = "indicators"
    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(6), index=True)
    indicator: Mapped[str] = mapped_column(String(40), index=True)
    obs_date: Mapped[date] = mapped_column(Date)
    actual: Mapped[float] = mapped_column(Float)
    previous: Mapped[Optional[float]] = mapped_column(Float)
    forecast: Mapped[Optional[float]] = mapped_column(Float)  # nullable on purpose: free sources rarely have it
    unit: Mapped[str] = mapped_column(String(10), default="%")
    release_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("currency", "indicator", "obs_date", "source", name="uq_indicator_obs"),)


class PolicyRate(Base):
    __tablename__ = "policy_rates"
    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(6), index=True)
    bank: Mapped[str] = mapped_column(String(60))
    rate: Mapped[float] = mapped_column(Float)
    effective_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("currency", "effective_date", "source", name="uq_rate_obs"),)


class CentralBankProfile(Base):
    __tablename__ = "central_bank_profiles"
    currency: Mapped[str] = mapped_column(String(6), primary_key=True)
    bank: Mapped[str] = mapped_column(String(60))
    stance: Mapped[Optional[str]] = mapped_column(String(10), default=None)  # hawkish | neutral | dovish | None (not assessed)
    last_decision: Mapped[Optional[str]] = mapped_column(String(200))
    next_meeting: Mapped[Optional[date]] = mapped_column(Date)
    statement_url: Mapped[Optional[str]] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    meetings: Mapped[Any] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BondYield(Base):
    __tablename__ = "bond_yields"
    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(6), index=True)
    maturity: Mapped[str] = mapped_column(String(4))  # 2Y / 10Y
    value: Mapped[float] = mapped_column(Float)
    obs_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("currency", "maturity", "obs_date", "source", name="uq_yield_obs"),)


class NewsItem(Base):
    __tablename__ = "news"
    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(6), index=True)
    headline: Mapped[str] = mapped_column(String(500))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(80))
    source_url: Mapped[str] = mapped_column(String(600))
    category: Mapped[str] = mapped_column(String(20), default="other")
    tone: Mapped[float] = mapped_column(Float, default=0.0)  # -1 dovish/negative .. +1 hawkish/positive
    impact: Mapped[str] = mapped_column(String(6), default="low")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("source_url", "currency", name="uq_news_url_cur"),)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(6), index=True)
    title: Mapped[str] = mapped_column(String(200))
    event_date: Mapped[date] = mapped_column(Date, index=True)
    event_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    impact: Mapped[str] = mapped_column(String(6), default="medium")
    kind: Mapped[str] = mapped_column(String(20), default="data")  # data | central_bank
    actual: Mapped[Optional[str]] = mapped_column(String(40))
    forecast: Mapped[Optional[str]] = mapped_column(String(40))
    previous: Mapped[Optional[str]] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    __table_args__ = (UniqueConstraint("currency", "title", "event_date", name="uq_event"),)


class CurrencyScore(Base):
    __tablename__ = "currency_scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(6), index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=utcnow)
    total: Mapped[float] = mapped_column(Float)
    coverage: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(8))
    surprise_method: Mapped[str] = mapped_column(String(20), default="none")
    factors: Mapped[Any] = mapped_column(JSON)   # {factor: score|None}
    evidence: Mapped[Any] = mapped_column(JSON)  # {factor: {notes, inputs}}
    weights: Mapped[Any] = mapped_column(JSON)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class RawResponse(Base):
    __tablename__ = "raw_responses"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    key: Mapped[str] = mapped_column(String(200))
    payload: Mapped[str] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class QuotaUsage(Base):
    __tablename__ = "quota_usage"
    provider: Mapped[str] = mapped_column(String(40), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    used: Mapped[int] = mapped_column(Integer, default=0)


class ProviderHealth(Base):
    __tablename__ = "provider_health"
    provider: Mapped[str] = mapped_column(String(40), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    open_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_success: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(String(300))
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class JobState(Base):
    __tablename__ = "job_state"
    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[Optional[str]] = mapped_column(String(20))
    last_error: Mapped[Optional[str]] = mapped_column(String(300))
    last_detail: Mapped[Optional[str]] = mapped_column(String(300))


class HttpCache(Base):
    __tablename__ = "http_cache"
    url: Mapped[str] = mapped_column(String(500), primary_key=True)
    etag: Mapped[Optional[str]] = mapped_column(String(200))
    last_modified: Mapped[Optional[str]] = mapped_column(String(100))


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)


class ExplanationCache(Base):
    __tablename__ = "explanation_cache"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    facts_hash: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(12))  # llm | template
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AlertLog(Base):
    __tablename__ = "alert_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(200), unique=True)
    message: Mapped[str] = mapped_column(Text)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
