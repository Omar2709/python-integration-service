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
    InvalidUpstreamResponseError,
    MappingError,
    RateLimitError,
    UpstreamConnectionError,
    UpstreamServerError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from python_integration_service.integrations.vendor_client import VendorClient
from python_integration_service.integrations.vendor_schemas import (
    ItemsPage,
    VendorCategory,
    VendorItem,
    VendorItemAttributes,
    VendorStatus,
)


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


def test_get_vendor_items_returns_first_page_by_default(
    test_app: FastAPI,
    vendor_client: MagicMock,
) -> None:
    vendor_client.get_items_page.return_value = ItemsPage(
        items=[
            VendorItem(
                id=1,
                attributes=VendorItemAttributes(
                    display_name="  Item 1  ",
                    category=VendorCategory.HARDWARE,
                ),
                status=VendorStatus.ENABLED,
            )
        ],
        next_page=2,
    )

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "items": [
            {
                "id": 1,
                "name": "Item 1",
                "category": "hardware",
                "active": True,
            }
        ],
        "next_page": 2,
    }

    vendor_client.get_items_page.assert_called_once_with(page=1)


def test_get_vendor_items_returns_mapping_error_for_unsupported_category(
    test_app: FastAPI,
    vendor_client: MagicMock,
) -> None:
    vendor_client.get_items_page.return_value = ItemsPage(
        items=[
            VendorItem(
                id=42,
                attributes=VendorItemAttributes(
                    display_name="Bundle",
                    category=VendorCategory.BUNDLE,
                ),
                status=VendorStatus.ENABLED,
            )
        ],
        next_page=None,
    )

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.json() == {
        "code": "upstream_mapping_error",
        "detail": (
            "The upstream data could not be adapted to the public API contract."
        ),
    }

    vendor_client.get_items_page.assert_called_once_with(page=1)


def test_get_vendor_items_requests_selected_page(
    test_app: FastAPI,
    vendor_client: MagicMock,
) -> None:
    vendor_client.get_items_page.return_value = ItemsPage(
        items=[],
        next_page=None,
    )

    with TestClient(test_app) as client:
        response = client.get("/vendor/items?page=3")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "items": [],
        "next_page": None,
    }

    vendor_client.get_items_page.assert_called_once_with(page=3)


@pytest.mark.parametrize(
    "page",
    [
        0,
        -1,
    ],
)
def test_get_vendor_items_rejects_invalid_page_query(
    test_app: FastAPI,
    vendor_client: MagicMock,
    page: int,
) -> None:
    with TestClient(test_app) as client:
        response = client.get(
            "/vendor/items",
            params={"page": page},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    vendor_client.get_items_page.assert_not_called()


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
            InvalidUpstreamResponseError("provider payload failed internal validation"),
            status.HTTP_502_BAD_GATEWAY,
            "upstream_invalid_response",
            "The upstream service returned an invalid response.",
        ),
        (
            MappingError("internal mapping failed"),
            status.HTTP_502_BAD_GATEWAY,
            "upstream_mapping_error",
            ("The upstream data could not be adapted to the public API contract."),
        ),
        (
            RateLimitError(
                "provider rate limit exceeded",
                retry_after_seconds=30.0,
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
    vendor_client.get_items_page.side_effect = integration_exception

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == expected_status
    assert response.json() == {
        "code": expected_code,
        "detail": expected_detail,
    }

    assert str(integration_exception) not in response.text

    vendor_client.get_items_page.assert_called_once_with(page=1)


def test_rate_limit_error_exposes_retry_after_seconds(
    test_app: FastAPI,
    vendor_client: MagicMock,
) -> None:
    vendor_client.get_items_page.side_effect = RateLimitError(
        "provider rate limit exceeded",
        retry_after_seconds=30.0,
    )

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["Retry-After"] == "30"


def test_rate_limit_error_rounds_retry_after_up(
    test_app: FastAPI,
    vendor_client: MagicMock,
) -> None:
    vendor_client.get_items_page.side_effect = RateLimitError(
        "provider rate limit exceeded",
        retry_after_seconds=30.2,
    )

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["Retry-After"] == "31"


def test_rate_limit_error_exposes_zero_retry_after(
    test_app: FastAPI,
    vendor_client: MagicMock,
) -> None:
    vendor_client.get_items_page.side_effect = RateLimitError(
        "provider rate limit exceeded",
        retry_after_seconds=0.0,
    )

    with TestClient(test_app) as client:
        response = client.get("/vendor/items")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["Retry-After"] == "0"


def test_rate_limit_error_omits_missing_retry_after(
    test_app: FastAPI,
    vendor_client: MagicMock,
) -> None:
    vendor_client.get_items_page.side_effect = RateLimitError(
        "provider rate limit exceeded",
        retry_after_seconds=None,
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


def test_vendor_endpoint_documents_paginated_success_response(
    test_app: FastAPI,
) -> None:
    openapi = test_app.openapi()

    response_schema = openapi["paths"]["/vendor/items"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]

    assert response_schema == {
        "$ref": "#/components/schemas/ItemsPageResponse",
    }
