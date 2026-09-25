from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import JobState, QuotaUsage
from ..providers.registry import build_chain
from ..schemas import StatusOut
from ..services.auth import current_user
from ..timeutil import today_utc

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status", response_model=StatusOut)
def status(session: Session = Depends(get_db), _=Depends(current_user)):
    settings = get_settings()
    jobs = [{"name": j.name, "last_run": j.last_run, "status": j.last_status, "error": j.last_error,
            "detail": j.last_detail} for j in session.execute(select(JobState)).scalars().all()]
    providers = {
        "fx": [p.name for p in build_chain("fx", settings.fx_chain)],
        "macro": [p.name for p in build_chain("macro", settings.macro_chain)],
        "news": [p.name for p in build_chain("news", settings.news_chain)],
        "calendar": [p.name for p in build_chain("calendar", settings.calendar_chain)],
    }
    quota = {}
    for row in session.execute(select(QuotaUsage).where(QuotaUsage.day == today_utc())).scalars().all():
        quota[row.provider] = {"used_today": row.used}
    return StatusOut(demo_mode=settings.demo_mode, jobs=jobs, providers=providers, quota=quota)
