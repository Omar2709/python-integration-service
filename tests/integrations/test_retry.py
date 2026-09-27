from unittest.mock import MagicMock, call

import pytest

from python_integration_service.integrations.exceptions import (
    AuthenticationError,
    RateLimitError,
    UpstreamTimeoutError,
)
from python_integration_service.integrations.retry import RetryPolicy


def test_retry_policy_returns_without_retry_on_first_success() -> None:
    operation = MagicMock(return_value="ok")
    sleep = MagicMock()
    jitter = MagicMock()

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
    )

    result = policy.execute(operation)

    assert result == "ok"
    operation.assert_called_once_with()
    sleep.assert_not_called()
    jitter.assert_not_called()


def test_retry_policy_uses_exponential_backoff_with_jitter() -> None:
    operation = MagicMock(
        side_effect=[
            UpstreamTimeoutError("timeout 1"),
            UpstreamTimeoutError("timeout 2"),
            "ok",
        ]
    )
    sleep = MagicMock()
    jitter = MagicMock(
        side_effect=[
            0.4,
            1.25,
        ]
    )

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
    )

    result = policy.execute(operation)

    assert result == "ok"
    assert operation.call_count == 3

    assert jitter.call_args_list == [
        call(0.0, 1.0),
        call(0.0, 2.0),
    ]

    assert sleep.call_args_list == [
        call(0.4),
        call(1.25),
    ]


def test_retry_policy_does_not_retry_non_transient_errors() -> None:
    operation = MagicMock(side_effect=AuthenticationError("invalid credentials"))
    sleep = MagicMock()
    jitter = MagicMock()

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
    )

    with pytest.raises(
        AuthenticationError,
        match="invalid credentials",
    ):
        policy.execute(operation)

    operation.assert_called_once_with()
    sleep.assert_not_called()
    jitter.assert_not_called()


def test_retry_policy_propagates_after_max_attempts() -> None:
    operation = MagicMock(side_effect=UpstreamTimeoutError("timeout"))
    sleep = MagicMock()
    jitter = MagicMock(return_value=0.5)

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
    )

    with pytest.raises(
        UpstreamTimeoutError,
        match="timeout",
    ):
        policy.execute(operation)

    assert operation.call_count == 3
    assert sleep.call_count == 2
    assert jitter.call_count == 2


def test_retry_policy_respects_larger_retry_after() -> None:
    operation = MagicMock(
        side_effect=[
            RateLimitError(
                "rate limited",
                retry_after_seconds=30.0,
            ),
            "ok",
        ]
    )
    sleep = MagicMock()
    jitter = MagicMock(return_value=0.75)

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
    )

    result = policy.execute(operation)

    assert result == "ok"

    jitter.assert_called_once_with(
        0.0,
        1.0,
    )
    sleep.assert_called_once_with(30.0)


def test_retry_policy_keeps_larger_local_backoff() -> None:
    operation = MagicMock(
        side_effect=[
            RateLimitError(
                "rate limited",
                retry_after_seconds=0.25,
            ),
            "ok",
        ]
    )
    sleep = MagicMock()
    jitter = MagicMock(return_value=0.75)

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
    )

    result = policy.execute(operation)

    assert result == "ok"
    jitter.assert_called_once_with(0.0, 1.0)
    sleep.assert_called_once_with(0.75)


def test_retry_policy_does_not_retry_excessive_retry_after() -> None:
    error = RateLimitError(
        "rate limited",
        retry_after_seconds=300.0,
    )

    operation = MagicMock(side_effect=error)
    sleep = MagicMock()
    jitter = MagicMock()

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
    )

    with pytest.raises(RateLimitError) as exc_info:
        policy.execute(operation)

    assert exc_info.value is error
    operation.assert_called_once_with()
    sleep.assert_not_called()
    jitter.assert_not_called()


@pytest.mark.parametrize(
    "max_attempts",
    [
        0,
        -1,
    ],
)
def test_retry_policy_rejects_invalid_max_attempts(
    max_attempts: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_attempts must be greater than 0",
    ):
        RetryPolicy(
            max_attempts=max_attempts,
            base_delay=1.0,
            max_retry_after_seconds=60.0,
        )


def test_retry_policy_rejects_negative_base_delay() -> None:
    with pytest.raises(
        ValueError,
        match="base_delay must be greater than or equal to 0",
    ):
        RetryPolicy(
            max_attempts=3,
            base_delay=-1.0,
            max_retry_after_seconds=60.0,
        )


@pytest.mark.parametrize(
    "max_retry_after_seconds",
    [
        0.0,
        -1.0,
    ],
)
def test_retry_policy_rejects_invalid_max_retry_after(
    max_retry_after_seconds: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_retry_after_seconds must be greater than 0",
    ):
        RetryPolicy(
            max_attempts=3,
            base_delay=1.0,
            max_retry_after_seconds=max_retry_after_seconds,
        )
