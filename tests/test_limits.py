from __future__ import annotations

from src.backend.api.limits import SlidingWindowLimiter


def test_sliding_window_rejects_burst_and_opens_after_expiry():
    now = [100.0]
    limiter = SlidingWindowLimiter(2, 10, clock=lambda: now[0])

    assert limiter.allow("customer-1")
    assert limiter.allow("customer-1")
    assert not limiter.allow("customer-1")
    assert 1 <= limiter.retry_after("customer-1") <= 10

    now[0] = 110.01
    assert limiter.allow("customer-1")
    assert limiter.allow("customer-2")


def test_limiter_keeps_keys_isolated():
    limiter = SlidingWindowLimiter(1, 60)
    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")
