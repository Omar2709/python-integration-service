import random
import time
from collections.abc import Callable
from typing import TypeVar

from python_integration_service.integrations.exceptions import (
    RateLimitError,
    RetryBudgetExceededError,
    TransientIntegrationError,
)

T = TypeVar("T")


def _retry_all_transient(
    error: TransientIntegrationError,
) -> bool:
    return True


class RetryPolicy:
    def __init__(
        self,
        max_attempts: int,
        base_delay: float,
        max_retry_after_seconds: float,
        retry_budget_seconds: float | None = None,
        retry_if: Callable[
            [TransientIntegrationError],
            bool,
        ] = _retry_all_transient,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[float, float], float] = random.uniform,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be greater than 0")

        if base_delay < 0:
            raise ValueError("base_delay must be greater than or equal to 0")

        if max_retry_after_seconds <= 0:
            raise ValueError("max_retry_after_seconds must be greater than 0")

        if retry_budget_seconds is not None and retry_budget_seconds <= 0:
            raise ValueError("retry_budget_seconds must be greater than 0")

        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_retry_after_seconds = max_retry_after_seconds
        self._retry_budget_seconds = retry_budget_seconds
        self._retry_if = retry_if
        self._sleep = sleep
        self._jitter = jitter
        self._clock = clock

    def execute(
        self,
        operation: Callable[[], T],
    ) -> T:
        deadline = self._create_deadline()

        for attempt in range(1, self._max_attempts + 1):
            try:
                return operation()

            except TransientIntegrationError as exc:
                if attempt == self._max_attempts:
                    raise

                retry_decision = self._retry_if(exc)

                if not isinstance(retry_decision, bool):
                    raise TypeError("retry_if must return a bool")

                if not retry_decision:
                    raise

                delay = self._calculate_delay(
                    exception=exc,
                    attempt=attempt,
                )

                if delay is None:
                    raise

                self._ensure_retry_can_be_scheduled(
                    deadline=deadline,
                    delay=delay,
                    cause=exc,
                )

                self._sleep(delay)

                self._ensure_deadline_has_not_expired(
                    deadline=deadline,
                    cause=exc,
                )

        raise RuntimeError("Retry policy reached an unreachable state")

    def _create_deadline(self) -> float | None:
        if self._retry_budget_seconds is None:
            return None

        return self._clock() + self._retry_budget_seconds

    def _ensure_retry_can_be_scheduled(
        self,
        *,
        deadline: float | None,
        delay: float,
        cause: TransientIntegrationError,
    ) -> None:
        if deadline is None:
            return

        remaining = deadline - self._clock()

        if remaining <= 0 or delay >= remaining:
            raise RetryBudgetExceededError(
                "Retry budget exhausted before another attempt could be scheduled"
            ) from cause

    def _ensure_deadline_has_not_expired(
        self,
        *,
        deadline: float | None,
        cause: TransientIntegrationError,
    ) -> None:
        if deadline is None:
            return

        if self._clock() >= deadline:
            raise RetryBudgetExceededError(
                "Retry budget exhausted before another attempt could start"
            ) from cause

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
