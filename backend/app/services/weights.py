"""Editable scoring weights, stored in the `settings` table so an admin can retune the model
without a redeploy. Falls back to DEFAULT_WEIGHTS."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..constants import DEFAULT_WEIGHTS, FACTORS
from ..models import Setting

KEY = "scoring_weights"


def current_weights(session: Session) -> dict[str, float]:
    row = session.get(Setting, KEY)
    if not row or not isinstance(row.value, dict):
        return dict(DEFAULT_WEIGHTS)
    w = {k: float(row.value.get(k, DEFAULT_WEIGHTS[k])) for k in FACTORS}
    total = sum(w.values())
    return {k: v / total for k, v in w.items()} if total else dict(DEFAULT_WEIGHTS)


def set_weights(session: Session, weights: dict[str, float]) -> dict[str, float]:
    bad = set(weights) - set(FACTORS)
    if bad:
        raise ValueError(f"unknown factor(s): {sorted(bad)}")
    merged = {**DEFAULT_WEIGHTS, **weights}
    row = session.get(Setting, KEY)
    if row is None:
        row = Setting(key=KEY, value=merged)
        session.add(row)
    else:
        row.value = merged
    session.commit()
    return current_weights(session)
