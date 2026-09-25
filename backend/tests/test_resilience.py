import pytest

from app.providers.resilience import (FAILURE_THRESHOLD, ProviderUnavailable, QuotaExceeded, add_usage,
                                      breaker_open, guarded_call, quota_remaining, record_failure)


class FakeProvider:
    name = "fake"
    daily_credit_limit = 10


def test_quota_blocks_when_exhausted(session):
    add_usage(session, "fake", 9)
    with pytest.raises(QuotaExceeded):
        guarded_call(session, FakeProvider(), lambda: "ok", cost=5)


def test_quota_allows_when_within_budget(session):
    add_usage(session, "fake", 2)
    result = guarded_call(session, FakeProvider(), lambda: "ok", cost=3)
    assert result == "ok"


def test_circuit_opens_after_threshold_failures(session):
    for _ in range(FAILURE_THRESHOLD):
        record_failure(session, "fake", RuntimeError("boom"))
    assert breaker_open(session, "fake") is True


def test_guarded_call_raises_when_breaker_open(session):
    for _ in range(FAILURE_THRESHOLD):
        record_failure(session, "fake", RuntimeError("boom"))
    with pytest.raises(ProviderUnavailable):
        guarded_call(session, FakeProvider(), lambda: "should not run")


def test_successful_call_resets_failure_count(session):
    record_failure(session, "fake", RuntimeError("boom"))
    guarded_call(session, FakeProvider(), lambda: "ok", cost=1)
    assert breaker_open(session, "fake") is False
