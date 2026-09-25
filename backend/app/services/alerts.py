"""Threshold alerts -> Telegram. Free, and the notification channel the blueprint recommended
for a small private group."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..models import AlertLog, CurrencyScore
from ..providers import http
from ..timeutil import utcnow


def send_telegram(settings: Settings, text: str) -> bool:
    if not (settings.telegram_bot_token and settings.telegram_chat_id):
        return False
    try:
        http.post_json(f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                       {"chat_id": settings.telegram_chat_id, "text": text, "parse_mode": "HTML"})
        return True
    except Exception:  # noqa: BLE001
        return False


def _log_once(session: Session, key: str, message: str, settings: Settings) -> bool:
    if session.get(AlertLog, key):
        return False
    delivered = send_telegram(settings, message)
    session.add(AlertLog(key=key, message=message, delivered=delivered))
    session.commit()
    return True


def check_score_moves(session: Session, settings: Optional[Settings] = None) -> list[str]:
    """Alerts when a currency's total score moves by more than ALERT_SCORE_MOVE since its previous snapshot."""
    settings = settings or get_settings()
    from sqlalchemy import select
    fired: list[str] = []
    currencies = {r[0] for r in session.execute(select(CurrencyScore.currency).distinct())}
    for ccy in currencies:
        rows = session.execute(select(CurrencyScore).where(CurrencyScore.currency == ccy)
                               .order_by(CurrencyScore.computed_at.desc()).limit(2)).scalars().all()
        if len(rows) < 2:
            continue
        latest, prior = rows
        move = latest.total - prior.total
        if abs(move) < settings.alert_score_move:
            continue
        key = f"score_move:{ccy}:{latest.computed_at.isoformat()}"
        msg = f"\U0001F514 {ccy} strength moved {move:+.2f} to {latest.total}/10 ({prior.total} -> {latest.total})."
        if _log_once(session, key, msg, settings):
            fired.append(msg)
    return fired
