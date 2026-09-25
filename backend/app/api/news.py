from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import NewsOut
from ..services.auth import current_user
from ..services.repo import recent_news

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("", response_model=list[NewsOut])
def list_news(currency: str | None = Query(default=None), hours: int = Query(default=72, le=24 * 14),
             limit: int = Query(default=100, le=300), session: Session = Depends(get_db), _=Depends(current_user)):
    items = recent_news(session, currency.upper() if currency else None, hours=hours, limit=limit)
    return [NewsOut(id=i.id, currency=i.currency, headline=i.headline, summary=i.summary, published_at=i.published_at,
                    source=i.source, source_url=i.source_url, category=i.category, tone=i.tone, impact=i.impact)
            for i in items]
