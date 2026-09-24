import httpx
import pytest

from python_integration_service.integrations.exceptions import (
    AuthenticationError,
    IntegrationError,
    RateLimitError,
    TransientIntegrationError,
)
from python_integration_service.integrations.httpx_transport import HttpxTransport


def test_get_returns_json_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.headers["Accept"] == "application/json"

        return httpx.Response(
            200,
            json={
                "id": 123,
                "name": "Alice",
            },
        )

    with HttpxTransport(
        access_token="test-token",
        timeout=10.0,
        transport=httpx.MockTransport(handler),
    ) as transport:
        result = transport.get("https://api.vendor.test/customers/123")

    assert result == {
        "id": 123,
        "name": "Alice",
    }


def test_401_raises_authentication_error_with_http_status_cause() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"detail": "invalid token"},
        )

    with (
        HttpxTransport(
            access_token="test-token",
            timeout=10.0,
            transport=httpx.MockTransport(handler),
        ) as transport,
        pytest.raises(AuthenticationError) as exc_info,
    ):
        transport.get("https://api.vendor.test/customers/123")

    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)


def test_429_preserves_retry_after_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "30"},
            json={"detail": "too many requests"},
        )

    with (
        HttpxTransport(
            access_token="test-token",
            timeout=10.0,
            transport=httpx.MockTransport(handler),
        ) as transport,
        pytest.raises(RateLimitError) as exc_info,
    ):
        transport.get("https://api.vendor.test/customers/123")

    assert exc_info.value.retry_after == "30"


def test_timeout_raises_transient_integration_error_with_timeout_cause() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(
            "Read operation timed out",
            request=request,
        )

    with (
        HttpxTransport(
            access_token="test-token",
            timeout=10.0,
            transport=httpx.MockTransport(handler),
        ) as transport,
        pytest.raises(TransientIntegrationError) as exc_info,
    ):
        transport.get("https://api.vendor.test/customers/123")

    assert isinstance(exc_info.value.__cause__, httpx.ReadTimeout)


def test_connect_error_raises_transient_integration_error_with_connect_cause() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "Could not connect",
            request=request,
        )

    with (
        HttpxTransport(
            access_token="test-token",
            timeout=10.0,
            transport=httpx.MockTransport(handler),
        ) as transport,
        pytest.raises(TransientIntegrationError) as exc_info,
    ):
        transport.get("https://api.vendor.test/customers/123")

    assert isinstance(exc_info.value.__cause__, httpx.ConnectError)


def test_read_error_raises_transient_integration_error_with_read_cause() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadError(
            "Connection interrupted while reading response",
            request=request,
        )

    with (
        HttpxTransport(
            access_token="test-token",
            timeout=10.0,
            transport=httpx.MockTransport(handler),
        ) as transport,
        pytest.raises(TransientIntegrationError) as exc_info,
    ):
        transport.get("https://api.vendor.test/customers/123")

    assert isinstance(exc_info.value.__cause__, httpx.ReadError)


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
def test_transient_http_statuses_raise_transient_integration_error(
    status_code: int,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            json={"detail": "temporary upstream failure"},
        )

    with (
        HttpxTransport(
            access_token="test-token",
            timeout=10.0,
            transport=httpx.MockTransport(handler),
        ) as transport,
        pytest.raises(TransientIntegrationError) as exc_info,
    ):
        transport.get("https://api.vendor.test/customers/123")

    assert isinstance(
        exc_info.value.__cause__,
        httpx.HTTPStatusError,
    )


@pytest.mark.parametrize("status_code", [403, 404])
def test_permanent_http_statuses_raise_integration_error(
    status_code: int,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            json={"detail": "request cannot be fulfilled"},
        )

    with (
        HttpxTransport(
            access_token="test-token",
            timeout=10.0,
            transport=httpx.MockTransport(handler),
        ) as transport,
        pytest.raises(IntegrationError),
    ):
        transport.get("https://api.vendor.test/customers/123")
