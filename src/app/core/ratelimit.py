"""
Minimal in-memory sliding-window rate limiter.

Suitable for the single-process deployment used here. For multi-process or
multi-instance setups, back this with Redis instead.
"""
import threading
import time
from collections import defaultdict


class SlidingWindowLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._events: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Record an attempt and return True if it is allowed."""
        now = time.time()
        cutoff = now - self.window
        with self._lock:
            events = self._events[key]
            events[:] = [t for t in events if t > cutoff]
            if len(events) >= self.max_attempts:
                return False
            events.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
