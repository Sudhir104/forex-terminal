"""python -m app.cli <command>

Commands:
  init-db                         create tables
  create-user EMAIL PASSWORD      create a login (first user becomes admin automatically)
  seed-demo                       run one full ingest+score pass using demo providers (no keys needed)
  tick JOB                        run one ingestion job now (fx | macro-fast | macro-full | news | calendar | scores | alerts)
  doctor                          check config, provider keys, and feed/central-bank yaml health
  reload-central-banks            re-read data/central_banks.yaml into the calendar
"""
from __future__ import annotations

import sys

from sqlalchemy import select

from .config import get_settings
from .db import init_db, session_scope
from .models import User
from .services.auth import hash_password
from .services import ingest


def cmd_init_db() -> None:
    init_db()
    print("tables created")


def cmd_create_user(email: str, password: str) -> None:
    init_db()
    with session_scope() as session:
        is_first = session.execute(select(User.id)).first() is None
        if session.execute(select(User).where(User.email == email.lower())).scalar_one_or_none():
            print(f"user {email} already exists")
            return
        user = User(email=email.lower(), password_hash=hash_password(password), is_admin=is_first)
        session.add(user)
        print(f"created {email} (admin={is_first})")


def cmd_seed_demo() -> None:
    import os
    os.environ["DEMO_MODE"] = "true"
    from .config import reset_settings_cache
    reset_settings_cache()
    init_db()
    with session_scope() as session:
        print("fx     ", ingest.ingest_fx(session))
        print("macro  ", ingest.ingest_macro(session))
        print("news   ", ingest.ingest_news(session))
        print("calendar", ingest.ingest_calendar(session))
        print("scores ", ingest.recompute_scores(session))


def cmd_tick(job: str) -> None:
    init_db()
    with session_scope() as session:
        fn = {"fx": ingest.ingest_fx, "macro-fast": lambda s: ingest.ingest_macro(s, "fast"),
             "macro-full": lambda s: ingest.ingest_macro(s, "all"), "news": ingest.ingest_news,
             "calendar": ingest.ingest_calendar, "scores": ingest.recompute_scores}.get(job)
        if job == "alerts":
            from .services.alerts import check_score_moves
            print(check_score_moves(session))
            return
        if fn is None:
            print(f"unknown job {job}")
            sys.exit(1)
        print(fn(session))


def cmd_doctor() -> None:
    settings = get_settings()
    print(f"demo_mode={settings.demo_mode}")
    for kind, chain, key_attr in [
        ("fx", settings.fx_providers, ["twelvedata_api_key"]),
        ("macro", settings.macro_providers, ["fred_api_key"]),
        ("news", settings.news_providers, ["finnhub_api_key"]),
        ("calendar", settings.calendar_providers, ["tradingeconomics_api_key", "fred_api_key"]),
    ]:
        print(f"{kind}_providers = {chain}")
    print(f"twelvedata_api_key set: {bool(settings.twelvedata_api_key)}")
    print(f"fred_api_key set: {bool(settings.fred_api_key)}")
    print(f"database_url = {settings.database_url}")
    from .providers.news_rss import load_feeds
    from . import providers as _p
    from .providers import http as _http
    print(f"\n{len(load_feeds())} RSS feeds configured; checking reachability...")
    for feed in load_feeds():
        try:
            r = _http.get(feed["url"], retries=0, timeout=8)
            print(f"  OK   {feed['name']} ({r.status_code})")
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {feed['name']}: {e}")
    from .providers.calendar_official import load_cb_yaml
    cfg = load_cb_yaml()
    missing = [c for c, row in cfg.items() if not row.get("meetings")]
    if missing:
        print(f"\nNote: no upcoming meeting dates set for {missing} in data/central_banks.yaml")


def cmd_reload_central_banks() -> None:
    from datetime import timedelta

    from .providers.calendar_official import load_cb_yaml, meetings_to_events
    from .services.repo import save_events
    from .timeutil import utcnow
    init_db()
    with session_scope() as session:
        today = utcnow().date()
        events = meetings_to_events(load_cb_yaml(), today - timedelta(days=2), today + timedelta(days=365))
        n = save_events(session, events)
        print(f"upserted {n} central-bank meeting events")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd, rest = args[0], args[1:]
    table = {"init-db": cmd_init_db, "create-user": cmd_create_user, "seed-demo": cmd_seed_demo,
            "tick": cmd_tick, "doctor": cmd_doctor, "reload-central-banks": cmd_reload_central_banks}
    fn = table.get(cmd)
    if fn is None:
        print(f"unknown command {cmd}\n\n{__doc__}")
        sys.exit(1)
    fn(*rest)


if __name__ == "__main__":
    main()
