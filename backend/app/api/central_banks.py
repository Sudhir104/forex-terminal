from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import BASE_DIR
from ..constants import CURRENCIES, CURRENCY_META
from ..db import get_db
from ..providers.calendar_official import load_cb_yaml
from ..schemas import CentralBankOut
from ..services.auth import current_user, require_admin
from ..services.repo import latest_rate
from ..models import User

router = APIRouter(prefix="/api/central-banks", tags=["central-banks"])


def _build(session: Session, ccy: str) -> CentralBankOut:
    cfg = load_cb_yaml().get(ccy, {})
    rate_row = latest_rate(session, ccy)
    meetings = sorted(cfg.get("meetings") or [])
    next_meeting = None
    if meetings:
        from datetime import date as _date
        today = _date.today()
        upcoming = [m if isinstance(m, _date) else _date.fromisoformat(str(m)) for m in meetings]
        upcoming = [m for m in upcoming if m >= today]
        next_meeting = min(upcoming) if upcoming else None
    rate = cfg.get("rate")
    return CentralBankOut(
        currency=ccy, bank=cfg.get("bank", CURRENCY_META[ccy]["bank"]), stance=cfg.get("stance"),
        policy_rate=rate_row.rate if rate_row else rate,
        rate_effective_date=rate_row.effective_date if rate_row else cfg.get("as_of"),
        next_meeting=next_meeting, statement_url=cfg.get("statement_url"), notes=cfg.get("notes"),
    )


@router.get("", response_model=list[CentralBankOut])
def list_central_banks(session: Session = Depends(get_db), _=Depends(current_user)):
    return [_build(session, c) for c in CURRENCIES]


@router.get("/{currency}", response_model=CentralBankOut)
def get_central_bank(currency: str, session: Session = Depends(get_db), _=Depends(current_user)):
    currency = currency.upper()
    if currency not in CURRENCIES:
        raise HTTPException(404, f"Unknown currency {currency}")
    return _build(session, currency)


@router.post("/reload")
def reload_central_banks(session: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Re-reads data/central_banks.yaml into the calendar (meeting dates) without a restart."""
    from datetime import date, timedelta

    from ..providers.calendar_official import meetings_to_events
    from ..services.repo import save_events
    from ..timeutil import utcnow as _now
    cfg = load_cb_yaml()
    today = _now().date()
    events = meetings_to_events(cfg, today - timedelta(days=2), today + timedelta(days=365))
    n = save_events(session, events)
    return {"reloaded": True, "currencies": len(cfg), "events_upserted": n}
