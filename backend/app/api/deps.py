from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import FACTOR_LABELS
from ..models import CurrencyScore
from ..schemas import CurrencyScoreOut, FactorOut
from ..services.scoring import ScoreResult


def latest_score_row(session: Session, currency: str) -> CurrencyScore | None:
    return session.execute(select(CurrencyScore).where(CurrencyScore.currency == currency)
                           .order_by(CurrencyScore.computed_at.desc())).scalars().first()


def row_to_out(row: CurrencyScore) -> CurrencyScoreOut:
    return CurrencyScoreOut(
        currency=row.currency, total=row.total, coverage=row.coverage, confidence=row.confidence,
        surprise_method=row.surprise_method, computed_at=row.computed_at,
        factors=[FactorOut(factor=k, label=FACTOR_LABELS.get(k, k), score=v,
                           notes=(row.evidence or {}).get(k, {}).get("notes", ""),
                           stale=bool((row.evidence or {}).get(k, {}).get("stale", False)))
                 for k, v in (row.factors or {}).items()],
    )


def result_to_out(result: ScoreResult, computed_at: datetime | None = None) -> CurrencyScoreOut:
    return CurrencyScoreOut(
        currency=result.currency, total=result.total, coverage=result.coverage, confidence=result.confidence,
        surprise_method=result.surprise_method, computed_at=computed_at,
        factors=[FactorOut(factor=k, label=FACTOR_LABELS.get(k, k), score=v,
                           notes=result.evidence[k]["notes"], stale=bool(result.evidence[k].get("stale", False)))
                 for k, v in result.factors.items()],
    )
