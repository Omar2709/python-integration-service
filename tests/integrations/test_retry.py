import pytest

from python_integration_service.integrations.retry import retry


def test_success_on_first_attempt() -> None:
    attempts = {"count": 0}

    @retry(
        max_attempts=3,
        retry_on=(TimeoutError,),
    )
    def operation() -> str:
        attempts["count"] += 1
        return "ok"

    result = operation()

    assert result == "ok"
    assert attempts["count"] == 1


def test_retries_twice_and_then_succeeds() -> None:
    attempts = {"count": 0}

    @retry(
        max_attempts=3,
        retry_on=(TimeoutError,),
    )
    def operation() -> str:
        attempts["count"] += 1

        if attempts["count"] < 3:
            raise TimeoutError("temporary failure")

        return "ok"

    result = operation()

    assert result == "ok"
    assert attempts["count"] == 3


def test_non_retryable_exception_is_propagated_immediately() -> None:
    attempts = {"count": 0}

    @retry(
        max_attempts=3,
        retry_on=(TimeoutError,),
    )
    def operation() -> None:
        attempts["count"] += 1
        raise ValueError("invalid data")

    with pytest.raises(ValueError):
        operation()

    assert attempts["count"] == 1


def test_raises_after_max_attempts_are_exhausted() -> None:
    attempts = {"count": 0}

    @retry(
        max_attempts=3,
        retry_on=(TimeoutError,),
    )
    def operation() -> None:
        attempts["count"] += 1
        raise TimeoutError("vendor unavailable")

    with pytest.raises(TimeoutError):
        operation()

    assert attempts["count"] == 3


@pytest.mark.parametrize(
    "max_attempts",
    [0, -1, -10],
)
def test_invalid_max_attempts_raises_value_error(max_attempts: int) -> None:
    with pytest.raises(
        ValueError,
        match="max_attempts must be greater than 0",
    ):
        retry(
            max_attempts=max_attempts,
            retry_on=(TimeoutError,),
        )


def test_retry_preserves_function_metadata() -> None:
    @retry(
        max_attempts=3,
        retry_on=(TimeoutError,),
    )
    def process_order() -> str:
        """Process an order."""
        return "ok"

    assert process_order.__name__ == "process_order"
    assert process_order.__doc__ == "Process an order."