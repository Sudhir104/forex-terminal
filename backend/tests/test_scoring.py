from datetime import date, timedelta

from app.providers.base import IndicatorObs, RateObs, YieldObs
from app.services import repo, scoring


def test_no_data_gives_none_total(session):
    r = scoring.score_currency(session, "USD")
    assert r.total is None
    assert r.coverage == 0.0
    assert r.confidence == "none"


def test_rate_hike_raises_monetary_score(session):
    today = date.today()
    repo.save_rate(session, RateObs("USD", "Fed", 4.5, today - timedelta(days=200), "fred"))
    repo.save_rate(session, RateObs("USD", "Fed", 5.5, today - timedelta(days=10), "fred"))
    session.flush()
    result = scoring.factor_monetary(session, "USD")
    assert result.score is not None and result.score > 5.0


def test_rate_cut_lowers_monetary_score(session):
    today = date.today()
    repo.save_rate(session, RateObs("USD", "Fed", 5.5, today - timedelta(days=200), "fred"))
    repo.save_rate(session, RateObs("USD", "Fed", 4.5, today - timedelta(days=10), "fred"))
    session.flush()
    result = scoring.factor_monetary(session, "USD")
    assert result.score is not None and result.score < 5.0


def test_unemployment_is_inverted(session):
    today = date.today()
    repo.save_indicator(session, IndicatorObs("USD", "unemployment", today, 5.0, "fred", previous=4.0))
    session.flush()
    result = scoring.factor_employment(session, "USD")
    # unemployment ROSE -> currency-negative -> score below neutral midpoint
    assert result.score is not None and result.score < 5.0


def test_missing_factor_excluded_from_weighted_average(session):
    today = date.today()
    repo.save_rate(session, RateObs("USD", "Fed", 5.0, today - timedelta(days=10), "fred"))
    session.flush()
    result = scoring.score_currency(session, "USD")
    assert result.total is not None
    assert result.factors["inflation"] is None
    assert result.coverage < 1.0


def test_yield_spread_beats_absolute_level(session):
    today = date.today()
    repo.save_yield(session, YieldObs("EUR", "10Y", 3.0, today, "ecb"))
    session.flush()
    lower_us = scoring.factor_yields(session, "EUR", usd_10y=2.0)
    higher_us = scoring.factor_yields(session, "EUR", usd_10y=4.0)
    assert lower_us.score > higher_us.score


def test_surprise_prefers_forecast_over_previous(session):
    today = date.today()
    repo.save_indicator(session, IndicatorObs("USD", "cpi_yoy", today, 3.5, "fred", previous=3.0, forecast=3.6))
    session.flush()
    result, method = scoring.factor_surprise(session, "USD")
    assert method == "vs_forecast"


def test_pair_differential(session):
    from app.services.scoring import ScoreResult
    scores = {
        "USD": ScoreResult("USD", 7.0, 1.0, "high", "none", {}, {}, {}),
        "EUR": ScoreResult("EUR", 5.0, 1.0, "high", "none", {}, {}, {}),
    }
    assert scoring.pair_differential(scores, "USD", "EUR") == 2.0
    assert scoring.pair_differential(scores, "EUR", "USD") == -2.0
