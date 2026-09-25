from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..constants import ALL_PAIRS, CURRENCIES, split_pair
from ..db import get_db
from ..schemas import CurrencyScoreOut, PairExplainOut, PairOut, PriceOut
from ..services.auth import current_user
from ..services.explain import explain_pair
from ..services.repo import latest_prices
from ..services.scoring import pair_differential, score_currency
from . import deps

router = APIRouter(prefix="/api/pairs", tags=["pairs"])


def _norm(pair: str) -> str:
    return pair.replace("-", "/").replace("_", "/").upper()


def _validate(pair: str) -> tuple[str, str]:
    base, quote = split_pair(pair)
    if base not in CURRENCIES or quote not in CURRENCIES or base == quote:
        raise HTTPException(404, f"Unknown or invalid pair {pair}")
    return base, quote


@router.get("", response_model=list[str])
def list_pairs():
    return ALL_PAIRS


@router.get("/{pair}", response_model=PairOut)
def get_pair(pair: str, session: Session = Depends(get_db), _=Depends(current_user)):
    base, quote = _validate(_norm(pair))
    prices = latest_prices(session, [f"{base}/{quote}"])
    price_row = prices.get(f"{base}/{quote}")
    base_row, quote_row = deps.latest_score_row(session, base), deps.latest_score_row(session, quote)
    base_out = deps.row_to_out(base_row) if base_row else deps.result_to_out(score_currency(session, base))
    quote_out = deps.row_to_out(quote_row) if quote_row else deps.result_to_out(score_currency(session, quote))
    diff = None if base_out.total is None or quote_out.total is None else round(base_out.total - quote_out.total, 2)
    return PairOut(
        pair=f"{base}/{quote}", base=base, quote=quote,
        price=(PriceOut(pair=price_row.pair, mid=price_row.mid, ts=price_row.ts, source=price_row.source,
                        is_reference=price_row.is_reference) if price_row else None),
        base_score=base_out, quote_score=quote_out, differential=diff,
    )


@router.get("/{pair}/explain", response_model=PairExplainOut)
def explain_pair_route(pair: str, session: Session = Depends(get_db), _=Depends(current_user)):
    base, quote = _validate(_norm(pair))
    base_result, quote_result = score_currency(session, base), score_currency(session, quote)
    return explain_pair(session, base_result, quote_result)
