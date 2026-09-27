from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from python_integration_service.api.errors import register_exception_handlers
from python_integration_service.api.vendor import router
from python_integration_service.dependencies import get_vendor_client
from python_integration_service.integrations.exceptions import (
    AuthenticationError,
    IntegrationError,
    RateLimitError,
    UpstreamConnectionError,
    UpstreamServerError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from python_integration_service.integrations.vendor_client import VendorClient


@pytest.fixture
def vendor_client() -> MagicMock:
    return MagicMock(spec=VendorClient)


@pytest.fixture
def test_app(vendor_client: MagicMock) -> FastAPI:
    app = FastAPI()

    app.include_router(router)
    register_exception_handlers(app)

    app.dependency_overrides[get_vendor_client] = lambda: vendor_client

    return app


def test_get_vendor_items_returns_vendor_response(
    test_app: FastAPI,
    vendor_client: MagicMock,
) -> None:
    vendor_client.get.return_value = {
        "items": [
            {
                "id": 1,
                "name": "Item 1",
            },
        ]
    }

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "items": [
            {
                "id": 1,
                "name": "Item 1",
            },
        ]
    }

    vendor_client.get.assert_called_once_with("/items")


@pytest.mark.parametrize(
    (
        "integration_exception",
        "expected_status",
        "expected_code",
        "expected_detail",
    ),
    [
        (
            AuthenticationError("provider rejected credentials"),
            status.HTTP_502_BAD_GATEWAY,
            "upstream_authentication_error",
            "The upstream service could not authenticate the request.",
        ),
        (
            RateLimitError(
                "provider rate limit exceeded",
                retry_after="30",
            ),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "upstream_rate_limited",
            "The upstream service is temporarily rate limited.",
        ),
        (
            UpstreamTimeoutError(
                "request timed out while calling internal upstream URL"
            ),
            status.HTTP_504_GATEWAY_TIMEOUT,
            "upstream_timeout",
            "The upstream service did not respond in time.",
        ),
        (
            UpstreamConnectionError("network connection to internal upstream failed"),
            status.HTTP_502_BAD_GATEWAY,
            "upstream_connection_error",
            "The upstream service could not be reached.",
        ),
        (
            UpstreamServerError("external provider returned HTTP 500"),
            status.HTTP_502_BAD_GATEWAY,
            "upstream_server_error",
            "The upstream service failed to process the request.",
        ),
        (
            UpstreamUnavailableError("external provider returned HTTP 503"),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "upstream_unavailable",
            "The upstream service is temporarily unavailable.",
        ),
        (
            IntegrationError("unexpected internal integration failure"),
            status.HTTP_502_BAD_GATEWAY,
            "upstream_integration_error",
            "The upstream service could not complete the request.",
        ),
    ],
)
def test_integration_errors_are_translated_to_public_http_responses(
    test_app: FastAPI,
    vendor_client: MagicMock,
    integration_exception: IntegrationError,
    expected_status: int,
    expected_code: str,
    expected_detail: str,
) -> None:
    vendor_client.get.side_effect = integration_exception

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == expected_status
    assert response.json() == {
        "code": expected_code,
        "detail": expected_detail,
    }

    assert str(integration_exception) not in response.text

    vendor_client.get.assert_called_once_with("/items")


def test_rate_limit_error_preserves_valid_retry_after_seconds(
    test_app: FastAPI,
    vendor_client: MagicMock,
) -> None:
    vendor_client.get.side_effect = RateLimitError(
        "provider rate limit exceeded",
        retry_after="30",
    )

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["Retry-After"] == "30"


def test_rate_limit_error_preserves_valid_retry_after_http_date(
    test_app: FastAPI,
    vendor_client: MagicMock,
) -> None:
    retry_after = "Fri, 31 Dec 1999 23:59:59 GMT"

    vendor_client.get.side_effect = RateLimitError(
        "provider rate limit exceeded",
        retry_after=retry_after,
    )

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["Retry-After"] == retry_after


@pytest.mark.parametrize(
    "retry_after",
    [
        None,
        "",
        "   ",
        "-10",
        "bananas",
    ],
)
def test_rate_limit_error_omits_invalid_retry_after(
    test_app: FastAPI,
    vendor_client: MagicMock,
    retry_after: str | None,
) -> None:
    vendor_client.get.side_effect = RateLimitError(
        "provider rate limit exceeded",
        retry_after=retry_after,
    )

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Retry-After" not in response.headers


def test_vendor_endpoint_documents_integration_error_responses(
    test_app: FastAPI,
) -> None:
    openapi = test_app.openapi()

    responses = openapi["paths"]["/vendor/items"]["get"]["responses"]

    assert "502" in responses
    assert "503" in responses
    assert "504" in responses

    error_schema = {
        "$ref": "#/components/schemas/ErrorResponse",
    }

    assert responses["502"]["content"]["application/json"]["schema"] == error_schema
    assert responses["503"]["content"]["application/json"]["schema"] == error_schema
    assert responses["504"]["content"]["application/json"]["schema"] == error_schema
