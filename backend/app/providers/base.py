"""Provider interfaces + normalised record types.

Everything downstream (database, scoring, API, UI) only ever sees the normalised
records below. To move from a free source to a paid one you add a class that
implements one of the interfaces and put its name first in the *_PROVIDERS env var.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class PriceQuote:
    pair: str
    mid: float
    ts: datetime
    source: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    is_reference: bool = False


@dataclass
class IndicatorObs:
    currency: str
    indicator: str
    obs_date: date
    actual: float
    source: str
    source_url: Optional[str] = None
    previous: Optional[float] = None
    forecast: Optional[float] = None
    unit: str = "%"
    release_time: Optional[datetime] = None


@dataclass
class RateObs:
    currency: str
    bank: str
    rate: float
    effective_date: date
    source: str
    source_url: Optional[str] = None


@dataclass
class YieldObs:
    currency: str
    maturity: str
    value: float
    obs_date: date
    source: str
    source_url: Optional[str] = None


@dataclass
class NewsObs:
    headline: str
    published_at: datetime
    source: str
    source_url: str
    summary: Optional[str] = None
    currency: Optional[str] = None  # feed-level tag; the classifier may add more


@dataclass
class EventObs:
    currency: str
    title: str
    event_date: date
    source: str
    event_time: Optional[datetime] = None
    impact: str = "medium"
    kind: str = "data"
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class MacroBundle:
    indicators: list[IndicatorObs] = field(default_factory=list)
    rates: list[RateObs] = field(default_factory=list)
    yields: list[YieldObs] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # partial failures, non-fatal

    def extend(self, other: "MacroBundle") -> None:
        self.indicators += other.indicators
        self.rates += other.rates
        self.yields += other.yields
        self.errors += other.errors


class Provider(ABC):
    name: str = "provider"
    requires_key: bool = False
    daily_credit_limit: Optional[int] = None  # None = unlimited / not metered
    is_demo: bool = False

    def is_configured(self) -> bool:
        return True


class FxProvider(Provider):
    supports_live: bool = True
    cost_per_call_per_pair: int = 1

    @abstractmethod
    def fetch_quotes(self, pairs: list[str]) -> list[PriceQuote]: ...

    def cost(self, pairs: list[str]) -> int:
        return self.cost_per_call_per_pair * len(pairs)


class MacroProvider(Provider):
    covers: tuple[str, ...] = ()

    @abstractmethod
    def fetch(self, currencies: list[str], scope: str = "all") -> MacroBundle:
        """scope='fast' -> policy rates, yields, VIX only; scope='all' -> everything."""


class NewsProvider(Provider):
    @abstractmethod
    def fetch(self, session=None) -> list[NewsObs]: ...


class CalendarProvider(Provider):
    @abstractmethod
    def fetch(self, start: date, end: date) -> list[EventObs]: ...
