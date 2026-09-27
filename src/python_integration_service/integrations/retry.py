import random
import time
from collections.abc import Callable
from typing import TypeVar

from python_integration_service.integrations.exceptions import (
    RateLimitError,
    TransientIntegrationError,
)

T = TypeVar("T")


class RetryPolicy:
    def __init__(
        self,
        max_attempts: int,
        base_delay: float,
        max_retry_after_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[float, float], float] = random.uniform,
    ) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be greater than 0")

        if base_delay < 0:
            raise ValueError("base_delay must be greater than or equal to 0")

        if max_retry_after_seconds <= 0:
            raise ValueError("max_retry_after_seconds must be greater than 0")

        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_retry_after_seconds = max_retry_after_seconds
        self._sleep = sleep
        self._jitter = jitter

    def execute(
        self,
        operation: Callable[[], T],
    ) -> T:
        for attempt in range(1, self._max_attempts + 1):
            try:
                return operation()

            except TransientIntegrationError as exc:
                if attempt == self._max_attempts:
                    raise

                delay = self._calculate_delay(
                    exception=exc,
                    attempt=attempt,
                )

                if delay is None:
                    raise

                self._sleep(delay)

        raise RuntimeError("Retry policy reached an unreachable state")

    def _calculate_delay(
        self,
        exception: TransientIntegrationError,
        attempt: int,
    ) -> float | None:
        if (
            isinstance(exception, RateLimitError)
            and exception.retry_after_seconds is not None
            and exception.retry_after_seconds > self._max_retry_after_seconds
        ):
            return None

        backoff_window = self._base_delay * (2 ** (attempt - 1))

        local_delay = self._jitter(
            0.0,
            backoff_window,
        )

        if (
            isinstance(exception, RateLimitError)
            and exception.retry_after_seconds is not None
        ):
            return max(
                local_delay,
                exception.retry_after_seconds,
            )

        return local_delay
