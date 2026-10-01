"""Single-process sliding-window limits; use shared storage with multiple workers."""
import math
import time
from collections import deque
from threading import Lock

from fastapi import HTTPException, Request

from app.core.config import settings


class RateLimiter:
    def __init__(self, clock=time.monotonic, max_keys=10000):
        self.clock = clock
        self.max_keys = max_keys
        self.attempts = {}
        self.lock = Lock()

    def check(self, key: str, limit: int, window: int) -> None:
        with self.lock:
            now = self.clock()
            for old_key, (_, expiry) in list(self.attempts.items()):
                if expiry <= now:
                    del self.attempts[old_key]
            if key not in self.attempts and len(self.attempts) >= self.max_keys:
                self.reject(window)
            events, _ = self.attempts.get(key, (deque(), now))
            while events and events[0] <= now - window:
                events.popleft()
            if len(events) >= limit:
                self.reject(max(1, math.ceil(events[0] + window - now)))
            events.append(now)
            self.attempts[key] = (events, now + window)

    @staticmethod
    def reject(seconds: int) -> None:
        raise HTTPException(429, "Too many attempts. Please try again later.",
                            headers={"Retry-After": str(seconds), "Cache-Control": "no-store"})


limiter = RateLimiter()


def _check(request: Request, action: str, limit: int) -> None:
    # Do not trust caller-supplied X-Forwarded-For headers.
    ip = request.client.host if request.client else "unknown"
    limiter.check(f"{action}:{ip}", limit, settings.auth_rate_window_seconds)


def limit_login(request: Request) -> None:
    _check(request, "login", settings.login_rate_limit)


def limit_recovery(request: Request) -> None:
    _check(request, "recovery", settings.recovery_rate_limit)
