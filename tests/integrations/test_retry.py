from unittest.mock import MagicMock, call

import pytest

from python_integration_service.integrations.exceptions import (
    AuthenticationError,
    RateLimitError,
    RetryBudgetExceededError,
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
    error = AuthenticationError("invalid credentials")
    clock = MagicMock(
        side_effect=[
            100.0,
            106.0,
        ]
    )

    def operation() -> str:
        clock()
        raise error

    sleep = MagicMock()
    jitter = MagicMock()

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
        retry_budget_seconds=5.0,
        clock=clock,
    )

    with pytest.raises(AuthenticationError) as exc_info:
        policy.execute(operation)

    assert exc_info.value is error
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


def test_retry_policy_does_not_retry_when_predicate_rejects_error() -> None:
    error = UpstreamTimeoutError("timeout")
    operation = MagicMock(side_effect=error)
    retry_if = MagicMock(return_value=False)
    sleep = MagicMock()
    jitter = MagicMock()

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        retry_if=retry_if,
        sleep=sleep,
        jitter=jitter,
    )

    with pytest.raises(UpstreamTimeoutError) as exc_info:
        policy.execute(operation)

    assert exc_info.value is error
    operation.assert_called_once_with()
    retry_if.assert_called_once_with(error)
    jitter.assert_not_called()
    sleep.assert_not_called()


def test_retry_policy_retries_when_predicate_accepts_error() -> None:
    error = UpstreamTimeoutError("timeout")
    operation = MagicMock(
        side_effect=[
            error,
            "ok",
        ]
    )
    retry_if = MagicMock(return_value=True)
    sleep = MagicMock()
    jitter = MagicMock(return_value=0.25)

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        retry_if=retry_if,
        sleep=sleep,
        jitter=jitter,
    )

    result = policy.execute(operation)

    assert result == "ok"
    retry_if.assert_called_once_with(error)
    sleep.assert_called_once_with(0.25)


def test_retry_policy_does_not_evaluate_predicate_after_max_attempts() -> None:
    error = UpstreamTimeoutError("timeout")
    operation = MagicMock(side_effect=error)
    retry_if = MagicMock(return_value=True)

    policy = RetryPolicy(
        max_attempts=1,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        retry_if=retry_if,
    )

    with pytest.raises(UpstreamTimeoutError) as exc_info:
        policy.execute(operation)

    assert exc_info.value is error
    retry_if.assert_not_called()


def test_retry_policy_propagates_predicate_exception() -> None:
    operation = MagicMock(side_effect=UpstreamTimeoutError("timeout"))
    retry_if = MagicMock(side_effect=RuntimeError("policy bug"))

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        retry_if=retry_if,
    )

    with pytest.raises(
        RuntimeError,
        match="policy bug",
    ):
        policy.execute(operation)

    assert operation.call_count == 1


@pytest.mark.parametrize(
    "invalid_decision",
    [
        pytest.param("yes", id="string"),
        pytest.param(1, id="integer"),
        pytest.param(None, id="none"),
    ],
)
def test_retry_policy_rejects_non_boolean_predicate_result(
    invalid_decision: object,
) -> None:
    operation = MagicMock(side_effect=UpstreamTimeoutError("timeout"))

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        retry_if=MagicMock(return_value=invalid_decision),
    )

    with pytest.raises(
        TypeError,
        match="retry_if must return a bool",
    ):
        policy.execute(operation)

    operation.assert_called_once_with()


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
    clock = MagicMock(return_value=100.0)

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
        retry_budget_seconds=5.0,
        clock=clock,
    )

    with pytest.raises(RateLimitError) as exc_info:
        policy.execute(operation)

    assert exc_info.value is error
    operation.assert_called_once_with()
    sleep.assert_not_called()
    jitter.assert_not_called()


def test_retry_policy_rejects_retry_after_that_exceeds_remaining_budget() -> None:
    error = RateLimitError(
        "rate limited",
        retry_after_seconds=4.0,
    )
    operation = MagicMock(side_effect=error)
    sleep = MagicMock()
    clock = MagicMock(
        side_effect=[
            100.0,
            102.0,
        ]
    )

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        retry_budget_seconds=5.0,
        sleep=sleep,
        jitter=MagicMock(return_value=0.5),
        clock=clock,
    )

    with pytest.raises(RetryBudgetExceededError) as exc_info:
        policy.execute(operation)

    assert exc_info.value.__cause__ is error
    operation.assert_called_once_with()
    sleep.assert_not_called()


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


