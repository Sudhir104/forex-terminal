from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..constants import CURRENCIES
from ..db import get_db
from ..schemas import CurrencyScoreOut, ExplainOut
from ..services.auth import current_user
from ..services.explain import explain
from ..services.scoring import score_currency
from ..services.weights import current_weights
from . import deps

router = APIRouter(prefix="/api/currencies", tags=["currencies"])


@router.get("", response_model=list[CurrencyScoreOut])
def list_currencies(session: Session = Depends(get_db), _=Depends(current_user)):
    out = []
    for ccy in CURRENCIES:
        row = deps.latest_score_row(session, ccy)
        out.append(deps.row_to_out(row) if row else deps.result_to_out(score_currency(session, ccy)))
    return out


@router.get("/{currency}", response_model=CurrencyScoreOut)
def get_currency(currency: str, session: Session = Depends(get_db), _=Depends(current_user)):
    currency = currency.upper()
    if currency not in CURRENCIES:
        raise HTTPException(404, f"Unknown currency {currency}")
    row = deps.latest_score_row(session, currency)
    return deps.row_to_out(row) if row else deps.result_to_out(score_currency(session, currency))


@router.get("/{currency}/explain", response_model=ExplainOut)
def explain_currency(currency: str, session: Session = Depends(get_db), _=Depends(current_user)):
    currency = currency.upper()
    if currency not in CURRENCIES:
        raise HTTPException(404, f"Unknown currency {currency}")
    result = score_currency(session, currency)  # recompute fresh evidence for the explanation
    return explain(session, result)
