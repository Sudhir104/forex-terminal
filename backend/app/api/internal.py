"""Cron-triggered ingestion endpoint, for when the scheduler runs externally (GitHub Actions,
cron-job.org) instead of Render's in-process APScheduler - this is how you dodge Render free-tier
sleep for time-sensitive collectors without paying for an always-on instance."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import session_scope
from ..services import ingest

router = APIRouter(prefix="/api/internal", tags=["internal"])


def _check(token: str | None) -> None:
    settings = get_settings()
    if not settings.cron_token:
        raise HTTPException(503, "CRON_TOKEN not configured on the server")
    if token != settings.cron_token:
        raise HTTPException(401, "Bad or missing X-Cron-Token")


@router.post("/tick/{job}")
def tick(job: str, x_cron_token: str | None = Header(default=None)):
    _check(x_cron_token)
    with session_scope() as session:
        if job == "fx":
            return ingest.ingest_fx(session)
        if job == "macro-fast":
            return ingest.ingest_macro(session, scope="fast")
        if job == "macro-full":
            return ingest.ingest_macro(session, scope="all")
        if job == "news":
            return ingest.ingest_news(session)
        if job == "calendar":
            return ingest.ingest_calendar(session)
        if job == "scores":
            return ingest.recompute_scores(session)
        if job == "alerts":
            from ..services.alerts import check_score_moves
            return {"fired": check_score_moves(session)}
        raise HTTPException(404, f"Unknown job '{job}'")
