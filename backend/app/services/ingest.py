"""Ingestion orchestrator: pulls from provider chains with fallback, quota-awareness and a circuit
breaker, writes normalised data, and records what happened in JobState so /api/status can show it.
This is the ONLY place that knows about provider chains - everything else reads the database.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..constants import ALL_PAIRS, CURRENCIES, FETCH_PAIRS
from ..models import JobState
from ..providers.registry import build_chain
from ..providers.resilience import ProviderUnavailable, QuotaExceeded, guarded_call, quota_aware_interval
from ..timeutil import utcnow
from . import repo
from .crosses import derive_pairs

log = logging.getLogger("ingest")


def _record(session: Session, name: str, status: str, error: Optional[str] = None, detail: Optional[str] = None) -> None:
    row = session.get(JobState, name)
    if row is None:
        row = JobState(name=name)
        session.add(row)
    row.last_run, row.last_status, row.last_error, row.last_detail = utcnow(), status, error, detail
    session.commit()


def ingest_fx(session: Session, settings: Optional[Settings] = None) -> dict:
    settings = settings or get_settings()
    chain = build_chain("fx", settings.fx_chain)
    errors: list[str] = []
    for provider in chain:
        try:
            cost = provider.cost(FETCH_PAIRS) if hasattr(provider, "cost") else len(FETCH_PAIRS)
            quotes = guarded_call(session, provider, lambda: provider.fetch_quotes(FETCH_PAIRS), cost=cost)
            n = repo.save_quotes(session, quotes)
            fetched = {q.pair: q.mid for q in quotes}
            crosses = derive_pairs(fetched, [p for p in ALL_PAIRS if p not in fetched])
            from ..providers.base import PriceQuote
            n += repo.save_quotes(session, [PriceQuote(pair=p, mid=v, ts=utcnow(), source=f"{provider.name}+cross")
                                            for p, v in crosses.items()])
            session.commit()
            _record(session, "fx", "ok", detail=f"{provider.name}: {n} prices ({len(fetched)} fetched + {len(crosses)} crosses)")
            return {"provider": provider.name, "saved": n, "errors": errors}
        except (ProviderUnavailable, QuotaExceeded) as e:
            errors.append(str(e))
            continue
        except Exception as e:  # noqa: BLE001
            errors.append(f"{provider.name}: {e}")
            continue
    _record(session, "fx", "failed", error="; ".join(errors) or "no fx provider configured")
    return {"provider": None, "saved": 0, "errors": errors}


def next_fx_interval(session: Session, settings: Optional[Settings] = None) -> float:
    settings = settings or get_settings()
    chain = build_chain("fx", settings.fx_chain)
    if not chain:
        return settings.fx_idle_interval
    p = chain[0]
    return quota_aware_interval(session, p.name, getattr(p, "daily_credit_limit", None),
                                p.cost(FETCH_PAIRS) if hasattr(p, "cost") else len(FETCH_PAIRS),
                                settings.fx_active_interval)


def ingest_macro(session: Session, scope: str = "all", settings: Optional[Settings] = None) -> dict:
    settings = settings or get_settings()
    chain = build_chain("macro", settings.macro_chain)
    if not chain:
        _record(session, f"macro_{scope}", "failed", error="no macro provider configured")
        return {"providers": [], "counts": {}, "errors": ["no macro provider configured"]}
    counts = {"indicators": 0, "rates": 0, "yields": 0}
    errors: list[str] = []
    used: list[str] = []
    remaining = list(CURRENCIES)
    for provider in chain:
        if not remaining:
            break
        want = [c for c in remaining if not provider.covers or c in provider.covers]
        if not want:
            continue
        try:
            bundle = guarded_call(session, provider, lambda: provider.fetch(want, scope=scope))
            c = repo.save_macro_bundle(session, bundle)
            for k in counts:
                counts[k] += c[k]
            errors += bundle.errors
            used.append(provider.name)
            session.commit()
            covered = {ccy for ccy in want if any(r.currency == ccy for r in bundle.rates)
                      or any(y.currency == ccy for y in bundle.yields)
                      or any(i.currency == ccy for i in bundle.indicators)}
            remaining = [c for c in remaining if c not in covered] if scope == "all" else \
                        [c for c in remaining if c not in {y.currency for y in bundle.yields} & {r.currency for r in bundle.rates}]
        except (ProviderUnavailable, QuotaExceeded) as e:
            errors.append(str(e))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{provider.name}: {e}")
    status = "ok" if used else "failed"
    _record(session, f"macro_{scope}", status, error="; ".join(errors[:5]) if errors and status == "failed" else None,
           detail=f"providers={used} counts={counts}" + (f" uncovered={remaining}" if remaining else ""))
    return {"providers": used, "counts": counts, "errors": errors, "uncovered": remaining}


def ingest_news(session: Session, settings: Optional[Settings] = None) -> dict:
    settings = settings or get_settings()
    chain = build_chain("news", settings.news_chain)
    total, errors, used = 0, [], []
    for provider in chain:
        try:
            items = guarded_call(session, provider, lambda: provider.fetch(session=session))
            n = repo.save_news(session, items)
            session.commit()
            total += n
            used.append(provider.name)
            errors += getattr(provider, "errors", [])
        except (ProviderUnavailable, QuotaExceeded) as e:
            errors.append(str(e))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{provider.name}: {e}")
    status = "ok" if used else "failed"
    _record(session, "news", status, error="; ".join(errors[:5]) if status == "failed" else None,
           detail=f"providers={used} new_items={total}" + (f" feed_errors={len(errors)}" if errors else ""))
    return {"providers": used, "saved": total, "errors": errors}


def ingest_calendar(session: Session, settings: Optional[Settings] = None) -> dict:
    settings = settings or get_settings()
    chain = build_chain("calendar", settings.calendar_chain)
    start, end = utcnow().date() - timedelta(days=2), utcnow().date() + timedelta(days=21)
    total, errors, used = 0, [], []
    for provider in chain:
        try:
            events = guarded_call(session, provider, lambda: provider.fetch(start, end))
            n = repo.save_events(session, events)
            session.commit()
            total += n
            used.append(provider.name)
            errors += getattr(provider, "errors", [])
        except (ProviderUnavailable, QuotaExceeded) as e:
            errors.append(str(e))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{provider.name}: {e}")
    status = "ok" if used else "failed"
    _record(session, "calendar", status, error="; ".join(errors[:5]) if status == "failed" else None,
           detail=f"providers={used} new_events={total}")
    return {"providers": used, "saved": total, "errors": errors}


def recompute_scores(session: Session, settings: Optional[Settings] = None) -> dict:
    from datetime import datetime as _dt

    from ..config import get_settings as _gs
    from ..models import CurrencyScore
    from .scoring import score_all
    from .weights import current_weights

    settings = settings or _gs()
    weights = current_weights(session)
    scores = score_all(session, weights=weights)
    now = utcnow()
    for ccy, r in scores.items():
        session.add(CurrencyScore(currency=ccy, computed_at=now, total=r.total or 0.0, coverage=r.coverage,
                                  confidence=r.confidence, surprise_method=r.surprise_method, factors=r.factors,
                                  evidence=r.evidence, weights=r.weights, is_demo=settings.demo_mode))
    session.commit()
    _record(session, "scores", "ok", detail=f"{len(scores)} currencies scored")
    return {ccy: r.total for ccy, r in scores.items()}
