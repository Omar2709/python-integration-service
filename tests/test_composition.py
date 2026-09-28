from unittest.mock import MagicMock, patch

import pytest
from pydantic import AnyHttpUrl, SecretStr

from python_integration_service.composition import create_vendor_client
from python_integration_service.config import Settings


def make_settings() -> Settings:
    return Settings(
        vendor_base_url=AnyHttpUrl("https://api.example.com"),
        vendor_access_token=SecretStr("test-token"),
        vendor_timeout=15.0,
        vendor_retry_max_attempts=4,
        vendor_retry_base_delay=0.75,
        vendor_retry_max_retry_after_seconds=120.0,
        vendor_retry_budget_seconds=None,
        vendor_rate_limit_requests_per_second=None,
        vendor_rate_limit_capacity=None,
    )


def test_create_vendor_client_wires_dependencies() -> None:
    settings = make_settings()
    transport = MagicMock()
    retry_policy = MagicMock()

    with (
        patch(
            "python_integration_service.composition.HttpxTransport"
        ) as transport_class,
        patch(
            "python_integration_service.composition.RetryPolicy"
        ) as retry_policy_class,
    ):
        transport_class.return_value.__enter__.return_value = transport
        retry_policy_class.return_value = retry_policy

        with create_vendor_client(settings) as client:
            retry_policy_class.assert_called_once_with(
                max_attempts=4,
                base_delay=0.75,
                max_retry_after_seconds=120.0,
                retry_budget_seconds=None,
            )

            transport_class.assert_called_once_with(
                access_token="test-token",
                timeout=15.0,
            )

            assert client.base_url == "https://api.example.com/"
            assert client.transport is transport
            assert client.retry_policy is retry_policy


def test_create_vendor_client_configures_retry_budget() -> None:
    settings = Settings(
        vendor_base_url=AnyHttpUrl("https://api.example.com"),
        vendor_access_token=SecretStr("test-token"),
        vendor_timeout=15.0,
        vendor_retry_max_attempts=4,
        vendor_retry_base_delay=0.75,
        vendor_retry_max_retry_after_seconds=120.0,
        vendor_retry_budget_seconds=10.0,
        vendor_rate_limit_requests_per_second=None,
        vendor_rate_limit_capacity=None,
    )

    with (
        patch("python_integration_service.composition.HttpxTransport"),
        patch(
            "python_integration_service.composition.RetryPolicy"
        ) as retry_policy_class,
        create_vendor_client(settings),
    ):
        retry_policy_class.assert_called_once_with(
            max_attempts=4,
            base_delay=0.75,
            max_retry_after_seconds=120.0,
            retry_budget_seconds=10.0,
        )


def test_create_vendor_client_uses_no_op_rate_limiter_when_disabled() -> None:
    settings = make_settings()

    with (
        patch("python_integration_service.composition.HttpxTransport"),
        patch("python_integration_service.composition.NoOpRateLimiter") as no_op_class,
        create_vendor_client(settings) as client,
    ):
        assert client.rate_limiter is no_op_class.return_value

    no_op_class.assert_called_once_with()


def test_create_vendor_client_configures_token_bucket_rate_limiter() -> None:
    settings = Settings(
        vendor_base_url=AnyHttpUrl("https://api.example.com"),
        vendor_access_token=SecretStr("test-token"),
        vendor_timeout=15.0,
        vendor_retry_max_attempts=4,
        vendor_retry_base_delay=0.75,
        vendor_retry_max_retry_after_seconds=120.0,
        vendor_retry_budget_seconds=None,
        vendor_rate_limit_requests_per_second=2.5,
        vendor_rate_limit_capacity=10,
    )

    with (
        patch("python_integration_service.composition.HttpxTransport"),
        patch(
            "python_integration_service.composition.TokenBucketRateLimiter"
        ) as limiter_class,
        create_vendor_client(settings) as client,
    ):
        limiter_class.assert_called_once_with(
            requests_per_second=2.5,
            capacity=10,
        )
        assert client.rate_limiter is limiter_class.return_value


def test_create_vendor_client_exits_transport_context() -> None:
    settings = make_settings()

    with patch(
        "python_integration_service.composition.HttpxTransport"
    ) as transport_class:
        with create_vendor_client(settings):
            pass

        transport_class.return_value.__exit__.assert_called_once()


def test_create_vendor_client_exits_transport_context_on_exception() -> None:
    settings = make_settings()

    with patch(
        "python_integration_service.composition.HttpxTransport"
    ) as transport_class:
        with (
            pytest.raises(RuntimeError, match="boom"),
            create_vendor_client(settings),
        ):
            raise RuntimeError("boom")

        transport_class.return_value.__exit__.assert_called_once()
