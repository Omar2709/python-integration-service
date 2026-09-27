import threading
import time
from collections.abc import Callable
from typing import Protocol

_TOKEN_EPSILON = 1e-12


class RateLimiter(Protocol):
    def acquire(self) -> None: ...


class NoOpRateLimiter:
    def acquire(self) -> None:
        pass


class TokenBucketRateLimiter:
    def __init__(
        self,
        requests_per_second: float,
        capacity: int,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be greater than 0")

        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")

        self._rate = requests_per_second
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._clock = clock
        self._sleep = sleep
        self._last_refill = clock()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                self._refill(now)

                if self._tokens + _TOKEN_EPSILON >= 1.0:
                    self._tokens = max(
                        0.0,
                        self._tokens - 1.0,
                    )
                    return

                missing_tokens = 1.0 - self._tokens
                wait_seconds = missing_tokens / self._rate

            self._sleep(wait_seconds)

    def _refill(self, now: float) -> None:
        elapsed = now - self._last_refill

        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._rate,
        )
        self._last_refill = now
