from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    is_admin: bool


class FactorOut(BaseModel):
    factor: str
    label: str
    score: Optional[float]
    notes: str
    stale: bool = False


class CurrencyScoreOut(BaseModel):
    currency: str
    total: Optional[float]
    coverage: float
    confidence: str
    surprise_method: str
    computed_at: Optional[datetime] = None
    factors: list[FactorOut]


class PriceOut(BaseModel):
    pair: str
    mid: float
    ts: datetime
    source: str
    is_reference: bool = False


class PairOut(BaseModel):
    pair: str
    base: str
    quote: str
    price: Optional[PriceOut]
    base_score: CurrencyScoreOut
    quote_score: CurrencyScoreOut
    differential: Optional[float]


class ExplainOut(BaseModel):
    text: str
    origin: str
    drivers: list[str] = Field(default_factory=list)


class PairExplainOut(BaseModel):
    text: str
    origin: str
    differential: Optional[float]


class NewsOut(BaseModel):
    id: int
    currency: str
    headline: str
    summary: Optional[str]
    published_at: datetime
    source: str
    source_url: str
    category: str
    tone: float
    impact: str


class EventOut(BaseModel):
    id: int
    currency: str
    title: str
    event_date: date
    event_time: Optional[datetime]
    impact: str
    kind: str
    actual: Optional[str]
    forecast: Optional[str]
    previous: Optional[str]
    source: str
    source_url: Optional[str]


class CentralBankOut(BaseModel):
    currency: str
    bank: str
    stance: Optional[str]
    policy_rate: Optional[float]
    rate_effective_date: Optional[date]
    next_meeting: Optional[date]
    statement_url: Optional[str]
    notes: Optional[str]


class WeightsIn(BaseModel):
    weights: dict[str, float]


class StatusOut(BaseModel):
    demo_mode: bool
    jobs: list[dict]
    providers: dict[str, list[str]]
    quota: dict[str, dict]
