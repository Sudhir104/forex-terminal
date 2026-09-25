from app.services.crosses import derive_pairs, missing_currencies, usd_values

QUOTES = {"EUR/USD": 1.10, "GBP/USD": 1.30, "AUD/USD": 0.66, "NZD/USD": 0.60,
         "USD/JPY": 150.0, "USD/CHF": 0.90, "USD/CAD": 1.35}


def test_derives_all_28_pairs_from_7():
    out = derive_pairs(QUOTES)
    assert len(out) == 28


def test_cross_rate_is_consistent_with_usd_legs():
    out = derive_pairs(QUOTES)
    # EUR/GBP should equal (EUR/USD) / (GBP/USD)
    assert abs(out["EUR/GBP"] - (1.10 / 1.30)) < 1e-9


def test_inverse_pair_math():
    out = derive_pairs(QUOTES)
    assert abs(out["CHF/JPY"] - (150.0 / 0.90)) < 1e-9


def test_no_missing_currencies_when_all_legs_present():
    assert missing_currencies(QUOTES) == []


def test_missing_currency_detected():
    partial = dict(QUOTES)
    del partial["USD/JPY"]
    assert "JPY" in missing_currencies(partial)
