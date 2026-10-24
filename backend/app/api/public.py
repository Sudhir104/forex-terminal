from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..constants import CURRENCIES
from ..db import get_db
from ..services.scoring import score_currency
from . import deps

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/currencies")
def public_currencies(session: Session = Depends(get_db)):
    out = []
    for ccy in CURRENCIES:
        row = deps.latest_score_row(session, ccy)
        if row:
            out.append({"currency": ccy, "total": row.total, "confidence": row.confidence,
                       "computed_at": row.computed_at.isoformat() if row.computed_at else None})
        else:
            r = score_currency(session, ccy)
            out.append({"currency": ccy, "total": r.total, "confidence": r.confidence, "computed_at": None})
    return out