import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core import rate_limit
from app.core.rate_limit import RateLimiter


def test_limit_retry_and_expiry():
    now = [0]
    limiter = RateLimiter(clock=lambda: now[0])
    limiter.check("login:ip", 2, 60)
    now[0] = 10
    limiter.check("login:ip", 2, 60)
    with pytest.raises(HTTPException) as error:
        limiter.check("login:ip", 2, 60)
    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "50"
    limiter.check("recovery:ip", 2, 60)
    limiter.check("login:other-ip", 2, 60)
    now[0] = 60
    limiter.check("login:ip", 2, 60)
    now[0] = 121
    limiter.check("fresh", 2, 60)
    assert set(limiter.attempts) == {"fresh"}


def test_limiter_has_bounded_storage():
    limiter = RateLimiter(max_keys=1)
    limiter.check("one", 1, 60)
    with pytest.raises(HTTPException):
        limiter.check("two", 1, 60)
    assert len(limiter.attempts) == 1


def test_untrusted_forwarded_header_cannot_bypass_limit(monkeypatch):
    monkeypatch.setattr(rate_limit, "limiter", RateLimiter())
    monkeypatch.setattr(rate_limit.settings, "login_rate_limit", 1)
    for index in range(2):
        request = Request({"type": "http", "client": ("127.0.0.1", 1234),
                           "headers": [(b"x-forwarded-for", f"192.0.2.{index}".encode())]})
        if index == 0:
            rate_limit.limit_login(request)
        else:
            with pytest.raises(HTTPException):
                rate_limit.limit_login(request)
