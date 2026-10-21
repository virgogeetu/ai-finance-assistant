"""Sliding-window rate limiter (per-minute and per-day budgets)."""
from __future__ import annotations

import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, per_minute: int, per_day: int, clock=time.time):
        self.per_minute, self.per_day = per_minute, per_day
        self._minute: deque[float] = deque()
        self._day: deque[float] = deque()
        self._clock = clock
        self._lock = threading.Lock()

    def _trim(self, now: float) -> None:
        while self._minute and now - self._minute[0] >= 60:
            self._minute.popleft()
        while self._day and now - self._day[0] >= 86400:
            self._day.popleft()

    def try_acquire(self) -> bool:
        with self._lock:
            now = self._clock()
            self._trim(now)
            if len(self._minute) >= self.per_minute or len(self._day) >= self.per_day:
                return False
            self._minute.append(now)
            self._day.append(now)
            return True

    def remaining(self) -> dict:
        with self._lock:
            self._trim(self._clock())
            return {"minute": self.per_minute - len(self._minute), "day": self.per_day - len(self._day)}
