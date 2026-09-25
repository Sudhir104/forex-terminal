"""In-process background jobs (used when ENABLE_SCHEDULER=true, e.g. on a paid always-on instance
or when running locally). On Render's free tier, use the cron endpoints in api/internal.py instead,
driven by GitHub Actions - see .github/workflows/cron.yml - so ingestion keeps happening while the
web service sleeps."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .config import get_settings
from .db import session_scope
from .services import ingest

log = logging.getLogger("scheduler")
_scheduler: BackgroundScheduler | None = None


def _run(job_name: str, fn) -> None:
    try:
        with session_scope() as session:
            fn(session)
    except Exception:  # noqa: BLE001 - a failed job must not kill the scheduler thread
        log.exception("scheduled job failed: %s", job_name)


def _fx_job() -> None:
    with session_scope() as session:
        ingest.ingest_fx(session)
    # Re-schedule itself at a quota-aware interval so the free daily credit budget lasts until midnight.
    settings = get_settings()
    with session_scope() as session:
        interval = ingest.next_fx_interval(session, settings)
    if _scheduler and _scheduler.get_job("fx"):
        _scheduler.reschedule_job("fx", trigger="interval", seconds=max(15, interval))


def start(app_settings=None) -> BackgroundScheduler | None:
    global _scheduler
    settings = app_settings or get_settings()
    if not settings.enable_scheduler:
        return None
    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(_fx_job, "interval", seconds=settings.fx_active_interval, id="fx", next_run_time=None)
    sched.add_job(lambda: _run("macro_fast", lambda s: ingest.ingest_macro(s, scope="fast")), "interval",
                 seconds=settings.macro_fast_interval, id="macro_fast")
    sched.add_job(lambda: _run("macro_full", lambda s: ingest.ingest_macro(s, scope="all")), "interval",
                 seconds=settings.macro_full_interval, id="macro_full")
    sched.add_job(lambda: _run("news", ingest.ingest_news), "interval", seconds=settings.news_interval, id="news")
    sched.add_job(lambda: _run("calendar", ingest.ingest_calendar), "interval",
                 seconds=settings.calendar_interval, id="calendar")
    sched.add_job(lambda: _run("scores", ingest.recompute_scores), "interval",
                 seconds=settings.scores_interval, id="scores")

    def _alerts(session):
        from .services.alerts import check_score_moves
        check_score_moves(session)
    sched.add_job(lambda: _run("alerts", _alerts), "interval", seconds=settings.scores_interval, id="alerts")
    sched.start()
    _scheduler = sched
    log.info("scheduler started")
    return sched


def shutdown() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