@pytest.mark.parametrize(
    "retry_budget_seconds",
    [
        0.0,
        -1.0,
    ],
)
def test_retry_policy_rejects_non_positive_retry_budget(
    retry_budget_seconds: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="retry_budget_seconds must be greater than 0",
    ):
        RetryPolicy(
            max_attempts=3,
            base_delay=1.0,
            max_retry_after_seconds=60.0,
            retry_budget_seconds=retry_budget_seconds,
        )


def test_retry_policy_without_budget_preserves_attempt_based_behavior() -> None:
    operation = MagicMock(
        side_effect=[
            UpstreamTimeoutError("timeout"),
            "ok",
        ]
    )
    sleep = MagicMock()
    jitter = MagicMock(return_value=5.0)
    clock = MagicMock()

    policy = RetryPolicy(
        max_attempts=2,
        base_delay=5.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
        retry_budget_seconds=None,
        clock=clock,
    )

    assert policy.execute(operation) == "ok"

    sleep.assert_called_once_with(5.0)
    clock.assert_not_called()


def test_retry_policy_fails_when_delay_exceeds_remaining_budget() -> None:
    error = UpstreamTimeoutError("temporary timeout")
    operation = MagicMock(side_effect=error)
    sleep = MagicMock()
    jitter = MagicMock(return_value=4.0)
    clock = MagicMock(
        side_effect=[
            100.0,
            102.0,
        ]
    )

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=4.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=jitter,
        retry_budget_seconds=5.0,
        clock=clock,
    )

    with pytest.raises(RetryBudgetExceededError) as exc_info:
        policy.execute(operation)

    assert exc_info.value.__cause__ is error
    operation.assert_called_once_with()
    sleep.assert_not_called()


def test_retry_policy_rejects_delay_equal_to_remaining_budget() -> None:
    error = UpstreamTimeoutError("temporary timeout")
    operation = MagicMock(side_effect=error)
    sleep = MagicMock()
    clock = MagicMock(
        side_effect=[
            100.0,
            102.0,
        ]
    )

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=3.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=MagicMock(return_value=3.0),
        retry_budget_seconds=5.0,
        clock=clock,
    )

    with pytest.raises(RetryBudgetExceededError) as exc_info:
        policy.execute(operation)

    assert exc_info.value.__cause__ is error
    operation.assert_called_once_with()
    sleep.assert_not_called()


def test_retry_policy_rechecks_deadline_after_sleep() -> None:
    error = UpstreamTimeoutError("temporary timeout")
    operation = MagicMock(side_effect=error)
    clock = MagicMock(
        side_effect=[
            100.0,
            101.0,
            105.1,
        ]
    )
    sleep = MagicMock()

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=2.0,
        max_retry_after_seconds=60.0,
        sleep=sleep,
        jitter=MagicMock(return_value=2.0),
        retry_budget_seconds=5.0,
        clock=clock,
    )

    with pytest.raises(RetryBudgetExceededError) as exc_info:
        policy.execute(operation)

    assert exc_info.value.__cause__ is error
    operation.assert_called_once_with()
    sleep.assert_called_once_with(2.0)


def test_retry_policy_returns_success_from_attempt_started_before_deadline() -> None:
    clock = MagicMock(
        side_effect=[
            100.0,
            101.0,
            102.0,
            106.0,
        ]
    )
    attempt = 0

    def operation() -> str:
        nonlocal attempt
        attempt += 1

        if attempt == 1:
            raise UpstreamTimeoutError("temporary timeout")

        assert clock() == 106.0
        return "ok"

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        sleep=MagicMock(),
        jitter=MagicMock(return_value=1.0),
        retry_budget_seconds=5.0,
        clock=clock,
    )

    assert policy.execute(operation) == "ok"
    assert attempt == 2


def test_retry_policy_preserves_last_error_when_max_attempts_is_exhausted() -> None:
    error = UpstreamTimeoutError("final timeout")
    clock = MagicMock(
        side_effect=[
            100.0,
            106.0,
        ]
    )

    def operation() -> str:
        clock()
        raise error

    policy = RetryPolicy(
        max_attempts=1,
        base_delay=1.0,
        max_retry_after_seconds=60.0,
        retry_budget_seconds=5.0,
        clock=clock,
    )

    with pytest.raises(UpstreamTimeoutError) as exc_info:
        policy.execute(operation)

    assert exc_info.value is error
